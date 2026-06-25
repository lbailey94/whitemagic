import re
from pathlib import Path
from typing import List

from whitemagic.tools.strata.models import Finding, FindingSeverity
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.checkers import register


@register
def check_typescript(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """TypeScript-specific checks: explicit any, missing return types."""
    for ts_file in file_index.files_by_extension(".ts", ".tsx"):
        try:
            content = file_index.read_text(ts_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Explicit : any usage
            if re.search(r':\s*\bany\b', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="ts_explicit_any",
                    file=str(ts_file.relative_to(project_path)),
                    line=i,
                    message="Explicit 'any' type weakens type safety.",
                    suggestion="Use a more specific type or 'unknown' with narrowing."
                ))

            # Function declarations without return type annotation
            # Match: function foo(...) {  or  const foo = (...) => {
            func_match = re.match(r'^\s*(?:export\s+)?(?:async\s+)?function\s+\w+\s*\([^)]*\)\s*(?!:)', stripped)
            if func_match and "{" in stripped:
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="ts_missing_return_type",
                    file=str(ts_file.relative_to(project_path)),
                    line=i,
                    message="Function lacks explicit return type annotation.",
                    suggestion="Add a return type to improve documentation and catch errors."
                ))

            # Arrow function assigned to const without return type
            arrow_match = re.match(r"^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*(?!:)\s*=>", stripped)
            if arrow_match:
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="ts_missing_return_type",
                    file=str(ts_file.relative_to(project_path)),
                    line=i,
                    message="Arrow function lacks explicit return type annotation.",
                    suggestion="Add a return type to improve documentation and catch errors."
                ))
