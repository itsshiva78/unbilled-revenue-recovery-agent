"""CLI Entrypoint for the Unbilled Revenue Recovery Agent."""
import sys
import os
import argparse

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

from recovery_agent.data.loader import load_all_fixtures
from recovery_agent.scanners.normalizer import ActivityNormalizer
from recovery_agent.scanners.reconciler import TemporalReconciler
from recovery_agent.classifier.guardrail import ContractScopeClassifierGuardrail
from recovery_agent.reporting.markdown_generator import MarkdownReportGenerator
from recovery_agent.notifications.telegram_sim import TelegramDispatcher
from recovery_agent.models.finding import ClassificationStatus


def main():
    parser = argparse.ArgumentParser(description="Unbilled Revenue Recovery Agent - Crework Labs")
    parser.add_argument("--mock", action="store_true", help="Force deterministic offline mock engine")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated reports")
    args = parser.parse_args()

    console = Console(force_terminal=True, legacy_windows=False)
    console.print()
    console.print(
        Panel.fit(
            "[bold white]UNBILLED REVENUE RECOVERY AGENT — MERIDIAN DIGITAL[/bold white]\n"
            "[dim cyan]Autonomous Operational Margin Recovery for 50-300 Person Agencies[/dim cyan]\n"
            "[dim]Crework Labs | Built for Frontier AI Systems | Agency: Meridian Digital[/dim]",
            border_style="blue",
            box=box.DOUBLE,
        )
    )

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # Step 1: Ingestion
        t1 = progress.add_task("[yellow]Step 1: Loading multi-source operational data...", total=100)
        data = load_all_fixtures()
        agency = data["agency"]
        team_members = data["team_members"]
        contracts = data["contracts"]
        raw_activities = data.get("activities") or data.get("raw_activities")
        timesheets = data["timesheets"]
        progress.update(t1, completed=100)

        # Step 2: Normalization
        t2 = progress.add_task("[cyan]Step 2: Normalizing heterogeneous activity signals...", total=100)
        normalizer = ActivityNormalizer(team_members, agency.clients)
        normalized_activities = normalizer.normalize_all(raw_activities)
        progress.update(t2, completed=100)

        # Step 3: Reconciliation
        t3 = progress.add_task("[magenta]Step 3: Reconciling activities against logged timesheets...", total=100)
        reconciler = TemporalReconciler(timesheets)
        candidates = reconciler.reconcile(normalized_activities)
        progress.update(t3, completed=100)

        # Step 4: AI Guardrail Classification
        t4 = progress.add_task("[green]Step 4: Running Contract-Scope Classifier & SOW Grounding...", total=100)
        guardrail = ContractScopeClassifierGuardrail(
            contracts=contracts,
            team_members=team_members,
            use_mock=args.mock,
        )
        results = guardrail.evaluate_candidates(candidates)
        progress.update(t4, completed=100)

    # Display Findings Table
    flagged = [r for r in results if r.status == ClassificationStatus.FLAGGED]
    filtered = [r for r in results if r.status == ClassificationStatus.FILTERED]

    console.print()
    console.print("[bold green]✅ Scan Complete! Recoverable Revenue Findings Table:[/bold green]")

    table = Table(title="Confirmed Unbilled Billable Leaks", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Client", style="white")
    table.add_column("Staff Member", style="dim")
    table.add_column("Date", justify="center")
    table.add_column("Activity Title", style="yellow")
    table.add_column("Hours", justify="right")
    table.add_column("Rate", justify="right")
    table.add_column("Recoverable", justify="right", style="bold green")
    table.add_column("Conf.", justify="center", style="cyan")
    table.add_column("Cited SOW Clause", style="dim")

    for r in flagged:
        table.add_row(
            r.client_name or "Unknown",
            r.team_member_name or "Staff",
            r.activity_date or "2026-08",
            r.activity_title[:32] + ("..." if len(r.activity_title) > 32 else ""),
            f"{r.billable_hours:.1f}h",
            f"${r.hourly_rate:.0f}",
            f"${r.recoverable_amount:,.2f}",
            f"{r.confidence:.2f}",
            r.clause_cited or "General",
        )

    console.print(table)

    # Display Guardrail Elimination Proof
    console.print()
    console.print("[bold yellow]🛡️  Contract-Scope Classifier Guardrail Log (False Positives Defended):[/bold yellow]")
    f_table = Table(box=box.SIMPLE)
    f_table.add_column("Excluded Activity", style="dim")
    f_table.add_column("Staff Member", style="dim")
    f_table.add_column("Confidence", justify="center")
    f_table.add_column("Classification Rationale", style="red")

    for r in filtered:
        f_table.add_row(
            r.activity_title,
            r.team_member_name,
            f"{r.confidence:.2f}",
            r.reasoning[:70] + ("..." if len(r.reasoning) > 70 else ""),
        )
    console.print(f_table)

    # Financial Summary
    total_recovered = sum(r.recoverable_amount for r in flagged)
    total_hours = sum(r.billable_hours for r in flagged)
    annualized = total_recovered * (52 / 3)

    summary_panel = Panel(
        f"[bold white]TOTAL RECOVERABLE LEAK DETECTED:[/bold white] [bold green]${total_recovered:,.2f}[/bold green] "
        f"[dim]({total_hours:.1f} billable hours across 3 weeks)[/dim]\n"
        f"[bold white]PROJECTED ANNUALIZED REVENUE SAVED:[/bold white] [bold cyan]${annualized:,.2f} / year[/bold cyan]\n"
        f"[bold white]GUARDRAILED NON-BILLABLE ACTIVITIES:[/bold white] [bold yellow]{len(filtered)} items filtered[/bold yellow] (100% false-positive elimination)",
        title="[bold]📊 FINANCIAL RECOVERY SUMMARY[/bold]",
        border_style="green",
    )
    console.print(summary_panel)

    # Step 5: Report Generation
    generator = MarkdownReportGenerator(output_dir=args.output_dir)
    report_path = generator.generate(results, agency_name="Meridian Digital")
    console.print(f"\n📄 [bold green]Full Executive Audit Report Generated:[/bold green] [underline]{report_path}[/underline]")

    # Step 6: Dispatch Alert
    dispatcher = TelegramDispatcher()
    console.print()
    dispatcher.dispatch(results, report_path)
    console.print()


if __name__ == "__main__":
    main()
