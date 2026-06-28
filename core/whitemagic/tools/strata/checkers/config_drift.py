import re
from pathlib import Path
from typing import Dict, List

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_config_drift(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """Detect when config keys are read in one place but not another."""
    config_reads: Dict[str, List[str]] = {}
    for py_file in file_index.python_files():
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        # Find dictionary key accesses that look like config
        for match in re.finditer(r'config\[(?:["\'])(\w+)(?:["\'])\]', content):
            key = match.group(1)
            rel_path = str(py_file.relative_to(project_path))
            config_reads.setdefault(key, []).append(rel_path)

    # Keys read in only one file might be missed by other consumers
    for key, files in config_reads.items():
        if len(files) == 1 and len(config_reads) > 5:
            findings.append(Finding(
                severity=FindingSeverity.INFO,
                category="config_drift",
                file=files[0],
                line=None,
                message=f"Config key '{key}' is only read in one location.",
                suggestion="Verify this key is visible to all consumers that need it."
            ))
