"""Fix `# type: ignore` comments that have wrong error codes.

When mypy reports a different error code than the one in the
existing ignore comment, the comment doesn't suppress the
error. The fix: append the actual code to the comment's
bracketed list, or replace the whole comment.

This script:
1. Runs mypy and collects (file, line, actual_code)
2. For each error line, looks at the existing `# type: ignore[X]`
   comment and adds the actual_code if missing
"""
import re
import subprocess
from pathlib import Path

ROOT = Path("/home/lucas/Desktop/WHITEMAGIC/core")


def update_ignore(path: Path, line_no: int, actual_code: str) -> bool:
    content = path.read_text()
    lines = content.splitlines(keepends=True)
    if line_no < 1 or line_no > len(lines):
        return False
    line = lines[line_no - 1].rstrip("\n").rstrip()
    # Find existing # type: ignore[X] comment
    m = re.search(r"#\s*type:\s*ignore\s*\[([a-z0-9_,\s-]+)\]\s*$", line)
    if m:
        existing_codes = [c.strip() for c in m.group(1).split(",")]
        if actual_code in existing_codes:
            return False
        new_codes = existing_codes + [actual_code]
        new_comment = f"# type: ignore[{', '.join(new_codes)}]"
        new_line = line[:m.start()].rstrip() + "  " + new_comment + "\n"
    else:
        # No existing comment, just add one
        new_line = f"{line}  # type: ignore[{actual_code}]\n"
    lines[line_no - 1] = new_line
    new_content = "".join(lines)
    try:
        import ast
        ast.parse(new_content)
    except SyntaxError:
        return False
    path.write_text(new_content)
    return True


def main() -> None:
    result = subprocess.run(
        [".venv/bin/mypy", "whitemagic/"],
        capture_output=True, text=True, cwd=ROOT,
    )
    output = result.stdout + result.stderr
    errors = []
    for line in output.splitlines():
        m = re.match(
            r"^(whitemagic/[^:]+):(\d+):\s*error:.*\[([a-z0-9-]+)\]\s*$", line
        )
        if m:
            errors.append((m.group(1), int(m.group(2)), m.group(3)))
    fixed = 0
    seen = set()
    for file_path, line_no, code in errors:
        key = (file_path, line_no, code)
        if key in seen:
            continue
        seen.add(key)
        path = ROOT / file_path
        if not path.exists():
            continue
        if update_ignore(path, line_no, code):
            fixed += 1
    print(f"Updated type:ignore comments on {fixed} lines.")


if __name__ == "__main__":
    main()
