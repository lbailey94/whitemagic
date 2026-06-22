#!/usr/bin/env python3
"""Auto-fix safe Ruff style issues and report remainder.

This is a non-blocking hygiene script. It auto-fixes safe issues
(whitespace, trailing spaces, semicolons) and reports what remains.

Usage:
    python scripts/style_hygiene.py              # Check + auto-fix
    python scripts/style_hygiene.py --check-only # Report only, no fixes
    python scripts/style_hygiene.py --ci         # Exit 1 if high-signal rules fail

Run periodically or in CI with continue-on-error for style-only checks.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE = REPO_ROOT / "core"
WHITEMAGIC = CORE / "whitemagic"

# Rules that are auto-fixable and safe
SAFE_AUTO_FIX = "W291,W293,E702,F841,F823"
# Rules that MUST be zero (semantic correctness)
HIGH_SIGNAL = "F821,F601,F401"
# All style rules (non-blocking advisory)
ALL_STYLE = "E,F,W"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=CORE,
        capture_output=True,
        text=True,
    )


def count_errors(stdout: str) -> int:
    """Extract error count from ruff output."""
    for line in stdout.splitlines():
        if "Found" in line and "error" in line:
            try:
                return int(line.split("Found")[1].split()[0])
            except (ValueError, IndexError):
                pass
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="WhiteMagic style hygiene")
    parser.add_argument("--check-only", action="store_true", help="Report only, do not fix")
    parser.add_argument("--ci", action="store_true", help="Exit 1 if high-signal rules fail")
    args = parser.parse_args()

    print("=" * 60)
    print("WhiteMagic Style Hygiene")
    print("=" * 60)

    exit_code = 0

    # 1. High-signal rules (must be zero)
    print(f"\n[1/3] High-signal rules ({HIGH_SIGNAL})...")
    high_result = run([
        sys.executable, "-m", "ruff", "check", "whitemagic/",
        "--select", HIGH_SIGNAL,
        "--ignore", "E501",
    ])
    high_count = count_errors(high_result.stdout)
    if high_count == 0:
        print("  ✅ Clean")
    else:
        print(f"  ❌ {high_count} issues found")
        print(high_result.stdout)
        exit_code = 1

    # 2. Auto-fix safe issues
    if not args.check_only:
        print(f"\n[2/3] Auto-fixing safe issues ({SAFE_AUTO_FIX})...")
        fix_result = run([
            sys.executable, "-m", "ruff", "check", "whitemagic/",
            "--select", SAFE_AUTO_FIX,
            "--ignore", "E501",
            "--fix", "--unsafe-fixes",
        ])
        fix_count = count_errors(fix_result.stdout)
        if fix_count == 0:
            print("  ✅ All fixable issues resolved")
        else:
            print(f"  ℹ️  {fix_count} issues remain (not auto-fixable)")
            if fix_count > 0 and not args.ci:
                print(fix_result.stdout)

    # 3. Style-only remainder (non-blocking)
    print(f"\n[3/3] Style-only remainder (E701, E402, etc. — non-blocking)...")
    style_result = run([
        sys.executable, "-m", "ruff", "check", "whitemagic/",
        "--select", ALL_STYLE,
        "--ignore", "E501",
    ])
    style_count = count_errors(style_result.stdout)
    if style_count == 0:
        print("  ✅ All style rules clean")
    else:
        print(f"  ℹ️  {style_count} style notes")
        print("  (Non-blocking: E701 = compact one-liners, E402 = conditional imports)")
        if not args.ci:
            # Show first 10 in non-CI mode
            lines = style_result.stdout.strip().splitlines()
            for line in lines[:20]:
                print(f"    {line}")

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("Style hygiene passed.")
    else:
        print("Style hygiene FAILED — high-signal rules have issues.")
    print("=" * 60)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
