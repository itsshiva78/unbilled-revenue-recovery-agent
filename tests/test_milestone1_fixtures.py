"""Verification test suite for Milestone 1: Domain Models, Fixtures, and Loader."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path so recovery_agent can be imported
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


class TestMilestone1(unittest.TestCase):
    """Test suite validating all Milestone 1 domain models, fixtures, and loaders."""

    def test_agency_loading(self):
        """Verify agency profile loads cleanly with 50 headcount, rate cards, and clients."""
        agency = load_agency()
        self.assertIsInstance(agency, Agency)
        self.assertEqual(agency.name, "Meridian Digital Inc.")
        self.assertEqual(agency.headcount, 50)
        self.assertIn("meridiandigital.io", agency.domains)
        self.assertEqual(len(agency.rate_cards), 12)
        self.assertEqual(len(agency.clients), 5)

        # Validate rate cards
        roles = {rc.role: rc.hourly_rate for rc in agency.rate_cards}
        self.assertEqual(roles["Principal Solutions Architect"], 250.0)
        self.assertEqual(roles["Cloud Security Specialist"], 240.0)
        self.assertEqual(roles["Senior Fullstack Engineer"], 200.0)
        self.assertEqual(roles["QA Automation Engineer"], 150.0)

    def test_team_members_loading(self):
        """Verify 12 staff members load with correct roles, rates, and emails."""
        members = load_team_members()
        self.assertEqual(len(members), 12)
        member_dict = {m.member_id: m for m in members}

        self.assertIn("EMP-001", member_dict)
        sarah = member_dict["EMP-001"]
        self.assertEqual(sarah.full_name, "Sarah Chen")
        self.assertEqual(sarah.billable_rate, 250.0)
        self.assertEqual(sarah.email, "sarah.chen@meridiandigital.io")

        tariq = member_dict["EMP-009"]
        self.assertEqual(tariq.full_name, "Tariq Al-Mansoor")
        self.assertEqual(tariq.billable_rate, 240.0)

        marcus = member_dict["EMP-002"]
        self.assertEqual(marcus.full_name, "Marcus Brody")
        self.assertEqual(marcus.billable_rate, 200.0)

        # Ensure all rates fall within $150 - $250 and emails are valid
        for m in members:
            self.assertTrue(150.0 <= m.billable_rate <= 250.0)
            self.assertTrue(m.email.endswith("@meridiandigital.io"))

    def test_contracts_loading(self):
        """Verify 5 client SOWs load with verbatim billing clauses and exclusions."""
        contracts = load_contracts()
        self.assertIn("CLI-001", contracts)
        self.assertIn("CLI-002", contracts)
        self.assertIn("CLI-003", contracts)
        self.assertIn("CLI-004", contracts)
        self.assertIn("CLI-005", contracts)

        # Check Apex Health (CLI-001) SOW §4.2
        c_apx = contracts["CLI-001"]
        self.assertEqual(c_apx.client_name, "Apex Health")
        self.assertEqual(c_apx.billing_model, BillingModel.TIME_AND_MATERIALS)
        clause_ids = [cl.clause_id for cl in c_apx.clauses]
        self.assertIn("§4.2", clause_ids)
        sec_clause = next(cl for cl in c_apx.clauses if cl.clause_id == "§4.2")
        self.assertEqual(sec_clause.rate_override, 240.0)
        self.assertTrue(sec_clause.is_billable)
        self.assertIn("HIPAA", sec_clause.text)

        # Check RetailPulse (CLI-003) SOW §2.3 and warranty §8.1
        c_ret = contracts["CLI-003"]
        self.assertEqual(c_ret.billing_model, BillingModel.RETAINER_OVERAGE)
        warr_clause = next(cl for cl in c_ret.clauses if cl.clause_id == "§8.1")
        self.assertFalse(warr_clause.is_billable)
        self.assertIn("30 days", warr_clause.text)

        # Check FinScale (CLI-002) SOW §3.4
        c_fin = contracts["CLI-002"]
        spike_clause = next(cl for cl in c_fin.clauses if cl.clause_id == "§3.4")
        self.assertTrue(spike_clause.is_billable)

        # Check OmniFlow (CLI-004) SOW §5.1
        c_omn = contracts["CLI-004"]
        wh_clause = next(cl for cl in c_omn.clauses if cl.clause_id == "§5.1")
        self.assertTrue(wh_clause.is_billable)
        self.assertEqual(wh_clause.rate_override, 200.0)

        # Check CloudShift (CLI-005) SOW §6.3
        c_cld = contracts["CLI-005"]
        dr_clause = next(cl for cl in c_cld.clauses if cl.clause_id == "§6.3")
        self.assertTrue(dr_clause.is_billable)
        self.assertEqual(dr_clause.rate_override, 225.0)

    def test_raw_activities_loading(self):
        """Verify raw activities load across calendar, email, and task streams."""
        activities = load_raw_activities()
        self.assertGreaterEqual(len(activities.calendar), 15)
        self.assertGreaterEqual(len(activities.emails), 10)
        self.assertGreaterEqual(len(activities.tasks), 10)
        self.assertGreaterEqual(activities.total_count(), 35)

        # Positive Leak events
        cal_ids = {e.event_id: e for e in activities.calendar}
        self.assertIn("CAL-APX-001", cal_ids)  # Leak 1: Urgent HIPAA call
        self.assertIn("CAL-RET-001", cal_ids)  # Leak 3: RetailPulse Architecture workshop
        self.assertIn("CAL-CLD-001", cal_ids)  # Leak 5: Weekend DR drill

        task_ids = {t.task_id: t for t in activities.tasks}
        self.assertIn("FIN-142", task_ids)  # Leak 2: FIX 4.4 spike
        self.assertIn("OMNI-89", task_ids)  # Leak 4: Salesforce webhook
        self.assertIn("RET-204", task_ids)  # Control 4: Warranty bug fix
        self.assertIn("warranty", task_ids["RET-204"].tags)

        email_ids = {e.thread_id: e for e in activities.emails}
        self.assertIn("EML-APX-001", email_ids)  # Leak 1 email
        self.assertIn("EML-BIO-001", email_ids)  # Control 2 pre-sales

        # Negative Control events
        self.assertIn("CAL-INT-001", cal_ids)  # Control 1: All-Hands retro
        self.assertIn("CAL-PER-001", cal_ids)  # Control 3: Dentist block
        self.assertIn("CAL-BIO-001", cal_ids)  # Control 2: BioGen pitch

    def test_timesheets_and_leak_omissions(self):
        """Verify timesheets contain regular entries but accurately omit the 5 injected leaks."""
        timesheets = load_timesheets()
        self.assertEqual(len(timesheets), 25)

        # Check Leak 1 (Tariq on 2026-08-14 for Apex) is NOT in timesheets
        tariq_apx_entries = [
            t for t in timesheets
            if t.team_member_id == "EMP-009" and t.client_id == "CLI-001" and t.date == "2026-08-14"
        ]
        self.assertEqual(len(tariq_apx_entries), 0, "Leak 1 should NOT be logged in timesheets")

        # Check Leak 2 (Marcus on 2026-08-18 for FinScale) is NOT in timesheets
        marcus_fin_entries = [
            t for t in timesheets
            if t.team_member_id == "EMP-002" and t.client_id == "CLI-002" and t.date == "2026-08-18"
        ]
        self.assertEqual(len(marcus_fin_entries), 0, "Leak 2 should NOT be logged in timesheets")

        # Check Leak 3 (RetailPulse architecture workshop on 2026-08-21) is NOT logged for RetailPulse
        sarah_alex_ret_entries = [
            t for t in timesheets
            if t.client_id == "CLI-003" and t.date == "2026-08-21"
        ]
        self.assertEqual(len(sarah_alex_ret_entries), 0, "Leak 3 workshop should NOT be logged under RetailPulse")

        # Check Leak 4 (Priya on 2026-08-24 for OmniFlow) is NOT in timesheets
        priya_omn_entries = [
            t for t in timesheets
            if t.team_member_id == "EMP-005" and t.date == "2026-08-24"
        ]
        self.assertEqual(len(priya_omn_entries), 0, "Leak 4 should NOT be logged in timesheets")

        # Check Leak 5 (David Kalu on Saturday 2026-08-29 for CloudShift) is NOT in timesheets
        david_cld_weekend = [
            t for t in timesheets
            if t.team_member_id == "EMP-004" and t.date == "2026-08-29"
        ]
        self.assertEqual(len(david_cld_weekend), 0, "Leak 5 should NOT be logged in timesheets")

    def test_domain_model_instantiation(self):
        """Verify NormalizedActivity, UnbilledCandidate, and ClassificationResult instantiate cleanly."""
        activity = NormalizedActivity(
            activity_id="ACT-001",
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
        self.assertEqual(activity.duration_hours, 3.5)

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

        result = ClassificationResult(
            candidate_id="CAN-001",
            status=ClassificationStatus.FLAGGED,
            confidence=0.95,
            is_billable=True,
            clause_cited="SOW §4.2: Out-of-hours security remediation ($240/hr)",
            reasoning="Requested by client CTO for HIPAA compliance CVE patch during out-of-hours window.",
            evidence_snippet="Tariq, our compliance auditor flagged CVE-2026-4412 in production audit logs.",
            billable_hours=3.5,
            hourly_rate=240.0,
            recoverable_amount=840.0,
            client_id="CLI-001",
            client_name="Apex Health",
            team_member_name="Tariq Al-Mansoor",
            activity_title=activity.title_or_subject,
            activity_date="2026-08-14",
        )
        self.assertEqual(result.recoverable_amount, 840.0)
        self.assertEqual(result.classification_bucket, ClassificationStatus.FLAGGED)
        self.assertEqual(result.confidence_score, 0.95)

    def test_load_all_fixtures(self):
        """Verify load_all_fixtures orchestrates complete dataset loading."""
        all_data = load_all_fixtures()
        self.assertIn("agency", all_data)
        self.assertIn("team_members", all_data)
        self.assertIn("contracts", all_data)
        self.assertIn("activities", all_data)
        self.assertIn("timesheets", all_data)


if __name__ == "__main__":
    unittest.main()
