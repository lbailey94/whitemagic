"""Project audit command - comprehensive health check."""

import json
import re
from pathlib import Path
from typing import Any, Dict

from rich.console import Console
from rich.table import Table

console = Console()


def audit_project(full: bool = False) -> Dict[str, Any]:
    """Run comprehensive project audit."""
    results = {
        "version_sync": check_version_sync(),
        "doc_coverage": check_documentation(),
        "memory_stats": get_memory_stats(),
        "package_config": check_package_config(),
    }

    if full:
        results["code_quality"] = check_code_quality()

    return results


def check_version_sync() -> Dict[str, Any]:
    """Check version consistency across all files."""
    version_files = {
        "VERSION": Path("VERSION"),
        "pyproject.toml": Path("pyproject.toml"),
        "whitemagic-mcp/package.json": Path("whitemagic-mcp/package.json"),
        "clients/python/pyproject.toml": Path("clients/python/pyproject.toml"),
        "clients/typescript/package.json": Path("clients/typescript/package.json"),
    }

    versions = {}
    for name, path in version_files.items():
        if path.exists():
            content = path.read_text()
            if name.endswith(".json"):
                data = json.loads(content)
                versions[name] = data.get("version", "MISSING")
            elif name.endswith(".toml"):
                match = re.search(r'version\s*=\s*["\']([^"\']+)', content)
                versions[name] = match.group(1) if match else "MISSING"
            else:
                versions[name] = content.strip()
        else:
            versions[name] = "FILE_NOT_FOUND"

    unique_versions = {v for v in versions.values() if v not in ["MISSING", "FILE_NOT_FOUND"]}

    return {
        "status": "OK" if len(unique_versions) == 1 else "MISMATCH",
        "versions": versions,
        "canonical": list(unique_versions)[0] if len(unique_versions) == 1 else None,
    }


def check_documentation() -> Dict[str, Any]:
    """Check for documentation drift and coverage."""
    issues = []
    docs_path = Path("docs")

    if not docs_path.exists():
        return {"status": "NO_DOCS", "issues": [], "total_docs": 0}

    # Scan for version references in docs
    for doc in docs_path.rglob("*.md"):
        try:
            content = doc.read_text()
            # Find old version patterns (2.6.5 through 2.6.5)
            old_versions = re.findall(r"2\.2\.[0-6](?![0-9])", content)
            if old_versions:
                issues.append(
                    {
                        "file": doc.name,
                        "type": "outdated_version",
                        "found": list(set(old_versions)),
                    }
                )
        except Exception:
            pass  # Skip unreadable files

    return {
        "status": "OK" if not issues else "DRIFT_DETECTED",
        "issues": issues,
        "total_docs": len(list(docs_path.rglob("*.md"))),
    }


def get_memory_stats() -> Dict[str, Any]:
    """Get memory system statistics."""
    memory_path = Path("memory")

    if not memory_path.exists():
        return {"status": "NO_MEMORY_SYSTEM", "short_term": 0, "long_term": 0}

    short_term = (
        len(list((memory_path / "short_term").glob("*.md")))
        if (memory_path / "short_term").exists()
        else 0
    )
    long_term = (
        len(list((memory_path / "long_term").glob("*.md")))
        if (memory_path / "long_term").exists()
        else 0
    )

    # Check for consolidation need
    consolidation_needed = short_term > 15

    return {
        "status": "OK",
        "short_term": short_term,
        "long_term": long_term,
        "total": short_term + long_term,
        "consolidation_needed": consolidation_needed,
    }


def check_package_config() -> Dict[str, Any]:
    """Check package configuration completeness."""
    issues = []

    # Check pyproject.toml
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        content = pyproject.read_text()

        # Check for old license format
        if "[project.license]" in content or "license = {text" in content:
            issues.append(
                {
                    "file": "pyproject.toml",
                    "issue": "Deprecated license format",
                    "severity": "HIGH",
                }
            )

        # Check for setuptools package list
        if "[tool.setuptools]" in content:
            packages_section = re.search(
                r"\[tool\.setuptools\](.*?)(?=\n\[|\Z)", content, re.DOTALL
            )
            if packages_section and "packages = [" not in packages_section.group(1):
                issues.append(
                    {
                        "file": "pyproject.toml",
                        "issue": "Missing explicit package list",
                        "severity": "MEDIUM",
                    }
                )

    return {
        "status": "OK" if not issues else "ISSUES_FOUND",
        "issues": issues,
    }


def check_code_quality() -> Dict[str, Any]:
    """Check code quality metrics (optional, slower)."""
    # Placeholder for future pytest-cov integration
    return {
        "status": "NOT_IMPLEMENTED",
        "note": "Run 'pytest --cov' for coverage report",
    }


def print_audit_report(results: Dict[str, Any]) -> None:
    """Print formatted audit report."""
    console.print("\n[bold cyan]🔍 WhiteMagic Project Audit[/bold cyan]")
    console.print("━" * 60)

    # Version Sync
    version_sync = results["version_sync"]
    if version_sync["status"] == "OK":
        console.print(f"✅ [green]Version Sync[/green]: {version_sync['canonical']}")
    else:
        console.print("⚠️  [yellow]Version Sync: MISMATCH[/yellow]")
        table = Table()
        table.add_column("File")
        table.add_column("Version")
        for file, version in version_sync["versions"].items():
            table.add_row(file, version)
        console.print(table)

    # Documentation
    doc_check = results["doc_coverage"]
    if doc_check["status"] == "OK":
        console.print(f"✅ [green]Documentation[/green]: {doc_check['total_docs']} files, no drift")
    else:
        console.print(f"⚠️  [yellow]Documentation Drift[/yellow]: {len(doc_check['issues'])} files")
        for issue in doc_check["issues"][:5]:  # Show first 5
            console.print(f"   • {issue['file']}: Found {issue['found']}")

    # Memory Stats
    memory = results["memory_stats"]
    if memory["status"] == "OK":
        console.print(
            f"📊 [blue]Memories[/blue]: {memory['short_term']} short-term, "
            f"{memory['long_term']} long-term"
        )
        if memory["consolidation_needed"]:
            console.print("   💡 [yellow]Recommendation: Consider consolidating memories[/yellow]")

    # Package Config
    pkg_config = results["package_config"]
    if pkg_config["status"] == "OK":
        console.print("✅ [green]Package Config[/green]: Clean")
    else:
        console.print(f"⚠️  [yellow]Package Config[/yellow]: {len(pkg_config['issues'])} issues")
        for issue in pkg_config["issues"]:
            severity_color = "red" if issue["severity"] == "HIGH" else "yellow"
            console.print(
                f"   • [{severity_color}]{issue['issue']}[/{severity_color}] in {issue['file']}"
            )

    console.print("━" * 60)

    # Overall status
    has_issues = any(
        r.get("status") not in ["OK", "NOT_IMPLEMENTED"]
        for r in results.values()
        if isinstance(r, dict)
    )

    if has_issues:
        console.print("\n⚠️  [yellow]Issues found[/yellow] - Review above for details")
        console.print("💡 Run 'whitemagic docs-check --fix' to fix documentation drift")
    else:
        console.print("\n✅ [green]All checks passed![/green]")
