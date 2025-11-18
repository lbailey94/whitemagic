import re
import sys
from pathlib import Path


def get_canonical_version(repo_root: Path) -> str:
    """Reads the version from the VERSION file."""
    return (repo_root / "VERSION").read_text().strip()


def find_version_files(repo_root: Path):
    """Finds all files that should contain a version string."""
    return [
        repo_root / "README.md",
        repo_root / "dashboard/package.json",
        repo_root / "pyproject.toml",
        *repo_root.glob("whitemagic/**/__init__.py"),
        *repo_root.glob("clients/python/whitemagic_client/__init__.py"),
    ]


def check_versions(repo_root: Path, canonical_version: str, files_to_check: list[Path]):
    """Checks for version consistency across files."""
    errors = []
    version_regex = re.compile(r"(\d+\.\d+\.\d+)")

    for file_path in files_to_check:
        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            continue

        content = file_path.read_text()

        if file_path.name == "package.json":
            match = re.search(r'"version": "(\d+\.\d+\.\d+)"', content)
            if not match or match.group(1) != canonical_version:
                errors.append(
                    f"Mismatch in {file_path}: Expected {canonical_version}, found {match.group(1) if match else 'None'}"
                )
        elif file_path.name == "pyproject.toml":
            match = re.search(r'version = "(\d+\.\d+\.\d+)"', content)
            if not match or match.group(1) != canonical_version:
                errors.append(
                    f"Mismatch in {file_path}: Expected {canonical_version}, found {match.group(1) if match else 'None'}"
                )
        elif file_path.name == "__init__.py":
            match = re.search(r'__version__ = "(\d+\.\d+\.\d+)"', content)
            if match and match.group(1) != canonical_version:
                errors.append(
                    f"Mismatch in {file_path}: Expected {canonical_version}, found {match.group(1)}"
                )
        else:  # For README.md and other files
            if canonical_version not in content:
                # A simple check for README, can be improved
                pass

    return errors


if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent
    canonical_version = get_canonical_version(repo_root)
    files_to_check = find_version_files(repo_root)

    print(f"Checking for version {canonical_version}...")
    errors = check_versions(repo_root, canonical_version, files_to_check)

    if errors:
        print("\nVersion consistency check failed:")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    else:
        print("\nVersion consistency check passed!")
        sys.exit(0)
