"""Domain models for Raw Activities (Calendar, Email, Project Task) and Normalized Activity."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """Source stream classification for activity signals."""
    CALENDAR = "calendar"
    EMAIL = "email"
    TASK = "task"


class CalendarEvent(BaseModel):
    """Calendar meeting or scheduled invite."""
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(..., description="Unique calendar invite ID, e.g. CAL-001")
    title: str = Field(..., description="Meeting title / summary")
    start_time: str = Field(..., description="Start timestamp in ISO 8601 string, e.g. 2026-08-14T20:00:00")
    end_time: str = Field(..., description="End timestamp in ISO 8601 string, e.g. 2026-08-14T23:30:00")
    duration_hours: float = Field(..., description="Calculated duration in decimal hours", ge=0.0)
    organizer: str = Field(..., description="Organizer email address")
    attendees: List[str] = Field(default_factory=list, description="Participant email addresses")
    description: Optional[str] = Field(None, description="Calendar description or agenda notes")
    meeting_link: Optional[str] = Field(None, description="Video conference URL")
    is_recurring: bool = Field(default=False, description="Whether event is part of a recurring series")
    location: Optional[str] = Field(None, description="Meeting location or room")
    client_id: Optional[str] = Field(None, description="Identified or matched client ID")
    team_member_id: Optional[str] = Field(None, description="Internal staff member associated")


class EmailThread(BaseModel):
    """Email correspondence or customer thread metadata."""
    model_config = ConfigDict(extra="ignore")

    thread_id: str = Field(..., description="Unique email thread ID, e.g. EML-001")
    subject: str = Field(..., description="Subject line")
    sender: str = Field(..., description="Sender email address")
    recipients: List[str] = Field(default_factory=list, description="Direct recipient emails")
    cc: List[str] = Field(default_factory=list, description="Carbon copy recipient emails")
    timestamp: str = Field(..., description="Message sent timestamp in ISO 8601 format")
    body_snippet: str = Field(..., description="Excerpt of email message body")
    estimated_effort_hours: float = Field(default=0.5, description="Estimated effort spent on email communication", ge=0.0)
    client_id: Optional[str] = Field(None, description="Identified or matched client ID")
    team_member_id: Optional[str] = Field(None, description="Internal staff member associated")
    is_urgent: bool = Field(default=False, description="Whether marked urgent or high priority")


class ProjectTask(BaseModel):
    """Jira/Asana project ticket, sprint task, or bug remediation."""
    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(..., description="Unique task identifier, e.g. FIN-142")
    project_key: str = Field(..., description="Client or project code, e.g. FIN, APX, RET")
    title: str = Field(..., description="Task title or user story")
    description: str = Field(..., description="Detailed task requirements and acceptance criteria")
    assignee_id: str = Field(..., description="Team member ID assigned, e.g. EMP-002")
    assignee_email: str = Field(..., description="Assignee corporate email")
    status: str = Field(..., description="Workflow status, e.g. Completed, In Progress")
    logged_date: str = Field(..., description="Task completion or execution date (YYYY-MM-DD)")
    completed_at: Optional[str] = Field(None, description="Timestamp of task completion")
    estimated_hours: float = Field(default=0.0, description="Original estimated hours", ge=0.0)
    actual_hours: float = Field(..., description="Actual effort spent in decimal hours", ge=0.0)
    client_id: Optional[str] = Field(None, description="Associated client ID")
    tags: List[str] = Field(default_factory=list, description="Labels and tags (e.g. warranty, spike, webhook)")


class NormalizedActivity(BaseModel):
    """Canonical harmonized activity schema across all source types."""
    model_config = ConfigDict(extra="ignore")

    activity_id: str = Field(..., description="Unique normalized activity identifier, e.g. ACT-001")
    source_type: SourceType = Field(..., description="Original stream source")
    raw_id: str = Field(..., description="Identifier in originating source system")
    timestamp_start: str = Field(..., description="Activity start timestamp in ISO format")
    timestamp_end: str = Field(..., description="Activity end timestamp in ISO format")
    duration_hours: float = Field(..., description="Calculated duration in decimal hours", ge=0.0)
    team_member_id: str = Field(..., description="Internal staff member ID")
    team_member_name: str = Field(..., description="Full name of staff member")
    team_member_email: str = Field(..., description="Email address of staff member")
    client_id: Optional[str] = Field(None, description="Matched client ID, if any")
    client_name: Optional[str] = Field(None, description="Matched client name, if any")
    title_or_subject: str = Field(..., description="Unified title or subject line")
    description_or_snippet: str = Field(..., description="Unified description or body excerpt")
    attendee_emails: List[str] = Field(default_factory=list, description="All known participant emails")
    project_key: Optional[str] = Field(None, description="Associated project code")
    external_participants: List[str] = Field(default_factory=list, description="Emails not in agency domains")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary source-specific metadata")
