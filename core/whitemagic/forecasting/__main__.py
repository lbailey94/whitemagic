"""CLI for the WhiteMagic forecasting / prescience module.

Usage
-----
    python -m whitemagic.forecasting summary
    python -m whitemagic.forecasting claims [--status validated|pending|falsified]
    python -m whitemagic.forecasting calibration
    python -m whitemagic.forecasting json [--output prescience.json]
    python -m whitemagic.forecasting brier

Examples
--------
    $ python -m whitemagic.forecasting summary
    WhiteMagic Prescience Scorecard
    =================================
    Validated claims: 15
    Total points:     380
    Avg lead time:    25.3 weeks
    Brier score:      0.0625
    Brier skill:      0.7500

    $ python -m whitemagic.forecasting claims --status validated
    # prints a formatted table of all validated claims
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from whitemagic.forecasting.temporal_db import TemporalForecastDB


def _db() -> TemporalForecastDB:
    db = TemporalForecastDB()
    db.seed_validated_claims()
    return db


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """WhiteMagic Forecasting CLI — prescience audit, Brier scoring, calibration."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
def summary() -> None:
    """Print the prescience scorecard summary."""
    db = _db()
    s = db.export_summary()

    click.echo("WhiteMagic Prescience Scorecard")
    click.echo("=" * 40)
    click.echo(f"  Validated claims:   {s['validated']}")
    click.echo(f"  Pending claims:     {s['pending']}")
    click.echo(f"  Falsified claims:   {s['falsified']}")
    click.echo(f"  Total points:       {s['total_points']}")
    click.echo(f"  Avg lead time:      {s['avg_lead_weeks']} weeks")
    click.echo(f"  Brier score:        {s['brier_score']}")
    click.echo(f"  Brier skill score:  {s['brier_skill_score']}")
    click.echo(f"  Brier Index:        {s['brier_index']}%  (superforecasters ≈ 71%)")
    click.echo(f"  Calibration gap:    {s['calibration_gap']:+.3f}  (- = underconfident)")
    click.echo()
    click.echo("Categories:")
    for cat, count in s["categories"].items():
        click.echo(f"  {cat}: {count}")


@cli.command()
@click.option(
    "--status",
    type=click.Choice(["validated", "pending", "falsified", "expired"], case_sensitive=False),
    help="Filter by claim status.",
)
@click.option("--json-out", is_flag=True, help="Output raw JSON instead of table.")
def claims(status: str | None, json_out: bool) -> None:
    """List predictions (optionally filtered by status)."""
    db = _db()
    rows = db.export_claims(status=status)

    if json_out:
        click.echo(json.dumps(rows, indent=2, default=str))
        return

    if not rows:
        click.echo("No claims found.")
        return

    # Simple table formatting
    header = f"{'Date':<12} {'Status':<12} {'Points':>6} {'Category':<20} Claim"
    click.echo(header)
    click.echo("-" * len(header) + "-" * 40)
    for r in rows:
        date = r.get("source_date", "?")[:10]
        stat = r.get("status", "?")[:12]
        pts = f"{r.get('points', 0):>5.0f}" if r.get("points") is not None else "    —"
        cat = (r.get("category", "?")[:18] + "..") if len(r.get("category", "")) > 20 else r.get("category", "?")
        claim_text = r.get("claim", "?")[:60]
        click.echo(f"{date:<12} {stat:<12} {pts:>6} {cat:<20} {claim_text}")


@cli.command()
def calibration() -> None:
    """Print the calibration curve (reliability diagram data)."""
    db = _db()
    curve = db.calibration(n_bins=5)

    click.echo("Calibration Curve (5 bins)")
    click.echo("=" * 50)
    click.echo(f"{'Bin':<10} {'Mean Forecast':<15} {'Mean Outcome':<15} {'Count':>6}")
    click.echo("-" * 50)
    for bucket in curve:
        low, high = bucket["bin_lower"], bucket["bin_upper"]
        mf = bucket["mean_forecast"]
        mo = bucket["mean_outcome"]
        cnt = bucket["count"]
        mo_str = f"{mo:.3f}" if mo == mo else "—"
        click.echo(
            f"[{low:.1f}, {high:.1f})   {mf:<15.3f} {mo_str:<15} {cnt:>6}"
        )


@cli.command()
def brier() -> None:
    """Print Brier score decomposition (reliability / resolution / uncertainty)."""
    from whitemagic.forecasting.brier import decompose_brier

    db = _db()
    rows = db.all_predictions()
    closed = [r for r in rows if r["status"] in ("validated", "falsified")]
    if not closed:
        click.echo("No closed predictions to score.")
        return

    forecasts = [r["confidence"] for r in closed]
    outcomes = [1 if r["status"] == "validated" else 0 for r in closed]
    decomp = decompose_brier(forecasts, outcomes)

    click.echo("Brier Decomposition")
    click.echo("=" * 30)
    for key in ("brier_score", "reliability", "resolution", "uncertainty", "bss", "brier_index", "calibration_gap"):
        val = decomp[key]
        if key == "brier_index":
            click.echo(f"  {key:<15}: {val:.1f}%")
        else:
            click.echo(f"  {key:<15}: {val:.4f}")


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Write JSON to file instead of stdout.")
def json_dump(output: str | None) -> None:
    """Export full ledger state (summary + claims + calibration) as JSON."""
    db = _db()
    payload = db.to_json(indent=2)
    if output:
        Path(output).write_text(payload, encoding="utf-8")
        click.echo(f"Wrote {len(payload)} characters to {output}")
    else:
        click.echo(payload)


if __name__ == "__main__":
    cli()
