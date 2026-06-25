"""Add exc_info=True to logger.error calls.

Two passes:
1. The original Pass 5 pattern: first non-blank line after `except ... as e:`
2. Aggressive: any `logger.error(f"...{e}")` in any context where `e`
   is in scope (i.e., we're inside an except block, possibly nested)

For pass 2, the script tracks whether the cursor is inside an
except block by maintaining a stack of `try/except` contexts.
This is approximate but works for the typical patterns.
"""
import re
from pathlib import Path

ROOT = Path("whitemagic")


def has_exc_info(line: str) -> bool:
    return "exc_info" in line


def convert_fstring_to_percent(line: str) -> tuple[str, list[str]] | None:
    """Convert `f"...{var}..."` to `"...%s..."` and return (new_line, vars).

    Returns None if the line is not a logger.error f-string.
    """
    m = re.match(
        r"^(\s*)logger\.(error|warning|info|debug|exception)\(f(['\"])(.*?)\3\s*\)\s*$",
        line.rstrip("\n"),
    )
    if not m:
        return None
    indent, level, quote, msg = m.groups()
    if "{" not in msg:
        return None
    var_re = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")
    vars_in_order: list[str] = []
    new_msg = var_re.sub(lambda m: (vars_in_order.append(m.group(1)) or "%s"), msg)
    if not vars_in_order:
        return None
    args = ", ".join(vars_in_order)
    if "exception" in level:
        # logger.exception already includes exc_info implicitly
        new_line = f"{indent}logger.{level}({quote}{new_msg}{quote}, {args})\n"
    else:
        new_line = f"{indent}logger.{level}({quote}{new_msg}{quote}, {args}, exc_info=True)\n"
    return new_line, vars_in_order


def add_exc_info_to_logger_calls(path: Path) -> int:
    """Add exc_info=True to all logger.error/warning f-string calls in except blocks."""
    content = path.read_text()
    lines = content.splitlines(keepends=True)
    new_lines = []
    in_except = 0  # depth of except blocks
    fixed = 0
    for line in lines:
        # Track try/except depth
        if re.search(r"^\s*try\s*:\s*$", line):
            pass  # we're entering a try; no depth change
        elif re.search(r"^\s*except\b.*:\s*$", line):
            in_except += 1
        elif re.search(r"^\s*(finally|else)\s*:\s*$", line):
            pass
        elif re.search(r"^\s*(class|def|async def)\b", line) and in_except > 0:
            # entering a function inside except (rare but possible)
            pass

        # If we're in an except block and the line is a logger call
        # with f-string, convert it
        if in_except > 0 and not has_exc_info(line):
            result = convert_fstring_to_percent(line)
            if result is not None:
                new_line, _ = result
                new_lines.append(new_line)
                fixed += 1
                # Track that we left the except block at the right indent
                # (heuristic: if the line is dedented, the except is over)
                continue

        new_lines.append(line)

        # Detect except block end (next non-indented line)
        # Actually we should track based on dedent
        if in_except > 0:
            stripped = line.lstrip()
            if stripped and not line.startswith(" "):
                # We're back to module-level — except blocks are over
                in_except = 0

    if fixed > 0:
        new_content = "".join(new_lines)
        try:
            import ast
            ast.parse(new_content)
        except SyntaxError as e:
            return 0
        path.write_text(new_content)
    return fixed


def main() -> None:
    total = 0
    files = 0
    for path in sorted(ROOT.rglob("*.py")):
        if "_archived" in path.parts:
            continue
        n = add_exc_info_to_logger_calls(path)
        if n > 0:
            total += n
            files += 1
    print(f"Fixed {total} logger calls across {files} files.")


if __name__ == "__main__":
    main()
