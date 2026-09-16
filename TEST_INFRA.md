# Test Infrastructure Specification: Unbilled Revenue Recovery Agent

**Project**: Unbilled Revenue Recovery Agent (`Meridian Digital`)  
**Document**: `TEST_INFRA.md`  
**Owner**: E2E Testing Track (`test_writer_e2e`)  
**Version**: 1.0.0  
**Status**: ACTIVE & RATIFIED  

---

## 1. Test Philosophy & Principles

The Unbilled Revenue Recovery Agent test infrastructure is engineered around four non-negotiable testing tenets:

### 1.1 Opaque-Box, Requirement-Driven Verification
- Tests interact with the system strictly through public module interfaces, data contracts, and CLI invocations defined in `PROJECT.md` and `ORIGINAL_REQUEST.md`.
- No internal private state inspection, monkey-patching of private helper methods, or facade tests that bypass real business logic.
- Every assertion is grounded in an explicit authoritative source (e.g. SOW clause citations, hourly rates, calculated dollar totals, or domain model schemas).

### 1.2 Deterministic Grounding & No Mock Pollution
- In test environments, deterministic behavior is paramount. Tests must run 100% reliably in offline, CI/CD, and evaluation environments without requiring live third-party API credentials (`GEMINI_API_KEY` or `GROQ_API_KEY`).
- When testing AI classification logic, tests verify the contract-scope guardrail using deterministic rule-based grounding engines (`MockScopeClassifier`) or pure interface contracts, ensuring repeatable evaluations.

### 1.3 Progressive Testability Across Milestones
- Development occurs in structured milestones (M1: Data Models & Fixtures, M2: Scanners & Classifier Guardrail, M3: UI & Reporting, M4: Assets, M5: Documentation, M6: Hardening).
- The test suite is designed with progressive testability: tests for current and completed milestones execute directly and assert full functional compliance. Tests targeting subsequent milestones detect implementation availability via interface contracts, executing fully when modules are present and skipping cleanly when pending, ensuring test suite compilation and exit code 0 stability at every phase.

### 1.4 Financial Precision & Negative Control Invariance
- In professional services, overbilling damages client trust while underbilling destroys agency EBITDA. The test suite enforces:
  - **Positive Leak Recovery Precision**: 100% identification of all 5 injected billable leaks (17.0 hours / $4,052.50).
  - **Negative Control Precision**: 100% exclusion of all 4 non-billable activities (internal all-hands, personal blocks, prospective pre-sales, and warranty bug fixes). Zero false positive leakage into billable status.

---

## 2. Feature Inventory Coverage Mapping

Every feature identified in `PROJECT.md § Feature Inventory` is mapped to an authoritative test tier:

