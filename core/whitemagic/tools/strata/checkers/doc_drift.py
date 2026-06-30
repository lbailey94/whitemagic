import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_doc_drift(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Check if README.md and AGENTS.md reference files that no longer exist."""
    docs_to_check = []
    agents_path = project_path / "AGENTS.md"
    readme_path = project_path / "README.md"

    if agents_path.exists():
        docs_to_check.append(("AGENTS.md", agents_path.read_text(encoding="utf-8")))
    if readme_path.exists():
        docs_to_check.append(("README.md", readme_path.read_text(encoding="utf-8")))

    for doc_name, doc_content in docs_to_check:
        # Find file references in docs (backtick-quoted paths)
        file_refs = re.findall(
            r"`([\w\-/~.]+\.(?:py|rs|jsx?|ts|tsx|sh|md|toml|yaml))`", doc_content
        )
        for ref in set(file_refs):
            # Skip absolute home directory references
            if ref.startswith("~/"):
                continue
            ref_path = project_path / ref
            if not ref_path.exists() and "/" in ref:
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="doc_drift",
                        file=doc_name,
                        line=None,
                        message=f"{doc_name} references '{ref}' which does not exist.",
                        suggestion=f"Update {doc_name} or restore the missing file.",
                    )
                )
