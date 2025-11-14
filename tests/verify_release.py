#!/usr/bin/env python3
"""
WhiteMagic v0.1.0 Release Verification Script

Runs comprehensive checks to ensure the release is ready.
"""

import sys
import subprocess
from pathlib import Path
from typing import Tuple, List


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_test(name: str, passed: bool, details: str = ""):
    status = (
        f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    )
    print(f"{status} {name}")
    if details:
        print(f"     {Colors.YELLOW}{details}{Colors.RESET}")


def run_command(cmd: List[str], timeout: int = 10) -> Tuple[bool, str]:
    """Run a command and return (success, output)"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=Path(__file__).parent
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def main():
    project_root = Path(__file__).parent
    all_passed = True

    print_header("WhiteMagic v0.1.0 Release Verification")

    # 1. File Structure
    print_header("1. File Structure")

    required_files = {
        "Python Package": [
            "whitemagic/__init__.py",
            "whitemagic/core.py",
            "whitemagic/models.py",
            "whitemagic/exceptions.py",
            "whitemagic/utils.py",
            "whitemagic/constants.py",
        ],
        "MCP Server": [
            "whitemagic-mcp/package.json",
            "whitemagic-mcp/tsconfig.json",
            "whitemagic-mcp/dist/index.js",
            "whitemagic-mcp/dist/client.js",
        ],
        "CLI": [
            "cli.py",
            "memory_manager.py",
        ],
        "Tests": [
            "tests/test_memory_manager.py",
            "tests/test_mcp_integration.py",
        ],
        "Documentation": [
            "README.md",
            "INSTALL.md",
            "RELEASE_NOTES_v0.1.0.md",
            "ROADMAP.md",
            "LICENSE",
        ],
        "Packaging": [
            "pyproject.toml",
            "setup.py",
            "MANIFEST.in",
        ],
    }

    for category, files in required_files.items():
        for file in files:
            file_path = project_root / file
            exists = file_path.exists()
            print_test(f"{category}: {file}", exists)
            if not exists:
                all_passed = False

    # 2. Python Package Import
    print_header("2. Python Package Import")

    success, output = run_command(
        [
            "python3",
            "-c",
            'import sys; sys.path.insert(0, "."); from whitemagic import MemoryManager, __version__; print(f"v{__version__}")',
        ]
    )
    print_test("Import whitemagic package", success, output.strip() if success else output[:100])
    if not success:
        all_passed = False

    # 3. Unit Tests
    print_header("3. Unit Tests")

    success, output = run_command(
        ["python3", "-m", "unittest", "tests.test_memory_manager", "-v"], timeout=30
    )
    if success:
        lines = output.split("\n")
        summary = [l for l in lines if "Ran" in l or "OK" in l or "FAILED" in l]
        print_test("Python unit tests (18 tests)", success, " ".join(summary))
    else:
        print_test("Python unit tests (18 tests)", False, output[-200:])
        all_passed = False

    # 4. MCP Integration Tests
    print_header("4. MCP Integration Tests")

    success, output = run_command(
        ["python3", "-m", "unittest", "tests.test_mcp_integration", "-v"], timeout=30
    )
    if success:
        lines = output.split("\n")
        summary = [l for l in lines if "Ran" in l or "OK" in l or "FAILED" in l]
        print_test("MCP integration tests (5 tests)", success, " ".join(summary))
    else:
        print_test("MCP integration tests (5 tests)", False, output[-200:])
        all_passed = False

    # 5. CLI Functionality
    print_header("5. CLI Functionality")

    success, output = run_command(["python3", "cli.py", "--help"])
    print_test("CLI help command", success)
    if not success:
        all_passed = False

    success, output = run_command(["python3", "cli.py", "list", "--json"])
    print_test("CLI list command", success)
    if not success:
        all_passed = False

    # 6. MCP Server Build
    print_header("6. MCP Server")

    mcp_built = (project_root / "whitemagic-mcp" / "dist" / "index.js").exists()
    print_test("MCP server built", mcp_built)
    if not mcp_built:
        all_passed = False

    # Check Node.js
    success, output = run_command(["node", "--version"])
    print_test("Node.js available", success, output.strip() if success else "")
    if not success:
        all_passed = False

    # 7. Documentation Complete
    print_header("7. Documentation")

    docs = {
        "README.md": 1000,  # Minimum lines
        "INSTALL.md": 100,
        "RELEASE_NOTES_v0.1.0.md": 200,
    }

    for doc, min_size in docs.items():
        doc_path = project_root / doc
        if doc_path.exists():
            content = doc_path.read_text()
            size_ok = len(content) > min_size
            print_test(f"{doc} (>{min_size} chars)", size_ok, f"{len(content)} chars")
            if not size_ok:
                all_passed = False
        else:
            print_test(f"{doc}", False, "File not found")
            all_passed = False

    # 8. Version Consistency
    print_header("8. Version Consistency")

    # Check __init__.py version
    init_file = project_root / "whitemagic" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text()
        has_version = '__version__ = "2.1.0"' in content
        print_test("whitemagic/__init__.py version", has_version, "v2.1.0")
        if not has_version:
            all_passed = False

    # Check constants.py version
    constants_file = project_root / "whitemagic" / "constants.py"
    if constants_file.exists():
        content = constants_file.read_text()
        has_version = 'VERSION = "2.1.0"' in content
        print_test("whitemagic/constants.py version", has_version, "v2.1.0")
        if not has_version:
            all_passed = False

    # Check pyproject.toml version
    pyproject_file = project_root / "pyproject.toml"
    if pyproject_file.exists():
        content = pyproject_file.read_text()
        has_version = 'version = "2.1.0"' in content
        print_test("pyproject.toml version", has_version, "v2.1.0")
        if not has_version:
            all_passed = False

    # Final Summary
    print_header("Verification Summary")

    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED{Colors.RESET}")
        print(f"\n{Colors.GREEN}WhiteMagic v0.1.0 is ready for release!{Colors.RESET}")
        print(f"\n{Colors.BLUE}Next steps:{Colors.RESET}")
        print("  1. Tag the release: git tag v0.1.0-beta")
        print("  2. Push to GitHub: git push origin v0.1.0-beta")
        print("  3. Create GitHub release with release notes")
        print("  4. Proceed to Phase 2A (Whop integration)")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ SOME CHECKS FAILED{Colors.RESET}")
        print(f"\n{Colors.RED}Please fix the issues above before releasing.{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
