import re
from pathlib import Path
from typing import List

from whitemagic.tools.strata.models import Finding, FindingSeverity
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.checkers import register


@register
def check_zig(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """Basic Zig hygiene: panic, unreachable, manual alloc/free, debug prints."""
    for zig_file in file_index.files_by_extension(".zig"):
        try:
            content = zig_file.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            # @panic() calls
            if re.search(r'@panic\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="zig_bare_panic",
                    file=str(zig_file.relative_to(project_path)),
                    line=i,
                    message="Bare @panic() detected.",
                    suggestion="Return errors or use unreachable only for truly impossible states."
                ))

            # unreachable keyword (often hides bugs)
            if re.search(r'\bunreachable\b', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category="zig_unreachable",
                    file=str(zig_file.relative_to(project_path)),
                    line=i,
                    message="unreachable keyword may hide logic errors.",
                    suggestion="Ensure this branch is truly impossible."
                ))

            # catch unreachable (dangerous pattern)
            if re.search(r'catch\s+unreachable', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.ERROR,
                    category="zig_catch_unreachable",
                    file=str(zig_file.relative_to(project_path)),
                    line=i,
                    message="catch unreachable suppresses all errors.",
                    suggestion="Handle the error explicitly or use a proper fallback."
                ))

            # std.debug.print
            if re.search(r'std\.debug\.print\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="zig_debug_print",
                    file=str(zig_file.relative_to(project_path)),
                    line=i,
                    message="Debug print detected.",
                    suggestion="Remove or replace with proper logging."
                ))

            # Raw alloc/free without defer (naive check)
            if re.search(r'\.alloc\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="zig_manual_alloc",
                    file=str(zig_file.relative_to(project_path)),
                    line=i,
                    message="Manual allocation detected.",
                    suggestion="Ensure matching free() or use an arena allocator."
                ))
