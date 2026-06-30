# ruff: noqa: BLE001
# mypy: disable-error-code=no-untyped-def
"""Health & Resonance CLI Commands
System health checks, dharma assessment, and related diagnostics.
"""

from importlib.util import find_spec

import click


@click.command(name="immune-status")
def immune_status() -> None:
    """Check immune system status."""
    click.echo("\n🛡️  Immune System Status")
    click.echo("=" * 30)
    try:
        from whitemagic.core.immune.health_check import get_health_check

        checker = get_health_check()
        result = checker.check_all()
        click.echo(f"✅ Overall Status: {result['overall_status']}")
        if result["issues"]:
            for issue in result["issues"]:
                click.echo(f"   ⚠️  {issue}")
        else:
            click.echo("   ✨ All systems healthy")
    except Exception as e:
        click.echo(f"⚠️  Immune check unavailable: {e}")


@click.command(name="homeostasis-check")
def homeostasis_check() -> None:
    """Run homeostasis check."""
    click.echo("\n⚖️  Homeostasis Check")
    click.echo("=" * 30)
    try:
        from whitemagic.homeostasis import (
            HomeostaticMonitor,  # type: ignore[import-not-found]
        )

        monitor = HomeostaticMonitor()
        status_data = monitor.check_status()
        click.echo(f"✅ Status: {status_data.get('status', 'unknown')}")
        if status_data.get("alerts"):
            for alert in status_data["alerts"]:
                click.echo(f"   ⚠️  {alert}")
        else:
            click.echo("   ✨ System balanced")
    except Exception as e:
        click.echo(f"⚠️  Homeostasis check unavailable: {e}")


@click.command(name="doctor-deep")
def doctor_deep() -> None:
    """Deep system capability and health audit (legacy / unstable)."""
    click.echo("\n🏥 WhiteMagic Doctor")
    click.echo("=" * 30)

    try:
        from whitemagic.core.alignment.grimoire_audit import get_auditor

        auditor = get_auditor()
        report = auditor.generate_capability_report()
        click.echo(f"✨ Spells Discovered: {report['total_spells']}")
        for cat, count in report["categories"].items():
            click.echo(f"   • {cat.replace('_', ' ').title()}: {count}")
    except Exception as e:
        click.echo(f"⚠️  Grimoire audit failed: {e}")

    try:
        from whitemagic.core.polyglot.mansion_bridge import get_mansion_bridge

        bridge = get_mansion_bridge()
        click.echo("\n🚀 Polyglot Acceleration")
        status = bridge.get_status()
        for name, bs in status.items():
            symbol = "✅" if bs.available else "❌"
            click.echo(f"   {symbol} {name.upper()}")
    except Exception as e:
        click.echo(f"⚠️  MansionBridge check failed: {e}")

    click.echo("\n🌐 Polyglot Bridges")
    if find_spec("whitemagic_rs") is not None:
        click.echo("   ✅ Rust (whitemagic_rs)")
    else:
        click.echo("   ❌ Rust (whitemagic_rs not installed)")
    try:
        from whitemagic.core.acceleration.julia_interface import JuliaBridge

        jb = JuliaBridge()
        symbol = "✅" if jb.check_availability() else "❌"
        click.echo(f"   {symbol} Julia ({jb.julia_bin})")
    except (ImportError, ModuleNotFoundError) as e:
        click.echo(f"   ❌ Julia ({e})")
    try:
        from whitemagic.core.acceleration.haskell_interface import HaskellBridge

        hb = HaskellBridge()
        symbol = "✅" if hb.available else "❌"
        click.echo(f"   {symbol} Haskell (divination FFI)")
    except (ImportError, ModuleNotFoundError) as e:
        click.echo(f"   ❌ Haskell ({e})")

    try:
        from whitemagic.core.temporal.chronos_guard import get_chronos_guard

        chronos = get_chronos_guard()
        pulse = chronos.generate_pulse()
        click.echo("\n⏳ Temporal Grounding")
        click.echo(f"   Now: {pulse.timestamp}")
        click.echo(f"   Lunar: {pulse.mansion_name} ({pulse.lunar_phase:.2f})")
        click.echo("   ✅ Resonance synchronized")
    except Exception as e:
        click.echo(f"\n⚠️  Temporal grounding failed: {e}")


