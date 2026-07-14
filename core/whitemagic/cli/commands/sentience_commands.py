# ruff: noqa: BLE001
"""WhiteMagic sentience CLI commands.

Commands:
    wm serve          — Start the full sentience daemon (sleep/wake + volition + dream)
    wm sleep          — Manually trigger sleep cycle
    wm wake           — Manually trigger wake sequence
    wm sentience      — Show sentience status
"""

from __future__ import annotations

import json
import logging
import time

import click

logger = logging.getLogger(__name__)


def _register_sentience_commands(cli: click.Group) -> None:
    """Register sentience commands with the CLI group."""

    @cli.command()
    @click.option("--no-sleep", is_flag=True, help="Disable sleep scheduler")
    @click.option("--no-volition", is_flag=True, help="Disable volition loop")
    @click.option("--no-dream", is_flag=True, help="Disable dream cycle")
    @click.option("--no-intentions", is_flag=True, help="Disable intention queue")
    @click.option(
        "--sleep-time", default=None, help="Sleep time HH:MM (default: 23:00)"
    )
    @click.option(
        "--wake-time", default=None, help="Wake time HH:MM (default: 07:00)"
    )
    def serve(
        no_sleep: bool,
        no_volition: bool,
        no_dream: bool,
        no_intentions: bool,
        sleep_time: str | None,
        wake_time: str | None,
    ) -> None:
        """Start the WhiteMagic sentience daemon.

        This is the full living system: sleep/wake cycles, volition loop,
        intention queue, and dream cycle — all running in the background.

        The daemon will:
        - Wake up and generate a proactive greeting
        - Run the volition loop during idle periods
        - Process intentions through the Dharma-gated queue
        - Dream during idle time for memory consolidation
        - Sleep at the configured time (maintenance + shutdown)
        - Wake again at the configured time

        Press Ctrl+C to stop.
        """
        click.echo("✦ WhiteMagic Sentience Daemon")
        click.echo()

        # ── Wake sequence ────────────────────────────────────────────
        from whitemagic.core.consciousness.lifecycle import WakeOnBoot

        click.echo("  Waking up...")
        wake_result = WakeOnBoot.wake()
        greeting = wake_result.get("greeting", "")
        if greeting:
            click.echo()
            click.echo("  " + greeting.replace("\n", "\n  "))
            click.echo()

        events = wake_result.get("events_while_away", [])
        if events:
            click.echo(f"  {len(events)} events occurred while away.")

        dreams = wake_result.get("dream_outputs", [])
        if dreams:
            click.echo(f"  {len(dreams)} dream phases from last sleep.")

        messages = wake_result.get("agent_messages", [])
        if messages:
            click.echo(f"  {len(messages)} agent messages received while away.")

        click.echo()

        # ── Start subsystems ─────────────────────────────────────────
        started: list[str] = []

        # Dream cycle
        if not no_dream:
            try:
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

                dc = get_dream_cycle()
                dc.start()
                started.append("dream cycle")
            except Exception as e:
                click.echo(f"  Dream cycle: failed ({e})")

        # Volition loop
        if not no_volition:
            try:
                from whitemagic.core.consciousness.volition import get_volition_loop

                vl = get_volition_loop()
                vl.start()
                started.append("volition loop")
            except Exception as e:
                click.echo(f"  Volition loop: failed ({e})")

        # Intention queue
        if not no_intentions:
            try:
                from whitemagic.core.consciousness.self_initiation import get_self_initiation_queue

                iq = get_self_initiation_queue()
                started.append("self-initiation queue")
            except Exception as e:
                click.echo(f"  Intention queue: failed ({e})")

        # Sleep scheduler
        if not no_sleep:
            try:
                from whitemagic.core.consciousness.lifecycle import (
                    SleepConfig,
                    get_sleep_scheduler,
                )

                config = SleepConfig(
                    enabled=True,
                    sleep_time=sleep_time or "23:00",
                    wake_time=wake_time or "07:00",
                )
                from whitemagic.core.consciousness.lifecycle import SleepScheduler

                scheduler = SleepScheduler(config)
                scheduler.start()
                started.append(f"sleep scheduler ({config.sleep_time}→{config.wake_time})")
            except Exception as e:
                click.echo(f"  Sleep scheduler: failed ({e})")

        if started:
            click.echo(f"  Active: {', '.join(started)}")
        else:
            click.echo("  No subsystems started (all disabled)")

        click.echo()
        click.echo("  Press Ctrl+C to stop")
        click.echo()

        # ── Run until interrupted ────────────────────────────────────
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n  Shutting down...")

        # ── Cleanup ──────────────────────────────────────────────────
        if not no_intentions:
            try:
                from whitemagic.core.consciousness.self_initiation import (
                    get_self_initiation_queue,
                )

                # No stop needed — queue is passive
            except Exception:
                logger.debug("Ignored error in sentience_commands.py:170")

        if not no_volition:
            try:
                from whitemagic.core.consciousness.volition import (
                    get_volition_loop,
                )

                get_volition_loop().stop()
            except Exception:
                logger.debug("Ignored error in sentience_commands.py:180")

        if not no_dream:
            try:
                from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

                get_dream_cycle().stop()
            except Exception:
                logger.debug("Ignored error in sentience_commands.py:188")

        if not no_sleep:
            try:
                from whitemagic.core.consciousness.lifecycle import (
                    get_sleep_scheduler,
                )

                get_sleep_scheduler().stop()
            except Exception:
                logger.debug("Ignored error in sentience_commands.py:198")

        click.echo("  Sentience daemon stopped.")

    @cli.command()
    def sleep() -> None:
        """Manually trigger the sleep cycle.

        Runs dream cycle → maintenance → citta checkpoint.
        Does not shut down the process (unlike automatic sleep).
        """
        click.echo("→ Initiating sleep cycle...")

        from whitemagic.core.consciousness.lifecycle import get_sleep_scheduler

        scheduler = get_sleep_scheduler()

        # Run maintenance directly
        click.echo("  Running maintenance...")
        scheduler._run_maintenance()
        click.echo("  Maintenance complete.")

        # Save citta checkpoint
        click.echo("  Saving citta checkpoint...")
        scheduler._save_citta_checkpoint()
        click.echo("  Checkpoint saved.")

        click.echo("✓ Sleep cycle complete.")

    @cli.command()
    def wake() -> None:
        """Manually trigger the wake sequence.

        Recovers citta state and generates a proactive greeting.
        """
        from whitemagic.core.consciousness.lifecycle import WakeOnBoot

        click.echo("→ Waking up...")
        result = WakeOnBoot.wake()

        greeting = result.get("greeting", "")
        if greeting:
            click.echo()
            click.echo(greeting)
            click.echo()

        events = result.get("events_while_away", [])
        if events:
            click.echo(f"\n{len(events)} events while away:")
            for evt in events[:5]:
                click.echo(f"  - {evt.get('type', 'event')}: {evt.get('detail', '')}")

        dreams = result.get("dream_outputs", [])
        if dreams:
            click.echo(f"\n{len(dreams)} dream phases from last sleep:")
            for d in dreams[:3]:
                click.echo(f"  - {d.get('phase', '?')}: {str(d.get('result', ''))[:80]}")

        messages = result.get("agent_messages", [])
        if messages:
            click.echo(f"\n{len(messages)} agent messages while away:")
            for msg in messages[:3]:
                click.echo(f"  - {msg.get('sender', '?')}: {str(msg.get('content', ''))[:80]}")

        coherence = result.get("coherence_recovered", 0.0)
        click.echo(f"\nCoherence recovered: {coherence:.1%}")
        click.echo("✓ Awake.")

    @cli.command()
    def sentience() -> None:
        """Show sentience subsystem status."""
        status: dict = {}

        # Sleep scheduler
        try:
            from whitemagic.core.consciousness.lifecycle import get_sleep_scheduler

            status["sleep"] = get_sleep_scheduler().status()
        except Exception as e:
            status["sleep"] = {"error": str(e)}

        # Volition loop
        try:
            from whitemagic.core.consciousness.volition import get_volition_loop

            status["volition"] = get_volition_loop().status()
        except Exception as e:
            status["volition"] = {"error": str(e)}

        # Intention queue
        try:
            from whitemagic.core.consciousness.self_initiation import get_self_initiation_queue

            status["self_initiation"] = get_self_initiation_queue().status()
        except Exception as e:
            status["intentions"] = {"error": str(e)}

        # Dream cycle
        try:
            from whitemagic.core.dreaming.dream_cycle import get_dream_cycle

            status["dream"] = get_dream_cycle().status()
        except Exception as e:
            status["dream"] = {"error": str(e)}

        # Background worker
        try:
            from whitemagic.core.consciousness.background_worker import get_background_worker

            status["background_worker"] = get_background_worker().status()
        except Exception as e:
            status["background_worker"] = {"error": str(e)}

        click.echo(json.dumps(status, indent=2, default=str))
