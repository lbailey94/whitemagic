"""Remove botched BLE001 markers from all files, regardless of position.

The v22.2.2 first attempt placed markers inside function docstrings
or multi-line string literals. The fix: remove ALL `# ruff: noqa:
BLE001` lines, then re-apply with a corrected script.
"""
import re
import sys
from pathlib import Path

ROOT = Path("whitemagic")
MARKER = "# ruff: noqa: BLE001"


def fix_file(path: Path) -> bool:
    content = path.read_text()
    lines = content.splitlines(keepends=True)
    new_lines = []
    changed = False
    for line in lines:
        if MARKER in line:
            changed = True
            continue
        new_lines.append(line)
    if changed:
        path.write_text("".join(new_lines))
    return changed


def main():
    n_fixed = 0
    for path in sorted(ROOT.rglob("*.py")):
        if fix_file(path):
            n_fixed += 1
    print(f"Cleaned {n_fixed} files (removed all BLE001 markers).")


if __name__ == "__main__":
    main()
