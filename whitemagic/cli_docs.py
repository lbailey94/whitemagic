"""Documentation drift check/fix."""

import re
from pathlib import Path


def docs_check_and_fix(fix=False, dry_run=False):
    """Check/fix doc version drift."""
    from whitemagic.cli_audit import check_version_sync

    version_info = check_version_sync()
    canonical = version_info.get("canonical")

    if not canonical:
        print("❌ Version mismatch! Fix versions first.")
        return []

    issues = []
    docs_path = Path("docs")

    for doc in docs_path.rglob("*.md"):
        content = doc.read_text()
        old_pattern = r"2\.2\.[0-6](?![0-9])"
        matches = list(re.finditer(old_pattern, content))

        if matches:
            issues.append({"file": doc, "count": len(matches)})

            if fix and not dry_run:
                new_content = re.sub(old_pattern, canonical, content)
                doc.write_text(new_content)
                print(f"✅ Fixed: {doc.name}")
            elif dry_run:
                print(f"Would fix: {doc.name} ({len(matches)} occurrences)")

    return issues
