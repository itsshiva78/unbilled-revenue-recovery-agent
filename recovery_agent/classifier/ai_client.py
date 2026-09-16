"""Live AI client for Groq and Gemini with automatic fallback to mock classifier."""
import os
import json
import urllib.request
from typing import Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

from recovery_agent.classifier.base import BaseScopeClassifier
from recovery_agent.classifier.mock_classifier import MockScopeClassifier
from recovery_agent.models.finding import (
    UnbilledCandidate,
    ClassificationResult,
    ClassificationStatus,
)
from recovery_agent.models.contract import Contract
from recovery_agent.models.agency import TeamMember


class GroqScopeClassifier(BaseScopeClassifier):
    """Calls Groq API to evaluate SOW clauses with live LLM reasoning."""

    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-oss-20b"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        self.fallback = MockScopeClassifier()

    def classify(
        self,
        candidate: UnbilledCandidate,
        contract: Contract,
        team_member: TeamMember,
    ) -> ClassificationResult:
        if not self.api_key:
            return self.fallback.classify(candidate, contract, team_member)

        act = candidate.activity
        sow_clauses_text = ""
        if contract and hasattr(contract, "clauses"):
            for c in contract.clauses:
                sow_clauses_text += f"- {c.clause_id}: {c.title} -> {c.text}\n"

        prompt = f"""You are an elite Contract-Scope Auditor for a high-end digital agency.
Evaluate whether the following detected operational activity is contractually billable under the signed client SOW.

[CLIENT]
Name: {act.client_name or 'Unknown'}
Contract: {contract.title if contract else 'None'}
Billing Model: {contract.billing_model.value if contract else 'None'}

[SOW CLAUSES]
{sow_clauses_text or 'No specific clauses available.'}

[DETECTED OPERATIONAL ACTIVITY]
Source: {act.source_type.value}
Title: {act.title_or_subject}
Description: {act.description_or_snippet}
Staff Member: {act.team_member_name} ({team_member.role if team_member else 'Staff'}, Rate: ${team_member.hourly_rate if team_member else 175}/hr)
Duration: {candidate.unbilled_hours} hours
Date: {act.timestamp_start.split('T')[0]}

[RULES]
1. Internal meetings (all-hands, internal retros) and personal events are NEVER billable (status: FILTERED, confidence: 0.05).
2. Warranty bug fixes under 30 days are non-billable (status: FILTERED, confidence: 0.10).
3. Out-of-scope emergency support, weekend drills, or ad-hoc spikes with explicit SOW clauses are BILLABLE (status: FLAGGED, confidence: 0.85-0.95).
4. Return ONLY valid JSON.

JSON schema:
{{
  "is_billable": bool,
  "status": "FLAGGED" | "REVIEW" | "FILTERED",
  "confidence": float (0.0 to 1.0),
  "clause_cited": string or null,
  "reasoning": string
}}
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional legal auditor for B2B service contracts. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)

                status_val = parsed.get("status", "REVIEW").upper()
                status = ClassificationStatus[status_val] if status_val in ClassificationStatus.__members__ else ClassificationStatus.REVIEW
                confidence = float(parsed.get("confidence", 0.80))
                is_billable = bool(parsed.get("is_billable", True))
                clause = parsed.get("clause_cited")
                reasoning = parsed.get("reasoning", "Evaluated by Groq LLM.")

                rate = team_member.hourly_rate if team_member else 175.0
                billable_h = candidate.unbilled_hours if is_billable and status != ClassificationStatus.FILTERED else 0.0

                return ClassificationResult(
                    candidate_id=candidate.candidate_id,
                    status=status,
                    confidence=confidence,
                    is_billable=is_billable,
                    clause_cited=clause,
                    reasoning=f"[Groq {self.model}] {reasoning}",
                    evidence_snippet=act.title_or_subject,
                    billable_hours=billable_h,
                    hourly_rate=rate,
                    recoverable_amount=round(billable_h * rate, 2),
                    client_id=act.client_id,
                    client_name=act.client_name,
                    team_member_name=act.team_member_name,
                    activity_title=act.title_or_subject,
                    activity_date=act.timestamp_start.split("T")[0],
                )
        except Exception as e:
            # Resilient fallback to deterministic mock
            res = self.fallback.classify(candidate, contract, team_member)
            res.reasoning += f" (Note: Groq API fallback invoked due to: {type(e).__name__})"
            return res
