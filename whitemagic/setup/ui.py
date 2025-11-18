"""Rich UI components for setup wizard."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def show_welcome(console: Console) -> None:
    """Display welcome screen."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Welcome to WhiteMagic! 🧠✨[/bold cyan]\n\n"
            "This wizard will help you configure WhiteMagic for your needs.\n"
            "It only takes a few minutes.\n\n"
            "[dim]Press Ctrl+C anytime to cancel[/dim]",
            title="Setup Wizard",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


def show_tier_options(console: Console) -> None:
    """Display tier selection options."""
    console.print("[bold]How will you use WhiteMagic?[/bold]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Choice", style="cyan bold", width=3)
    table.add_column("Tier", style="bold")
    table.add_column("Description", style="dim")

    table.add_row("1", "🌟 Personal AI Companion", "Journaling, planning, creativity")
    table.add_row("2", "⚡ Development & Freelance", "Project memory, code context")
    table.add_row("3", "👥 Team Collaboration", "Shared knowledge, onboarding")
    table.add_row("4", "🔒 Regulated Domain", "Medical/legal/gov isolation")

    console.print(table)
    console.print()


def show_tier_summary(
    console: Console, tier: str, tier_name: str, description: str, highlight: str
) -> None:
    """Show selected tier summary."""
    console.print()
    console.print(
        Panel(
            f"[bold]{tier_name}[/bold]\n\n" f"{description}\n\n" f"{highlight}",
            title=f"✓ Selected: {tier.capitalize()}",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()


def show_installation_status(console: Console, has_embeddings: bool) -> None:
    """Show current installation status."""
    console.print("[bold]Current Installation:[/bold]\n")

    status_lines = [
        ("✓", "Core WhiteMagic installed", "green"),
        ("✓", "Configuration system ready", "green"),
        ("✓", "CLI commands available", "green"),
    ]

    if has_embeddings:
        status_lines.append(("✓", "Local AI embeddings installed", "green"))
    else:
        status_lines.append(("○", "Local AI not installed", "yellow"))

    for symbol, text, color in status_lines:
        console.print(f"  [{color}]{symbol}[/{color}] {text}")

    console.print()


def show_embeddings_options(console: Console, recommended: str) -> None:
    """Display embeddings provider options."""
    console.print("[bold]Choose Embeddings Provider:[/bold]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Choice", style="cyan bold", width=3)
    table.add_column("Provider", style="bold")
    table.add_column("Details", style="dim")

    rec_1 = " [green](recommended)[/green]" if recommended == "local" else ""
    rec_2 = " [green](recommended)[/green]" if recommended == "openai" else ""

    table.add_row("1", f"Local AI{rec_1}", "Privacy-first, offline, ~2.5GB download")
    table.add_row("2", f"OpenAI API{rec_2}", "Best quality, requires API key, $0.02/1M tokens")
    table.add_row("3", "Skip for now", "Configure later with: whitemagic setup-embeddings")

    console.print(table)
    console.print()


def show_completion(console: Console, tier: str, embeddings: str, config_path: str) -> None:
    """Show completion screen with next steps."""
    console.print()
    console.print(
        Panel.fit(
            "[bold green]✓ Setup Complete![/bold green]\n\n"
            f"Configuration saved to:\n"
            f"[cyan]{config_path}[/cyan]\n\n"
            "[bold]Next Steps:[/bold]\n\n"
            "  1. Create your first memory:\n"
            '     [cyan]whitemagic create --title "Setup complete"[/cyan]\n\n'
            "  2. List your memories:\n"
            "     [cyan]whitemagic list[/cyan]\n\n"
            + (
                "  3. Try semantic search:\n"
                '     [cyan]whitemagic search-semantic "your query"[/cyan]\n\n'
                if embeddings != "skip"
                else ""
            )
            + "  📚 Documentation: [link]https://github.com/lbailey94/whitemagic[/link]\n"
            "  💬 Get help: [cyan]whitemagic --help[/cyan]",
            title="🎉 Welcome to WhiteMagic",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()
