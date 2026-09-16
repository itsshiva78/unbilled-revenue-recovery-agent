"""Data loader and validation module for Meridian Digital fixtures."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from recovery_agent.models.activity import CalendarEvent, EmailThread, ProjectTask
from recovery_agent.models.agency import Agency, TeamMember
from recovery_agent.models.contract import Contract
from recovery_agent.models.timesheet import TimesheetEntry


# Default path pointing to recovery_agent/data/fixtures
DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class RawActivities(BaseModel):
    """Container holding all un-normalized raw activities across sources."""
    model_config = ConfigDict(extra="ignore")

    calendar: List[CalendarEvent] = Field(default_factory=list, description="Raw calendar events")
    emails: List[EmailThread] = Field(default_factory=list, description="Raw email threads")
    tasks: List[ProjectTask] = Field(default_factory=list, description="Raw project tasks")

    def __getitem__(self, item: str) -> List[Any]:
        """Support dict-style subscripting: activities['calendar']."""
        if item in ("calendar", "calendar_events"):
            return self.calendar
        if item in ("emails", "email_threads"):
            return self.emails
        if item in ("tasks", "project_tasks"):
            return self.tasks
        raise KeyError(f"Unknown activity source: {item}")

    def total_count(self) -> int:
        """Return total count of raw activities across all streams."""
        return len(self.calendar) + len(self.emails) + len(self.tasks)


def _resolve_dir(fixtures_dir: Optional[Union[str, Path]]) -> Path:
    """Resolve and validate directory path."""
    target_dir = Path(fixtures_dir) if fixtures_dir is not None else DEFAULT_FIXTURES_DIR
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"Fixtures directory does not exist: {target_dir.resolve()}")
    return target_dir


def _read_json(file_path: Path) -> Any:
    """Read and parse a JSON file with descriptive error handling."""
    if not file_path.exists():
        raise FileNotFoundError(f"Required fixture file not found: {file_path.resolve()}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupted JSON in fixture file {file_path.name}: {e}") from e


def load_agency(fixtures_dir: Optional[Union[str, Path]] = None) -> Agency:
    """Load and validate the Agency profile and settings from agency.json.

    Args:
        fixtures_dir: Optional custom path to fixtures directory.

    Returns:
        Validated Agency Pydantic model.
    """
    path = _resolve_dir(fixtures_dir) / "agency.json"
    raw_data = _read_json(path)
    try:
        return Agency.model_validate(raw_data)
    except ValidationError as e:
        raise ValueError(f"Schema validation error loading agency profile from {path.name}: {e}") from e


def load_team_members(fixtures_dir: Optional[Union[str, Path]] = None) -> List[TeamMember]:
    """Load and validate all staff members from team_members.json.

    Args:
        fixtures_dir: Optional custom path to fixtures directory.

    Returns:
        List of validated TeamMember Pydantic models.
    """
    path = _resolve_dir(fixtures_dir) / "team_members.json"
    raw_data = _read_json(path)
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path.name}, got {type(raw_data).__name__}")
    try:
        return [TeamMember.model_validate(item) for item in raw_data]
    except ValidationError as e:
        raise ValueError(f"Schema validation error loading team members from {path.name}: {e}") from e


def load_contracts(fixtures_dir: Optional[Union[str, Path]] = None) -> Dict[str, Contract]:
    """Load and validate signed client SOW contracts from contracts.json.

    Returns a dictionary mapping both client_id (e.g. 'CLI-001') and
    contract_id (e.g. 'CTR-APX-2026') to the validated Contract model.

    Args:
        fixtures_dir: Optional custom path to fixtures directory.

    Returns:
        Dictionary mapping client_id / contract_id to Contract models.
    """
    path = _resolve_dir(fixtures_dir) / "contracts.json"
    raw_data = _read_json(path)
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path.name}, got {type(raw_data).__name__}")

    class ContractsDict(dict):
        def __getitem__(self, key):
            if key in self:
                return super().__getitem__(key)
            for c in self.values():
                if getattr(c, "contract_id", None) == key:
                    return c
            raise KeyError(key)

        def get(self, key, default=None):
            try:
                return self[key]
            except KeyError:
                return default

    contracts_dict = ContractsDict()
    try:
        for item in raw_data:
            contract = Contract.model_validate(item)
            contracts_dict[contract.client_id] = contract
        return contracts_dict
    except ValidationError as e:
        raise ValueError(f"Schema validation error loading contracts from {path.name}: {e}") from e


def load_raw_activities(fixtures_dir: Optional[Union[str, Path]] = None) -> RawActivities:
    """Load and validate multi-source activities (calendar, emails, tasks).

    Args:
        fixtures_dir: Optional custom path to fixtures directory.

    Returns:
        RawActivities container with calendar, emails, and tasks.
    """
    base_dir = _resolve_dir(fixtures_dir)

    cal_path = base_dir / "calendar.json"
    email_path = base_dir / "emails.json"
    task_path = base_dir / "tasks.json"

    raw_cal = _read_json(cal_path)
    raw_emails = _read_json(email_path)
    raw_tasks = _read_json(task_path)

    try:
        cal_events = [CalendarEvent.model_validate(item) for item in raw_cal]
    except ValidationError as e:
        raise ValueError(f"Validation error in {cal_path.name}: {e}") from e

    try:
        email_threads = [EmailThread.model_validate(item) for item in raw_emails]
    except ValidationError as e:
        raise ValueError(f"Validation error in {email_path.name}: {e}") from e

    try:
        project_tasks = [ProjectTask.model_validate(item) for item in raw_tasks]
    except ValidationError as e:
        raise ValueError(f"Validation error in {task_path.name}: {e}") from e

    return RawActivities(
        calendar=cal_events,
        emails=email_threads,
        tasks=project_tasks,
    )


def load_timesheets(fixtures_dir: Optional[Union[str, Path]] = None) -> List[TimesheetEntry]:
    """Load and validate timesheet entries from timesheets.json.

    Args:
        fixtures_dir: Optional custom path to fixtures directory.

    Returns:
        List of validated TimesheetEntry Pydantic models.
    """
    path = _resolve_dir(fixtures_dir) / "timesheets.json"
    raw_data = _read_json(path)
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {path.name}, got {type(raw_data).__name__}")
    try:
        return [TimesheetEntry.model_validate(item) for item in raw_data]
    except ValidationError as e:
        raise ValueError(f"Schema validation error loading timesheets from {path.name}: {e}") from e


def load_all_fixtures(fixtures_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load and strictly validate all sample dataset fixtures in one call.

    Args:
        fixtures_dir: Optional custom path to fixtures directory.

    Returns:
        Dictionary containing agency, team_members, contracts, activities, timesheets.
    """
    base_dir = _resolve_dir(fixtures_dir)
    return {
        "agency": load_agency(base_dir),
        "team_members": load_team_members(base_dir),
        "contracts": load_contracts(base_dir),
        "activities": load_raw_activities(base_dir),
        "timesheets": load_timesheets(base_dir),
    }
