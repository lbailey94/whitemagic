import re
from pathlib import Path
from typing import List

from whitemagic.tools.strata.models import Finding, FindingSeverity
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.checkers import register


@register
def check_lua(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """Basic Lua hygiene: global pollution, debug prints, bare pcall."""
    for lua_file in file_index.files_by_extension(".lua"):
        try:
            content = lua_file.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue

            # Global variable assignment (no local keyword)
            match = re.match(r'^\s*([A-Za-z_]\w*)\s*=', stripped)
            if match and match.group(1) not in {"true", "false", "nil", "return", "function", "if", "while", "for", "local"}:
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="lua_global_pollution",
                    file=str(lua_file.relative_to(project_path)),
                    line=i,
                    message=f"Global variable assignment: '{match.group(1)}'.",
                    suggestion="Use 'local' to avoid polluting the global namespace."
                ))

            # print() debug statement
            if re.search(r'\bprint\s*\(', stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="lua_debug_print",
                    file=str(lua_file.relative_to(project_path)),
                    line=i,
                    message="Debug print detected.",
                    suggestion="Remove debug prints or use a proper logging system."
                ))

            # pcall without error handling
            if re.search(r'\bpcall\s*\(', stripped) and "if" not in stripped:
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="lua_bare_pcall",
                    file=str(lua_file.relative_to(project_path)),
                    line=i,
                    message="pcall() without error handling.",
                    suggestion="Capture and handle the success boolean and error value."
                ))