| Feature ID | Feature Name | Description | Test Tier | Primary Test File |
|---|---|---|---|---|
| **F01** | Meridian Digital Profile | 50-person agency profile, 12 team members ($150-$250/hr), rate cards | Tier 1, Tier 4 | `test_tier1_features.py`, `test_tier4_workloads.py` |
| **F02** | Multi-Client Contracts | 5 client SOWs (T&M, Retainer+Overage) with clauses §1-§8 | Tier 1, Tier 4 | `test_tier1_features.py`, `test_tier4_workloads.py` |
| **F03** | 3-Week Multi-Source Activity | 36 activity signals across Calendar, Email, Tasks, Timesheets | Tier 1, Tier 2 | `test_tier1_features.py`, `test_tier2_boundaries.py` |
| **F04** | Activity Normalization | Canonical `NormalizedActivity` schema across all 3 source streams | Tier 1, Tier 2 | `test_tier1_features.py`, `test_tier2_boundaries.py` |
| **F05** | Algorithmic Reconciliation | Temporal window & metadata matching detecting unbilled delta hours | Tier 1, Tier 3 | `test_tier1_features.py`, `test_tier3_combinations.py` |
| **F06** | Guardrail Stage 1 Pre-Filter | Deterministic drop of internal domains, personal OOO, missing SOW | Tier 1, Tier 2 | `test_tier1_features.py`, `test_tier2_boundaries.py` |
| **F07** | Guardrail Stage 2 AI Classifier | Contract scope evaluation extracting verbatim clause citations | Tier 1, Tier 3 | `test_tier1_features.py`, `test_tier3_combinations.py` |
| **F08** | Guardrail Stage 3 Thresholding | Multi-tier routing (>=0.85 FLAGGED, 0.60-0.84 REVIEW, <0.60 FILTERED) | Tier 1, Tier 3 | `test_tier1_features.py`, `test_tier3_combinations.py` |
| **F09** | Resilient Deterministic Mock | 100% offline fallback ensuring grading without API keys | Tier 1, Tier 2 | `test_tier1_features.py`, `test_tier2_boundaries.py` |
| **F10** | Rich Progress UI | Multi-source scanning progress bars and live status updates | Tier 1 | `test_tier1_features.py` |
| **F11** | Guardrail Filtration Panel | Terminal panel displaying filtered negative controls | Tier 1, Tier 2 | `test_tier1_features.py`, `test_tier2_boundaries.py` |
| **F12** | Rich Findings Table & Summary | 11-column findings table & 3-column executive financial summary | Tier 1, Tier 4 | `test_tier1_features.py`, `test_tier4_workloads.py` |
| **F13** | Markdown Report Generator | Comprehensive executive audit report generated in `outputs/` | Tier 1, Tier 4 | `test_tier1_features.py`, `test_tier4_workloads.py` |
| **F14** | Telegram Bot Dispatcher | Simulated Telegram alert card with recovery metrics and links | Tier 1, Tier 4 | `test_tier1_features.py`, `test_tier4_workloads.py` |
| **F15** | Windows CLI Entrypoint | `main.py` with flags (`--mock`, `--api-key`, `--output-dir`), UTF-8 | Tier 1, Tier 4 | `test_tier1_features.py`, `test_tier4_workloads.py` |
| **F16** | Visual Proof PNG Generator | Programmatic 1440x900 screenshots in `assets/` | Tier 4 | `test_tier4_workloads.py` |
| **F17** | Animated GIF Generator | High-framerate animated execution demo in `assets/` | Tier 4 | `test_tier4_workloads.py` |
| **F18** | Substack Submission Article | 1500+ word publication-ready article in `SUBMISSION_ARTICLE.md` | Tier 4 | `test_tier4_workloads.py` |
| **F19** | Formal Assignment Report | `ASSIGNMENT_REPORT.md` answering all 5 brief questions | Tier 4 | `test_tier4_workloads.py` |
| **F20** | Documentation & Dependencies | `README.md` and zero-compilation `requirements.txt` | Tier 1 | `test_tier1_features.py` |
| **F21** | E2E Test Suite | 4-tier comprehensive opaque-box test runner | All Tiers | `scripts/run_e2e.py` |

---

## 3. Test Architecture & Tier Organization

The test suite is partitioned into four distinct tiers, ordered by increasing scope and complexity:

```
Crework/
├── tests/
│   ├── __init__.py
│   ├── test_tier1_features.py        # Tier 1: Happy-path feature verification
│   ├── test_tier2_boundaries.py      # Tier 2: Boundary, edge case, and negative controls
│   ├── test_tier3_combinations.py    # Tier 3: Cross-feature combinations & multi-source
│   └── test_tier4_workloads.py       # Tier 4: Real-world agency simulation (Meridian Digital)
├── scripts/
│   ├── __init__.py
│   └── run_e2e.py                    # Automated test runner with reporting
└── TEST_INFRA.md                     # This specification document
```

### 3.1 Tier Definitions

#### Tier 1: Core Features & Happy Paths (`test_tier1_features.py`)
- **Focus**: Verifies isolated component contracts and primary happy-path workflows.
- **Coverage**:
  - Ingestion and Pydantic validation of Agency, Team Members, Contracts, Activities, and Timesheets.
  - Normalization of raw calendar events, email threads, and Jira tasks into canonical `NormalizedActivity`.
  - Reconciliation of activities against timesheet entries for clean gap detection.
  - Guardrail pre-filter and classification evaluating candidate activities against SOW clauses.
  - Generation of Markdown audit reports with required structural headings.
  - Formatting of simulated Telegram notifications.
  - Validation of CLI flags (`--help`, `--mock`).

#### Tier 2: Boundaries, Edge Cases & Negative Controls (`test_tier2_boundaries.py`)
- **Focus**: Boundary values, empty datasets, adversarial inputs, and negative controls.
- **Coverage**:
  - Empty activity inputs (zero calendar events, zero emails, zero tasks) producing 0 unbilled leaks.
  - Zero-hour timesheets and 100% timesheet compliance (zero unbilled leakage detected).
  - Activities for clients with no signed contract (pre-sales / prospective client detection).
  - Malformed email subjects, extreme timestamps, and unusual duration boundaries (< 15 min increments).
  - Negative Control 1: Internal all-hands retrospective (`@meridiandigital.io` only) -> `FILTERED`.
  - Negative Control 2: BioGen pre-sales discovery pitch -> `FILTERED`.
  - Negative Control 3: Marcus Brody personal dentist appointment -> `FILTERED`.
  - Negative Control 4: RetailPulse warranty bug fix (`RET-204`) -> `FILTERED` under SOW §8.1.

