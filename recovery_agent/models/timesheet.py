"""Domain model for Timesheet entries logged in Harvest, Toggl, or similar systems."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TimesheetEntry(BaseModel):
    """Single recorded timesheet entry representing logged time."""
    model_config = ConfigDict(extra="ignore")

    entry_id: str = Field(..., description="Unique timesheet identifier, e.g. TS-001")
    date: str = Field(..., description="Calendar date of logged work (YYYY-MM-DD)")
    team_member_id: str = Field(..., description="Staff member ID who logged time, e.g. EMP-001")
    team_member_name: Optional[str] = Field(None, description="Full name of staff member")
    client_id: str = Field(..., description="Client identifier billed, e.g. CLI-001")
    client_name: Optional[str] = Field(None, description="Client display name")
    project_id: Optional[str] = Field(None, description="Project code or identifier")
    hours: float = Field(..., description="Decimal hours recorded", ge=0.0)
    notes: str = Field(default="", description="Descriptive memo or notes logged by staff")
    is_billable: bool = Field(default=True, description="Whether marked billable in the timesheet tool")
    hourly_rate: Optional[float] = Field(None, description="Hourly rate applied on this entry")
    task_category: Optional[str] = Field(None, description="Task category, e.g. Development, Advisory, Meeting")

    @property
    def member_id(self) -> str:
        return self.team_member_id
