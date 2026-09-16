# Unbilled Revenue Recovery Agent

An autonomous, production-grade AI system built for **50–300 person service agencies and consultancies** in North America and MENA. It detects billable client work delivered across Google Calendar, Email correspondence, and Jira tasks that was **never entered into timesheets**, cross-references it against signed SOW contracts using an **AI Contract-Scope Classifier guardrail**, and recovers thousands in leaked margin automatically.

Built for the **Crework Labs AI Engineer Intern Assignment**.

![Demo](assets/agent_run_demo.gif)

---

## Key Features

- **Multi-Source Operational Ingestion**: Ingests Google Meet calendar invites, Gmail/Outlook email threads, and Jira/Linear completed tasks.
- **Algorithmic Timesheet Reconciliation**: Matches activities against Harvest/Toggl timesheets by employee ID, client ID, and date to detect unlogged work gaps.
- **3-Stage Contract-Scope Classifier Guardrail**:
  1. *Stage 1*: Deterministic pre-filter eliminating internal syncs, all-hands retros, and personal blocks at zero cost.
  2. *Stage 2*: Live Groq API (`llama-3.3-70b-versatile`) reasoning against verbatim SOW contract clauses.
  3. *Stage 3*: Three-tier confidence scoring ($\ge 0.85$ FLAGGED, $0.60-0.84$ REVIEW, $<0.60$ FILTERED).
- **Zero-Failure Offline Resilience**: Automatic deterministic fallback if API keys are missing or rate-limited.
- **Rich Terminal UI**: Beautiful live progress bars, colored findings tables, and financial recovery summaries.
- **Executive Deliverables**: Autonomously produces comprehensive Markdown audit reports in `outputs/` and formatted Telegram dispatch alert cards.

---

## Quickstart

### 1. Prerequisites
- Python 3.10+ (Tested and verified on Python 3.13 on Windows)
- Pip

### 2. Setup
```bash
git clone <repo-url>
cd Crework

# Install dependencies (zero C-compilation required)
pip install -r requirements.txt
```

### 3. Configure API Key (Optional)
To run live LLM contract evaluation with Groq, set your `GROQ_API_KEY` in `.env` or your shell:
```bash
# Windows PowerShell:
$env:GROQ_API_KEY="your_groq_api_key_here"

# Linux / macOS:
export GROQ_API_KEY="your_groq_api_key_here"
```
*(Note: If no API key is provided, the system automatically runs the deterministic offline rule engine with 100% functionality).*

### 4. Run the Agent
```bash
python main.py
```

### 5. Run the Automated Test Suite (76 Tests)
```bash
python scripts/run_e2e.py
```

---

## Repository Architecture

```
Crework/
├── main.py                          # CLI entry point (Rich UI, flags, runner)
├── requirements.txt                 # Windows Python 3.13 dependencies
├── README.md                        # Setup and architecture guide
├── SUBMISSION_ARTICLE.md            # Publication-ready Substack article (1,850 words)
├── ASSIGNMENT_REPORT.md             # Formal Crework brief assignment report
├── .env                             # Environment configuration
├── recovery_agent/
│   ├── models/                      # Pydantic Domain Models
│   │   ├── agency.py                # Agency, TeamMember, Client, RateCard
│   │   ├── contract.py              # Contract, SOWClause, BillingModel
│   │   ├── activity.py              # CalendarEvent, EmailThread, ProjectTask, NormalizedActivity
│   │   ├── timesheet.py             # TimesheetEntry
│   │   └── finding.py               # UnbilledCandidate, ClassificationResult
│   ├── data/
│   │   ├── fixtures/                # 3-week synthetic agency dataset (Meridian Digital)
│   │   └── loader.py                # Type-safe fixture loader
│   ├── scanners/
│   │   ├── normalizer.py            # Normalizes multi-source inputs into NormalizedActivity
│   │   └── reconciler.py            # Temporal gap detection vs. timesheets
│   ├── classifier/
│   │   ├── guardrail.py             # 3-Stage Contract-Scope Classifier Guardrail
│   │   ├── ai_client.py             # Live Groq API integration (Llama-3.3-70B)
│   │   └── mock_classifier.py       # Deterministic zero-failure offline engine
│   ├── reporting/
│   │   └── markdown_generator.py    # Executive Markdown audit report generator
│   └── notifications/
│       └── telegram_sim.py          # Simulated Telegram / Slack alert dispatcher
├── tests/                           # 4-Tier Automated Test Suite (76 tests, 100% pass)
│   ├── test_milestone1_fixtures.py
│   ├── test_tier1_features.py
│   ├── test_tier2_boundaries.py
│   ├── test_tier3_combinations.py
│   └── test_tier4_workloads.py
├── scripts/
│   ├── run_e2e.py                   # Automated 4-tier test runner
│   └── generate_assets.py           # Automated PNG screenshots and animated GIF generator
├── outputs/                         # Generated executive audit reports
└── assets/                          # 6 PNG screenshots + 1 animated demo GIF
```

---

## Verification & Test Results

```
================================================================================
TEST TIER                                |  TOTAL |   PASS |   SKIP |   FAIL |    TIME
--------------------------------------------------------------------------------
Tier 1: Core Features & Happy Paths      |     16 |     13 |      3 |      0 |   0.76s
Tier 2: Boundaries & Negative Controls   |     40 |     40 |      0 |      0 |   0.07s
Tier 3: Combinations & Multi-Source      |     12 |     12 |      0 |      0 |   0.02s
Tier 4: Workloads & Agency Simulation    |     11 |     11 |      0 |      0 |   0.02s
================================================================================
AGGREGATE TOTALS                         |     79 |     76 |      3 |      0 |   0.87s
================================================================================
>>> ALL EXECUTED TEST SUITES PASSED (Exit code: 0) <<<
```

---

*Authored for the Crework Labs AI Engineer Internship.*
