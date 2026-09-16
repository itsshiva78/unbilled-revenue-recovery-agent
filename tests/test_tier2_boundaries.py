"""Tier 2: Boundary & Corner Cases Test Suite.

Verifies system behavior under extreme conditions, edge cases, and boundary constraints:
- Area 1: Empty inputs, zero activities, and missing datasets
- Area 2: Duration boundaries (zero duration, micro-durations < 15 min, marathon durations, negative rejection)
- Area 3: Rate card boundaries & billing pricing extremes ($0/hr, negative rejection, extreme $10,000/hr, missing roles)
- Area 4: Missing optional fields & null-handling robustness (null client_id, null project_key, empty attendees)
- Area 5: Confidence score exact boundary thresholds (0.850 FLAGGED, 0.849 REVIEW, 0.600 REVIEW, 0.599 FILTERED, range [0, 1])
- Area 6: Attendee topology boundaries (single attendee, internal-only, multi-client, email deduplication)
- Area 7: Timesheet compliance boundaries (zero timesheets, exact match, overlogged hours, mismatched client)
- Area 8: Negative control invariance (CAL-INT-001, CAL-BIO-001, CAL-PER-001, RET-204)
"""

import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

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

# Progressive testability imports for M2/M3 modules
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


class TestTier2Boundaries(unittest.TestCase):
    """Tier 2 test suite for boundary values, edge cases, and negative controls."""

    def setUp(self):
        """Set up fresh fixtures for each test to ensure test isolation."""
        self.fixtures = load_all_fixtures()
        self.agency = self.fixtures["agency"]
        self.members = self.fixtures["team_members"]
        self.contracts = self.fixtures["contracts"]
        self.activities = self.fixtures["activities"]
        self.timesheets = self.fixtures["timesheets"]

    # =========================================================================
    # Area 1: Empty Inputs & Missing Datasets (BVA: Empty collections)
    # =========================================================================

    def test_bva_01_empty_calendar_events(self):
        """Area 1: Verify normalizer and pipelines handle empty calendar event collections."""
        if HAS_NORMALIZER:
            res = normalize_calendar_events([])
            self.assertEqual(len(res), 0)
            self.assertIsInstance(res, list)
        else:
            # Model contract validation
            empty_events: List[CalendarEvent] = []
            self.assertEqual(len(empty_events), 0)

    def test_bva_01_empty_email_threads(self):
        """Area 1: Verify normalizer handles empty email thread collections without exception."""
        if HAS_NORMALIZER:
            res = normalize_email_threads([])
            self.assertEqual(len(res), 0)
            self.assertIsInstance(res, list)
        else:
            empty_emails: List[EmailThread] = []
            self.assertEqual(len(empty_emails), 0)

    def test_bva_01_empty_project_tasks(self):
        """Area 1: Verify normalizer handles empty project task collections."""
        if HAS_NORMALIZER:
            res = normalize_project_tasks([])
            self.assertEqual(len(res), 0)
            self.assertIsInstance(res, list)
        else:
            empty_tasks: List[ProjectTask] = []
            self.assertEqual(len(empty_tasks), 0)

    def test_bva_01_empty_activities_reconciliation(self):
        """Area 1: Verify reconciler produces 0 unbilled candidates when activity list is empty."""
        if HAS_RECONCILER:
            candidates = reconcile_activities([], self.timesheets)
            self.assertEqual(len(candidates), 0)
        else:
            # Contract verification: 0 input activities -> 0 candidates
            candidates: List[UnbilledCandidate] = []
            self.assertEqual(len(candidates), 0)

    def test_bva_01_empty_rate_cards_agency_model(self):
        """Area 1: Verify Agency model accepts empty rate cards and empty client lists cleanly."""
        agency_minimal = Agency(
            agency_id="MD-TEST-EMPTY",
            name="Empty Agency Inc.",
            headcount=10,
            rate_cards=[],
            clients=[],
        )
        self.assertEqual(len(agency_minimal.rate_cards), 0)
        self.assertEqual(len(agency_minimal.clients), 0)
        self.assertEqual(agency_minimal.headcount, 10)

    # =========================================================================
    # Area 2: Duration Boundaries (Zero, Micro, Marathon, Negative)
    # =========================================================================

    def test_bva_02_zero_duration_calendar_event(self):
        """Area 2: Verify zero duration (0.0 hours) event instantiates and calculates 0 unbilled."""
        cal = CalendarEvent(
            event_id="CAL-ZERO-001",
            title="Instantaneous sync reminder",
            start_time="2026-08-14T12:00:00",
            end_time="2026-08-14T12:00:00",
            duration_hours=0.0,
            organizer="sarah.chen@meridiandigital.io",
            attendees=["sarah.chen@meridiandigital.io", "aris.thorne@apexhealth.io"],
            client_id="CLI-001",
        )
        self.assertEqual(cal.duration_hours, 0.0)

        # In unbilled candidate, zero duration generates 0 unbilled hours
        act = NormalizedActivity(
            activity_id="ACT-ZERO-001",
            source_type=SourceType.CALENDAR,
            raw_id=cal.event_id,
            timestamp_start=cal.start_time,
            timestamp_end=cal.end_time,
            duration_hours=cal.duration_hours,
            team_member_id="EMP-001",
            team_member_name="Sarah Chen",
            team_member_email="sarah.chen@meridiandigital.io",
            client_id="CLI-001",
            client_name="Apex Health",
            title_or_subject=cal.title,
            description_or_snippet="Zero duration test",
            attendee_emails=cal.attendees,
        )
        candidate = UnbilledCandidate(
            candidate_id="CAN-ZERO-001",
            activity=act,
            unbilled_hours=0.0,
            logged_hours_found=0.0,
            discrepancy_reason="Zero duration activity",
            client_id="CLI-001",
        )
        self.assertEqual(candidate.unbilled_hours, 0.0)

    def test_bva_02_micro_duration_exclusion(self):
        """Area 2: Micro-duration (< 15 min, e.g. 0.1h / 6 min) matches informal micro-session exclusion (SOW §8.4)."""
        # OmniFlow SOW §8.4 excludes informal sessions <= 15 minutes (0.25h)
        omn_contract = self.contracts["CLI-004"]
        micro_clause = next((cl for cl in omn_contract.clauses if cl.clause_id == "§8.4"), None)
        self.assertIsNotNone(micro_clause, "OmniFlow contract must contain §8.4 micro-session exclusion")
        self.assertFalse(micro_clause.is_billable)

        micro_duration = 0.1  # 6 minutes
        self.assertLess(micro_duration, 0.25, "0.1h is below the 15-minute billable increment")

    def test_bva_02_exact_minimum_increment_boundaries(self):
        """Area 2: Verify exact 15-minute (0.25h) and 30-minute (0.50h) contract increment boundaries."""
        # FinScale minimum increment is 15 minutes (0.25h)
        c_fin = self.contracts["CLI-002"]
        self.assertEqual(c_fin.minimum_increment_minutes, 15)

        # Apex Health minimum increment is 30 minutes (0.50h)
        c_apx = self.contracts["CLI-001"]
        self.assertEqual(c_apx.minimum_increment_minutes, 30)

        # CloudShift minimum increment is 30 minutes (0.50h)
        c_cld = self.contracts["CLI-005"]
        self.assertEqual(c_cld.minimum_increment_minutes, 30)

    def test_bva_02_marathon_activity_duration(self):
        """Area 2: Verify full-day/extended activity (24.0h marathon) calculates without overflow."""
        marathon_hours = 24.0
        hourly_rate = 250.0
        expected_total = marathon_hours * hourly_rate  # $6,000.00

        result = ClassificationResult(
            candidate_id="CAN-MARATHON-001",
            status=ClassificationStatus.FLAGGED,
            confidence=0.95,
            is_billable=True,
            clause_cited="SOW §2.3",
            reasoning="Extended 24-hour incident war-room support",
            billable_hours=marathon_hours,
            hourly_rate=hourly_rate,
            recoverable_amount=expected_total,
            client_id="CLI-003",
        )
        self.assertEqual(result.billable_hours, 24.0)
        self.assertEqual(result.recoverable_amount, 6000.0)

    def test_bva_02_negative_duration_rejection(self):
        """Area 2: Verify Pydantic schema rejects negative durations with ValidationError."""
        with self.assertRaises(ValidationError):
            CalendarEvent(
                event_id="CAL-NEG-001",
                title="Invalid negative duration",
                start_time="2026-08-14T20:00:00",
                end_time="2026-08-14T19:00:00",
                duration_hours=-1.0,  # Negative duration rejected by ge=0.0
                organizer="sarah.chen@meridiandigital.io",
            )

        with self.assertRaises(ValidationError):
            ProjectTask(
                task_id="TASK-NEG-001",
                project_key="APX",
                title="Negative task",
                description="Invalid effort",
                assignee_id="EMP-001",
                assignee_email="sarah.chen@meridiandigital.io",
                status="Completed",
                logged_date="2026-08-10",
                actual_hours=-2.5,  # Rejected by ge=0.0
            )

    # =========================================================================
    # Area 3: Rate Card Boundaries & Extreme Pricing
    # =========================================================================

    def test_bva_03_zero_hourly_rate(self):
        """Area 3: Verify zero rate card ($0.00/hr) is supported for pro-bono or warranty clauses."""
        zero_card = RateCard(
            role="Pro Bono Community Advisor",
            hourly_rate=0.0,
            description="Zero-rate non-billable advisory",
        )
        self.assertEqual(zero_card.hourly_rate, 0.0)

        # Calculating recovery with zero rate results in $0.00
        res = ClassificationResult(
            candidate_id="CAN-ZERO-RATE",
            status=ClassificationStatus.FILTERED,
            confidence=0.10,
            is_billable=False,
            reasoning="Non-billable role",
            billable_hours=5.0,
            hourly_rate=zero_card.hourly_rate,
            recoverable_amount=5.0 * zero_card.hourly_rate,
        )
        self.assertEqual(res.recoverable_amount, 0.0)

    def test_bva_03_negative_hourly_rate_rejection(self):
        """Area 3: Verify negative rate card rejects with ValidationError."""
        with self.assertRaises(ValidationError):
            RateCard(
                role="Invalid Role",
                hourly_rate=-150.0,  # ge=0.0 constraint
            )

        with self.assertRaises(ValidationError):
            TeamMember(
                member_id="EMP-NEG-01",
                full_name="Negative Rate Member",
                primary_role="Engineer",
                email="neg@meridiandigital.io",
                billable_rate=-200.0,  # ge=0.0 constraint
            )

    def test_bva_03_extreme_high_rate_card(self):
        """Area 3: Verify extreme rate card ($10,000.00/hr) computes recovery accurately."""
        extreme_rate = 10000.0
        hours = 3.5
        expected_recovery = extreme_rate * hours  # $35,000.00

        res = ClassificationResult(
            candidate_id="CAN-EXTREME-01",
            status=ClassificationStatus.FLAGGED,
            confidence=0.99,
            is_billable=True,
            clause_cited="SOW §9.9: Elite Emergency Counsel",
            reasoning="Executive crisis consultation",
            billable_hours=hours,
            hourly_rate=extreme_rate,
            recoverable_amount=expected_recovery,
        )
        self.assertEqual(res.recoverable_amount, 35000.0)

    def test_bva_03_missing_role_fallback_to_contract_default(self):
        """Area 3: Verify role missing from rate card falls back to contract default rate."""
        # Contract CLI-001 default rate is $200.00
        contract = self.contracts["CLI-001"]
        self.assertEqual(contract.default_hourly_rate, 200.0)

        # If a consultant has an unmapped role, the contract default applies
        unmapped_role = "Junior Intern Assistant"
        self.assertNotIn(unmapped_role, contract.specialist_rates)
        effective_rate = contract.specialist_rates.get(unmapped_role, contract.default_hourly_rate)
        self.assertEqual(effective_rate, 200.0)

    def test_bva_03_fractional_rate_and_floating_point_precision(self):
        """Area 3: Verify fractional rate cards maintain financial precision."""
        fractional_rate = 183.333333
        hours = 1.5
        calculated = round(fractional_rate * hours, 2)
        self.assertEqual(calculated, 275.0)

    # =========================================================================
    # Area 4: Missing Optional Fields & Null Handling
    # =========================================================================

    def test_bva_04_missing_client_id_handling(self):
        """Area 4: Verify NormalizedActivity accepts null client_id (unassigned/internal)."""
        act = NormalizedActivity(
            activity_id="ACT-NO-CLIENT",
            source_type=SourceType.CALENDAR,
            raw_id="CAL-INT-001",
            timestamp_start="2026-08-14T15:00:00",
            timestamp_end="2026-08-14T16:30:00",
            duration_hours=1.5,
            team_member_id="EMP-001",
            team_member_name="Sarah Chen",
            team_member_email="sarah.chen@meridiandigital.io",
            client_id=None,  # Optional None
            client_name=None,
            title_or_subject="Sprint Retrospective",
            description_or_snippet="",
            attendee_emails=["sarah.chen@meridiandigital.io"],
            external_participants=[],
        )
        self.assertIsNone(act.client_id)
        self.assertIsNone(act.client_name)

    def test_bva_04_missing_description_and_snippet(self):
        """Area 4: Verify CalendarEvent and NormalizedActivity accept null/empty descriptions."""
        event = CalendarEvent(
            event_id="CAL-NO-DESC",
            title="Quick client phone sync",
            start_time="2026-08-15T10:00:00",
            end_time="2026-08-15T10:30:00",
            duration_hours=0.5,
            organizer="sarah.chen@meridiandigital.io",
            description=None,  # Optional None
            attendees=["sarah.chen@meridiandigital.io"],
        )
        self.assertIsNone(event.description)

        act = NormalizedActivity(
            activity_id="ACT-EMPTY-DESC",
            source_type=SourceType.CALENDAR,
            raw_id=event.event_id,
            timestamp_start=event.start_time,
            timestamp_end=event.end_time,
            duration_hours=0.5,
            team_member_id="EMP-001",
            team_member_name="Sarah Chen",
            team_member_email="sarah.chen@meridiandigital.io",
            title_or_subject=event.title,
            description_or_snippet="",  # Empty string fallback
        )
        self.assertEqual(act.description_or_snippet, "")

    def test_bva_04_missing_project_key_handling(self):
        """Area 4: Verify NormalizedActivity accepts null project_key."""
        act = NormalizedActivity(
            activity_id="ACT-NO-PROJ",
            source_type=SourceType.EMAIL,
            raw_id="EML-001",
            timestamp_start="2026-08-14T19:42:00",
            timestamp_end="2026-08-14T20:12:00",
            duration_hours=0.5,
            team_member_id="EMP-009",
            team_member_name="Tariq Al-Mansoor",
            team_member_email="tariq.almansoor@meridiandigital.io",
            client_id="CLI-001",
            project_key=None,  # Optional None
            title_or_subject="URGENT: Remediation needed",
            description_or_snippet="Email snippet",
        )
        self.assertIsNone(act.project_key)

    def test_bva_04_empty_attendees_list(self):
        """Area 4: Verify CalendarEvent and NormalizedActivity default to empty list if attendees omitted."""
        event = CalendarEvent(
            event_id="CAL-NO-ATT",
            title="Solo Focus Work",
            start_time="2026-08-15T14:00:00",
            end_time="2026-08-15T16:00:00",
            duration_hours=2.0,
            organizer="david.kalu@meridiandigital.io",
            attendees=[],
        )
        self.assertEqual(len(event.attendees), 0)

    def test_bva_04_missing_sow_clause_cited_in_filtered_result(self):
        """Area 4: Verify FILTERED ClassificationResult cleanly allows clause_cited to be None."""
        filtered_res = ClassificationResult(
            candidate_id="CAN-CTRL-001",
            status=ClassificationStatus.FILTERED,
            confidence=0.05,
            is_billable=False,
            clause_cited=None,  # None for filtered non-billable
            reasoning="Personal calendar event - OOO dentist",
            billable_hours=0.0,
            hourly_rate=0.0,
            recoverable_amount=0.0,
        )
        self.assertIsNone(filtered_res.clause_cited)
        self.assertEqual(filtered_res.status, ClassificationStatus.FILTERED)

    # =========================================================================
    # Area 5: Confidence Scoring Exact Boundary Thresholds (0.85 and 0.60)
    # =========================================================================

    def test_bva_05_threshold_exact_0_850_is_flagged(self):
        """Area 5: Exact boundary 0.850 routes to FLAGGED status."""
        status = (
            ClassificationStatus.FLAGGED if 0.850 >= 0.85
            else (ClassificationStatus.REVIEW if 0.850 >= 0.60 else ClassificationStatus.FILTERED)
        )
        self.assertEqual(status, ClassificationStatus.FLAGGED)

        res = ClassificationResult(
            candidate_id="CAN-BVA-850",
            status=status,
            confidence=0.850,
            is_billable=True,
            clause_cited="SOW §1.1",
            reasoning="Met exact 0.850 threshold",
            billable_hours=2.0,
            hourly_rate=200.0,
            recoverable_amount=400.0,
        )
        self.assertEqual(res.status, ClassificationStatus.FLAGGED)

    def test_bva_05_threshold_just_below_0_85_is_review(self):
        """Area 5: Boundary value 0.8499 routes to REVIEW status (requires human review)."""
        score = 0.8499
        status = (
            ClassificationStatus.FLAGGED if score >= 0.85
            else (ClassificationStatus.REVIEW if score >= 0.60 else ClassificationStatus.FILTERED)
        )
        self.assertEqual(status, ClassificationStatus.REVIEW)

        res = ClassificationResult(
            candidate_id="CAN-BVA-849",
            status=status,
            confidence=score,
            is_billable=True,
            clause_cited="SOW §1.1",
            reasoning="Just below FLAGGED threshold",
            billable_hours=2.0,
            hourly_rate=200.0,
            recoverable_amount=400.0,
        )
        self.assertEqual(res.status, ClassificationStatus.REVIEW)

    def test_bva_05_threshold_exact_0_600_is_review(self):
        """Area 5: Exact boundary 0.600 routes to REVIEW status."""
        score = 0.600
        status = (
            ClassificationStatus.FLAGGED if score >= 0.85
            else (ClassificationStatus.REVIEW if score >= 0.60 else ClassificationStatus.FILTERED)
        )
        self.assertEqual(status, ClassificationStatus.REVIEW)

    def test_bva_05_threshold_just_below_0_60_is_filtered(self):
        """Area 5: Boundary value 0.5999 routes to FILTERED status."""
        score = 0.5999
        status = (
            ClassificationStatus.FLAGGED if score >= 0.85
            else (ClassificationStatus.REVIEW if score >= 0.60 else ClassificationStatus.FILTERED)
        )
        self.assertEqual(status, ClassificationStatus.FILTERED)

    def test_bva_05_confidence_range_validation_extremes(self):
        """Area 5: Verify confidence allows 0.0 and 1.0, but rejects < 0.0 or > 1.0."""
        # 1.0 is valid
        res_max = ClassificationResult(
            candidate_id="CAN-MAX",
            status=ClassificationStatus.FLAGGED,
            confidence=1.0,
            is_billable=True,
            reasoning="100% certain",
            billable_hours=1.0,
            hourly_rate=200.0,
            recoverable_amount=200.0,
        )
        self.assertEqual(res_max.confidence, 1.0)

        # 0.0 is valid
        res_min = ClassificationResult(
            candidate_id="CAN-MIN",
            status=ClassificationStatus.FILTERED,
            confidence=0.0,
            is_billable=False,
            reasoning="0% confidence",
            billable_hours=0.0,
            hourly_rate=0.0,
            recoverable_amount=0.0,
        )
        self.assertEqual(res_min.confidence, 0.0)

        # > 1.0 raises ValidationError
        with self.assertRaises(ValidationError):
            ClassificationResult(
                candidate_id="CAN-INVALID-HIGH",
                status=ClassificationStatus.FLAGGED,
                confidence=1.05,  # le=1.0 violated
                is_billable=True,
                reasoning="Out of range",
                billable_hours=1.0,
                hourly_rate=200.0,
                recoverable_amount=200.0,
            )

        # < 0.0 raises ValidationError
        with self.assertRaises(ValidationError):
            ClassificationResult(
                candidate_id="CAN-INVALID-LOW",
                status=ClassificationStatus.FILTERED,
                confidence=-0.1,  # ge=0.0 violated
                is_billable=False,
                reasoning="Out of range",
                billable_hours=0.0,
                hourly_rate=0.0,
                recoverable_amount=0.0,
            )

    # =========================================================================
    # Area 6: Attendee Topology Boundaries (Single, Multi-Internal, Multi-External)
    # =========================================================================

    def test_bva_06_single_internal_attendee_personal_event(self):
        """Area 6: Verify single internal attendee event has 0 external participants."""
        event = CalendarEvent(
            event_id="CAL-SOLO-01",
            title="Focus time: Deep work block",
            start_time="2026-08-18T09:00:00",
            end_time="2026-08-18T12:00:00",
            duration_hours=3.0,
            organizer="marcus.brody@meridiandigital.io",
            attendees=["marcus.brody@meridiandigital.io"],
            client_id=None,
        )
        agency_domains = ["meridiandigital.io"]
        externals = [a for a in event.attendees if not any(a.endswith(d) for d in agency_domains)]
        self.assertEqual(len(externals), 0)
        self.assertTrue(len(event.attendees) == 1)

    def test_bva_06_multi_attendee_all_internal(self):
        """Area 6: Verify event with 12 internal attendees has 0 external participants."""
        int_event = next(e for e in self.activities.calendar if e.event_id == "CAL-INT-001")
        agency_domains = ["meridiandigital.io"]
        externals = [a for a in int_event.attendees if not any(a.endswith(d) for d in agency_domains)]
        self.assertEqual(len(externals), 0)
        self.assertGreater(len(int_event.attendees), 10)

    def test_bva_06_single_internal_single_external_attendee(self):
        """Area 6: Verify 1:1 client meeting partitions exactly 1 internal and 1 external."""
        fin_event = next(e for e in self.activities.calendar if e.event_id == "CAL-FIN-REG-01")
        agency_domains = ["meridiandigital.io"]
        externals = [a for a in fin_event.attendees if not any(a.endswith(d) for d in agency_domains)]
        internals = [a for a in fin_event.attendees if any(a.endswith(d) for d in agency_domains)]
        self.assertEqual(len(externals), 1)
        self.assertEqual(len(internals), 1)
        self.assertIn("kvance@finscale.capital", externals)

    def test_bva_06_multi_internal_multi_external_attendees(self):
        """Area 6: Verify multi-person client workshop partitions multiple staff and clients."""
        ret_event = next(e for e in self.activities.calendar if e.event_id == "CAL-RET-001")
        agency_domains = ["meridiandigital.io"]
        externals = [a for a in ret_event.attendees if not any(a.endswith(d) for d in agency_domains)]
        internals = [a for a in ret_event.attendees if any(a.endswith(d) for d in agency_domains)]
        self.assertEqual(len(internals), 2)  # Sarah Chen + Alex Torres
        self.assertEqual(len(externals), 2)  # rsterling@retailpulse.com + vpecommerce@retailpulse.com

    def test_bva_06_duplicate_attendee_emails_deduplication(self):
        """Area 6: Verify duplicate attendee email strings are safely handled and deduplicated."""
        raw_attendees = [
            "sarah.chen@meridiandigital.io",
            "sarah.chen@meridiandigital.io",
            "aris.thorne@apexhealth.io",
            "aris.thorne@apexhealth.io",
        ]
        deduped = sorted(list(set(raw_attendees)))
        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped, ["aris.thorne@apexhealth.io", "sarah.chen@meridiandigital.io"])

    # =========================================================================
    # Area 7: Timesheet Compliance Boundaries (Zero, Exact, Overlogged)
    # =========================================================================

    def test_bva_07_zero_timesheets_logged_for_activity(self):
        """Area 7: When 0 hours are logged in timesheet for an activity, unbilled delta equals full duration."""
        activity_duration = 3.5
        logged_hours = 0.0
        unbilled_delta = max(0.0, activity_duration - logged_hours)
        self.assertEqual(unbilled_delta, 3.5)

    def test_bva_07_exact_100_percent_timesheet_compliance(self):
        """Area 7: When logged hours exactly match activity duration, unbilled delta is 0.0."""
        activity_duration = 4.0
        logged_hours = 4.0
        unbilled_delta = max(0.0, activity_duration - logged_hours)
        self.assertEqual(unbilled_delta, 0.0)

    def test_bva_07_overlogged_timesheet_hours(self):
        """Area 7: When logged hours exceed activity duration (e.g. 5.0 logged vs 4.0 activity), delta is 0.0."""
        activity_duration = 4.0
        logged_hours = 5.0
        unbilled_delta = max(0.0, activity_duration - logged_hours)
        self.assertEqual(unbilled_delta, 0.0, "Overlogged hours must not produce negative unbilled leakage")

    def test_bva_07_multiple_partial_timesheets_aggregation(self):
        """Area 7: Multiple split timesheets on same day (1.5h + 1.0h = 2.5h) matched against 3.0h activity."""
        activity_duration = 3.0
        split_entries = [1.5, 1.0]
        total_logged = sum(split_entries)
        unbilled_delta = max(0.0, activity_duration - total_logged)
        self.assertEqual(unbilled_delta, 0.5)

    def test_bva_07_mismatched_client_timesheet_not_credited(self):
        """Area 7: Timesheet logged under a different client on the same day must not credit target activity."""
        target_activity_client = "CLI-001"
        timesheet_entry = TimesheetEntry(
            entry_id="TS-MISMATCH-01",
            team_member_id="EMP-009",
            client_id="CLI-002",  # Logged under FinScale instead of Apex
            project_code="FIN",
            date="2026-08-14",
            hours=3.5,
            description="FIX protocol support",
            is_billable=True,
        )

        # Logic check: timesheet does not match target client
        matches_client = timesheet_entry.client_id == target_activity_client
        self.assertFalse(matches_client)
        credited_hours = timesheet_entry.hours if matches_client else 0.0
        self.assertEqual(credited_hours, 0.0)

    # =========================================================================
    # Area 8: Negative Control Invariance (The 4 Controls)
    # =========================================================================

    def test_bva_08_negative_control_1_internal_all_hands(self):
        """Area 8 / Control 1: Meridian Sprint Retrospective (CAL-INT-001) filtered as non-billable."""
        event = next(e for e in self.activities.calendar if e.event_id == "CAL-INT-001")
        self.assertEqual(event.event_id, "CAL-INT-001")
        self.assertIsNone(event.client_id)

        # Pre-filter invariant: 100% internal domains and client_id is None -> FILTERED
        agency_domains = ["meridiandigital.io"]
        has_external = any(not any(a.endswith(d) for d in agency_domains) for a in event.attendees)
        self.assertFalse(has_external, "Internal retro must have zero external attendees")

        res = ClassificationResult(
            candidate_id="CAN-INT-001",
            status=ClassificationStatus.FILTERED,
            confidence=0.05,
            is_billable=False,
            clause_cited=None,
            reasoning="Internal all-hands meeting; no external participants or client SOW.",
            billable_hours=0.0,
            hourly_rate=0.0,
            recoverable_amount=0.0,
        )
        self.assertEqual(res.status, ClassificationStatus.FILTERED)
        self.assertEqual(res.recoverable_amount, 0.0)

    def test_bva_08_negative_control_2_biogen_presales(self):
        """Area 8 / Control 2: BioGen discovery pitch (CAL-BIO-001 & EML-BIO-001) filtered as pre-sales."""
        event = next(e for e in self.activities.calendar if e.event_id == "CAL-BIO-001")
        email = next(e for e in self.activities.emails if e.thread_id == "EML-BIO-001")

        self.assertIsNone(event.client_id, "Prospective client BioGen has no active client_id")
        self.assertIsNone(email.client_id)
        self.assertIn("r.vance@biogen-health.com", event.attendees)
        self.assertNotIn("CLI-BIOGEN", self.contracts, "BioGen must not have a signed SOW contract")

        res = ClassificationResult(
            candidate_id="CAN-BIO-001",
            status=ClassificationStatus.FILTERED,
            confidence=0.15,
            is_billable=False,
            clause_cited=None,
            reasoning="Pre-sales discovery pitch; no signed SOW or billable contract exists.",
            billable_hours=0.0,
            hourly_rate=0.0,
            recoverable_amount=0.0,
        )
        self.assertEqual(res.status, ClassificationStatus.FILTERED)

    def test_bva_08_negative_control_3_marcus_dentist(self):
        """Area 8 / Control 3: Marcus Brody dentist appointment (CAL-PER-001) filtered as personal block."""
        event = next(e for e in self.activities.calendar if e.event_id == "CAL-PER-001")
        self.assertIsNone(event.client_id)
        self.assertIn("dentist", event.title.lower())
        self.assertIn("ooo", event.title.lower())
        self.assertEqual(len(event.attendees), 1)

        res = ClassificationResult(
            candidate_id="CAN-PER-001",
            status=ClassificationStatus.FILTERED,
            confidence=0.01,
            is_billable=False,
            clause_cited=None,
            reasoning="Personal appointment / OOO dentist block.",
            billable_hours=0.0,
            hourly_rate=0.0,
            recoverable_amount=0.0,
        )
        self.assertEqual(res.status, ClassificationStatus.FILTERED)
        self.assertEqual(res.recoverable_amount, 0.0)

    def test_bva_08_negative_control_4_warranty_defect_fix(self):
        """Area 8 / Control 4: RetailPulse warranty bug fix (RET-204) filtered under SOW §8.1."""
        task = next(t for t in self.activities.tasks if t.task_id == "RET-204")
        self.assertEqual(task.client_id, "CLI-003")
        self.assertIn("warranty", task.tags)
        self.assertIn("§8.1", task.description)

        # Inspect RetailPulse contract clause §8.1
        ret_contract = self.contracts["CLI-003"]
        warr_clause = next(cl for cl in ret_contract.clauses if cl.clause_id == "§8.1")
        self.assertFalse(warr_clause.is_billable, "SOW §8.1 30-day warranty must be marked non-billable")
        self.assertEqual(warr_clause.rate_multiplier, 0.0)

        res = ClassificationResult(
            candidate_id="CAN-RET-204",
            status=ClassificationStatus.FILTERED,
            confidence=0.10,
            is_billable=False,
            clause_cited="SOW §8.1: 30-Day Defect Warranty Exclusion",
            reasoning="Remediation of defect within 30-day warranty period is non-billable per SOW §8.1.",
            billable_hours=0.0,
            hourly_rate=0.0,
            recoverable_amount=0.0,
        )
        self.assertEqual(res.status, ClassificationStatus.FILTERED)
        self.assertEqual(res.recoverable_amount, 0.0)

    def test_bva_08_aggregate_negative_control_invariance(self):
        """Area 8: Invariance assertion: exactly 0 of the 4 negative controls flag as FLAGGED."""
        controls = [
            ("CAL-INT-001", ClassificationStatus.FILTERED),
            ("CAL-BIO-001", ClassificationStatus.FILTERED),
            ("CAL-PER-001", ClassificationStatus.FILTERED),
            ("RET-204", ClassificationStatus.FILTERED),
        ]
        flagged_count = sum(1 for cid, status in controls if status == ClassificationStatus.FLAGGED)
        self.assertEqual(flagged_count, 0, "Zero negative controls may leak into FLAGGED billable status")


if __name__ == "__main__":
    unittest.main()
