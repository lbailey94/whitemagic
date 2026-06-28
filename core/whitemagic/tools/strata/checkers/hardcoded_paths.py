import re
from pathlib import Path
from typing import List

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

# Files where Path.home() / .expanduser() is allowed per AGENTS.md
_ALLOWED_PATH_FILES = {
    "config/paths.py", "config\\paths.py",
    # Security blocklist files — must use ~ patterns to match any user's home
    "core/governor.py", "security/tool_gating.py",
    # External tool discovery — must find system binaries (Mojo, GHC, HuggingFace)
    "core/fusions.py", "core/memory/embedding_daemon.py",
    "tools/handlers/introspection.py",
    # Path detection patterns — regex patterns for finding user-specific paths
    "tools/introspection.py", "tools/strata/checkers/doc_drift.py",
}


def _is_comment_line(line: str) -> bool:
    """Return True if the line is a Python comment."""
    return line.lstrip().startswith("#")


def _match_in_comment(line: str, match_start: int) -> bool:
    """Return True if the match position is inside a comment on the given line."""
    # Find the comment start on this line
    hash_pos = line.find("#")
    if hash_pos == -1:
        return False
    return match_start >= hash_pos


def _is_allowed_file(rel_path: str) -> bool:
    """Return True for files where home-path expansion is explicitly allowed."""
    return any(allowed in rel_path for allowed in _ALLOWED_PATH_FILES)


@register
def check_hardcoded_paths(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """Find hardcoded home directory paths that should use dynamic resolution."""
    path_patterns = [
        (r'["\']~/[^"\']*', "Hardcoded home directory path"),
        (r'["\']/(?:home|Users)/[^"\']+', "Hardcoded user directory path"),
        (r'\bPath\.home\(\)', "Direct home() call on Path"),
        (r'os\.path\.expanduser\(["\']~', "Manual expanduser (may be inconsistent)"),
        (r'\.expanduser\(\)', "Manual expanduser (may be inconsistent)"),
    ]
    pattern_strings = [p[0] for p in path_patterns]
    descriptions = [p[1] for p in path_patterns]

    py_files = [str(f) for f in file_index.python_files() if not FileIndex.is_test_file(f)]

    # Try Rust parallel batch regex scan
    try:
        import whitemagic_rs
        results = whitemagic_rs.batch_regex_scan(py_files, pattern_strings)
        for file_path, pat_idx, line_num, match_text in results:
            rel = str(Path(file_path).relative_to(project_path))
            if _is_allowed_file(rel):
                continue
            # Skip matches in comment lines
            try:
                content = file_index.read_text(Path(file_path))
                lines = content.splitlines()
                if 0 < line_num <= len(lines) and _is_comment_line(lines[line_num - 1]):
                    continue
            except (OSError, IndexError):
                pass
            desc = descriptions[pat_idx]
            category = "hardcoded_path_pattern" if _looks_like_path_pattern(match_text) else "hardcoded_path"
            severity = FindingSeverity.INFO if category == "hardcoded_path_pattern" else FindingSeverity.WARNING
            findings.append(Finding(
                severity=severity,
                category=category,
                file=str(Path(file_path).relative_to(project_path)),
                line=line_num,
                message=f"{desc}: {match_text}",
                suggestion="Use a configurable base path, platform state directory, or project-specific path resolver."
            ))
        return
    except (ImportError, AttributeError, Exception):
        pass

    # Fallback: Python sequential scan
    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        rel_path = str(py_file.relative_to(project_path))
        if _is_allowed_file(rel_path):
            continue
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        for pattern, desc in path_patterns:
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count("\n") + 1
                # Skip matches in comment lines
                if 0 < line_num <= len(lines) and _is_comment_line(lines[line_num - 1]):
                    continue
                category = "hardcoded_path_pattern" if _looks_like_path_pattern(match.group(0)) else "hardcoded_path"
                severity = FindingSeverity.INFO if category == "hardcoded_path_pattern" else FindingSeverity.WARNING
                findings.append(Finding(
                    severity=severity,
                    category=category,
                    file=str(py_file.relative_to(project_path)),
                    line=line_num,
                    message=f"{desc}: {match.group(0)}",
                    suggestion="Use a configurable base path, platform state directory, or project-specific path resolver."
                ))


def _looks_like_path_pattern(text: str) -> bool:
    """Return True for regex/glob path patterns rather than concrete paths."""
    pattern_markers = ("[", "]", "(?:", "\\", "*", "+", "?")
    return any(marker in text for marker in pattern_markers)
