import re
from pathlib import Path
from typing import List

from whitemagic.tools.strata.models import Finding, FindingSeverity
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.checkers import register


@register
def check_todo_vs_fixme(project_path: Path, file_index: FileIndex, findings: List[Finding]):
    """Check for TODO comments that should be FIXME (non-blocking vs blocking)."""
    pattern = r'#\s*TODO\s*[:\s]*(\w+)'
    py_files = [str(f) for f in file_index.python_files() if not FileIndex.is_test_file(f)]

    # Try Rust parallel batch regex scan
    try:
        import whitemagic_rs
        results = whitemagic_rs.batch_regex_scan(py_files, [pattern])
        for file_path, _, line_num, match_text in results:
            # Extract the word after TODO
            m = re.search(r'TODO\s*[:\s]*(\w+)', match_text)
            word = m.group(1) if m else "unknown"
            findings.append(Finding(
                severity=FindingSeverity.INFO,
                category="todo_style",
                file=str(Path(file_path).relative_to(project_path)),
                line=line_num,
                message=f"TODO found: {word}",
                suggestion="Use FIXME for blocking issues, TODO for non-blocking enhancements."
            ))
        return
    except (ImportError, AttributeError, Exception):
        pass

    # Fallback: Python sequential scan
    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        try:
            content = file_index.read_text(py_file)
        except (OSError, UnicodeDecodeError):
            continue
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count("\n") + 1
            findings.append(Finding(
                severity=FindingSeverity.INFO,
                category="todo_style",
                file=str(py_file.relative_to(project_path)),
                line=line_num,
                message=f"TODO found: {match.group(1)}",
                suggestion="Use FIXME for blocking issues, TODO for non-blocking enhancements."
            ))
