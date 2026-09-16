"""Domain models package exporting all entities for Meridian Digital and the Recovery Agent."""

from recovery_agent.models.agency import Agency, Client, RateCard, TeamMember
from recovery_agent.models.contract import BillingModel, Contract, SOWClause
from recovery_agent.models.activity import (
    CalendarEvent,
    EmailThread,
    NormalizedActivity,
    ProjectTask,
    SourceType,
)
from recovery_agent.models.timesheet import TimesheetEntry
from recovery_agent.models.finding import (
    ClassificationResult,
    ClassificationStatus,
    UnbilledCandidate,
)

__all__ = [
    # Agency
    "Agency",
    "TeamMember",
    "Client",
    "RateCard",
    # Contract
    "Contract",
    "SOWClause",
    "BillingModel",
    # Activity
    "CalendarEvent",
    "EmailThread",
    "ProjectTask",
    "NormalizedActivity",
    "SourceType",
    # Timesheet
    "TimesheetEntry",
    # Finding
    "UnbilledCandidate",
    "ClassificationResult",
    "ClassificationStatus",
]
