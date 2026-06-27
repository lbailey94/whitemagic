#!/usr/bin/env python3
"""Check git hygiene across local WhiteMagic project workspaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from whitemagic.harmony.git_hygiene import evaluate_git_hygiene


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Parent directory containing WhiteMagic workspace roots.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=0.75,
        help="Exit non-zero if health score is below this threshold.",
    )
    args = parser.parse_args()

    report = evaluate_git_hygiene(args.root)
    if args.format == "markdown":
        sys.stdout.write(report.to_markdown())
    else:
        json.dump(report.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")

    return 0 if report.health_score >= args.fail_under else 1


if __name__ == "__main__":
    raise SystemExit(main())
