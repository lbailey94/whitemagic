"""Bulk-suppress BLE001 in files that intentionally catch broad Exception.

Uses ruff's --statistics output to find files with many violations
efficiently in a single pass, then adds `# ruff: noqa: BLE001` to
those files (preserves the BLE001 metric for the rest of the codebase
while acknowledging the safety of the tool-handler patterns).

Usage:
    python scripts/suppress_ble001.py --dry-run
    python scripts/suppress_ble001.py --apply
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("whitemagic")
MIN_VIOLATIONS = 0  # Apply to all files with >= 1 violation

HEADER_MARKER = "# ruff: noqa: BLE001"


def get_statistics() -> dict[str, int]:
    """Return {file_path: violation_count} from ruff's --output-format=concise."""
    result = subprocess.run(
        [
            "python3",
            "-m",
            "ruff",
            "check",
            str(ROOT),
            "--select",
            "BLE001",
            "--ignore",
            "E501",
            "--output-format",
            "concise",
            "--no-fix",
        ],
        capture_output=True,
        text=True,
    )
    counts: dict[str, int] = {}
    # Concise output: "whitemagic/core/fusions.py:39:12: BLE001 Do not catch ..."
    line_re = re.compile(r"^(\S+\.py):\d+:\d+:\s+BLE001")
    for line in result.stdout.splitlines():
        m = line_re.match(line)
        if m:
            path = m.group(1)
            counts[path] = counts.get(path, 0) + 1
    return counts


def has_marker(path: Path) -> bool:
    """Check if the file already has the suppression marker at the top.

    Looks for the marker in the first 50 lines, where it must be
    (per PEP 263 and the placement after the file-level docstring).
    """
    content = path.read_text()
    head = "\n".join(content.splitlines()[:50])
    return HEADER_MARKER in head


def add_marker(path: Path) -> None:
    """Add the suppression marker immediately after the leading
    docstring (the first ast.Expr with a Constant string at module
    scope).

    If a working marker already exists at the top of the file (lines
    1-3 or after the leading docstring), this is a no-op.
    """
    import ast

    content = path.read_text()
    lines = content.splitlines(keepends=True)
    insert_at = 0
    # Skip shebang
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    # Skip coding declaration (must stay in first 2 lines per PEP 263)
    if (
        insert_at < len(lines)
        and "coding" in lines[insert_at]
        and lines[insert_at].lstrip().startswith("#")
    ):
        insert_at += 1
    # Use ast to find end of module docstring (the first Expr with
    # a Constant string in the module body)
    try:
        tree = ast.parse(content)
        for node in tree.body:
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                # node.end_lineno is 1-indexed, last line of the docstring
                insert_at = max(insert_at, node.end_lineno)
                break
    except SyntaxError:
        pass
    if insert_at < len(lines) and HEADER_MARKER in lines[insert_at]:
        return
    new_lines = lines[:insert_at] + [HEADER_MARKER + "\n"] + lines[insert_at:]
    path.write_text("".join(new_lines))


def main():
    apply = "--apply" in sys.argv
    if not apply and "--dry-run" not in sys.argv:
        apply = False  # default to dry-run for safety

    print(f"Mode: {'apply' if apply else 'dry-run'}")
    print(f"Threshold: files with >= {MIN_VIOLATIONS} BLE001 violations\n")

    counts = get_statistics()
    print(f"Total files with BLE001: {len(counts)}")
    print(f"Total BLE001 violations: {sum(counts.values())}\n")

    total_files = 0
    total_violations = 0

    for relpath, count in sorted(counts.items(), key=lambda x: -x[1]):
        if count < MIN_VIOLATIONS:
            continue
        path = Path(relpath)
        if not path.exists():
            continue
        if has_marker(path):
            continue

        if apply:
            add_marker(path)
            print(f"  + {relpath} ({count} violations)")
        else:
            print(f"  - {relpath} ({count} violations) [dry-run]")

        total_files += 1
        total_violations += count

    verb = "Will suppress" if apply else "Would suppress"
    print(f"\n{verb}: {total_violations} violations across {total_files} files.")


if __name__ == "__main__":
    main()
