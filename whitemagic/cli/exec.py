"""CLI commands for terminal execution."""

import click

from ..terminal import Profile, TerminalMCPTools


@click.group()
def exec_cli():
    """Terminal execution commands."""
    pass


@exec_cli.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--cwd", default=None, help="Working directory")
@click.option("--profile", default="agent", type=click.Choice(["dev", "ci", "agent", "prod"]))
def run(command, cwd, profile):
    """Execute a command."""
    cmd = command[0]
    args = list(command[1:])

    profile_enum = Profile(profile)
    tools = TerminalMCPTools(profile=profile_enum)

    result = tools.exec_read(cmd, args, cwd)

    if "error" in result:
        click.secho(f"❌ Error: {result['error']}", fg="red")
        raise SystemExit(1)

    if result["stdout"]:
        click.echo(result["stdout"], nl=False)

    if result["stderr"]:
        click.secho(result["stderr"], fg="yellow", err=True, nl=False)

    if result["exit_code"] != 0:
        raise SystemExit(result["exit_code"])


@exec_cli.command()
@click.option("--days", default=7, help="Days to show")
def audit(days):
    """View audit log."""
    import json
    from datetime import datetime, timedelta

    from ..terminal.audit import AuditLogger

    logger = AuditLogger()
    start_date = datetime.now() - timedelta(days=days)

    entries = []
    for log_file in logger.log_dir.glob("*.jsonl"):
        try:
            file_date = datetime.strptime(log_file.stem, "%Y%m%d")
            if file_date >= start_date:
                with open(log_file) as f:
                    for line in f:
                        entries.append(json.loads(line))
        except:
            continue

    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    click.secho(f"\n📋 Audit Log (last {days} days)\n", bold=True)

    for entry in entries[:50]:
        run_id = entry.get("run_id", "N/A")[:8]
        cmd = entry.get("command", "N/A")
        exit_code = entry.get("exit_code", -1)
        duration = entry.get("duration_ms", 0)
        timestamp = entry.get("timestamp", "")[:19]

        status = "✅" if exit_code == 0 else "❌"
        color = "green" if exit_code == 0 else "red"

        click.echo(f"{timestamp} [{run_id}] ", nl=False)
        click.secho(f"{status}", fg=color, nl=False)
        click.echo(f" {cmd} ({duration:.1f}ms)")

    if not entries:
        click.secho("No audit entries found.", fg="yellow")
