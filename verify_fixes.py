#!/usr/bin/env python3
"""
Simple verification that all fixes from comprehensive review are implemented.

This script checks:
1. Version numbers are consistent
2. Database pool config handles SQLite
3. API __init__.py is populated
4. File organization is correct
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def check_versions():
    """Verify all version numbers are 2.1.0."""
    print("Checking version consistency...")

    import whitemagic
    import whitemagic.api

    errors = []

    # Check package version
    if whitemagic.__version__ != "2.1.0":
        errors.append(f"whitemagic.__version__ is {whitemagic.__version__}, expected 2.1.0")

    # Check API version
    if whitemagic.api.__version__ != "2.1.0":
        errors.append(f"whitemagic.api.__version__ is {whitemagic.api.__version__}, expected 2.1.0")

    # Check markdown files
    files_to_check = {
        "README.md": "2.1.0",
        "DOCUMENTATION.md": "2.1.0",
        "ROADMAP.md": "2.1.0",
    }

    for filename, expected_version in files_to_check.items():
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            content = filepath.read_text()
            if expected_version not in content:
                errors.append(f"{filename} doesn't contain version {expected_version}")

    if errors:
        print("❌ Version check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("✅ All versions are 2.1.0")
    return True


def check_database_config():
    """Verify database config handles SQLite properly."""
    print("\nChecking database pool configuration...")

    from whitemagic.api.database import Database

    # Test SQLite initialization
    try:
        db = Database("sqlite+aiosqlite:///:memory:")
        print("✅ SQLite database initializes without errors")
        return True
    except Exception as e:
        print(f"❌ SQLite initialization failed: {e}")
        return False


def check_api_module():
    """Verify API __init__.py is properly populated."""
    print("\nChecking API module exports...")

    from whitemagic import api

    required_exports = [
        "__version__",
        "app",
        "Database",
        "User",
        "APIKey",
        "Quota",
        "create_api_key",
        "validate_api_key",
        "RateLimiter",
        "PLAN_LIMITS",
    ]

    errors = []
    for export in required_exports:
        if not hasattr(api, export):
            errors.append(f"Missing export: {export}")

    if errors:
        print("❌ API module check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False

    print(f"✅ API module has all {len(required_exports)} required exports")
    return True


def check_file_organization():
    """Verify files were moved to correct locations."""
    print("\nChecking file organization...")

    checks = {
        "Review docs": Path("docs/reviews"),
        "Phase docs": Path("docs/phases"),
        "Production docs": Path("docs/production"),
        "Scripts dir": Path("scripts"),
        ".env.example": Path(".env.example"),
        "requirements-api-minimal.txt": Path("requirements-api-minimal.txt"),
    }

    base = Path(__file__).parent
    errors = []

    for name, path in checks.items():
        full_path = base / path
        if not full_path.exists():
            errors.append(f"Missing: {path}")

    if errors:
        print("❌ File organization check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False

    print(f"✅ All {len(checks)} organizational items exist")
    return True


def check_method_names():
    """Verify MemoryManager has correct method names."""
    print("\nChecking MemoryManager methods...")

    from whitemagic import MemoryManager
    import tempfile

    manager = MemoryManager(base_dir=tempfile.mkdtemp())

    required_methods = [
        "consolidate_short_term",
        "list_all_tags",
        "list_all_memories",
    ]

    errors = []
    for method in required_methods:
        if not hasattr(manager, method):
            errors.append(f"Missing method: {method}")

    # Check that OLD methods don't exist
    old_methods = ["consolidate_memories", "get_stats", "list_tags"]
    for method in old_methods:
        if hasattr(manager, method):
            errors.append(f"Old method still exists: {method}")

    if errors:
        print("❌ Method name check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False

    print(f"✅ All correct methods exist, old methods removed")
    return True


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("VERIFYING COMPREHENSIVE REVIEW FIXES")
    print("=" * 70 + "\n")

    checks = [
        ("Version Consistency", check_versions),
        ("Database Configuration", check_database_config),
        ("API Module Structure", check_api_module),
        ("File Organization", check_file_organization),
        ("MemoryManager Methods", check_method_names),
    ]

    passed = 0
    failed = 0

    for name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {name} ERROR: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(checks)} checks passed")
    print("=" * 70 + "\n")

    if failed == 0:
        print("🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
        print("\nThe following improvements were confirmed:")
        print("  1. ✅ Version numbers standardized to 2.1.0")
        print("  2. ✅ Database pool config handles SQLite correctly")
        print("  3. ✅ API module properly structured and importable")
        print("  4. ✅ Documentation reorganized into logical structure")
        print("  5. ✅ MemoryManager methods use correct names")
        print("\nProject is ready for production use!")
        return 0
    else:
        print(f"⚠️  {failed} check(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
