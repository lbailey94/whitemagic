"""Version bump automation."""

import json
import re
from pathlib import Path


def bump_version(new_version: str, commit=True):
    """Update version across all files."""
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        raise ValueError(f"Invalid version: {new_version}")

    files_updated = []

    # 1. VERSION
    Path("VERSION").write_text(new_version + "\n")
    files_updated.append("VERSION")

    # 2. pyproject.toml
    p = Path("pyproject.toml")
    content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', p.read_text())
    p.write_text(content)
    files_updated.append("pyproject.toml")

    # 3-5. package.json files
    for pkg in [
        "whitemagic-mcp/package.json",
        "clients/python/pyproject.toml",
        "clients/typescript/package.json",
    ]:
        path = Path(pkg)
        if path.suffix == ".json":
            data = json.loads(path.read_text())
            data["version"] = new_version
            path.write_text(json.dumps(data, indent=2) + "\n")
        else:  # .toml
            content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', path.read_text())
            path.write_text(content)
        files_updated.append(pkg)

    print(f"✅ Updated {len(files_updated)} files to v{new_version}")

    if commit:
        import subprocess

        subprocess.run(["git", "add"] + files_updated, check=False)  # nosec
        subprocess.run(
            ["git", "commit", "-m", f"chore: bump version to {new_version}"], check=False
        )  # nosec
        print("✅ Committed")

    return files_updated
