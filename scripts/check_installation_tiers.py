#!/usr/bin/env python3
"""scripts/check_installation_tiers.py — Validate optional-dependency matrix.

Parses pyproject.toml [project.optional-dependencies] and validates:
1. All tiered bundles (lite, core, heavy-tier, full) are self-consistent
2. Atomic extras referenced by tiered bundles exist
3. No duplicate dependencies within a single extra
4. Self-references (whitemagic[extra]) point to valid extras

Usage:
    python3 scripts/check_installation_tiers.py           # Report
    python3 scripts/check_installation_tiers.py --check   # CI gate (exit 1 on error)
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "core" / "pyproject.toml"


def _extract_dep_name(dep: str) -> str:
    """Extract package name from a dependency spec like 'numpy>=1.24.0'."""
    return re.split(r"[>=<!\[;]", dep)[0].strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Check installation tier consistency")
    parser.add_argument("--check", action="store_true", help="Exit 1 on error (CI mode)")
    args = parser.parse_args()

    if not PYPROJECT.exists():
        print("❌ pyproject.toml not found")
        if args.check:
            sys.exit(1)
        return

    with open(PYPROJECT, "rb") as f:
        data = tomllib.loads(f.read().decode("utf-8"))

    extras: dict[str, list[str]] = data.get("project", {}).get("optional-dependencies", {})

    if not extras:
        print("❌ No optional-dependencies found in pyproject.toml")
        if args.check:
            sys.exit(1)
        return

    errors: list[str] = []

    # Define tiered bundles and their expected sub-tiers
    tiered = {
        "lite": [],
        "core": ["lite"],
        "heavy-tier": ["core", "heavy"],
        "full": [],
    }

    # Check for duplicates within each extra
    for extra_name, deps in extras.items():
        names = [_extract_dep_name(d) for d in deps]
        seen = set()
        for name in names:
            if name in seen:
                errors.append(f"Duplicate dependency '{name}' in extra '{extra_name}'")
            seen.add(name)

    # Check that tiered bundles contain their sub-tier's deps
    for tier, sub_tiers in tiered.items():
        if tier not in extras:
            errors.append(f"Tiered bundle '{tier}' not found in optional-dependencies")
            continue
        tier_deps = {_extract_dep_name(d) for d in extras[tier]}
        for sub in sub_tiers:
            if sub not in extras:
                errors.append(f"Sub-tier '{sub}' referenced by '{tier}' not found")
                continue
            sub_deps = {_extract_dep_name(d) for d in extras[sub]}
            missing = sub_deps - tier_deps
            if missing:
                errors.append(
                    f"Tier '{tier}' is missing deps from sub-tier '{sub}': {sorted(missing)}"
                )

    # Check that whitemagic[...] self-references are valid
    for extra_name, deps in extras.items():
        for dep in deps:
            if dep.startswith("whitemagic["):
                ref = re.search(r"whitemagic\[(\w[\w-]*)\]", dep)
                if ref:
                    ref_name = ref.group(1)
                    if ref_name not in extras:
                        errors.append(
                            f"Extra '{extra_name}' references non-existent extra '{ref_name}'"
                        )

    # Report
    print("Optional-Dependency Matrix Report:")
    print(f"  Total extras: {len(extras)}")
    for name, deps in sorted(extras.items()):
        print(f"  {name}: {len(deps)} deps")

    if errors:
        print("\n❌ Dependency matrix errors:")
        for e in errors:
            print(f"   {e}")
        if args.check:
            sys.exit(1)
    else:
        print("\n✅ Optional-dependency matrix is consistent")


if __name__ == "__main__":
    main()
