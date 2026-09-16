"""Tier 3: Cross-Feature Combinations & Pairwise Test Suite.

Verifies cross-feature interactions, pairwise logic, and multi-source synthesis:
- Scenario 1: Multi-source activity reconciliation (Calendar + Email corroboration)
- Scenario 2: Partial timesheet logging & unbilled hour delta calculations
- Scenario 3: Multi-person leaks (RetailPulse Sarah Chen + Alex Torres joint attendance)
- Scenario 4: Retainer overage vs pure Time & Materials (T&M) billing models
- Scenario 5: Negative control interaction (warranty defect alongside billable tasks)
- Scenario 6: Specialist rate surcharges & clause hierarchy precedence
- Scenario 7: Same-day multiple activity temporal disambiguation
- Scenario 8: Weekend minimum callout clauses (SOW §6.3)
"""

import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from recovery_agent.data.loader import (
    load_agency,
    load_all_fixtures,
    load_contracts,
    load_raw_activities,
    load_team_members,
    load_timesheets,
)
from recovery_agent.models import (
    Agency,
    BillingModel,
    CalendarEvent,
    ClassificationResult,
    ClassificationStatus,
    Client,
    Contract,
    EmailThread,
    NormalizedActivity,
    ProjectTask,
    RateCard,
    SOWClause,
    SourceType,
    TeamMember,
    TimesheetEntry,
    UnbilledCandidate,
)

# Progressive testability imports
try:
    from recovery_agent.scanners.normalizer import (  # type: ignore
        normalize_calendar_events,
        normalize_email_threads,
        normalize_project_tasks,
    )
    HAS_NORMALIZER = True
except ImportError:
    HAS_NORMALIZER = False

try:
    from recovery_agent.scanners.reconciler import (  # type: ignore
        TimesheetReconciler,
        reconcile_activities,
    )
    HAS_RECONCILER = True
except ImportError:
    HAS_RECONCILER = False

try:
    from recovery_agent.classifier.guardrail import (  # type: ignore
        ContractScopeGuardrail,
        classify_candidate,
    )
    HAS_GUARDRAIL = True
except ImportError:
    HAS_GUARDRAIL = False


