from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_archive_reconnaissance(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Check if archive directories exist and compare with current code."""
    # Use file_index's cached tree walk to find archive directories
    # instead of doing separate rglob walks
    archive_dirs: list[Path] = []
    seen_dirs: set = set()
    ext_index = file_index._build_extension_index()
    for files in ext_index.values():
        for f in files:
            for parent in f.parents:
                if parent.name in ("archive", "archives") and parent not in seen_dirs:
                    seen_dirs.add(parent)
                    archive_dirs.append(parent)

    for archive_dir in archive_dirs:
        if not archive_dir.is_dir():
            continue
        # Find Python files in archive that might be more complete
        for archived_file in archive_dir.rglob("*.py"):
            rel_path = archived_file.relative_to(archive_dir)
            current_file = archive_dir.parent / rel_path
            if current_file.exists():
                archived_size = archived_file.stat().st_size
                current_size = current_file.stat().st_size
                if current_size == 0:
                    continue
                if archived_size > current_size * 1.5:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="archive_drift",
                            file=str(current_file.relative_to(project_path)),
                            line=None,
                            message=f"Archive version is {archived_size / current_size:.1f}x larger than current version.",
                            suggestion=f"Review {archived_file} — the archive may contain more complete code.",
                        )
                    )
