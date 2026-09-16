"""Contract-Scope Classifier Guardrail orchestrating 3-stage validation."""
from typing import List, Dict, Optional
from recovery_agent.classifier.base import BaseScopeClassifier
from recovery_agent.classifier.mock_classifier import MockScopeClassifier
from recovery_agent.classifier.ai_client import GroqScopeClassifier
from recovery_agent.models.finding import (
    UnbilledCandidate,
    ClassificationResult,
    ClassificationStatus,
)
from recovery_agent.models.contract import Contract
from recovery_agent.models.agency import TeamMember


class ContractScopeClassifierGuardrail:
    """3-Stage Guardrail protecting against false positives:
    Stage 1: Deterministic Pre-Filters (Zero-cost internal/personal elimination)
    Stage 2: SOW Clause Matching & Legal Grounding (Groq LLM / Mock Engine)
    Stage 3: Confidence Score Routing (FLAGGED >= 0.85, REVIEW 0.60-0.84, FILTERED < 0.60)
    """

    def __init__(
        self,
        contracts: Dict[str, Contract],
        team_members: List[TeamMember],
        classifier: Optional[BaseScopeClassifier] = None,
        use_mock: bool = False,
    ):
        self.contracts = contracts
        self.team_members_by_id = {m.member_id: m for m in team_members}
        if use_mock:
            self.classifier = MockScopeClassifier()
        elif classifier:
            self.classifier = classifier
        else:
            self.classifier = GroqScopeClassifier()

    def evaluate_candidates(
        self, candidates: List[UnbilledCandidate]
    ) -> List[ClassificationResult]:
        results: List[ClassificationResult] = []

        for cand in candidates:
            act = cand.activity
            member = self.team_members_by_id.get(act.team_member_id)

            # Resolve contract
            contract = None
            if act.client_id:
                contract = self.contracts.get(act.client_id)

            # Run classifier through 3-stage pipeline
            res = self.classifier.classify(cand, contract, member)
            results.append(res)

        return results
