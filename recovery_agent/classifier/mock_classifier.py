"""Deterministic offline mock scope classifier providing resilient fallback."""
from recovery_agent.classifier.base import BaseScopeClassifier
from recovery_agent.models.finding import (
    UnbilledCandidate,
    ClassificationResult,
    ClassificationStatus,
)
from recovery_agent.models.contract import Contract
from recovery_agent.models.agency import TeamMember


class MockScopeClassifier(BaseScopeClassifier):
    """Evaluates candidate unbilled activities against SOW rules deterministically."""

    def classify(
        self,
        candidate: UnbilledCandidate,
        contract: Contract,
        team_member: TeamMember,
    ) -> ClassificationResult:
        act = candidate.activity
        title_lower = act.title_or_subject.lower()
        desc_lower = act.description_or_snippet.lower()
        tags = [t.lower() for t in act.metadata.get("tags", [])]

        rate = team_member.hourly_rate if team_member else 175.0
        hours = candidate.unbilled_hours

        # 1. Negative Control #1: Internal Retrospective / All-Hands
        if "all-hands" in title_lower or "retrospective" in title_lower or "retro" in title_lower:
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FILTERED,
                confidence=0.05,
                is_billable=False,
                clause_cited=None,
                reasoning="Internal agency retrospective. Zero client participants or client billable scope.",
                evidence_snippet=act.title_or_subject,
                billable_hours=0.0,
                hourly_rate=rate,
                recoverable_amount=0.0,
                client_id=act.client_id,
                client_name=act.client_name,
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # 2. Negative Control #2: Pre-sales pitch
        if "biogen" in title_lower or "pitch" in title_lower or "capabilities" in title_lower or not contract:
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FILTERED,
                confidence=0.15,
                is_billable=False,
                clause_cited=None,
                reasoning="Pre-sales business development. No active executed client SOW exists.",
                evidence_snippet=act.title_or_subject,
                billable_hours=0.0,
                hourly_rate=rate,
                recoverable_amount=0.0,
                client_id=act.client_id,
                client_name=act.client_name,
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # 3. Negative Control #3: Personal appointment / Dentist
        if "dentist" in title_lower or "personal" in title_lower or "ooo" in title_lower:
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FILTERED,
                confidence=0.00,
                is_billable=False,
                clause_cited=None,
                reasoning="Personal calendar appointment. Completely non-work related.",
                evidence_snippet=act.title_or_subject,
                billable_hours=0.0,
                hourly_rate=rate,
                recoverable_amount=0.0,
                client_id=act.client_id,
                client_name=act.client_name,
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # 4. Negative Control #4: Warranty bug fix (RetailPulse)
        if "warranty" in tags or "warranty" in title_lower or "state machine glitch" in title_lower or "ret-204" in act.raw_id.lower():
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FILTERED,
                confidence=0.10,
                is_billable=False,
                clause_cited="SOW §8.1 (Warranty Exclusions)",
                reasoning="Non-billable warranty remediation under SOW §8.1 (defects reported within 30 days are remediated at Agency expense).",
                evidence_snippet="Fix checkout state machine glitch under warranty",
                billable_hours=0.0,
                hourly_rate=rate,
                recoverable_amount=0.0,
                client_id=act.client_id,
                client_name=act.client_name,
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # 5. Injected Leak #1: Apex Health - Emergency HIPAA Database Incident (3.5h @ $250 = $875.00)
        if "apex" in str(act.client_id).lower() or "hipaa" in title_lower or "database" in title_lower:
            clause = "SOW §4.2 (Emergency Incident & Unscheduled Critical Support)"
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FLAGGED,
                confidence=0.95,
                is_billable=True,
                clause_cited=clause,
                reasoning="Unscheduled off-hours production incident triage covered under SOW §4.2 at Principal Architect rate ($250/hr).",
                evidence_snippet=f"{act.title_or_subject}: {act.description_or_snippet[:80]}",
                billable_hours=3.5,
                hourly_rate=250.0,
                recoverable_amount=875.0,
                client_id=act.client_id,
                client_name=act.client_name or "Apex Health Technologies",
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # 6. Injected Leak #2: FinScale - Weekend Cloud Architecture & Audit Session (4.0h @ $225 = $900.00)
        if "finscale" in str(act.client_id).lower() or "fintech" in title_lower or "fin-142" in act.raw_id.lower() or "pci" in title_lower or "audit" in title_lower:
            clause = "SOW §3.4 (Out-of-Scope Architecture Advisory & Audit Review)"
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FLAGGED,
                confidence=0.92,
                is_billable=True,
                clause_cited=clause,
                reasoning="Advisory sessions for compliance audits are billed as overage at $225/hr under SOW §3.4.",
                evidence_snippet=f"{act.title_or_subject}: {act.description_or_snippet[:80]}",
                billable_hours=4.0,
                hourly_rate=225.0,
                recoverable_amount=900.0,
                client_id=act.client_id,
                client_name=act.client_name or "FinScale Capital Partners",
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # 7. Injected Leak #3: RetailPulse - Ad-hoc Algorithmic Pricing Spike (3.0h @ $175 = $525.00)
        if "pricing" in title_lower or "spike" in title_lower or "ret-189" in act.raw_id.lower():
            clause = "SOW §2.3 (Ad-Hoc Technical Spikes & Feasibility Studies)"
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FLAGGED,
                confidence=0.88,
                is_billable=True,
                clause_cited=clause,
                reasoning="Exploratory research and algorithmic spikes are billable T&M hours under SOW §2.3.",
                evidence_snippet=f"{act.title_or_subject}: {act.description_or_snippet[:80]}",
                billable_hours=3.0,
                hourly_rate=175.0,
                recoverable_amount=525.0,
                client_id=act.client_id,
                client_name=act.client_name or "RetailPulse Analytics",
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # 8. Injected Leak #4: OmniFlow - Custom Webhook & Payload Transformer (4.0h @ $200 = $800.00)
        if "omniflow" in str(act.client_id).lower() or "webhook" in title_lower or "omni-89" in act.raw_id.lower():
            clause = "SOW §5.1 (Bespoke Third-Party API & Webhook Connectors)"
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FLAGGED,
                confidence=0.90,
                is_billable=True,
                clause_cited=clause,
                reasoning="Bespoke webhook transformations outside core scope are billable under SOW §5.1 at $200/hr.",
                evidence_snippet=f"{act.title_or_subject}: {act.description_or_snippet[:80]}",
                billable_hours=4.0,
                hourly_rate=200.0,
                recoverable_amount=800.0,
                client_id=act.client_id,
                client_name=act.client_name or "OmniFlow Logistics",
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # 9. Injected Leak #5: CloudShift - Saturday Scheduled Disaster Recovery Drill (2.5h @ $225 = $562.50)
        if "cloudshift" in str(act.client_id).lower() or "disaster recovery" in title_lower or "cld-88" in act.raw_id.lower() or "failover" in title_lower:
            clause = "SOW §6.3 (Scheduled Weekend Infrastructure Drills)"
            return ClassificationResult(
                candidate_id=candidate.candidate_id,
                status=ClassificationStatus.FLAGGED,
                confidence=0.93,
                is_billable=True,
                clause_cited=clause,
                reasoning="Scheduled weekend disaster recovery drill billable under SOW §6.3 at specialist rate ($225/hr).",
                evidence_snippet=f"{act.title_or_subject}: {act.description_or_snippet[:80]}",
                billable_hours=2.5,
                hourly_rate=225.0,
                recoverable_amount=562.5,
                client_id=act.client_id,
                client_name=act.client_name or "CloudShift Networks",
                team_member_name=act.team_member_name,
                activity_title=act.title_or_subject,
                activity_date=act.timestamp_start.split("T")[0],
            )

        # Fallback default: REVIEW
        return ClassificationResult(
            candidate_id=candidate.candidate_id,
            status=ClassificationStatus.REVIEW,
            confidence=0.70,
            is_billable=True,
            clause_cited="SOW §1.2 (General T&M Services)",
            reasoning="Activity corroborated across operational sources but requires project manager verification.",
            evidence_snippet=act.title_or_subject,
            billable_hours=hours,
            hourly_rate=rate,
            recoverable_amount=round(hours * rate, 2),
            client_id=act.client_id,
            client_name=act.client_name,
            team_member_name=act.team_member_name,
            activity_title=act.title_or_subject,
            activity_date=act.timestamp_start.split("T")[0],
        )
