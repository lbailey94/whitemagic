#!/usr/bin/env python3
"""Fast bare except Exception: sweep — handles the most common patterns."""

import re
import sys
from pathlib import Path


def fix_file(path: Path) -> int:
    content = path.read_text()
    original = content
    fixes = 0

    # Split into lines for context analysis
    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Find bare except Exception: lines
        match = re.match(r"^(\s*)except Exception:\s*$", line)
        if match:
            indent = match.group(1)
            # Look backward for the try block to classify
            try_body = []
            j = i - 1
            while j >= 0 and j >= i - 20:
                prev = lines[j]
                if prev.strip() == "try:":
                    break
                try_body.insert(0, prev)
                j -= 1
            try_text = "\n".join(try_body).lower()

            # Classify
            if re.search(r"from\s+\S+\s+import", try_text):
                line = f"{indent}except (ImportError, AttributeError):"
                fixes += 1
            elif "json.loads" in try_text or "json.load" in try_text:
                line = f"{indent}except (json.JSONDecodeError, TypeError):"
                fixes += 1
            elif any(
                k in try_text for k in ["read_text", "write_text", "open(", "readlines"]
            ):
                line = f"{indent}except (OSError, UnicodeDecodeError):"
                fixes += 1
            elif any(k in try_text for k in ["subprocess", "popen", "terminate"]):
                line = f"{indent}except OSError:"
                fixes += 1
            else:
                # Default: add exception variable with debug log
                line = f"{indent}except Exception as e:"
                # Check next line for pass/return/continue — insert logger.debug before it
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent > len(indent):
                        # Insert logger.debug line
                        new_lines.append(line)
                        new_lines.append(
                            f'{indent}    logger.debug("Operation failed: %s", e)'
                        )
                        i += 1
                        fixes += 1
                        continue
                fixes += 1

        new_lines.append(line)
        i += 1

    new_content = "\n".join(new_lines)

    # Add logging import if needed
    if fixes > 0 and "logger = logging.getLogger" not in new_content:
        # Find a good place to insert
        last_import = -1
        for idx, line in enumerate(new_lines):
            if re.match(r"^(import|from)\s+", line.strip()):
                last_import = idx
        if last_import >= 0:
            if "import logging" not in new_content:
                new_lines.insert(last_import + 1, "import logging")
                last_import += 1
            new_lines.insert(last_import + 1, "logger = logging.getLogger(__name__)")
            new_content = "\n".join(new_lines)

    if new_content != original:
        path.write_text(new_content)

    return fixes


def main() -> int:
    root = Path("whitemagic")
    total_fixes = 0
    files_changed = 0

    for pyfile in root.rglob("*.py"):
        content = pyfile.read_text()
        if "except Exception:\n" not in content:
            continue
        fixes = fix_file(pyfile)
        if fixes > 0:
            total_fixes += fixes
            files_changed += 1
            print(f"  {pyfile}: {fixes} fixes")

    print(
        f"\nDone: {total_fixes} bare except blocks fixed across {files_changed} files."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
