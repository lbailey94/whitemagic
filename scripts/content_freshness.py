#!/usr/bin/env python3
"""
Content Freshness Scanner v1.0.0

Scans all MDX essays and canonical documents for last_verified frontmatter.
Flags any content older than 90 days without a recent verification.
Generates a freshness report as JSON.

Usage:
    python scripts/content_freshness.py
    python scripts/content_freshness.py --max-age 60  # 60-day threshold
    python scripts/content_freshness.py --output /tmp/freshness.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import frontmatter as _fm

# Paths to scan for content freshness
SCAN_PATHS: list[tuple[str, str]] = [
    ("apps/site/content/essays/", "Essays (MDX)"),
    ("docs/essay_frameworks/", "Essay Frameworks"),
    ("docs/message_board/", "Message Board"),
    ("docs/architecture/", "Architecture Docs"),
    ("docs/strategy_manifestos/", "Strategy Manifestos"),
    ("docs/plans/", "Plans"),
]

DEFAULT_MAX_AGE_DAYS = 90


def scan_directory(
    directory: Path, max_age_days: int
) -> list[dict]:
    """Scan a directory for content files and check freshness."""
    findings: list[dict] = []
    if not directory.exists():
        return findings

    for filepath in directory.rglob("*"):
        if not filepath.is_file():
            continue
        if filepath.suffix not in (".md", ".mdx", ".mdwn", ".markdown"):
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        try:
            post = _fm.loads(content)
        except Exception:
            post = None

        last_verified = None
        if post and post.metadata:
            last_verified = post.metadata.get("last_verified")

        # Check file modification time as fallback
        mtime = datetime.fromtimestamp(
            filepath.stat().st_mtime, tz=timezone.utc
        )
        now = datetime.now(timezone.utc)
        age_days = (now - mtime).days

        status = "ok"
        if last_verified:
            try:
                verified_date = datetime.fromisoformat(last_verified)
                if (now - verified_date).days > max_age_days:
                    status = "stale"
            except ValueError:
                status = "invalid_date"
        elif age_days > max_age_days:
            status = "stale_no_verification"
        elif age_days > max_age_days * 0.5:
            status = "aging"

        if status != "ok":
            findings.append(
                {
                    "path": str(filepath.relative_to(directory.parent.parent)),
                    "last_verified": last_verified,
                    "file_mtime": mtime.isoformat(),
                    "age_days": age_days,
                    "status": status,
                }
            )

    return findings


def generate_report(
    repo_root: Path, max_age_days: int
) -> dict:
    """Generate a full freshness report."""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_age_days": max_age_days,
        "scan_paths": [],
        "total_stale": 0,
        "total_aging": 0,
        "findings": [],
    }

    for rel_path, label in SCAN_PATHS:
        full_path = repo_root / rel_path
        findings = scan_directory(full_path, max_age_days)

        stale = sum(1 for f in findings if f["status"] == "stale")
        aging = sum(1 for f in findings if f["status"] == "aging")

        report["scan_paths"].append(
            {
                "path": rel_path,
                "label": label,
                "files_scanned": len(list(full_path.rglob("*"))) if full_path.exists() else 0,
                "stale": stale,
                "aging": aging,
            }
        )
        report["findings"].extend(findings)
        report["total_stale"] += stale
        report["total_aging"] += aging

    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Content Freshness Scanner"
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help=f"Maximum age in days before flagging (default: {DEFAULT_MAX_AGE_DAYS})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: stdout)",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Repository root path (default: auto-detect)",
    )
    args = parser.parse_args()

    # Auto-detect repo root
    if args.repo_root:
        repo_root = Path(args.repo_root)
    else:
        repo_root = Path(__file__).resolve().parent.parent

    report = generate_report(repo_root, args.max_age)

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        )
        print(f"Report written to {args.output}")
        print(f"  Stale documents: {report['total_stale']}")
        print(f"  Aging documents: {report['total_aging']}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    # Exit with error if stale content exists (for CI)
    if report["total_stale"] > 0:
        print(
            f"\nWARNING: {report['total_stale']} stale document(s) found. "
            f"Update last_verified frontmatter or review content.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
