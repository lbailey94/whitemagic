#!/usr/bin/env python3
"""
Fail the build if unsafe defaults slip back into the repo.

Currently checks:
  - No files (other than Markdown docs) set ALLOWED_ORIGINS to '*' by default.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN_PATTERN = re.compile(r"ALLOWED_ORIGINS[^:=\n]*[:=][^\n]*\*")
SKIP_SUFFIXES = {
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".gif",
    ".ico",
    ".pyc",
}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", "build"}
SKIP_FILES = {"check_security_guards.py"}


def should_check(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.name in SKIP_FILES:
        return False
    if path.suffix in SKIP_SUFFIXES:
        return False
    return True


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    violations: list[str] = []

    for file_path in repo_root.rglob("*"):
        if not file_path.is_file() or not should_check(file_path):
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            if "ALLOWED_ORIGINS" in line and "*" in line:
                if FORBIDDEN_PATTERN.search(line):
                    violations.append(f"{file_path}:{lineno}: {line.strip()}")

    if violations:
        print("❌ Unsafe ALLOWED_ORIGINS defaults detected:")
        for violation in violations:
            print(f"  - {violation}")
        print("Please replace '*' with explicit domains.")
        return 1

    print("✅ Security guard checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
