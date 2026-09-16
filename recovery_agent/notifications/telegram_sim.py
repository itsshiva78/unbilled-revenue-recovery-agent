"""Simulates Telegram / Slack alert card dispatch for operations directors."""
from typing import List
from rich.console import Console
from rich.panel import Panel
from recovery_agent.models.finding import ClassificationResult, ClassificationStatus


class TelegramDispatcher:
    """Dispatches formatted executive summary cards to agency leadership."""

    def __init__(self):
        self.console = Console()

    def format_card(
        self, results: List[ClassificationResult], report_path: str
    ) -> str:
        flagged = [r for r in results if r.status == ClassificationStatus.FLAGGED]
        total_amount = sum(r.recoverable_amount for r in flagged)
        total_hours = sum(r.billable_hours for r in flagged)
        annualized = total_amount * (52 / 3)

        card = (
            f"🚨 [bold yellow]REVENUE RECOVERY RADAR — MERIDIAN DIGITAL[/bold yellow] 🚨\n\n"
            f"💰 [bold green]Recoverable Unbilled Work Found:[/bold green] [bold white]${total_amount:,.2f}[/bold white] ({total_hours:.1f} hrs)\n"
            f"📈 [bold cyan]Projected Annual Recovery:[/bold cyan] [bold white]${annualized:,.2f}[/bold white]\n"
            f"🔍 [bold magenta]Audit Sample Period:[/bold magenta] Past 3 Weeks\n\n"
            f"[bold]Confirmed Recoverable Line Items:[/bold]\n"
        )
        for r in flagged:
            card += (
                f" • [bold white]{r.client_name}[/bold white]: {r.billable_hours}h (${r.recoverable_amount:,.2f})\n"
                f"   [dim]{r.activity_title} — {r.clause_cited}[/dim]\n"
            )

        card += (
            f"\n📄 [dim]Full Executive Report saved to: {report_path}[/dim]\n"
            f"👉 [bold green][ Approve & Generate Client Invoices ][/bold green] | [bold red][ Dismiss ][/bold red]"
        )
        return card

    def dispatch(self, results: List[ClassificationResult], report_path: str):
        card_content = self.format_card(results, report_path)
        panel = Panel(
            card_content,
            title="[bold green]📱 TELEGRAM DISPATCH SIMULATOR[/bold green]",
            subtitle="[dim]Channel: @meridian-ops-executive[/dim]",
            border_style="green",
        )
        self.console.print(panel)
