"""Activity normalizer converting raw inputs into canonical NormalizedActivity."""
from typing import List, Optional, Dict
from recovery_agent.models.activity import (
    CalendarEvent,
    EmailThread,
    ProjectTask,
    NormalizedActivity,
    SourceType,
)
from recovery_agent.models.agency import TeamMember, Client


class ActivityNormalizer:
    """Harmonizes calendar events, emails, and tasks into NormalizedActivity objects."""

    def __init__(self, team_members: List[TeamMember], clients: List[Client]):
        self.team_members_by_id: Dict[str, TeamMember] = {m.member_id: m for m in team_members}
        self.team_members_by_email: Dict[str, TeamMember] = {m.email.lower(): m for m in team_members}
        self.clients_by_id: Dict[str, Client] = {c.client_id: c for c in clients}
        self.clients_by_domain: Dict[str, Client] = {
            c.domain.lower(): c for c in clients if c.domain
        }

    def normalize_calendar(self, event: CalendarEvent) -> NormalizedActivity:
        member = None
        if event.team_member_id and event.team_member_id in self.team_members_by_id:
            member = self.team_members_by_id[event.team_member_id]
        elif event.organizer.lower() in self.team_members_by_email:
            member = self.team_members_by_email[event.organizer.lower()]
        else:
            for att in event.attendees:
                if att.lower() in self.team_members_by_email:
                    member = self.team_members_by_email[att.lower()]
                    break

        member_id = member.member_id if member else (event.team_member_id or "UNKNOWN")
        member_name = member.name if member else "Unknown Member"
        member_email = member.email if member else event.organizer

        client = None
        if event.client_id and event.client_id in self.clients_by_id:
            client = self.clients_by_id[event.client_id]
        else:
            for att in event.attendees + [event.organizer]:
                domain = att.split("@")[-1].lower() if "@" in att else ""
                if domain in self.clients_by_domain:
                    client = self.clients_by_domain[domain]
                    break

        external = [
            e for e in event.attendees + [event.organizer]
            if not e.lower().endswith("@meridiandigital.io")
        ]

        return NormalizedActivity(
            activity_id=f"NORM-{event.event_id}",
            source_type=SourceType.CALENDAR,
            raw_id=event.event_id,
            timestamp_start=event.start_time,
            timestamp_end=event.end_time,
            duration_hours=event.duration_hours,
            team_member_id=member_id,
            team_member_name=member_name,
            team_member_email=member_email,
            client_id=client.client_id if client else event.client_id,
            client_name=client.name if client else None,
            title_or_subject=event.title,
            description_or_snippet=event.description or "",
            attendee_emails=event.attendees,
            external_participants=list(set(external)),
            metadata={"meeting_link": event.meeting_link, "location": event.location},
        )

    def normalize_email(self, thread: EmailThread) -> NormalizedActivity:
        member = None
        if thread.team_member_id and thread.team_member_id in self.team_members_by_id:
            member = self.team_members_by_id[thread.team_member_id]
        elif thread.sender.lower() in self.team_members_by_email:
            member = self.team_members_by_email[thread.sender.lower()]

        member_id = member.member_id if member else (thread.team_member_id or "UNKNOWN")
        member_name = member.name if member else "Unknown Member"
        member_email = member.email if member else thread.sender

        client = None
        if thread.client_id and thread.client_id in self.clients_by_id:
            client = self.clients_by_id[thread.client_id]
        else:
            for email in [thread.sender] + thread.recipients:
                domain = email.split("@")[-1].lower() if "@" in email else ""
                if domain in self.clients_by_domain:
                    client = self.clients_by_domain[domain]
                    break

        external = [
            e for e in [thread.sender] + thread.recipients + thread.cc
            if not e.lower().endswith("@meridiandigital.io")
        ]

        return NormalizedActivity(
            activity_id=f"NORM-{thread.thread_id}",
            source_type=SourceType.EMAIL,
            raw_id=thread.thread_id,
            timestamp_start=thread.timestamp,
            timestamp_end=thread.timestamp,
            duration_hours=thread.estimated_effort_hours,
            team_member_id=member_id,
            team_member_name=member_name,
            team_member_email=member_email,
            client_id=client.client_id if client else thread.client_id,
            client_name=client.name if client else None,
            title_or_subject=thread.subject,
            description_or_snippet=thread.body_snippet,
            attendee_emails=thread.recipients,
            external_participants=list(set(external)),
            metadata={"is_urgent": thread.is_urgent},
        )

    def normalize_task(self, task: ProjectTask) -> NormalizedActivity:
        member = None
        if task.assignee_id and task.assignee_id in self.team_members_by_id:
            member = self.team_members_by_id[task.assignee_id]
        elif task.assignee_email.lower() in self.team_members_by_email:
            member = self.team_members_by_email[task.assignee_email.lower()]

        member_id = member.member_id if member else task.assignee_id
        member_name = member.name if member else "Unknown Assignee"
        member_email = member.email if member else task.assignee_email

        client = None
        if task.client_id and task.client_id in self.clients_by_id:
            client = self.clients_by_id[task.client_id]
        else:
            for c in self.clients_by_id.values():
                if task.project_key.upper() in c.client_id or c.name.lower().startswith(task.project_key.lower()):
                    client = c
                    break

        start_time = f"{task.logged_date}T09:00:00"
        end_time = task.completed_at or f"{task.logged_date}T17:00:00"

        return NormalizedActivity(
            activity_id=f"NORM-{task.task_id}",
            source_type=SourceType.TASK,
            raw_id=task.task_id,
            timestamp_start=start_time,
            timestamp_end=end_time,
            duration_hours=task.actual_hours,
            team_member_id=member_id,
            team_member_name=member_name,
            team_member_email=member_email,
            client_id=client.client_id if client else task.client_id,
            client_name=client.name if client else None,
            title_or_subject=task.title,
            description_or_snippet=task.description,
            attendee_emails=[],
            project_key=task.project_key,
            external_participants=[],
            metadata={"tags": task.tags, "status": task.status},
        )

    def normalize_all(self, raw_activities) -> List[NormalizedActivity]:
        results = []
        for cal in raw_activities.calendar:
            results.append(self.normalize_calendar(cal))
        for eml in raw_activities.emails:
            results.append(self.normalize_email(eml))
        for tsk in raw_activities.tasks:
            results.append(self.normalize_task(tsk))
        return results
