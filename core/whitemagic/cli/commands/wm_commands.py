"""CLI command for the WhiteMagic meta-tool ('wm').

Usage:
    wm "remember that the API uses X-User-Id headers"
    wm "search for architecture memories" --limit 10
    wm "think about the architecture" --route gana_three_stars.reasoning.bicameral
    wm --help-info
"""
import json as _json

import click


@click.command(name="wm")
@click.argument("thought", required=False)
@click.option("--route", default=None, help="Explicit route: gana_name or gana_name.sub_tool")
@click.option("--args", default=None, help="JSON dict of args to pass through")
@click.option("--help-info", is_flag=True, help="Show wm meta-tool help")
def wm_command(thought: str | None, route: str | None, args: str | None, help_info: bool) -> None:
    """WhiteMagic meta-tool — single entry point for all operations."""
    if help_info:
        from whitemagic.tools.handlers.meta_tool import handle_wm_help
        result = handle_wm_help()
        click.echo(_json.dumps(result, indent=2, default=str))
        return

    if not thought and not route:
        click.echo("Usage: wm <thought> [--route gana.subtool] [--args '{}']")
        click.echo("Run 'wm --help-info' for detailed help.")
        return

    from whitemagic.tools.handlers.meta_tool import handle_wm

    kwargs: dict = {}
    if thought:
        kwargs["thought"] = thought
    if route:
        kwargs["route"] = route
    if args:
        try:
            kwargs["args"] = _json.loads(args)
        except _json.JSONDecodeError as e:
            click.echo(f"Invalid --args JSON: {e}", err=True)
            return

    result = handle_wm(**kwargs)
    click.echo(_json.dumps(result, indent=2, default=str))
