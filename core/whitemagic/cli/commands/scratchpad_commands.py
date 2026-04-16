# mypy: disable-error-code=no-untyped-def
"""Scratchpad CLI Commands
Create, update, analyze, and finalize scratchpads.
"""

import click

from whitemagic.utils.fast_json import dumps_str as _json_dumps


@click.group()
def scratchpad() -> None:
    """Scratchpad management commands"""


@scratchpad.command()
@click.argument("name")
@click.option("--session-id", help="Optional session id to associate")
@click.pass_context
def create(ctx, name: str, session_id: str | None) -> None:
    """Create a new scratchpad"""
    from whitemagic.tools.unified_api import call_tool

    try:
        now = (ctx.obj or {}).get("now") if isinstance(ctx.obj, dict) else None
        json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

        result = call_tool("scratchpad_create", name=name, session_id=session_id, now=now)
        if json_output:
            click.echo(_json_dumps(result, indent=2, sort_keys=True))
            return
        if result.get("status") != "success":
            click.echo(f"❌ Error: {result.get('message', 'Unknown error')}")
            return
        pad = (result.get("details") or {}).get("scratchpad", {}) or {}
        click.echo(f"✅ Scratchpad created: {pad.get('id')}")
        if pad.get("focus"):
            click.echo(f"   Focus: {pad.get('focus')}")
    except Exception as exc:
        click.echo(f"❌ Error creating scratchpad: {exc}")


@scratchpad.command()
@click.argument("scratchpad_id")
@click.argument("section")
@click.argument("content")
@click.pass_context
def update(ctx, scratchpad_id: str, section: str, content: str) -> None:
    """Update a scratchpad section"""
    from whitemagic.tools.unified_api import call_tool

    try:
        now = (ctx.obj or {}).get("now") if isinstance(ctx.obj, dict) else None
        json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

        result = call_tool(
            "scratchpad_update",
            scratchpad_id=scratchpad_id,
            section=section,
            content=content,
            now=now,
        )
        if json_output:
            click.echo(_json_dumps(result, indent=2, sort_keys=True))
            return
        if result.get("status") != "success":
            click.echo(f"❌ Error: {result.get('message', 'Unknown error')}")
            return
        click.echo(f"✅ Scratchpad updated: {scratchpad_id} ({section})")
    except Exception as exc:
        click.echo(f"❌ Error updating scratchpad: {exc}")


@scratchpad.command()
@click.argument("scratchpad_id")
@click.pass_context
def analyze(ctx, scratchpad_id: str) -> None:
    """Run multi-spectral analysis on a scratchpad"""
    from whitemagic.tools.unified_api import call_tool

    click.echo(f"\n🧠 Analyzing scratchpad: {scratchpad_id}\n")
    try:
        now = (ctx.obj or {}).get("now") if isinstance(ctx.obj, dict) else None
        json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

        result = call_tool("analyze_scratchpad", scratchpad_id=scratchpad_id, now=now)
        if json_output:
            click.echo(_json_dumps(result, indent=2, sort_keys=True))
            return
        if result.get("status") != "success":
            click.echo(f"❌ Error: {result.get('message', 'Unknown error')}")
            return

        analysis = (result.get("details") or {}).get("analysis", {}) or {}
        click.echo("═" * 70)
        click.echo(f"\n📊 CONFIDENCE: {analysis.get('confidence', 0):.0%}\n")
        click.echo("═" * 70)
        click.echo(f"\n🧠 SYNTHESIS:\n{analysis.get('synthesis', '')}\n")
        click.echo("─" * 70)
        click.echo(f"\n💡 WISDOM:\n{analysis.get('wisdom', '')}\n")
        click.echo("─" * 70)

        perspectives = analysis.get("perspectives", [])
        click.echo(f"\n🔍 PERSPECTIVES ANALYZED: {len(perspectives)}")
        for perspective in perspectives:
            lens = perspective.get("lens", "unknown")
            emoji = {
                "i_ching": "☯️",
                "wu_xing": "🌸",
                "art_of_war": "⚔️",
                "zodiac": "♈",
            }.get(lens, "🔮")
            guidance = perspective.get("guidance", "")
            click.echo(f"\n  {emoji} {lens.upper()} (confidence: {perspective.get('confidence', 0):.0%})")
            click.echo(f"     {guidance[:100]}...")

        click.echo(f"\n📚 PATTERNS MATCHED: {analysis.get('patterns_matched', 0)}")
        click.echo("\n" + "═" * 70 + "\n")
    except Exception as exc:
        click.echo(f"❌ Error analyzing scratchpad: {exc}")


@scratchpad.command()
@click.argument("scratchpad_id")
@click.option(
    "--analyze/--no-analyze",
    default=True,
    help="Run multi-spectral analysis (default: yes)",
)
@click.option(
    "--type",
    "memory_type",
    default="long_term",
    type=click.Choice(["short_term", "long_term"]),
    help="Memory type (default: long_term)",
)
@click.pass_context
def finalize(ctx, scratchpad_id: str, analyze: bool, memory_type: str) -> None:
    """Finalize scratchpad to permanent memory"""
    from whitemagic.tools.unified_api import call_tool

    click.echo(f"\n📝 Finalizing scratchpad: {scratchpad_id}\n")
    if analyze:
        click.echo("🧠 Running multi-spectral analysis...\n")

    try:
        now = (ctx.obj or {}).get("now") if isinstance(ctx.obj, dict) else None
        json_output = (ctx.obj or {}).get("json_output") if isinstance(ctx.obj, dict) else False

        result = call_tool(
            "scratchpad_finalize",
            scratchpad_id=scratchpad_id,
            auto_analyze=analyze,
            memory_type=memory_type,
            now=now,
        )
        if json_output:
            click.echo(_json_dumps(result, indent=2, sort_keys=True))
            return
        if result.get("status") != "success":
            click.echo(f"❌ Error: {result.get('message', 'Unknown error')}")
            return

        details = result.get("details", {}) or {}
        click.echo("✅ Scratchpad finalized")
        if analyze and details.get("analysis"):
            analysis = details["analysis"]
            click.echo("   🧠 Multi-spectral synthesis included")
            click.echo(f"   📊 Confidence: {analysis.get('confidence', 0):.0%}")
            click.echo(f"   🔍 Perspectives: {analysis.get('perspectives_used', 0)}")
            click.echo(f"   📚 Patterns matched: {analysis.get('patterns_matched', 0)}")
        click.echo(f"   📁 Memory: {details.get('memory_path')}\n")
    except Exception as exc:
        click.echo(f"❌ Error finalizing scratchpad: {exc}")
