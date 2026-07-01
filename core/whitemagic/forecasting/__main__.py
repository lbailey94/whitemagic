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

from whitemagic.forecasting import tzpf
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
    click.echo(
        f"  Calibration gap:    {s['calibration_gap']:+.3f}  (- = underconfident)"
    )
    click.echo()
    click.echo("Categories:")
    for cat, count in s["categories"].items():
        click.echo(f"  {cat}: {count}")


@cli.command()
@click.option(
    "--status",
    type=click.Choice(
        ["validated", "pending", "falsified", "expired"], case_sensitive=False
    ),
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
        cat = (
            (r.get("category", "?")[:18] + "..")
            if len(r.get("category", "")) > 20
            else r.get("category", "?")
        )
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
        click.echo(f"[{low:.1f}, {high:.1f})   {mf:<15.3f} {mo_str:<15} {cnt:>6}")


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
    for key in (
        "brier_score",
        "reliability",
        "resolution",
        "uncertainty",
        "bss",
        "brier_index",
        "calibration_gap",
    ):
        val = decomp[key]
        if key == "brier_index":
            click.echo(f"  {key:<15}: {val:.1f}%")
        else:
            click.echo(f"  {key:<15}: {val:.4f}")


@cli.command()
@click.option(
    "--output", "-o", type=click.Path(), help="Write JSON to file instead of stdout."
)
def json_dump(output: str | None) -> None:
    """Export full ledger state (summary + claims + calibration) as JSON."""
    db = _db()
    payload = db.to_json(indent=2)
    if output:
        Path(output).write_text(payload, encoding="utf-8")
        click.echo(f"Wrote {len(payload)} characters to {output}")
    else:
        click.echo(payload)


@cli.command()
@click.option(
    "--actions-taken",
    type=int,
    default=None,
    help="Known count of actions taken on predictions.",
)
def tzpf_cmd(actions_taken: int | None) -> None:
    """Print Transition-Zone Prescience Framework (TZPF) scorecard."""
    db = _db()
    claims = db.export_claims()
    scorecard = tzpf.compute_tzpf(claims, actions_taken=actions_taken)

    click.echo("Transition-Zone Prescience Framework (TZPF)")
    click.echo("=" * 50)
    click.echo(f"  Claims total:      {scorecard['claims_total']}")
    click.echo(f"  Validated:         {scorecard['claims_validated']}")
    click.echo()

    comp = scorecard["composite"]
    click.echo("Composite Metrics")
    click.echo("-" * 30)
    click.echo(f"  Directional Foresight (DFI):   {comp['directional_prescience']:.0f}")
    tar = comp.get("timeline_calibration")
    click.echo(
        f"  Temporal Acceleration (TAR):   {tar:.2f}"
        if tar
        else "  Temporal Acceleration (TAR):   N/A"
    )
    click.echo(f"  Hyperstition (HC):             {comp['hyperstitional_potency']:.2f}")
    sg = comp.get("confidence_shyness")
    click.echo(
        f"  Shyness Gap (BCI):             {sg:+.3f}"
        if sg is not None
        else "  Shyness Gap (BCI):             N/A"
    )
    click.echo(
        f"  Partial Validation (PVS):      {comp['validation_completeness']:.2f}"
    )
    click.echo(f"  Narrative Resonance (NRS):     {comp['narrative_resonance']:.1f}")
    click.echo(
        f"  Positioning (PI):              {comp['action_orientation']:.2f}  [{scorecard['metrics']['pi']['status']}]"
    )
    click.echo()

    click.echo("DFI by Category")
    click.echo("-" * 30)
    for cat, data in scorecard["metrics"]["dfi"]["by_category"].items():
        click.echo(
            f"  {cat:<20} raw={data['raw_points']:>6.0f}  w={data['weighted']:>7.0f}"
        )

    if comp["action_orientation"] is not None and comp["action_orientation"] < 0.5:
        click.echo()
        click.echo("⚠  LOW POSITIONING INDEX")
        click.echo("   Actions taken / Actions implied is below 0.5.")
        click.echo("   Consider filing the LLC, submitting grants, or publishing.")


@cli.command()
def machine_time() -> None:
    """Print machine-time estimation profiles and CRPS calibration."""
    from whitemagic.core.consciousness.machine_time import get_machine_time_estimator

    est = get_machine_time_estimator()
    profile = est.get_profile()
    crps_summary = est.get_crps_summary()

    click.echo("Machine-Time Estimation Profiles")
    click.echo("=" * 50)
    click.echo(f"  Tools tracked:     {profile['total_tools_tracked']}")
    click.echo(f"  Total observations: {profile['total_observations']}")
    click.echo()

    if profile["tool_profiles"]:
        click.echo("Per-Tool Duration Profiles")
        click.echo("-" * 50)
        click.echo(f"{'Tool':<30} {'Count':>6} {'Median':>10} {'P90':>10} {'Mean':>10}")
        click.echo("-" * 50)
        for tool, stats in sorted(
            profile["tool_profiles"].items(), key=lambda x: x[1]["count"], reverse=True
        ):
            click.echo(
                f"{tool[:28]:<30} {stats['count']:>6} {stats['median']:>10.6f} {stats['p90']:>10.6f} {stats['mean']:>10.6f}"
            )
        click.echo()

    if profile["type_profiles"]:
        click.echo("Per-Operation-Type Profiles")
        click.echo("-" * 50)
        click.echo(f"{'Type':<20} {'Count':>6} {'Median':>10} {'P90':>10}")
        click.echo("-" * 50)
        for op_type, stats in sorted(
            profile["type_profiles"].items(), key=lambda x: x[1]["count"], reverse=True
        ):
            click.echo(
                f"{op_type[:18]:<20} {stats['count']:>6} {stats['median']:>10.6f} {stats['p90']:>10.6f}"
            )
        click.echo()

    click.echo("CRPS Calibration Summary")
    click.echo("-" * 50)
    if crps_summary["count"] == 0:
        click.echo("  No predictions recorded yet.")
    else:
        click.echo(f"  Predictions scored:  {crps_summary['count']}")
        click.echo(f"  Mean CRPS:           {crps_summary['mean_crps']}")
        click.echo(f"  Median CRPS:         {crps_summary['median_crps']}")
        click.echo(f"  Mean log-ratio err:  {crps_summary['mean_log_ratio_error']}")
        click.echo(f"  MAE log-ratio err:   {crps_summary['mae_log_ratio_error']}")
        if crps_summary.get("per_type"):
            click.echo()
            click.echo("  By Operation Type:")
            for op_type, stats in crps_summary["per_type"].items():
                click.echo(
                    f"    {op_type:<20} count={stats['count']:>4}  mean_crps={stats['mean_crps']}"
                )


@cli.command()
def crps() -> None:
    """Print CRPS decomposition for machine-time predictions."""
    from whitemagic.core.consciousness.machine_time import get_machine_time_estimator

    est = get_machine_time_estimator()

    import json

    predictions: list[float] = []
    actuals: list[float] = []
    sigmas: list[float] = []

    if est.log_path.exists():
        with open(est.log_path) as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if "predicted_seconds" in entry and "actual_seconds" in entry:
                    predictions.append(entry["predicted_seconds"])
                    actuals.append(entry["actual_seconds"])
                    # Reconstruct sigma from p90-p50 if available, else 20% of prediction
                    sigma = max(entry.get("predicted_seconds", 0) * 0.2, 0.001)
                    sigmas.append(sigma)

    if not predictions:
        click.echo("No machine-time predictions with CRPS data yet.")
        click.echo("Run some tool calls first to accumulate prediction data.")
        return

    from whitemagic.forecasting.scoring import crps_decomposition, dagstuhl_score

    decomp = crps_decomposition(predictions, actuals, sigmas)
    dagstuhl = dagstuhl_score(predictions, actuals, sigmas)

    click.echo("CRPS Decomposition (Machine-Time Predictions)")
    click.echo("=" * 50)
    click.echo(f"  Predictions scored:  {decomp['count']}")
    click.echo(f"  Mean CRPS:           {decomp['mean_crps']}")
    click.echo(f"  Miscalibration:      {decomp['miscalibration']}")
    click.echo(f"  Discrimination:      {decomp['discrimination']}")
    click.echo(f"  Uncertainty:         {decomp['uncertainty']}")
    click.echo(f"  CRPS Climatology:    {decomp['crps_climatology']}")
    click.echo(f"  Skill Score:         {decomp['skill_score']}")
    click.echo()
    click.echo("Dagstuhl Comprehensive Scoring")
    click.echo("-" * 50)
    click.echo(f"  Mean Log Score:      {dagstuhl['mean_log_score']}")
    click.echo(f"  QS-50 (median):      {dagstuhl['mean_quantile_score_50']}")
    click.echo(f"  QS-90:               {dagstuhl['mean_quantile_score_90']}")
    click.echo(f"  MAE:                 {dagstuhl['mae']}")
    click.echo(f"  MAPE:                {dagstuhl['mape']}%")
    click.echo(f"  Bias:                {dagstuhl['bias']}")
    click.echo(f"  Log-ratio error:     {dagstuhl['mean_log_ratio_error']}")
    click.echo(f"  MAE log-ratio:       {dagstuhl['mae_log_ratio_error']}")


if __name__ == "__main__":
    cli()
