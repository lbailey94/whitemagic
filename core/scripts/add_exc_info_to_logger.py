"""Add exc_info=True to logger.error calls inside except blocks.

The pattern in many files is:
    except Exception as e:
        logger.error("Failed to foo: %s", e)

The fix: change to:
    except Exception as e:
        logger.error("Failed to foo: %s", e, exc_info=True)

The new form:
- Uses %s lazy formatting (faster, doesn't construct the
  string unless the log level is enabled)
- Includes the full traceback via exc_info=True (so debugging
  doesn't require re-running with -X dev or breaking on the
  except)

The script targets the most common patterns:
- logger.error("...%s", e)  -> logger.error("...%s", e, exc_info=True)
- logger.exception(...)    -> unchanged (already includes traceback)

Only modifies calls that are *inside* an except block (heuristic:
  the logger.error call is the first statement after a line
  ending in 'except ... as e:'). This avoids changing
  legitimate non-except logger.error calls.
"""

import re
from pathlib import Path

ROOT = Path("whitemagic")


def fix_file(path: Path) -> int:
    content = path.read_text()
    lines = content.splitlines(keepends=True)
    fixed = 0
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        i += 1
        # Detect "except ... as e:" (or any except that captures e)
        if re.search(r"^\s*except\b.*\bas\s+\w+\s*:?\s*$", line):
            # The next non-blank, non-comment line is the body
            while i < len(lines):
                if lines[i].strip() and not lines[i].strip().startswith("#"):
                    body = lines[i]
                    m = re.match(
                        r'^(\s*)logger\.error\(f(["\'])(.*?)\2\s*\)\s*$',
                        body,
                    )
                    if m and "{" in m.group(3) and "}" in m.group(3):
                        # Strip simple {e} / {var} patterns
                        indent = m.group(1)
                        quote = m.group(2)
                        msg = m.group(3)
                        # Replace {var} with %s (assumes positional args
                        # will be added in the same order they appear)
                        var_re = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")
                        vars_in_order = []

                        def _capture(m: re.Match[str]) -> str:
                            vars_in_order.append(m.group(1))
                            return "%s"

                        new_msg = var_re.sub(_capture, msg)
                        if vars_in_order:
                            # Build the new call
                            args = ", ".join(vars_in_order)
                            new_call = (
                                f"{indent}logger.error({quote}{new_msg}{quote}, "
                                f"{args}, exc_info=True)\n"
                            )
                            new_lines.append(new_call)
                            fixed += 1
                            i += 1
                        else:
                            new_lines.append(body)
                            i += 1
                    else:
                        new_lines.append(body)
                        i += 1
                    break
                else:
                    new_lines.append(lines[i])
                    i += 1
    if fixed > 0:
        path.write_text("".join(new_lines))
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
            print(f"  {n:3d} {path}")
    print(f"\nFixed {total} logger.error calls across {files} files.")


if __name__ == "__main__":
    main()
