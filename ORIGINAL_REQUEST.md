# Original User Request

## 2026-09-15T08:43:21Z

Build a complete, submission-ready assignment for the Crework Labs AI Engineer Intern role. The project is the **Unbilled Revenue Recovery Agent** — a production-quality Python AI agent that detects billable work a 50–300 person service agency performed but never invoiced.

Working directory: `c:\Users\shiva\Desktop\Crework`
Integrity mode: demo

## Context

This is a job application assignment for Crework Labs (https://shikshita.substack.com). The company builds agentic AI systems for 50–300 person service/product businesses in North America and MENA with operational pain.

The assignment requires:
1. **Part 1**: Spot a frontier AI capability that shipped recently and the caveat designed around.
2. **Part 2**: Match it to a real operational pain point and build the smallest working version.

**Our chosen pairing:**
- **Frontier Capability**: Multi-source MCP tool orchestration + structured extraction with evidence grounding (Claude/Gemini extended reasoning). The agent reads across calendar events, email metadata, project task logs, and timesheets — then cross-references to find gaps where billable work happened but no hours were logged.
- **Caveat Designed Around**: False Positive Billable Detection. Not every meeting or email is billable. An internal standup ≠ a client call. A teammate's question ≠ project work. The guardrail: a Contract-Scope Classifier that tags each detected activity against the signed SOW/contract scope, and only surfaces findings where evidence confidence exceeds a threshold. Low-confidence items go to a Review bucket.
- **Pain Point**: Agencies lose 15–25% of profit margin to invisible unbilled work. Teams do work they never invoice — a quick call here, a small revision there. At /hr across 100 people, missing just 2 hrs/person/week = .56M/year leaked.

**Key constraints from the assignment:**
- NO Make.com, n8n, Zapier, or any visual node-based workflow builder
- NO full-stack app with its own frontend and backend
- Must be a script, automation, or agent calling existing tool APIs
- Screenshots must show actual working surface (code editor, terminal, API playground)
- Must use free-tier APIs only (no paid tools)
- Grading is based on the writeup, screenshots, and GIF

**Reference publication style**: https://shikshita.substack.com — articles like How To Stop Losing Warm Leads to Slow Generic Replies and I Automated Everything That Happens After a Client Signs. Structure: TLDR → What's Inside (step list) → Step 1–N with code blocks, key points, and screenshots → Limitations → Bonus ideas.

## Requirements

### R1. Working Python Agent Codebase

Build a modular Python project in `c:\Users\shiva\Desktop\Crework` that runs end-to-end as a CLI tool. The agent must:

- Include realistic built-in sample data simulating a fake 50-person agency (Meridian Digital) with 5 clients, 12 team members, and 3 weeks of activity data (calendar events, email threads, project tasks, timesheets, and signed contracts/SOWs).
- Use a free-tier AI API (Gemini or Groq) for the intelligent cross-referencing and evidence extraction. Must work with a user-provided API key set as an environment variable.
- Implement the core Revenue Leak Detection loop: scan calendar → scan emails → scan project tasks → cross-reference against timesheets → validate against contract scope → classify each finding with confidence score → output the recovery report.
- Implement the Contract-Scope Classifier guardrail: the agent must NOT flag internal meetings, personal events, or out-of-contract activities as billable. Each finding must cite the specific contract clause that makes it billable.
- Produce a rich terminal output using the Rich library showing: a progress bar during scanning, a formatted table of findings, confidence scores, dollar amounts, and a total recovery summary.
- Generate a markdown Proposal/Report file in `outputs/` with the full recovery analysis.
- Send a summary notification (simulate a Telegram bot message or print the formatted message that would be sent).
- Include clear error handling and helpful messages if the API key is missing or invalid.

### R2. Visual Proof Assets

Generate the following visual proof assets that demonstrate the workflow actually running:

- Step-by-step PNG screenshots (generated programmatically or captured from real terminal output) showing: (1) the project structure, (2) running the agent, (3) the scanning/analysis progress, (4) the findings table, (5) the generated report, (6) the notification dispatch.
- An animated GIF showing the agent running end-to-end in the terminal.
- All assets saved to `c:\Users\shiva\Desktop\Crework\assets\`.

### R3. Submission Article (SUBMISSION_ARTICLE.md)

Write a publication-ready Substack-style article in `c:\Users\shiva\Desktop\Crework\SUBMISSION_ARTICLE.md` following the exact tone and structure of Shikshita Juyal's Idea To Impact newsletter. Must include:

- A compelling title and TLDR
- What's Inside section listing all steps
- Step-by-step walkthrough with code snippets, key points, and references to screenshots
- A Limitations section with honest caveats
- A Bonus: Ideas to Take This Further section
- Professional but accessible writing tone — written for founders and operators, not developers
- Tools used listed clearly

### R4. Assignment Report (ASSIGNMENT_REPORT.md)

Write a formal assignment submission report in `c:\Users\shiva\Desktop\Crework\ASSIGNMENT_REPORT.md` that directly answers every requirement from the Crework assignment brief:

1. The capability spotted and the caveat designed around
2. The pain point matched and why that pairing made sense
3. The workflow step-by-step documentation
4. References to screenshots and GIF
5. At least 4 other capability-to-pain-point pairings the applicant considered, with brief rationale for each

### R5. Documentation and Runnability

- Include a clear README.md with setup instructions (install dependencies, set API key, run the agent)
- Include a requirements.txt with all Python dependencies
- The project must run successfully on Windows with Python 3.13
- All code must be well-commented explaining what each section does and why

## Acceptance Criteria

### Functional Correctness
- [ ] Running `python main.py` (or equivalent entry point) executes the full pipeline without errors when a valid API key is set
- [ ] The agent correctly identifies at least 3 distinct unbilled work items from the sample data with evidence citations
- [ ] The agent correctly does NOT flag at least 2 internal/non-billable activities (proving the guardrail works)
- [ ] A markdown report is generated in `outputs/` with the complete analysis
- [ ] Terminal output shows Rich-formatted tables with findings, confidence scores, and dollar recovery amounts

### Visual Assets
- [ ] At least 4 PNG screenshots exist in `assets/` showing different stages of the workflow
- [ ] An animated GIF exists in `assets/` showing the agent running
- [ ] Screenshots show real terminal/editor output, not mockups

### Documentation Quality
- [ ] SUBMISSION_ARTICLE.md is at least 1500 words and follows the Substack article structure
- [ ] ASSIGNMENT_REPORT.md directly answers all 5 required submission points from the assignment brief
- [ ] README.md contains working setup and run instructions
- [ ] requirements.txt lists all dependencies

### Code Quality
- [ ] Code is modular (separate files for data loading, AI analysis, report generation, notification)
- [ ] All functions have docstrings or clear comments
- [ ] No hardcoded API keys in the source code
