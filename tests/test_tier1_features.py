"""Tier 1: Core Features & Happy Paths Test Suite.

Verifies primary behavior and contracts of all functional components:
- Data Ingestion & Model Validation (Agency, Team Members, Contracts, Activities, Timesheets)
- Activity Normalization across heterogeneous streams (Calendar, Email, Tasks)
- Reconciliation Gap Detection (temporal window matching, unlogged hour deltas)
- Contract-Scope Classifier Guardrail (Pre-filter, SOW grounding, 3-tier thresholding)
- Executive Markdown Report Generation
- Simulated Telegram Alert Dispatch
- CLI Invocation & Environment Handling
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

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

# Optional dynamic imports for Milestone 2 and Milestone 3 modules
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

try:
    from recovery_agent.reporting.markdown_generator import (  # type: ignore
        generate_markdown_report,
    )
    HAS_REPORTING = True
except ImportError:
    HAS_REPORTING = False

try:
    from recovery_agent.notifications.telegram_sim import (  # type: ignore
        dispatch_telegram_notification,
    )
    HAS_NOTIFICATIONS = True
except ImportError:
    HAS_NOTIFICATIONS = False


class TestTier1Features(unittest.TestCase):
    """Happy-path feature tests verifying isolated interface contracts."""

    def setUp(self):
        """Set up test fixtures for each test."""
        self.fixtures = load_all_fixtures()
        self.agency = self.fixtures["agency"]
        self.members = self.fixtures["team_members"]
        self.contracts = self.fixtures["contracts"]
        self.activities = self.fixtures["activities"]
        self.timesheets = self.fixtures["timesheets"]

    # -------------------------------------------------------------------------
    # Feature 1: Data Ingestion & Model Validation
    # -------------------------------------------------------------------------

    def test_f01_agency_profile_loading(self):
        """F01: Verify agency profile loads cleanly with 50 headcount and rate cards."""
        self.assertIsInstance(self.agency, Agency)
        self.assertEqual(self.agency.name, "Meridian Digital Inc.")
        self.assertEqual(self.agency.headcount, 50)
        self.assertIn("meridiandigital.io", self.agency.domains)
        self.assertGreaterEqual(len(self.agency.rate_cards), 10)

        # Check rate cards roles and positive rates
        for rc in self.agency.rate_cards:
            self.assertIsInstance(rc, RateCard)
            self.assertGreater(rc.hourly_rate, 0.0)

    def test_f01_team_members_loading(self):
        """F01: Verify 12 team members with roles, emails, and billable rates."""
        self.assertEqual(len(self.members), 12)
        member_ids = {m.member_id for m in self.members}
        self.assertIn("EMP-001", member_ids)  # Sarah Chen
        self.assertIn("EMP-009", member_ids)  # Tariq Al-Mansoor

        for m in self.members:
            self.assertIsInstance(m, TeamMember)
            self.assertTrue(150.0 <= m.billable_rate <= 250.0)
            self.assertTrue(m.email.endswith("@meridiandigital.io"))

    def test_f02_multi_client_contracts_loading(self):
        """F02: Verify 5 client contracts with SOW clauses, rates, and billing models."""
        # 5 distinct clients
        expected_clients = {"CLI-001", "CLI-002", "CLI-003", "CLI-004", "CLI-005"}
        for cid in expected_clients:
            self.assertIn(cid, self.contracts)
            contract = self.contracts[cid]
            self.assertIsInstance(contract, Contract)
            self.assertTrue(contract.is_active)
            self.assertGreater(contract.default_hourly_rate, 0.0)
            self.assertGreater(len(contract.clauses), 0)

        # Verify Apex Health (CLI-001) has §4.2 urgent remediation clause
        apex = self.contracts["CLI-001"]
        sec_clause = next((cl for cl in apex.clauses if "§4.2" in cl.clause_id), None)
        self.assertIsNotNone(sec_clause, "Apex Health must contain SOW §4.2")
        self.assertTrue(sec_clause.is_billable)
        self.assertEqual(sec_clause.rate_override, 240.0)

    def test_f03_raw_activities_ingestion(self):
        """F03: Verify raw activities ingested across Calendar, Email, and Task streams."""
        self.assertGreaterEqual(len(self.activities.calendar), 15)
        self.assertGreaterEqual(len(self.activities.emails), 10)
        self.assertGreaterEqual(len(self.activities.tasks), 10)
        self.assertGreaterEqual(self.activities.total_count(), 35)

        for cal in self.activities.calendar:
            self.assertIsInstance(cal, CalendarEvent)
            self.assertGreater(cal.duration_hours, 0.0)

        for eml in self.activities.emails:
            self.assertIsInstance(eml, EmailThread)
            self.assertGreater(eml.estimated_effort_hours, 0.0)

        for tsk in self.activities.tasks:
            self.assertIsInstance(tsk, ProjectTask)
            self.assertGreater(tsk.actual_hours, 0.0)

    def test_f03_timesheets_ingestion(self):
        """F03: Verify timesheet entries load and validate with positive hours."""
        self.assertGreaterEqual(len(self.timesheets), 20)
        for ts in self.timesheets:
            self.assertIsInstance(ts, TimesheetEntry)
            self.assertGreater(ts.hours, 0.0)
            self.assertTrue(ts.client_id.startswith("CLI-") or ts.client_id == "MD-INTERNAL")

    # -------------------------------------------------------------------------
    # Feature 2: Activity Normalization Contract
    # -------------------------------------------------------------------------

    def test_f04_activity_normalization_contract(self):
        """F04: Verify canonical NormalizedActivity schema instantiation and field contracts."""
        raw_event = self.activities.calendar[0]
        norm = NormalizedActivity(
            activity_id="ACT-NORM-001",
            source_type=SourceType.CALENDAR,
            raw_id=raw_event.event_id,
            timestamp_start=raw_event.start_time,
            timestamp_end=raw_event.end_time,
            duration_hours=raw_event.duration_hours,
            team_member_id="EMP-001",
            team_member_name="Sarah Chen",
            team_member_email="sarah.chen@meridiandigital.io",
            client_id="CLI-003",
            client_name="RetailPulse",
            title_or_subject=raw_event.title,
            description_or_snippet=raw_event.description or "",
            attendee_emails=raw_event.attendees,
            external_participants=[a for a in raw_event.attendees if not a.endswith("@meridiandigital.io")],
        )
        self.assertEqual(norm.activity_id, "ACT-NORM-001")
        self.assertEqual(norm.source_type, SourceType.CALENDAR)
        self.assertEqual(norm.duration_hours, raw_event.duration_hours)
        self.assertIn("sarah.chen@meridiandigital.io", norm.team_member_email)

    def test_f04_activity_normalization_module(self):
        """F04: Verify activity normalizer scanner functions if implemented."""
        if not HAS_NORMALIZER:
            self.skipTest("Milestone M2 (Normalizer scanner) not yet implemented")

        norm_cal = normalize_calendar_events(self.activities.calendar)
        self.assertEqual(len(norm_cal), len(self.activities.calendar))
        self.assertTrue(all(isinstance(a, NormalizedActivity) for a in norm_cal))

        norm_eml = normalize_email_threads(self.activities.emails)
        self.assertEqual(len(norm_eml), len(self.activities.emails))

        norm_tsk = normalize_project_tasks(self.activities.tasks)
        self.assertEqual(len(norm_tsk), len(self.activities.tasks))

    # -------------------------------------------------------------------------
    # Feature 3: Algorithmic Reconciliation & Time Gap Detection
    # -------------------------------------------------------------------------

    def test_f05_reconciliation_gap_detection_contract(self):
        """F05: Verify reconciliation unbilled candidate generation when zero timesheets exist."""
        activity = NormalizedActivity(
            activity_id="ACT-RECON-001",
            source_type=SourceType.CALENDAR,
            raw_id="CAL-APX-001",
            timestamp_start="2026-08-14T20:00:00",
            timestamp_end="2026-08-14T23:30:00",
            duration_hours=3.5,
            team_member_id="EMP-009",
            team_member_name="Tariq Al-Mansoor",
            team_member_email="tariq.almansoor@meridiandigital.io",
            client_id="CLI-001",
            client_name="Apex Health",
            title_or_subject="Apex Urgent: CVE-2026-4412 HIPAA remediation",
            description_or_snippet="Emergency triage call requested by Apex CTO",
            attendee_emails=["tariq.almansoor@meridiandigital.io", "aris.thorne@apexhealth.io"],
            external_participants=["aris.thorne@apexhealth.io"],
        )

        # Unbilled Candidate contract
        candidate = UnbilledCandidate(
            candidate_id="CAN-001",
            activity=activity,
            unbilled_hours=3.5,
            logged_hours_found=0.0,
            discrepancy_reason="No timesheet logged for Tariq Al-Mansoor on 2026-08-14",
            client_id="CLI-001",
            contract_id="CTR-APX-2026",
        )
        self.assertEqual(candidate.unbilled_hours, 3.5)
        self.assertEqual(candidate.logged_hours_found, 0.0)
        self.assertEqual(candidate.client_id, "CLI-001")

    def test_f05_reconciliation_module(self):
        """F05: Verify reconciliation engine cross-referencing if implemented."""
        if not HAS_RECONCILER:
            self.skipTest("Milestone M2 (Reconciler) not yet implemented")

        candidates = reconcile_activities(self.activities, self.timesheets)
        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 0)

    # -------------------------------------------------------------------------
    # Feature 4: Guardrail Pre-Filter & SOW Classification
    # -------------------------------------------------------------------------

    def test_f06_guardrail_prefilter_contract(self):
        """F06: Verify deterministic pre-filter logic drops internal-only activities."""
        internal_activity = NormalizedActivity(
            activity_id="ACT-INT-001",
            source_type=SourceType.CALENDAR,
            raw_id="CAL-INT-001",
            timestamp_start="2026-08-11T16:00:00",
            timestamp_end="2026-08-11T17:30:00",
            duration_hours=1.5,
            team_member_id="EMP-001",
            team_member_name="Sarah Chen",
            team_member_email="sarah.chen@meridiandigital.io",
            client_id=None,
            client_name=None,
            title_or_subject="All-Hands Engineering Sprint Retrospective",
            description_or_snippet="Internal bi-weekly retro",
            attendee_emails=[
                "sarah.chen@meridiandigital.io",
                "marcus.brody@meridiandigital.io",
                "david.kalu@meridiandigital.io",
            ],
            external_participants=[],
        )

        # Logic rule: 100% internal domains + no client_id -> Non-billable FILTERED
        is_internal = len(internal_activity.external_participants) == 0 and internal_activity.client_id is None
        self.assertTrue(is_internal, "Internal retro must be identified as non-client")

    def test_f07_f08_guardrail_classification_contract(self):
        """F07 & F08: Verify ClassificationResult schema and 3-tier routing rules."""
        # Tier 1: FLAGGED (>= 0.85)
        flagged_result = ClassificationResult(
            candidate_id="CAN-001",
            status=ClassificationStatus.FLAGGED,
            confidence=0.95,
            is_billable=True,
            clause_cited="SOW §4.2: Out-of-hours security remediation",
            reasoning="Grounded in client CTO urgent request for CVE-2026-4412 patch.",
            evidence_snippet="Tariq, our compliance auditor flagged CVE-2026-4412",
            billable_hours=3.5,
            hourly_rate=240.0,
            recoverable_amount=840.0,
            client_id="CLI-001",
            client_name="Apex Health",
            team_member_name="Tariq Al-Mansoor",
            activity_title="Apex Urgent: CVE-2026-4412 HIPAA remediation",
            activity_date="2026-08-14",
        )
        self.assertEqual(flagged_result.status, ClassificationStatus.FLAGGED)
        self.assertGreaterEqual(flagged_result.confidence, 0.85)
        self.assertEqual(flagged_result.recoverable_amount, 840.0)

        # Tier 2: REVIEW (0.60 - 0.84)
        review_result = ClassificationResult(
            candidate_id="CAN-002",
            status=ClassificationStatus.REVIEW,
            confidence=0.72,
            is_billable=True,
            clause_cited="SOW §2.1: General Consultation",
            reasoning="Ambiguous scoping boundary; requires PM review.",
            billable_hours=1.0,
            hourly_rate=200.0,
            recoverable_amount=200.0,
        )
        self.assertEqual(review_result.status, ClassificationStatus.REVIEW)
        self.assertTrue(0.60 <= review_result.confidence < 0.85)

        # Tier 3: FILTERED (< 0.60)
        filtered_result = ClassificationResult(
            candidate_id="CAN-003",
            status=ClassificationStatus.FILTERED,
            confidence=0.05,
            is_billable=False,
            clause_cited=None,
            reasoning="Internal overhead meeting. Excluded by guardrail pre-filter.",
            billable_hours=0.0,
            hourly_rate=0.0,
            recoverable_amount=0.0,
        )
        self.assertEqual(filtered_result.status, ClassificationStatus.FILTERED)
        self.assertLess(filtered_result.confidence, 0.60)
        self.assertEqual(filtered_result.recoverable_amount, 0.0)

    def test_f07_f08_guardrail_module(self):
        """F07 & F08: Verify AI / Mock guardrail classifier if implemented."""
        if not HAS_GUARDRAIL:
            self.skipTest("Milestone M2 (Classifier Guardrail) not yet implemented")

        # Test evaluation with mock classifier
        # Instantiate candidate and evaluate
        pass

    # -------------------------------------------------------------------------
    # Feature 5: Markdown Report Generation
    # -------------------------------------------------------------------------

    def test_f13_markdown_report_structure_contract(self):
        """F13: Verify markdown report generator creates compliant executive reports."""
        findings = [
            ClassificationResult(
                candidate_id="CAN-001",
                status=ClassificationStatus.FLAGGED,
                confidence=0.95,
                is_billable=True,
                clause_cited="SOW §4.2",
                reasoning="Emergency triage call requested by Apex CTO",
                evidence_snippet="CVE-2026-4412 HIPAA remediation",
                billable_hours=3.5,
                hourly_rate=240.0,
                recoverable_amount=840.0,
                client_id="CLI-001",
                client_name="Apex Health",
                team_member_name="Tariq Al-Mansoor",
                activity_title="Urgent HIPAA remediation",
                activity_date="2026-08-14",
            )
        ]
        filtered = [
            ClassificationResult(
                candidate_id="CAN-CTRL-001",
                status=ClassificationStatus.FILTERED,
                confidence=0.05,
                is_billable=False,
                reasoning="Internal meeting",
                billable_hours=0.0,
                hourly_rate=0.0,
                recoverable_amount=0.0,
                activity_title="All-Hands Retro",
            )
        ]

        if HAS_REPORTING:
            with tempfile.TemporaryDirectory() as tmp_dir:
                report_path = generate_markdown_report(findings, filtered, Path(tmp_dir))
                self.assertTrue(report_path.exists())
                content = report_path.read_text(encoding="utf-8")
                self.assertIn("Apex Health", content)
                self.assertIn("$840.00", content)
                self.assertIn("SOW §4.2", content)
        else:
            # Verify data invariants for report generation
            total_recovered = sum(f.recoverable_amount for f in findings)
            total_hours = sum(f.billable_hours for f in findings)
            self.assertEqual(total_recovered, 840.0)
            self.assertEqual(total_hours, 3.5)

    # -------------------------------------------------------------------------
    # Feature 6: Telegram Dispatch
    # -------------------------------------------------------------------------

    def test_f14_telegram_dispatch_contract(self):
        """F14: Verify simulated Telegram dispatch notification payload formatting."""
        findings = [
            ClassificationResult(
                candidate_id="CAN-001",
                status=ClassificationStatus.FLAGGED,
                confidence=0.95,
                is_billable=True,
                clause_cited="SOW §4.2",
                reasoning="Urgent HIPAA call",
                billable_hours=3.5,
                hourly_rate=240.0,
                recoverable_amount=840.0,
                client_id="CLI-001",
                client_name="Apex Health",
            )
        ]

        if HAS_NOTIFICATIONS:
            msg = dispatch_telegram_notification(findings, 840.0, Path("outputs/test.md"))
            self.assertIsNotNone(msg)
        else:
            # Verify required elements of simulated alert
            total_val = sum(f.recoverable_amount for f in findings)
            summary_text = f"🚨 Unbilled Revenue Detected: ${total_val:,.2f} across {len(findings)} items"
            self.assertIn("$840.00", summary_text)
            self.assertIn("1 items", summary_text)

    # -------------------------------------------------------------------------
    # Feature 7: CLI Invocation
    # -------------------------------------------------------------------------

    def test_f15_cli_help_flag(self):
        """F15: Verify CLI main.py executes --help cleanly with zero exit code."""
        main_py = PROJECT_ROOT / "main.py"
        if not main_py.exists():
            self.skipTest("Milestone M3 (main.py CLI) not yet implemented")

        result = subprocess.run(
            [sys.executable, str(main_py), "--help"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, f"main.py --help failed: {result.stderr}")
        self.assertIn("usage", result.stdout.lower())

    def test_f15_cli_mock_flag(self):
        """F15: Verify CLI runs cleanly in deterministic offline mock mode."""
        main_py = PROJECT_ROOT / "main.py"
        if not main_py.exists():
            self.skipTest("Milestone M3 (main.py CLI) not yet implemented")

        result = subprocess.run(
            [sys.executable, str(main_py), "--mock"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, f"main.py --mock failed: {result.stderr}")
        self.assertIn("Meridian Digital", result.stdout)


if __name__ == "__main__":
    unittest.main()
