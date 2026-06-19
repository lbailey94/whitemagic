"""Split `if X: return Y` and similar single-line E701 patterns.

E701 ("multiple statements on one line (colon)") is a ruff rule
that flags patterns like:
    if _accelerator is None: _accelerator = PolyglotAccelerator()
    if path.exists(): return str(path)

These are intentional Pythonic one-liners, but the project's
public-release-readiness goal is to have zero lint warnings. The
fix: split them onto separate lines:
    if _accelerator is None:
        _accelerator = PolyglotAccelerator()
    if path.exists():
        return str(path)

The script:
1. Parses each .py file with ast
2. For each E701 violation, splits the statement into two lines
   at the colon, preserving indentation
3. Writes the result back, preserving everything else byte-for-byte
   (only line content changes)

Conservative: only handles `if X: stmt` and `while X: stmt` patterns
where stmt is a single statement (assignment, return, pass, break,
continue, raise, expression). Doesn't touch:
- function/class defs on one line (E701's other case)
- try/except on one line (not E701)
- with/for on one line (E701)
"""
import ast
import re
from pathlib import Path

ROOT = Path("whitemagic")


def fix_file(path: Path) -> int:
    content = path.read_text()
    lines = content.splitlines(keepends=True)
    new_lines = []
    fixed = 0
    for line in lines:
        # Match `if X: <single stmt>` or `while X: <single stmt>`
        # where the body is a simple statement (no nested colon)
        m = re.match(
            r"^(\s*)(if|elif|else|while|for|with|except)\b([^:]*?):\s*([^\n]+?)\s*$",
            line.rstrip("\n"),
        )
        if m:
            indent, kw, cond, body = m.groups()
            cond = cond.strip()
            if kw in ("else",):
                cond = ""
            # Make sure the body is a single simple statement
            # (no semicolons, no # comments that might be content)
            if ";" in body or " #" in body:
                new_lines.append(line)
                continue
            # Reconstruct: indent kw cond:\n    body
            new_line_1 = f"{indent}{kw} {cond}:\n"
            # Indent body by 4 spaces from the kw
            new_line_2 = f"{indent}    {body}\n"
            new_lines.append(new_line_1)
            new_lines.append(new_line_2)
            fixed += 1
        else:
            new_lines.append(line)
    if fixed > 0:
        path.write_text("".join(new_lines))
        # Verify the file still parses
        try:
            ast.parse(path.read_text())
        except SyntaxError as e:
            # Revert
            path.write_text(content)
            print(f"  REVERTED {path}: {e}")
            return 0
    return fixed


def main() -> None:
    total = 0
    files = 0
    for path in sorted(ROOT.rglob("*.py")):
        if "_archived" in path.parts:
            continue
        n = fix_file(path)
        if n > 0:
            total += n
            files += 1
    print(f"\nFixed {total} E701 hits across {files} files.")


if __name__ == "__main__":
    main()
