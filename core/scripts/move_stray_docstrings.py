"""Move stray inner docstrings out of the import section.

Some files have:
    import logging
    logger = logging.getLogger(__name__)

    \"\"\"Real second docstring describing the module.\"\"\"

    ...

The middle Expr(string) breaks up the imports (E402). Move the
inner docstring to right after the file-level docstring (so it
still serves as a "section header" in the source) and the imports
become contiguous.
"""

import ast
from pathlib import Path

ROOT = Path("whitemagic")


def find_stray_string_expressions(content: str) -> list[int]:
    """Return 1-indexed line numbers of Expr(Constant(str)) statements
    that are NOT the module docstring (i.e., not the first statement
    in the module body)."""
    tree = ast.parse(content)
    body = tree.body
    stray = []
    # First statement may be a docstring (Expr) - skip
    start = 0
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        start = 1
    for i, stmt in enumerate(body[start:], start=start):
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            stray.append(stmt.lineno)
    return stray


def fix_file(path: Path) -> bool:
    content = path.read_text()
    if not find_stray_string_expressions(content):
        return False
    lines = content.splitlines(keepends=True)
    tree = ast.parse(content)
    body = tree.body
    # Find the stray docstring(s) and the line where they live
    stray_indices = [
        i
        for i, stmt in enumerate(body)
        if isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
        and not (i == 0 and body[0] is stmt)
    ]
    if not stray_indices:
        return False
    # Extract the stray docstring text from each
    stray_texts = []
    for idx in stray_indices:
        stmt = body[idx]
        # Determine the start and end line of this Expr
        start = stmt.lineno - 1  # 0-indexed
        end = stmt.end_lineno  # 1-indexed, exclusive
        stray_texts.append("".join(lines[start:end]))
    for idx in sorted(stray_indices, reverse=True):
        stmt = body[idx]
        start = stmt.lineno - 1
        end = stmt.end_lineno
        del lines[start:end]
    # Re-insert the stray docstrings right after the module docstring
    # (i.e., at index 1, since the file-level docstring is at index 0)
    insert_at = 0
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        # Find the end of the module docstring
        insert_at = body[0].end_lineno  # 1-indexed
    # Re-parse to find new positions
    new_content = "".join(lines)
    new_tree = ast.parse(new_content)
    new_body = new_tree.body
    # Find the first code statement (not string Expr) and insert before
    new_insert_at = 0
    for i, stmt in enumerate(new_body):
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            new_insert_at = i + 1
            continue
        break
    # Insert the stray docstrings at new_insert_at
    # new_insert_at is 0-indexed; convert to 1-indexed line
    if new_insert_at == 0:
        # No code statement; append at end (shouldn't happen)
        new_lines = "".join(lines) + "".join(stray_texts)
    else:
        target_stmt = new_body[new_insert_at]
        target_line = target_stmt.lineno - 1  # 0-indexed
        new_lines = (
            "".join(lines[:target_line])
            + "".join(stray_texts)
            + "\n"  # blank line separator
            + "".join(lines[target_line:])
        )
    path.write_text(new_lines)
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
