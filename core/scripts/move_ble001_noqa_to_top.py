"""Move `# ruff: noqa: BLE001` from after-docstring to top-of-file.

The current placement (after the module docstring, before imports)
triggers E402 ("module level import not at top of file") because
the noqa is treated as an expression that the imports follow.

The fix: move the noqa comment to line 1 (or 2 after a shebang),
which is the standard PEP 263 / PEP 8 location for module-level
lint directives.
"""
import re
from pathlib import Path

ROOT = Path("whitemagic")
NOQA_PATTERN = re.compile(r"^#\s*ruff:\s*noqa:\s*BLE001\s*$", re.MULTILINE)


def fix_file(path: Path) -> bool:
    content = path.read_text()
    lines = content.splitlines(keepends=True)
    # Find the noqa line
    noqa_lines = [i for i, l in enumerate(lines) if NOQA_PATTERN.match(l)]
    if not noqa_lines:
        return False
    # Remove the noqa from its current position
    for i in sorted(noqa_lines, reverse=True):
        del lines[i]
    # Insert at top (after shebang if present)
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    # Skip coding declaration if present
    if insert_at < len(lines) and "coding" in lines[insert_at] and lines[insert_at].lstrip().startswith("#"):
        insert_at += 1
    # Insert the noqa at the top
    lines.insert(insert_at, "# ruff: noqa: BLE001\n")
    new_content = "".join(lines)
    if new_content != content:
        path.write_text(new_content)
        return True
    return False


def main():
    n = 0
    for path in sorted(ROOT.rglob("*.py")):
        if "_archived" in path.parts:
            continue
        if fix_file(path):
            n += 1
            print(f"  moved: {path}")
    print(f"\nFixed {n} files.")


if __name__ == "__main__":
    main()
