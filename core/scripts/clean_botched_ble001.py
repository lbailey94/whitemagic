"""Remove botched BLE001 markers from files where the marker was
placed inside a function docstring (from the v22.2.2 first attempt
that had a buggy add_marker).

The correct placement is:
  - Line 1 or 2 (after shebang / coding declaration)
  - Then a single line "# ruff: noqa: BLE001"
  - Before any other content

The botched placement is the marker appearing inside a function
docstring (e.g. line 8+ on a file with a function def at line 6
that has a multi-line docstring starting at line 7).
"""

from pathlib import Path

ROOT = Path("whitemagic")
MARKER = "# ruff: noqa: BLE001"


def is_marker_in_docstring(content: str, line_no: int) -> bool:
    """Heuristic: is the marker on `line_no` (1-indexed) inside a docstring?"""
    lines = content.splitlines()
    if line_no < 1 or line_no > len(lines):
        return False
    # Walk lines, tracking in-docstring state
    in_doc = False
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if in_doc:
            # Look for closing triple quote
            if '"""' in line or "'''" in line:
                # Count occurrences; if odd, the docstring is closing
                triple_count = line.count('"""') + line.count("'''")
                if triple_count % 2 == 1:
                    if MARKER in line:
                        return True
                    in_doc = False
        else:
            if '"""' in line or "'''" in line:
                # Check if this line both opens and closes (single-line docstring)
                triple_count = line.count('"""') + line.count("'''")
                if triple_count % 2 == 0:
                    if MARKER in line:
                        return True
                else:
                    in_doc = True
    return False


def fix_file(path: Path) -> bool:
    """Remove the botched marker (if any) and return True if changed."""
    content = path.read_text()
    lines = content.splitlines(keepends=True)
    new_lines = []
    changed = False
    for i, line in enumerate(lines, 1):
        if MARKER in line and is_marker_in_docstring(content, i):
            # Remove this line entirely
            changed = True
            continue
        if MARKER in line and i > 50:
            # Marker is too far down — likely botched
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
            print(f"  cleaned: {path}")
            n_fixed += 1
    print(f"\nCleaned {n_fixed} files.")


if __name__ == "__main__":
    main()
