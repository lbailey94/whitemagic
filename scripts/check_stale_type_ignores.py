#!/usr/bin/env python3
"""scripts/check_stale_type_ignores.py — Inventory and detect stale type: ignore comments.

Scans for `# type: ignore` comments and categorizes them:
- `# type: ignore` (bare) — should specify error code
- `# type: ignore[import-untyped]` — intentional, for optional deps
- `# type: ignore[attr-defined]` — may be stale if attribute now exists

This script does NOT remove type ignores blindly. It inventories them
for manual review, in accordance with the strategy doc decision rule:
"Do not optimize without measurements."

Usage:
    python3 scripts/check_stale_type_ignores.py           # Report
    python3 scripts/check_stale_type_ignores.py --check   # CI gate (warn only)
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = REPO_ROOT / "core"


def _scan_type_ignores(root: Path) -> list[dict]:
    """Scan all .py files for type: ignore comments."""
    results: list[dict] = []
    pattern = re.compile(r"#\s*type:\s*ignore(?:\[([^\]]+)\])?")
    
    for py_file in root.rglob("*.py"):
        if any(p in str(py_file) for p in (".venv", "__pycache__", ".git", "archive")):
            continue
        try:
            text = py_file.read_text()
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            m = pattern.search(line)
            if m:
                error_codes = m.group(1)
                results.append({
                    "file": str(py_file.relative_to(root)),
                    "line": i,
                    "codes": error_codes.split(",") if error_codes else [],
                    "bare": error_codes is None,
                    "text": line.strip()[:120],
                })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Check stale type: ignore comments")
    parser.add_argument("--check", action="store_true", help="CI mode (warn only)")
    args = parser.parse_args()

    results = _scan_type_ignores(CORE_ROOT / "whitemagic")
    
    bare_count = sum(1 for r in results if r["bare"])
    coded_count = len(results) - bare_count
    
    # Categorize by error code
    code_counter: Counter[str] = Counter()
    for r in results:
        if r["bare"]:
            code_counter["(bare)"] += 1
        else:
            for c in r["codes"]:
                code_counter[c.strip()] += 1
    
    print("Type Ignore Inventory:")
    print(f"  Total: {len(results)}")
    print(f"  Bare (no error code): {bare_count}")
    print(f"  Coded: {coded_count}")
    print(f"\n  By error code:")
    for code, count in code_counter.most_common():
        print(f"    {code}: {count}")
    
    # Flag bare type: ignores as candidates for improvement
    if bare_count > 0:
        print(f"\n⚠️  {bare_count} bare `# type: ignore` comments (should specify error codes)")
        if bare_count <= 20:
            for r in results:
                if r["bare"]:
                    print(f"   {r['file']}:{r['line']}: {r['text']}")
    
    # This is advisory only — no exit 1
    print("\n✅ Inventory complete (advisory only, no CI gate)")


if __name__ == "__main__":
    main()
