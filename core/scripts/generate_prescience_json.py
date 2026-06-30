#!/usr/bin/env python3
"""Generate /api/prescience.json from TemporalForecastDB.

Exports the validated prescience track record as a static JSON file
that the Next.js API route can serve.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from whitemagic.forecasting.temporal_db import TemporalForecastDB


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate prescience.json from TemporalForecastDB"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("apps/site/public/api/prescience.json"),
        help="Output path for prescience.json (default: apps/site/public/api/prescience.json)",
    )
    args = parser.parse_args()

    db = TemporalForecastDB()
    try:
        db.seed_validated_claims()
    except RuntimeError as e:
        print(f"Warning: {e}", file=sys.stderr)
        return 1

    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "summary": db.export_summary(),
        "claims": db.export_claims(),
        "calibration": db.calibration(n_bins=5),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"Prescience JSON written to {output_path}")
    print(f"Claims: {payload['summary']['total']}")
    print(f"Validated: {payload['summary']['validated']}")
    print(f"Total points: {payload['summary']['total_points']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
