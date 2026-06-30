#!/usr/bin/env python3
"""
CI gate for path hygiene violations.

This script checks that all path resolution goes through config/paths.py
and no code directly uses Path.home() or expanduser() outside of the
centralized path configuration.

Exit codes:
  0 - No violations found
  1 - Violations found (CI should fail)
"""

import re
import sys
from pathlib import Path


def find_path_violations(whitemagic_root: Path) -> list[dict]:
    """Find all path.home/expanduser usages outside of config/paths.py."""

    violations = []

    # Files/directories that are allowed to use path expansion
    allowed_patterns = [
        # Centralized path configuration (obviously allowed)
        r"config/paths\.py$",
        # Documentation (not runtime)
        r"grimoire/",
        r"archive/",
        r"_archived/",
        # Security gating (legitimate validation)
        r"security/tool_gating\.py$",
        # Tests (need to test path behavior)
        r"tests/",
        # Initialization command (needs to setup paths)
        r"cli/init_command\.py$",
        # Intelligence/hologram modules: resolve external binary paths (Mojo, pixi, etc.)
        r"core/intelligence/",
        r"modular/",
        # External tool/session discovery (Windsurf IDE, ~/.codeium/, etc.)
        r"archaeology/windsurf_reader\.py$",
        # Multi-runtime binary discovery (Mojo ~/.modular/, GHC ~/.ghcup/)
        r"core/fusions\.py$",
        r"tools/handlers/introspection\.py$",
        # Config-driven path resolution (governor security, embedder, daemon)
        r"core/governor\.py$",
        r"inference/unified_embedder\.py$",
        r"core/memory/embedding_daemon\.py$",
        r"tools/unified_api\.py$",
    ]

    # Patterns to detect
    path_patterns = [
        (r"Path\.home\(\)", "Path.home()"),
        (r"\.expanduser\(\)", "expanduser()"),
        (r"os\.path\.expanduser", "os.path.expanduser"),
    ]

    for py_file in whitemagic_root.rglob("*.py"):
        rel_path = str(py_file.relative_to(whitemagic_root))

        # Skip allowed files
        if any(re.search(pattern, rel_path) for pattern in allowed_patterns):
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            code_part = line.split("#")[0]

            for pattern, description in path_patterns:
                if re.search(pattern, code_part):
                    violations.append(
                        {
                            "file": rel_path,
                            "line": line_num,
                            "code": line.strip(),
                            "violation": description,
                        }
                    )

    return violations


def main() -> int:
    """Main entry point."""
    # Find the whitemagic package root
    script_dir = Path(__file__).parent
    whitemagic_root = script_dir.parent.parent / "whitemagic"

    if not whitemagic_root.exists():
        print(f"ERROR: Could not find whitemagic root at {whitemagic_root}")
        return 1

    print(f"Checking path hygiene in {whitemagic_root}")
    print("=" * 60)

    violations = find_path_violations(whitemagic_root)

    if not violations:
        print("✅ No path hygiene violations found!")
        print("   All path.home/expanduser usage is properly centralized.")
        return 0

    # Group by violation type
    by_type: dict[str, list[dict]] = {}
    for v in violations:
        vtype = v["violation"]
        by_type.setdefault(vtype, []).append(v)

    print(f"❌ Found {len(violations)} path hygiene violations:\n")

    for vtype, items in by_type.items():
        print(f"{vtype} ({len(items)} occurrences):")
        for v in items[:5]:  # Show first 5 of each type
            print(f"  {v['file']}:{v['line']}")
            print(f"    {v['code'][:80]}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")
        print()

    print("=" * 60)
    print("To fix these violations:")
    print("1. Use whitemagic.config.paths.WM_ROOT for state paths")
    print("2. Use whitemagic.config.paths.PROJECT_ROOT for repo paths")
    print("3. If you must use expanduser, add file to allowed_patterns in this script")
    print("   with a justification comment")
    print()
    print("To opt-in to CWD fallback in restricted environments:")
    print("  export WM_FALLBACK_TO_CWD=true")
    print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
