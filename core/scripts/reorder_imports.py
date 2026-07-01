"""Move from-imports to the top, before the first code statement.

The pattern in many handler files:
    import logging
    logger = logging.getLogger(__name__)
    from typing import Any       <-- ruff E402

The fix: move all `from ... import ...` statements to the top of
the import block, alongside the bare `import ...` statements, before
any code statement (logger = ..., def ..., class ..., etc.).
"""

import ast
from pathlib import Path

ROOT = Path("whitemagic")


def fix_file(path: Path) -> bool:
    content = path.read_text()
    tree = ast.parse(content)
    body = tree.body
    # Find the first non-import statement in the module body
    first_code_idx = None
    for i, stmt in enumerate(body):
        if isinstance(stmt, (ast.Import, ast.Expr)):
            continue
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        first_code_idx = i
        break
    if first_code_idx is None or first_code_idx == 0:
        return False
    # Collect the lines for the first first_code_idx statements
    lines = content.splitlines(keepends=True)
    if not lines:
        return False
    # Determine the line ranges for each statement 0..first_code_idx-1
    # Reorder: imports first, then non-imports (logger, assignments)
    imports_block = []
    non_imports_block = []
    for stmt in body[:first_code_idx]:
        if isinstance(stmt, (ast.Import, ast.Expr)):
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                non_imports_block.append(stmt)
            else:
                imports_block.append(stmt)
        else:
            non_imports_block.append(stmt)
    # Reorder: imports first, then non-imports
    reordered = imports_block + non_imports_block
    if [id(s) for s in reordered] == [id(s) for s in body[:first_code_idx]]:
        return False
    # Reconstruct source: replace the lines for statements 0..first_code_idx-1
    # with the source for reordered statements
    first_stmt = body[0]
    last_stmt = body[first_code_idx - 1]
    start_line = first_stmt.lineno - 1  # 0-indexed
    end_line = last_stmt.end_lineno  # 1-indexed, exclusive

    def stmt_source(stmt):
        if hasattr(stmt, "col_offset") and hasattr(stmt, "end_col_offset"):
            s = stmt.lineno - 1
            e = stmt.end_lineno
            return "".join(lines[s:e])
        return ""

    new_block = ""
    for s in reordered:
        new_block += stmt_source(s)
    if not new_block.endswith("\n"):
        new_block += "\n"
    # Replace
    new_lines = lines[:start_line] + [new_block] + lines[end_line:]
    path.write_text("".join(new_lines))
    return True


def main():
    n = 0
    for path in sorted(ROOT.rglob("*.py")):
        if "_archived" in path.parts:
            continue
        if fix_file(path):
            n += 1
            print(f"  fixed: {path}")
    print(f"\nFixed {n} files.")


if __name__ == "__main__":
    main()
