"""Temporal reconciler matching activities against timesheets and detecting unbilled gaps."""
from typing import List, Dict
from recovery_agent.models.activity import NormalizedActivity
from recovery_agent.models.timesheet import TimesheetEntry
from recovery_agent.models.finding import UnbilledCandidate


class TemporalReconciler:
    """Matches activities against timesheets by employee, client, date, and description."""

    def __init__(self, timesheets: List[TimesheetEntry]):
        self.timesheets = timesheets
        # Index timesheets by (member_id, client_id, date)
        self.timesheet_index: Dict[tuple, List[TimesheetEntry]] = {}
        for ts in timesheets:
            key = (ts.member_id, ts.client_id, ts.date)
            if key not in self.timesheet_index:
                self.timesheet_index[key] = []
            self.timesheet_index[key].append(ts)

    def reconcile(self, activities: List[NormalizedActivity]) -> List[UnbilledCandidate]:
        candidates: List[UnbilledCandidate] = []
        counter = 1

        for act in activities:
            date_str = act.timestamp_start.split("T")[0]
            # Key for employee on that date
            key = (act.team_member_id, act.client_id, date_str)
            matching_ts = self.timesheet_index.get(key, [])

            total_logged_hours = sum(t.hours for t in matching_ts)

            # Check if this specific activity was logged
            activity_logged = False
            for ts in matching_ts:
                # Semantic / keyword overlap check
                act_words = set(act.title_or_subject.lower().split())
                ts_words = set(ts.notes.lower().split())
                overlap = len(act_words.intersection(ts_words))
                if overlap >= 2 or ts.hours >= act.duration_hours:
                    activity_logged = True
                    break

            # If no timesheet or hours logged is zero or activity was unlogged
            if not matching_ts or not activity_logged or total_logged_hours == 0:
                unbilled_h = act.duration_hours
                candidates.append(
                    UnbilledCandidate(
                        candidate_id=f"CAN-{counter:03d}",
                        activity=act,
                        unbilled_hours=unbilled_h,
                        logged_hours_found=total_logged_hours,
                        discrepancy_reason=(
                            f"Zero matching timesheet entries logged on {date_str} for "
                            f"{act.team_member_name} ({act.duration_hours}h work detected)"
                        ),
                        client_id=act.client_id,
                    )
                )
                counter += 1

        return candidates
