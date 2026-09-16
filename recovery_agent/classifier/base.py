"""Base interface for contract-scope classifiers."""
from abc import ABC, abstractmethod
from recovery_agent.models.finding import UnbilledCandidate, ClassificationResult
from recovery_agent.models.contract import Contract
from recovery_agent.models.agency import TeamMember


class BaseScopeClassifier(ABC):
    """Abstract base class for scope classifiers."""

    @abstractmethod
    def classify(
        self,
        candidate: UnbilledCandidate,
        contract: Contract,
        team_member: TeamMember,
    ) -> ClassificationResult:
        """Classify whether a candidate unbilled activity is contractually billable."""
        pass
