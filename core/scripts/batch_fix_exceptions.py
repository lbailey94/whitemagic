#!/usr/bin/env python3
"""Batch fixer for identified except Exception patterns.

Automatically fixes:
- import_error: Exception → ImportError, ModuleNotFoundError
- file_io: Exception → OSError, FileNotFoundError, PermissionError
- sqlite: Exception → sqlite3.Error, sqlite3.OperationalError
- json: Exception → json.JSONDecodeError, TypeError
- network: Exception → ConnectionError, TimeoutError, OSError

Usage:
    python scripts/batch_fix_exceptions.py --dry-run
    python scripts/batch_fix_exceptions.py --apply
"""

import argparse
import re
from pathlib import Path


def fix_file(filepath: Path, apply: bool = False) -> dict:
    """Fix except Exception patterns in a file."""
    with open(filepath, "r") as f:
        content = f.read()

    original = content
    changes = []

    # Get line-by-line for context
    lines = content.split("\n")

    for i in range(len(lines)):
        line = lines[i]
        if "except Exception" not in line:
            continue

        # Look at context (previous 5 lines)
        context_start = max(0, i - 5)
        context = "\n".join(lines[context_start:i]).lower()

        # Determine replacement based on context
        replacement = None
        import_add = None

        if "import" in context:
            replacement = "ImportError, ModuleNotFoundError"
        elif any(
            x in context
            for x in [
                "open(",
                "read(",
                "write(",
                ".read()",
                ".write()",
                "path(",
                "file(",
            ]
        ):
            replacement = "OSError, FileNotFoundError, PermissionError"
        elif any(
            x in context for x in ["json.loads", "json.dumps", "json.load", "json.dump"]
        ):
            replacement = "json.JSONDecodeError, TypeError"
            import_add = "import json"
        elif any(
            x in context
            for x in ["sqlite", "execute(", "cursor(", "commit(", "db.execute"]
        ):
            replacement = "sqlite3.Error, sqlite3.OperationalError"
            import_add = "import sqlite3"
        elif any(
            x in context for x in ["requests.", "urllib", "http", "connect(", "socket"]
        ):
            replacement = "ConnectionError, TimeoutError, OSError"

        if replacement:
            # Replace the exception type
            new_line = re.sub(
                r"except Exception(\s+as\s+e)?:", f"except {replacement}\\1:", line
            )
            lines[i] = new_line
            changes.append(f"Line {i + 1}: Exception → {replacement}")

            # Add import if needed
            if import_add and import_add not in content:
                # Find the last import block
                import_line = -1
                for j, l in enumerate(lines):
                    if l.strip().startswith("import ") or l.strip().startswith("from "):
                        import_line = j
                if import_line >= 0:
                    lines.insert(import_line + 1, import_add)
                    changes.append(f"Added import: {import_add}")

    if changes:
        new_content = "\n".join(lines)
        if apply:
            with open(filepath, "w") as f:
                f.write(new_content)
        return {"file": str(filepath), "changes": changes, "applied": apply}
    return None


def main():
    parser = argparse.ArgumentParser(description="Batch fix except Exception patterns")
    parser.add_argument(
        "--directory", type=str, default="whitemagic", help="Directory to scan"
    )
    parser.add_argument("--apply", action="store_true", help="Apply fixes")
    parser.add_argument(
        "--dry-run", action="store_true", help="Only show what would be fixed"
    )
    args = parser.parse_args()

    directory = Path(args.directory)

    results = []
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        result = fix_file(py_file, apply=args.apply)
        if result:
            results.append(result)

    total_changes = sum(len(r["changes"]) for r in results)
    print(
        f"{'Would fix' if args.dry_run else 'Fixed'} {total_changes} patterns in {len(results)} files\n"
    )

    for result in results[:10]:
        print(f"{result['file']}:")
        for change in result["changes"]:
            print(f"  {change}")

    if len(results) > 10:
        print(f"\n... and {len(results) - 10} more files")


if __name__ == "__main__":
    main()