@click.command(name="orchestra-health")
def orchestra_health() -> None:
    """Full system orchestra health check."""
    click.echo("\n🎼 Orchestra Health")
    click.echo("=" * 30)
    try:
        from whitemagic.core.automation.orchestra import AutomationOrchestra

        orchestra = AutomationOrchestra()
        report = orchestra.perform_health_check()
        click.echo(f"✅ Overall Health: {report['overall_health']}")
        click.echo(f"   Systems Checked: {len(report['systems'])}")
        if report.get("recommendations"):
            click.echo("   Recommendations:")
            for rec in report["recommendations"][:3]:
                click.echo(f"     • {rec}")
    except ImportError:
        click.echo("⚠️  Orchestra requires: whitemagic.automation module")
    except Exception as error:
        click.echo(f"⚠️  Orchestra health unavailable: {error}")


@click.command(name="dharma-assess")
def dharma_assess() -> None:
    """Assess dharma alignment."""
    click.echo("\n☸️  Dharma Assessment")
    click.echo("=" * 30)
    try:
        from whitemagic.gardens.dharma.core import get_dharma_core

        dharma = get_dharma_core()
        history = dharma.get_history(limit=5)
        allowed_count = sum(1 for h in history if h.get("allowed", True))
        total = len(history) if history else 1
        alignment_pct = (allowed_count / total) * 100
        click.echo(
            f"✅ Alignment: {alignment_pct:.0f}% ({allowed_count}/{total} actions aligned)"
        )
        click.echo(f"   Principles active: {len(dharma.principles)}")
    except Exception as e:
        click.echo(f"⚠️  Dharma assessment unavailable: {e}")


@click.command(name="dharma-check-boundary")
@click.argument("action")
def dharma_check_boundary(action: str) -> None:
    """Check if an action violates dharma boundaries."""
    try:
        from whitemagic.gardens.dharma.boundaries import BoundaryType, check_boundaries

        boundary = check_boundaries(action, {})
        if (
            boundary.boundary_type == BoundaryType.INTERFERING
            and boundary.confidence > 0.6
        ):
            click.echo(boundary.reasoning)
            click.get_current_context().exit(1)
        click.echo(boundary.reasoning)
        click.get_current_context().exit(0)
    except Exception as e:
        click.echo(f"⚠️  Boundary check unavailable: {e}")
        click.get_current_context().exit(1)


@click.command(name="voice-narrate")
@click.argument("prompt")
def voice_narrate(prompt: str) -> None:
    """Generate a narrative from the Voice garden."""
    click.echo("\n🎙️  Voice Narrate")
    click.echo("=" * 30)
    try:
        from whitemagic.gardens.voice.narrator import get_narrator

        narrator = get_narrator()
        narrative = narrator.narrate(prompt)
        click.echo(f"✅ Narrative: {narrative}")
        click.echo(f"   Story: {narrator.current_story}")
        click.echo(f"   Chapter: {narrator.current_chapter}")
    except Exception as e:
        click.echo(f"⚠️  Voice narrate unavailable: {e}")


@click.command(name="rabbit-hole-start")
@click.argument("topic")
def rabbit_hole_start(topic: str) -> None:
    """Start a deep research rabbit-hole."""
    click.echo("\n🐇 Rabbit Hole Start")
    click.echo("=" * 30)
    try:
        from whitemagic.gardens.wisdom.rabbit_hole import (
            RabbitHoleEntry,
            ResearchReport,
        )

        entry = RabbitHoleEntry(term=topic, depth=0)
        report = ResearchReport(title=f"Research: {topic}", topics=[topic])
        report.entries.append(entry)
        click.echo(f"✅ Rabbit hole started for: {topic}")
        click.echo("   Depth: 0 (starting point)")
        click.echo("   Use research tools to explore further")
    except Exception as e:
        click.echo(f"⚠️  Rabbit hole unavailable: {e}")


def register_health_commands(main_group: click.Group) -> None:
    """Register all health/resonance commands onto the main CLI group."""
    main_group.add_command(immune_status)
    main_group.add_command(homeostasis_check)
    main_group.add_command(doctor_deep)
    main_group.add_command(orchestra_health)
    main_group.add_command(dharma_assess)
    main_group.add_command(dharma_check_boundary)
    main_group.add_command(voice_narrate)
    main_group.add_command(rabbit_hole_start)