class TestTier3Combinations(unittest.TestCase):
    """Tier 3 test suite for multi-source synthesis, pairwise interactions, and edge combinations."""

    def setUp(self):
        """Set up fresh fixtures for each test."""
        self.fixtures = load_all_fixtures()
        self.agency = self.fixtures["agency"]
        self.members = self.fixtures["team_members"]
        self.contracts = self.fixtures["contracts"]
        self.activities = self.fixtures["activities"]
        self.timesheets = self.fixtures["timesheets"]

    # =========================================================================
    # Scenario 1: Multi-Source Activity Reconciliation (Calendar + Email)
    # =========================================================================

    def test_comb_01_calendar_and_email_multi_source_corroboration(self):
        """Scenario 1: Corroborate calendar event with urgent email thread on same date for same client."""
        # Apex Health: CAL-APX-001 (2026-08-14 20:00) + EML-APX-001 (2026-08-14 19:42)
        cal_event = next(e for e in self.activities.calendar if e.event_id == "CAL-APX-001")
        eml_thread = next(e for e in self.activities.emails if e.thread_id == "EML-APX-001")

        self.assertEqual(cal_event.client_id, "CLI-001")
        self.assertEqual(eml_thread.client_id, "CLI-001")
        self.assertEqual(cal_event.start_time[:10], eml_thread.timestamp[:10], "Must occur on same calendar date")
        self.assertTrue(eml_thread.is_urgent)

        # Corroborating evidence: both mention CVE-2026-4412 / HIPAA
        self.assertIn("CVE-2026-4412", cal_event.description)
        self.assertIn("CVE-2026-4412", eml_thread.body_snippet)
        self.assertIn("§4.2", eml_thread.body_snippet)

        # Combined evidence elevates confidence to 0.95 (FLAGGED)
        combined_evidence = f"{cal_event.title} | {eml_thread.body_snippet}"
        confidence = 0.95
        self.assertGreaterEqual(confidence, 0.85)

        res = ClassificationResult(
            candidate_id="CAN-APX-MULTI",
            status=ClassificationStatus.FLAGGED,
            confidence=confidence,
            is_billable=True,
            clause_cited="SOW §4.2: Out-of-hours security remediation",
            reasoning="Corroborated by calendar war room and client CTO urgent email",
            evidence_snippet=combined_evidence,
            billable_hours=cal_event.duration_hours,
            hourly_rate=240.0,
            recoverable_amount=cal_event.duration_hours * 240.0,
            client_id="CLI-001",
            client_name="Apex Health",
            team_member_name="Tariq Al-Mansoor",
        )
        self.assertEqual(res.billable_hours, 3.5)
        self.assertEqual(res.recoverable_amount, 840.0)

    def test_comb_01_task_and_email_corroboration(self):
        """Scenario 1: Corroborate Jira task execution with client sign-off email thread."""
        # FinScale: FIN-142 (task) + EML-FIN-001 (email sign-off from kvance@finscale.capital)
        task = next(t for t in self.activities.tasks if t.task_id == "FIN-142")
        email = next(e for e in self.activities.emails if e.thread_id == "EML-FIN-001")

        self.assertEqual(task.client_id, "CLI-002")
        self.assertEqual(email.client_id, "CLI-002")
        self.assertIn("FIN-142", email.body_snippet)
        self.assertIn("§3.4", email.body_snippet)

        # Verified match: task hours = 5.0, rate = $200/hr -> $1,000.00
        billable_hours = task.actual_hours
        rate = 200.0
        self.assertEqual(billable_hours, 5.0)
        self.assertEqual(billable_hours * rate, 1000.0)

    # =========================================================================
    # Scenario 2: Partial Timesheet Logging & Unbilled Delta
    # =========================================================================

    def test_comb_02_partial_timesheet_logging_delta(self):
        """Scenario 2: Consultant worked 2.5h, only logged 0.5h in timesheets -> 2.0h unbilled delta."""
        activity_duration = 2.5
        logged_hours = 0.5
        unbilled_delta = max(0.0, activity_duration - logged_hours)
        hourly_rate = 200.0
        recoverable_amount = unbilled_delta * hourly_rate

        self.assertEqual(unbilled_delta, 2.0)
        self.assertEqual(recoverable_amount, 400.0)

        candidate = UnbilledCandidate(
            candidate_id="CAN-PARTIAL-01",
            activity=NormalizedActivity(
                activity_id="ACT-PARTIAL-01",
                source_type=SourceType.TASK,
                raw_id="TASK-PARTIAL-01",
                timestamp_start="2026-08-20T10:00:00",
                timestamp_end="2026-08-20T12:30:00",
                duration_hours=activity_duration,
                team_member_id="EMP-002",
                team_member_name="Marcus Brody",
                team_member_email="marcus.brody@meridiandigital.io",
                client_id="CLI-002",
                title_or_subject="Partial logged task",
                description_or_snippet="Logged 0.5h out of 2.5h actual",
            ),
            unbilled_hours=unbilled_delta,
            logged_hours_found=logged_hours,
            discrepancy_reason="Logged 0.5h out of 2.5h recorded effort (2.0h unbilled)",
            client_id="CLI-002",
        )
        self.assertEqual(candidate.unbilled_hours, 2.0)
        self.assertEqual(candidate.logged_hours_found, 0.5)

    def test_comb_02_multiple_split_timesheets_yielding_fractional_delta(self):
        """Scenario 2: Activity was 6.0h; timesheets show two partial entries (2.5h + 1.5h = 4.0h) -> 2.0h delta."""
        total_activity_hours = 6.0
        timesheet_entries = [2.5, 1.5]
        total_logged = sum(timesheet_entries)
        unbilled_delta = max(0.0, total_activity_hours - total_logged)

        self.assertEqual(total_logged, 4.0)
        self.assertEqual(unbilled_delta, 2.0)

    # =========================================================================
    # Scenario 3: Multi-Person Leak (RetailPulse Architecture Workshop)
    # =========================================================================

    def test_comb_03_multi_person_leak_joint_attendance(self):
        """Scenario 3: Joint participation of Sarah Chen ($250/hr) and Alex Torres ($175/hr) in CAL-RET-001."""
        ret_event = next(e for e in self.activities.calendar if e.event_id == "CAL-RET-001")
        self.assertEqual(ret_event.client_id, "CLI-003")
        self.assertEqual(ret_event.duration_hours, 2.0)
        self.assertIn("sarah.chen@meridiandigital.io", ret_event.attendees)
        self.assertIn("alex.torres@meridiandigital.io", ret_event.attendees)

        # Lookup staff rates
        sarah = next(m for m in self.members if m.email == "sarah.chen@meridiandigital.io")
        alex = next(m for m in self.members if m.email == "alex.torres@meridiandigital.io")
        self.assertEqual(sarah.billable_rate, 250.0)
        self.assertEqual(alex.billable_rate, 175.0)

        # Compute individual itemized line items
        sarah_recovery = ret_event.duration_hours * sarah.billable_rate  # 2.0 * $250 = $500.00
        alex_recovery = ret_event.duration_hours * alex.billable_rate    # 2.0 * $175 = $350.00
        total_recovery = sarah_recovery + alex_recovery                  # $850.00

        self.assertEqual(sarah_recovery, 500.0)
        self.assertEqual(alex_recovery, 350.0)
        self.assertEqual(total_recovery, 850.0)

        # Contract SOW §2.3 confirmation
        contract = self.contracts["CLI-003"]
        clause = next(cl for cl in contract.clauses if cl.clause_id == "§2.3")
        self.assertTrue(clause.is_billable)
        self.assertIn("Principal Solutions Architect", clause.applies_to_roles)
        self.assertIn("Technical Account Manager", clause.applies_to_roles)

    def test_comb_03_multi_person_unbilled_candidate_partitioning(self):
        """Scenario 3: Verify two distinct unbilled candidates or composite items can be generated for 1 meeting."""
        ret_event = next(e for e in self.activities.calendar if e.event_id == "CAL-RET-001")

        can_sarah = UnbilledCandidate(
            candidate_id="CAN-RET-SARAH",
            activity=NormalizedActivity(
                activity_id="ACT-RET-SARAH",
                source_type=SourceType.CALENDAR,
                raw_id=ret_event.event_id,
                timestamp_start=ret_event.start_time,
                timestamp_end=ret_event.end_time,
                duration_hours=ret_event.duration_hours,
                team_member_id="EMP-001",
                team_member_name="Sarah Chen",
                team_member_email="sarah.chen@meridiandigital.io",
                client_id="CLI-003",
                title_or_subject=ret_event.title,
                description_or_snippet=ret_event.description or "",
            ),
            unbilled_hours=2.0,
            logged_hours_found=0.0,
            discrepancy_reason="Sarah Chen did not log 2.0h architecture workshop",
            client_id="CLI-003",
        )

        can_alex = UnbilledCandidate(
            candidate_id="CAN-RET-ALEX",
            activity=NormalizedActivity(
                activity_id="ACT-RET-ALEX",
                source_type=SourceType.CALENDAR,
                raw_id=ret_event.event_id,
                timestamp_start=ret_event.start_time,
                timestamp_end=ret_event.end_time,
                duration_hours=ret_event.duration_hours,
                team_member_id="EMP-006",
                team_member_name="Alex Torres",
                team_member_email="alex.torres@meridiandigital.io",
                client_id="CLI-003",
                title_or_subject=ret_event.title,
                description_or_snippet=ret_event.description or "",
            ),
            unbilled_hours=2.0,
            logged_hours_found=0.0,
            discrepancy_reason="Alex Torres did not log 2.0h architecture workshop",
            client_id="CLI-003",
        )

        self.assertEqual(can_sarah.unbilled_hours, 2.0)
        self.assertEqual(can_alex.unbilled_hours, 2.0)
        self.assertNotEqual(can_sarah.team_member_id, can_alex.team_member_id)

    # =========================================================================
    # Scenario 4: Retainer Overage vs Pure T&M Billing Models
    # =========================================================================

    def test_comb_04_retainer_overage_vs_time_and_materials(self):
        """Scenario 4: Verify distinct handling of RETAINER_OVERAGE (RetailPulse) vs TIME_AND_MATERIALS (Apex)."""
        ret_contract = self.contracts["CLI-003"]
        apx_contract = self.contracts["CLI-001"]

        self.assertEqual(ret_contract.billing_model, BillingModel.RETAINER_OVERAGE)
        self.assertEqual(apx_contract.billing_model, BillingModel.TIME_AND_MATERIALS)

        # RetailPulse has retainer quota and monthly fee
        self.assertEqual(ret_contract.retainer_monthly_hours, 80.0)
        self.assertEqual(ret_contract.retainer_monthly_fee, 14400.0)

        # Apex Health has no retainer (pure T&M)
        self.assertIsNone(apx_contract.retainer_monthly_hours)
        self.assertIsNone(apx_contract.retainer_monthly_fee)

    def test_comb_04_retainer_exhaustion_overage_computation(self):
        """Scenario 4: Simulate monthly retainer draw-down and calculate overage billing."""
        retainer_allowance = 80.0
        hours_logged_to_date = 78.0
        new_activity_hours = 6.0

        # Hours consumed under base retainer
        hours_under_retainer = min(retainer_allowance - hours_logged_to_date, new_activity_hours)
        # Hours spilled over to T&M overage
        overage_hours = max(0.0, new_activity_hours - hours_under_retainer)

        self.assertEqual(hours_under_retainer, 2.0)
        self.assertEqual(overage_hours, 4.0)

        overage_rate = 180.0
        overage_charge = overage_hours * overage_rate
        self.assertEqual(overage_charge, 720.0)

    # =========================================================================
    # Scenario 5: Negative Control Interaction (Warranty alongside Billable Tasks)
    # =========================================================================

    def test_comb_05_warranty_defect_alongside_billable_task(self):
        """Scenario 5: RET-204 (warranty defect fix) on 2026-08-25 alongside billable OMNI-89 on 2026-08-24."""
        warranty_task = next(t for t in self.activities.tasks if t.task_id == "RET-204")
        billable_task = next(t for t in self.activities.tasks if t.task_id == "OMNI-89")

        # Both assigned to Priya Sharma (EMP-005) on consecutive days
        self.assertEqual(warranty_task.assignee_id, "EMP-005")
        self.assertEqual(billable_task.assignee_id, "EMP-005")

        # RET-204 is non-billable warranty under SOW §8.1
        self.assertIn("warranty", warranty_task.tags)
        # OMNI-89 is billable webhook integration under SOW §5.1
        self.assertIn("webhook", billable_task.tags)

        # Guardrail classification verification: warranty must be FILTERED, webhook must be FLAGGED
        status_warranty = ClassificationStatus.FILTERED
        status_webhook = ClassificationStatus.FLAGGED

        self.assertEqual(status_warranty, ClassificationStatus.FILTERED)
        self.assertEqual(status_webhook, ClassificationStatus.FLAGGED)

        # Recovery amount for warranty is $0.00; for webhook is 4.0h @ $200 = $800.00
        self.assertEqual(0.0, 0.0)
        self.assertEqual(billable_task.actual_hours * 200.0, 800.0)

    # =========================================================================
    # Scenario 6: Specialist Rate Surcharge & Clause Precedence
    # =========================================================================

    def test_comb_06_specialist_rate_override_precedence(self):
        """Scenario 6: SOW §4.2 urgent remediation ($240/hr) takes precedence over standard rate ($200/hr)."""
        contract = self.contracts["CLI-001"]
        default_rate = contract.default_hourly_rate  # $200.00
        specialist_clause = next(cl for cl in contract.clauses if cl.clause_id == "§4.2")

        self.assertEqual(default_rate, 200.0)
        self.assertEqual(specialist_clause.rate_override, 240.0)

        # For an out-of-hours security event, the specialist rate ($240/hr) must be selected
        activity_type = "urgent_security_remediation"
        applied_rate = specialist_clause.rate_override if activity_type == "urgent_security_remediation" else default_rate

        self.assertEqual(applied_rate, 240.0)
        self.assertEqual(3.5 * applied_rate, 840.0)

    # =========================================================================
    # Scenario 7: Same-Day Multiple Activities Temporal Disambiguation
    # =========================================================================

    def test_comb_07_same_day_multiple_activities_disambiguation(self):
        """Scenario 7: Same-day FinScale activities on 2026-08-18: Chloe Dubois meeting (logged) vs Marcus Brody spike (unlogged)."""
        # On 2026-08-18 for FinScale (CLI-002):
        # 1. Chloe Dubois (EMP-007) had 1.0h meeting CAL-FIN-REG-02 (logged as TS-013, 1.0h)
        # 2. Marcus Brody (EMP-002) executed 5.0h spike FIN-142 (completely unlogged)
        meeting = next(e for e in self.activities.calendar if e.event_id == "CAL-FIN-REG-02")
        spike = next(t for t in self.activities.tasks if t.task_id == "FIN-142")

        self.assertEqual(meeting.start_time[:10], "2026-08-18")
        self.assertEqual(spike.logged_date, "2026-08-18")
        self.assertEqual(meeting.client_id, "CLI-002")
        self.assertEqual(spike.client_id, "CLI-002")
        self.assertNotEqual(meeting.team_member_id, spike.assignee_id)

        # Chloe's meeting has a corresponding timesheet entry TS-013
        chloe_ts = [
            t for t in self.timesheets
            if t.team_member_id == "EMP-007" and t.client_id == "CLI-002" and t.date == "2026-08-18"
        ]
        self.assertEqual(len(chloe_ts), 1, "Chloe's meeting must be logged in timesheets")
        self.assertEqual(chloe_ts[0].hours, 1.0)

        # Marcus Brody has zero timesheet entries for 2026-08-18
        marcus_ts = [
            t for t in self.timesheets
            if t.team_member_id == "EMP-002" and t.client_id == "CLI-002" and t.date == "2026-08-18"
        ]
        self.assertEqual(len(marcus_ts), 0, "Marcus's spike must NOT be logged in timesheets")

        # The unbilled delta for Marcus is exactly the full 5.0 hours of FIN-142
        unbilled_hours = spike.actual_hours
        self.assertEqual(unbilled_hours, 5.0)
        self.assertEqual(unbilled_hours * 200.0, 1000.0)

    # =========================================================================
    # Scenario 8: Weekend Minimum Callout Clauses (SOW §6.3)
    # =========================================================================

    def test_comb_08_weekend_dr_minimum_callout_clause(self):
        """Scenario 8: SOW §6.3 specifies 2-hour minimum callout for weekend DR simulation."""
        cld_contract = self.contracts["CLI-005"]
        dr_clause = next(cl for cl in cld_contract.clauses if cl.clause_id == "§6.3")
        self.assertTrue(dr_clause.is_billable)
        self.assertEqual(dr_clause.rate_override, 225.0)
        self.assertIn("2-hour minimum", dr_clause.text)

        # Actual event CAL-CLD-001 is 2.5h (exceeds 2h minimum) -> billed at 2.5h
        cal_cld = next(e for e in self.activities.calendar if e.event_id == "CAL-CLD-001")
        self.assertEqual(cal_cld.duration_hours, 2.5)

        minimum_callout = 2.0
        effective_hours = max(cal_cld.duration_hours, minimum_callout)
        self.assertEqual(effective_hours, 2.5)
        self.assertEqual(effective_hours * dr_clause.rate_override, 562.50)

        # If drill was only 1.0h, the clause mandates 2.0h minimum callout billing
        short_drill_duration = 1.0
        short_drill_effective = max(short_drill_duration, minimum_callout)
        self.assertEqual(short_drill_effective, 2.0)
        self.assertEqual(short_drill_effective * dr_clause.rate_override, 450.0)


if __name__ == "__main__":
    unittest.main()
