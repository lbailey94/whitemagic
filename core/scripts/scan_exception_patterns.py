#!/usr/bin/env python3
"""Simple regex-based scanner for except Exception patterns.

Identifies patterns that can be safely narrowed based on context.
"""

from pathlib import Path
from collections import defaultdict


def scan_file(filepath: Path) -> dict:
    """Scan a file for except Exception patterns with context."""
    with open(filepath, "r") as f:
        lines = f.readlines()

    patterns = {
        "file_io": [],
        "json": [],
        "sqlite": [],
        "import_error": [],
        "network": [],
        "unknown": [],
    }

    for i, line in enumerate(lines, 1):
        if "except Exception" in line:
            # Look at context (previous 5 lines)
            context_start = max(0, i - 6)
            context = "".join(lines[context_start:i]).lower()

            if any(
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
                patterns["file_io"].append(i)
            elif any(
                x in context
                for x in ["json.loads", "json.dumps", "json.load", "json.dump"]
            ):
                patterns["json"].append(i)
            elif any(
                x in context
                for x in ["sqlite", "execute(", "cursor(", "commit(", "db.execute"]
            ):
                patterns["sqlite"].append(i)
            elif "import" in context:
                patterns["import_error"].append(i)
            elif any(
                x in context
                for x in ["requests.", "urllib", "http", "connect(", "socket"]
            ):
                patterns["network"].append(i)
            else:
                patterns["unknown"].append(i)

    total = sum(len(v) for v in patterns.values())
    return {"file": str(filepath), "total": total, "patterns": patterns}


def main():
    directory = Path("whitemagic")

    all_results = defaultdict(lambda: defaultdict(list))
    total_count = 0

    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        result = scan_file(py_file)
        if result["total"] > 0:
            total_count += result["total"]
            for pattern, lines in result["patterns"].items():
                if lines:
                    all_results[pattern][str(py_file)] = lines

    print(f"Scanned whitemagic/ directory")
    print(f"Total except Exception blocks: {total_count}")
    print(f"\nBreakdown by pattern:")

    for pattern, files in sorted(all_results.items()):
        count = sum(len(lines) for lines in files.values())
        print(f"\n{pattern}: {count} occurrences")
        for filepath, lines in sorted(files.items())[:5]:
            print(f"  {filepath}: {len(lines)} at lines {lines[:3]}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more files")


if __name__ == "__main__":
    main()
