"""Domain models for Statements of Work (SOW), Contracts, and Billing Clauses."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BillingModel(str, Enum):
    """Contractual billing models recognized by the agency."""
    TIME_AND_MATERIALS = "TIME_AND_MATERIALS"
    RETAINER_OVERAGE = "RETAINER_OVERAGE"
    HOURLY_SPECIALIST = "HOURLY_SPECIALIST"


class SOWClause(BaseModel):
    """Granular Statement of Work (SOW) clause defining scope, rates, or exclusions."""
    model_config = ConfigDict(extra="ignore")

    clause_id: str = Field(..., description="Clause section reference, e.g. §4.2 or SOW §4.2")
    title: str = Field(..., description="Clause title, e.g. Out-of-Hours Security Remediation")
    text: str = Field(..., description="Verbatim legal text of the clause")
    is_billable: bool = Field(default=True, description="True for scoped billable work, False for warranty/exclusions")
    rate_override: Optional[float] = Field(None, description="Specific hourly rate applied under this clause")
    rate_multiplier: float = Field(default=1.0, description="Multiplier for standard rate (e.g. 1.5x for emergency)")
    keywords: List[str] = Field(default_factory=list, description="Keywords and triggers associated with clause")
    applies_to_roles: List[str] = Field(default_factory=list, description="Staff roles governed by this clause")


class Contract(BaseModel):
    """Signed Master Services Agreement (MSA) or Statement of Work (SOW)."""
    model_config = ConfigDict(extra="ignore")

    contract_id: str = Field(..., description="Unique contract identifier, e.g. SOW-APX-2026")
    client_id: str = Field(..., description="Referenced client identifier, e.g. CLI-001")
    client_name: str = Field(..., description="Client legal name")
    billing_model: BillingModel = Field(default=BillingModel.TIME_AND_MATERIALS, description="Billing model enum")
    start_date: str = Field(..., description="Contract effective start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Contract expiration or renewal date (YYYY-MM-DD)")
    is_active: bool = Field(default=True, description="Whether the contract is currently active")
    default_hourly_rate: float = Field(..., description="Baseline hourly rate in USD", ge=0.0)
    minimum_increment_minutes: int = Field(default=15, description="Minimum billing increment in minutes")
    specialist_rates: Dict[str, float] = Field(default_factory=dict, description="Role-specific hourly rates")
    retainer_monthly_hours: Optional[float] = Field(None, description="Base retainer hours included per month")
    retainer_monthly_fee: Optional[float] = Field(None, description="Fixed monthly retainer fee in USD")
    clauses: List[SOWClause] = Field(default_factory=list, description="Structured SOW clauses")
    inclusions_summary: Optional[str] = Field(None, description="Executive summary of scoped inclusions")
    exclusions_summary: Optional[str] = Field(None, description="Executive summary of express exclusions")

    @property
    def title(self) -> str:
        return f"{self.contract_id} ({self.client_name})"