#### Tier 3: Combinatorial Interactions & Multi-Source Synthesis (`test_tier3_combinations.py`)
- **Focus**: Cross-feature interactions and multi-source corroboration.
- **Coverage**:
  - Multi-source corroboration: Correlating a Google Meet invite + urgent client email thread + Jira ticket for the same leak incident.
  - Multi-attendee client workshops: Joint participation of multiple team members (e.g. Sarah Chen at $250/hr and Alex Torres at $175/hr) generating discrete itemized recovery line items.
  - Retainer + T&M overage calculations: Applying base retainer hours and routing excess hours to hourly rate cards.
  - Role-specific specialist rate surcharges (e.g. Cloud Security Specialist out-of-hours rate §4.2 vs baseline engineer rate).
  - Same-day multiple leaks: Disambiguating distinct morning and evening events for the same consultant and client.

#### Tier 4: Real-World Workloads & Full Simulation (`test_tier4_workloads.py`)
- **Focus**: End-to-end integration and simulation of the full Meridian Digital dataset.
- **Coverage**:
  - Exact recovery of all 5 positive injected leaks:
    1. **Apex Health**: Tariq Al-Mansoor, 3.5h @ $240/hr = **$840.00** (SOW §4.2).
    2. **FinScale**: Marcus Brody, 5.0h @ $200/hr = **$1,000.00** (SOW §3.4).
    3. **RetailPulse**: Sarah Chen & Alex Torres, 2.0h * ($250 + $175) = **$850.00** (SOW §2.3).
    4. **OmniFlow**: Priya Sharma, 4.0h @ $200/hr = **$800.00** (SOW §5.1).
    5. **CloudShift**: David Kalu, 2.5h @ $225/hr = **$562.50** (SOW §6.3).
  - Total Verified Unbilled Hours: **17.0 hours**.
  - Total Verified Recoverable Amount: **$4,052.50**.
  - 100% filtration of all 4 negative controls (`CAL-INT-001`, `CAL-BIO-001`, `CAL-PER-001`, `RET-204`).
  - Validation of output artifacts: Markdown report written to `outputs/` with financial breakdown matching terminal tables.

---

## 4. Execution & Runner Commands

### 4.1 Standard Test Runners
The test suite is fully compatible with Python's built-in `unittest` framework and `pytest`:

```powershell
# Run the automated E2E test runner (recommended):
python scripts/run_e2e.py

# Run all test tiers via Python standard unittest discovery:
python -m unittest discover tests -p "test_*.py" -v

# Run individual test tiers:
python -m unittest tests/test_tier1_features.py -v
python -m unittest tests/test_tier2_boundaries.py -v
python -m unittest tests/test_tier3_combinations.py -v
python -m unittest tests/test_tier4_workloads.py -v
```

### 4.2 Pass/Fail Semantics & Exit Codes
- **Exit Code 0**: All executed test assertions passed. Any tests for unimplemented future milestones are skipped with explicit diagnostic annotations.
- **Exit Code 1**: Any assertion failure, unhandled exception, or unexpected regression.
- **Strict Isolation**: Each test case initializes its own state. Tests do not share mutable globals or rely on execution sequence.

---

## 5. Coverage & Quality Thresholds

| Metric | Target Threshold | Rationale |
|---|---|---|
| **Positive Leak Detection Recall** | **100.0% (5 of 5 leaks)** | Every injected billable leak must be detected and quantified |
| **Negative Control Precision** | **100.0% (0 of 4 flagged)** | Zero non-billable events may leak into `FLAGGED` recovery |
| **Financial Computation Accuracy** | **$0.00 tolerance ($4,052.50)** | Exact dollar amounts derived from (hours * contracted rate) |
| **Hour Delta Computation Accuracy** | **0.00 hr tolerance (17.0 hrs)** | Exact hour deltas verified across all 5 leak scenarios |
| **Offline Independence** | **100% offline runnable** | No external network calls required for test execution |
| **Suite Exit Code** | **Exit Code 0** | Clean execution across all supported Windows environments |

---
*Authored by E2E Testing Track (`test_writer_e2e`) — September 15, 2026*
