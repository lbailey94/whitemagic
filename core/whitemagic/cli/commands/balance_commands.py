# mypy: disable-error-code=no-untyped-def
"""Balance CLI Commands
Yin-Yang balance tracking and reporting.
"""

import click

from whitemagic.utils.fast_json import loads as _json_loads


@click.group()
def balance() -> None:
    """Yin-Yang balance tracking and reporting (v4.13.0)"""


@balance.command(name="status")
def balance_status() -> None:
    """Show current Yin-Yang balance"""
    try:
        from whitemagic.harmony.yin_yang_tracker import get_tracker

        tracker = get_tracker()
        report = tracker.get_report()

        click.echo(f"\n{report['status_emoji']} {report['status']}")
        click.echo(f"Balance Score: {report['balance_score']:.2f}/1.00")
        click.echo(f"Burnout Risk: {report['burnout_risk']:.1%}")
        click.echo(f"\nActivity in last {report['window_minutes']} minutes:")
        click.echo(f"  Yang (Action):     {report['yang_count']} ({report['yang_ratio']:.1%})")
        click.echo(f"  Yin (Reflection):  {report['yin_count']} ({report['yin_ratio']:.1%})")

        if report["recommendation"]:
            click.echo(f"\n💡 {report['recommendation']}")
    except Exception as e:
        click.echo(f"❌ Balance tracker error: {e}", err=True)


@balance.command()
@click.option("--limit", default=20, help="Number of activities to show")
def history(limit: int) -> None:
    """Show Yin-Yang activity history"""
    try:
        from whitemagic.harmony.yin_yang_tracker import get_tracker

        tracker = get_tracker()
        history_file = tracker.storage_dir / "activity_log.jsonl"

        if not history_file.exists():
            click.echo("No activity history yet.")
            return

        click.echo("\nRecent Activity:")
        with open(history_file) as f:
            lines = list(f)[-limit:]
            for line in lines:
                data = _json_loads(line)
                timestamp = data["timestamp"][:19]
                activity = data["activity"]
                activity_type = "Yang" if activity in [
                    "CREATE", "WRITE", "EXECUTE", "BUILD", "CODE",
                    "UPDATE", "IMPLEMENT", "DEPLOY",
                ] else "Yin"
                emoji = "⚡" if activity_type == "Yang" else "🌊"
                click.echo(f"  {timestamp} {emoji} {activity_type:4} - {activity}")
    except Exception as e:
        click.echo(f"❌ History error: {e}", err=True)
