#!/usr/bin/env python3
"""Deep import audit for whitemagic package."""
import importlib
import sys
from pathlib import Path

# Add the package to path
package_root = Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic")
sys.path.insert(0, str(package_root.parent))

failures = []
successes = []

# List of subpackages to audit
subpackages = [
    "whitemagic.core",
    "whitemagic.core.bridge",
    "whitemagic.core.resonance",
    "whitemagic.core.memory",
    "whitemagic.core.intelligence",
    "whitemagic.core.intelligence.phylogenetics",
    "whitemagic.zodiac",
    "whitemagic.gardens",
    "whitemagic.oracle",
    "whitemagic.core.orchestration",
    "whitemagic.core.health_monitor",
    "whitemagic.core.immune",
]

# Try to import each subpackage and its modules
for pkg_name in subpackages:
    try:
        pkg = importlib.import_module(pkg_name)
        successes.append(pkg_name)

        # Try to import all submodules
        pkg_path = getattr(pkg, "__path__", None)
        if pkg_path:
            for path in pkg_path:
                for item in Path(path).glob("*.py"):
                    if item.name.startswith("_") or item.name == "__init__.py":
                        continue
                    module_name = f"{pkg_name}.{item.stem}"
                    try:
                        importlib.import_module(module_name)
                        successes.append(f"  - {module_name}")
                    except ImportError as e:
                        error_msg = str(e)
                        if "No module named" in error_msg:
                            category = "missing_module"
                        elif "cannot import" in error_msg:
                            category = "missing_symbol"
                        elif "circular" in error_msg.lower():
                            category = "circular"
                        else:
                            category = "other"
                        failures.append({
                            "module": module_name,
                            "error": error_msg,
                            "category": category,
                        })
    except ImportError as e:
        failures.append({
            "module": pkg_name,
            "error": str(e),
            "category": "missing_module",
        })

print("=== Import Audit Results ===")
print(f"Successes: {len(successes)}")
print(f"Failures: {len(failures)}")
print()

if failures:
    print("=== Failures by Category ===")
    by_category = {}
    for f in failures:
        cat = f["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(f)

    for cat, items in sorted(by_category.items()):
        print(f"\n{cat.upper()}: {len(items)}")
        for item in items:
            print(f"  - {item['module']}: {item['error'][:100]}")
else:
    print("No failures detected!")
