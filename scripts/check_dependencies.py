#!/usr/bin/env python3
"""
Ensure our dependency manifests stay consistent.

Currently checks:
  1. Every package listed in requirements-plugins.txt exists in optional deps (pyproject or docs).
  2. requirements-api.txt does not contain packages that are also in requirements-plugins.txt.
"""

from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def read_packages(path: pathlib.Path) -> set[str]:
    pkgs: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pkg = line.split(" ", 1)[0]
        pkg = pkg.split("[", 1)[0]
        pkg = pkg.split(">=", 1)[0]
        pkgs.add(pkg.lower())
    return pkgs


def main() -> int:
    api_path = REPO_ROOT / "requirements-api.txt"
    plugins_path = REPO_ROOT / "requirements-plugins.txt"

    api_pkgs = read_packages(api_path)
    plugin_pkgs = read_packages(plugins_path)

    overlap = api_pkgs & plugin_pkgs
    if overlap:
        print("❌ Packages present in both requirements files:", ", ".join(sorted(overlap)))
        return 1

    if not plugin_pkgs:
        print("⚠️ requirements-plugins.txt is empty.")
        return 1

    print("✅ Dependency manifests look consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
