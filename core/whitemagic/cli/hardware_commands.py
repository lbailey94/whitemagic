"""Hardware CLI commands for adaptive inference."""
# ruff: noqa: BLE001

import click

try:
    from whitemagic.hardware import get_hardware_monitor, get_hardware_recommendations
    HAS_HARDWARE = True
except ImportError:
    HAS_HARDWARE = False


@click.group()
def hardware():
    """Hardware monitoring and recommendations."""
    pass


@hardware.command()
def status():
    """Show current hardware state."""
    if not HAS_HARDWARE:
        click.echo("❌ Hardware monitoring not available")
        return

    try:
        monitor = get_hardware_monitor()
        stats = monitor.get_stats()

        click.echo("\n🖥️  Hardware Status")
        click.echo("=" * 50)

        state = stats['current_state']
        click.echo("\n📊 Current State:")
        click.echo(f"  CPU: {state['cpu_percent']:.1f}%")
        click.echo(f"  Memory: {state['memory_percent']:.1f}% ({state['memory_available_gb']:.1f} GB available)")
        click.echo(f"  Thermal: {state['thermal_state']}")
        click.echo(f"  Power: {'Battery' if state['on_battery'] else 'AC Power'}")

        click.echo("\n⚙️  Thresholds:")
        thresholds = stats['thresholds']
        click.echo(f"  CPU High: {thresholds['cpu_high']}%")
        click.echo(f"  CPU Critical: {thresholds['cpu_critical']}%")
        click.echo(f"  Memory High: {thresholds['memory_high']}%")
        click.echo(f"  Memory Critical: {thresholds['memory_critical']}%")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@hardware.command()
def suggest():
    """Get hardware-based inference recommendations."""
    if not HAS_HARDWARE:
        click.echo("❌ Hardware monitoring not available")
        return

    try:
        recommendations = get_hardware_recommendations()

        click.echo("\n💡 Inference Recommendations")
        click.echo("=" * 50)

        click.echo("\n🎯 Allowed Tiers:")
        click.echo(f"  Fast: {'✅' if recommendations['allow_fast'] else '❌'}")
        click.echo(f"  Explore: {'✅' if recommendations['allow_explore'] else '❌'}")
        click.echo(f"  Deep: {'✅' if recommendations['allow_deep'] else '❌'}")

        click.echo(f"\n⚡ Max Parallel: {recommendations['max_parallel']}")

        if recommendations['reason']:
            click.echo("\n📝 Reasons:")
            for reason in recommendations['reason']:
                click.echo(f"  • {reason}")
        else:
            click.echo("\n✅ All systems optimal")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


if __name__ == '__main__':
    hardware()
