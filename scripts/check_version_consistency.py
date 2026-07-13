#!/usr/bin/env python3
"""scripts/check_version_consistency.py — Validate version metadata across all sources.

Checks that VERSION, pyproject.toml, mcp-registry.json, server.json, and
whitemagic.__version__ all agree.

Usage:
    python3 scripts/check_version_consistency.py           # Report
    python3 scripts/check_version_consistency.py --check   # CI gate (exit 1 on drift)
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read_version_file() -> str:
    vf = REPO_ROOT / "VERSION"
    if not vf.exists():
        return None
    return vf.read_text().strip()


def _read_core_version_file() -> str:
    vf = REPO_ROOT / "core" / "VERSION"
    if not vf.exists():
        return None
    return vf.read_text().strip()


def _read_pyproject_version() -> str:
    pp = REPO_ROOT / "core" / "pyproject.toml"
    text = pp.read_text()
    # Static version
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if m:
        return m.group(1)
    # Dynamic version — read from VERSION file (which we already check)
    if "dynamic = [\"version\"]" in text:
        return _read_version_file()
    return None


def _read_mcp_registry_version() -> str:
    mr = REPO_ROOT / "mcp-registry.json"
    if not mr.exists():
        return None
    data = json.loads(mr.read_text())
    return data.get("version")


def _read_server_json_version() -> str:
    sj = REPO_ROOT / "server.json"
    if not sj.exists():
        return None
    data = json.loads(sj.read_text())
    return data.get("version")


def _read_package_version() -> str:
    core = REPO_ROOT / "core"
    sys.path.insert(0, str(core))
    try:
        from whitemagic import __version__
        return __version__
    except ImportError:
        return None
    finally:
        if str(core) in sys.path:
            sys.path.remove(str(core))


def main() -> None:
    parser = argparse.ArgumentParser(description="Check version consistency")
    parser.add_argument("--check", action="store_true", help="Exit 1 on drift (CI mode)")
    args = parser.parse_args()

    sources = {
        "VERSION file": _read_version_file(),
        "core/VERSION file": _read_core_version_file(),
        "pyproject.toml": _read_pyproject_version(),
        "mcp-registry.json": _read_mcp_registry_version(),
        "server.json": _read_server_json_version(),
        "whitemagic.__version__": _read_package_version(),
    }

    versions = set(v for v in sources.values() if v is not None)
    all_present = all(v is not None for v in sources.values())

    if len(versions) == 1 and all_present:
        v = versions.pop()
        print(f"✅ All version sources agree: {v}")
        return

    print("❌ Version drift detected:")
    for name, ver in sources.items():
        status = ver if ver else "MISSING"
        print(f"   {name}: {status}")

    if args.check:
        sys.exit(1)


if __name__ == "__main__":
    main()
