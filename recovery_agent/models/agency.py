"""Domain models for Agency, Team Members, Clients, and Rate Cards."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RateCard(BaseModel):
    """Standard billing rate card definition for agency roles."""
    model_config = ConfigDict(extra="ignore")

    role: str = Field(..., description="Role title, e.g. Senior DevOps Lead")
    hourly_rate: float = Field(..., description="Standard hourly billing rate in USD", ge=0.0)
    description: Optional[str] = Field(None, description="Scope and level description")
    specialist_rate: Optional[float] = Field(None, description="Out-of-hours or specialist surcharge rate")


class TeamMember(BaseModel):
    """Individual agency staff member / consultant."""
    model_config = ConfigDict(extra="ignore")

    member_id: str = Field(..., description="Unique staff identifier, e.g. EMP-001")
    full_name: str = Field(..., description="Full legal/display name")
    primary_role: str = Field(..., description="Primary functional role")
    email: str = Field(..., description="Corporate email address")
    billable_rate: float = Field(..., description="Hourly billable rate in USD", ge=0.0)
    active_client_assignments: List[str] = Field(default_factory=list, description="Client IDs or client names assigned")
    skills: List[str] = Field(default_factory=list, description="Technical competencies")
    is_active: bool = Field(default=True, description="Active employment status")

    @property
    def name(self) -> str:
        return self.full_name

    @property
    def hourly_rate(self) -> float:
        return self.billable_rate

    @property
    def role(self) -> str:
        return self.primary_role


class Client(BaseModel):
    """Client organization receiving agency services."""
    model_config = ConfigDict(extra="ignore")

    client_id: str = Field(..., description="Unique client identifier, e.g. CLI-001")
    name: str = Field(..., description="Company name, e.g. Apex Health")
    industry: str = Field(..., description="Industry domain or context")
    primary_contact_name: Optional[str] = Field(None, description="Client sponsor / stakeholder")
    primary_contact_email: Optional[str] = Field(None, description="Client stakeholder email")
    billing_domain: Optional[str] = Field(None, description="Primary external email domain, e.g. apexhealth.io")
    allowed_domains: List[str] = Field(default_factory=list, description="All valid participant domains for client")
    default_rate: Optional[float] = Field(None, description="Default hourly billing rate in USD")
    minimum_increment_minutes: int = Field(default=15, description="Minimum billing increment in minutes (15, 30)")
    notes: Optional[str] = Field(None, description="Operational notes")

    @property
    def domain(self) -> Optional[str]:
        return self.billing_domain


class Agency(BaseModel):
    """Profile and configuration for the consulting agency."""
    model_config = ConfigDict(extra="ignore")

    agency_id: str = Field(default="MD-001", description="Agency unique ID")
    name: str = Field(default="Meridian Digital Inc.", description="Company name")
    headcount: int = Field(default=50, description="Total employee headcount")
    domains: List[str] = Field(default_factory=lambda: ["meridiandigital.io"], description="Corporate email domains")
    offices: List[str] = Field(default_factory=lambda: ["New York", "London"], description="Office locations")
    contact_email: str = Field(default="ops@meridiandigital.io", description="Operations contact email")
    default_currency: str = Field(default="USD", description="Billing currency")
    rate_cards: List[RateCard] = Field(default_factory=list, description="Standard agency rate cards")
    clients: List[Client] = Field(default_factory=list, description="Client portfolio")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Operational configurations")
