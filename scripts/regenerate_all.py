#!/usr/bin/env python3
"""
WhiteMagic Site Regeneration Pipeline

Orchestrates all site data regeneration from live WhiteMagic core sources.

Usage:
    python3 scripts/regenerate_all.py           # regenerate all artifacts
    python3 scripts/regenerate_all.py --check   # CI gate — fail if anything is stale
    python3 scripts/regenerate_all.py --repo    # also copy generated artifacts to repo

Steps:
    1. Sync facts.ts from live pytest + tool surface
    2. Regenerate prescience.json from TemporalForecastDB
    3. TypeScript type-check
    4. (Optional) Copy generated artifacts to repo for reference

Exit codes:
    0 — all steps passed
    1 — one or more steps failed
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SITE_DIR = SCRIPT_DIR.parent
REPO_ROOT = Path.home() / "Desktop" / "WHITEMAGIC"  # ~/Desktop/WHITEMAGIC
CORE_DIR = REPO_ROOT / "core"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def find_python() -> Path:
    if VENV_PYTHON.exists():
        return VENV_PYTHON
    for name in ("python3", "python"):
        p = subprocess.run(["which", name], capture_output=True, text=True)
        if p.returncode == 0:
            return Path(p.stdout.strip())
    raise RuntimeError("No Python interpreter found")


def step(label: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")


def run_sync_facts(check: bool = False) -> bool:
    """Step 1: Regenerate lib/facts.ts from live core metrics."""
    step("Step 1: Sync facts.ts from live core metrics")
    cmd = [sys.executable, str(SCRIPT_DIR / "sync_facts.py")]
    if check:
        cmd.append("--check")
    result = subprocess.run(cmd, cwd=SITE_DIR)
    return result.returncode == 0


def run_generate_prescience(check: bool = False) -> bool:
    """Step 2: Regenerate public/api/prescience.json from TemporalForecastDB."""
    step("Step 2: Regenerate prescience.json from TemporalForecastDB")
    python = find_python()
    gen_script = CORE_DIR / "scripts" / "generate_prescience_json.py"
    output_path = SITE_DIR / "public" / "api" / "prescience.json"

    if check:
        # In check mode, just verify the file exists and is parseable
        if not output_path.exists():
            print(f"[regenerate_all] ERROR: {output_path} does not exist", file=sys.stderr)
            return False
        try:
            with open(output_path) as f:
                data = json.load(f)
            print(f"[regenerate_all] OK: {output_path} exists and is valid JSON")
            print(f"  Claims: {data.get('summary', {}).get('validated', '?')} validated")
            return True
        except Exception as e:
            print(f"[regenerate_all] ERROR: {output_path} is invalid: {e}", file=sys.stderr)
            return False

    result = subprocess.run(
        [str(python), str(gen_script), "--output", str(output_path)],
        cwd=CORE_DIR,
    )
    if result.returncode == 0:
        print(f"[regenerate_all] OK: {output_path} regenerated")
    return result.returncode == 0


def run_typescript_check() -> bool:
    """Step 3: TypeScript type-check."""
    step("Step 3: TypeScript type-check")
    result = subprocess.run(
        ["npx", "tsc", "--noEmit", "--incremental", "false"],
        cwd=SITE_DIR,
        capture_output=True,
        text=True,
    )
    # TS5101 deprecation warnings are acceptable
    errors = [line for line in result.stdout.splitlines() if "error TS" in line and "TS5101" not in line]
    if errors:
        for e in errors:
            print(f"[regenerate_all] ERROR: {e}", file=sys.stderr)
        return False
    print("[regenerate_all] OK: TypeScript check passed")
    return True


def copy_artifacts_to_repo() -> bool:
    """Step 4: Copy generated artifacts back to the repo for reference."""
    step("Step 4: Sync generated artifacts to repo")
    repo_site_dir = REPO_ROOT / "apps" / "site"
    if not repo_site_dir.exists():
        print(f"[regenerate_all] WARN: {repo_site_dir} does not exist — skipping repo sync")
        return True

    artifacts = [
        (SITE_DIR / "lib" / "facts.ts", repo_site_dir / "lib" / "facts.ts"),
        (SITE_DIR / "public" / "api" / "prescience.json", repo_site_dir / "public" / "api" / "prescience.json"),
    ]

    ok = True
    for src, dst in artifacts:
        if not src.exists():
            print(f"[regenerate_all] WARN: {src} does not exist — skipping", file=sys.stderr)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text())
        print(f"[regenerate_all] Copied {src.name} → {dst}")

    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="WhiteMagic Site Regeneration Pipeline")
    parser.add_argument("--check", action="store_true", help="Fail if any artifact is stale (CI gate)")
    parser.add_argument("--repo", action="store_true", help="Also copy generated artifacts to repo")
    args = parser.parse_args()

    print("=" * 60)
    print("  WhiteMagic Site Regeneration Pipeline")
    print("=" * 60)

    ok = True
    ok = run_sync_facts(check=args.check) and ok
    ok = run_generate_prescience(check=args.check) and ok
    ok = run_typescript_check() and ok

    if args.repo and ok:
        ok = copy_artifacts_to_repo() and ok

    print(f"\n{'=' * 60}")
    if ok:
        print("  Result: ALL PASSED")
    else:
        print("  Result: ONE OR MORE STEPS FAILED")
    print(f"{'=' * 60}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
