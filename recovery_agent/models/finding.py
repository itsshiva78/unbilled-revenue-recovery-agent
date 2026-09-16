"""Domain models for Unbilled Candidates, Classification Results, and Statuses."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from recovery_agent.models.activity import NormalizedActivity


class ClassificationStatus(str, Enum):
    """Routing and classification status for candidate leaks."""
    FLAGGED = "FLAGGED"    # Score >= 0.85: Confirmed billable leak for recovery
    REVIEW = "REVIEW"      # Score 0.60 - 0.84: Ambiguous or borderline, requires PM review
    FILTERED = "FILTERED"  # Score < 0.60: Internal, personal, or excluded non-billable


class UnbilledCandidate(BaseModel):
    """Candidate unbilled activity detected by reconciliation engine."""
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(..., description="Unique candidate identifier, e.g. CAN-001")
    activity: NormalizedActivity = Field(..., description="Underlying normalized activity")
    unbilled_hours: float = Field(..., description="Calculated unbilled hours delta", ge=0.0)
    logged_hours_found: float = Field(default=0.0, description="Hours logged in timesheets for this date/client", ge=0.0)
    discrepancy_reason: str = Field(..., description="Explanation of why candidate was generated")
    client_id: Optional[str] = Field(None, description="Matched client ID")
    contract_id: Optional[str] = Field(None, description="Associated SOW or Contract ID")

    @property
    def team_member_id(self) -> str:
        return self.activity.team_member_id


class ClassificationResult(BaseModel):
    """Guardrail evaluation result for an unbilled candidate."""
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(..., description="Referenced candidate identifier")
    status: ClassificationStatus = Field(..., description="Classification routing status")
    confidence: float = Field(..., description="Evidence confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    is_billable: bool = Field(..., description="Whether the work is contractually billable")
    clause_cited: Optional[str] = Field(None, description="Verbatim SOW clause reference, e.g. SOW §4.2")
    reasoning: str = Field(..., description="Detailed grounding rationale and legal/operational justification")
    evidence_snippet: str = Field(default="", description="Verbatim quote or excerpt from activity serving as evidence")
    billable_hours: float = Field(..., description="Billable hours recommended", ge=0.0)
    hourly_rate: float = Field(..., description="Applicable staff hourly rate in USD", ge=0.0)
    recoverable_amount: float = Field(..., description="Total recoverable dollars (billable_hours * hourly_rate)", ge=0.0)
    client_id: Optional[str] = Field(None, description="Associated client ID")
    client_name: Optional[str] = Field(None, description="Associated client name")
    team_member_name: Optional[str] = Field(None, description="Staff member who performed the work")
    activity_title: Optional[str] = Field(None, description="Title of the detected activity")
    activity_date: Optional[str] = Field(None, description="Date of the detected activity (YYYY-MM-DD)")

    @property
    def confidence_score(self) -> float:
        """Alias for confidence score for backward compatibility."""
        return self.confidence

    @property
    def classification_bucket(self) -> ClassificationStatus:
        """Alias for classification status for backward compatibility."""
        return self.status
