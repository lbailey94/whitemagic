import hashlib
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

# Minimum block size to flag as copy-paste
_DUPLICATE_BLOCK_SIZE = 75


@register
def check_copy_paste(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect identical code blocks across files using a sliding window hash.

    Skips false positives:
    - grimoire/ directory (intentional 28-fold repetition pattern)
    - Module-level boilerplate (handled by start_offset skip to first def/class)
    """
    # Directories with intentional repetitive patterns
    _REPETITIVE_DIRS = {"grimoire", "harmony", "handlers", "registry_defs"}

    window_hashes: dict[str, tuple[Path, int]] = {}

    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        rel = py_file.relative_to(project_path)
        # Skip files in repetitive pattern directories (e.g., grimoire 28-fold)
        if any(part in _REPETITIVE_DIRS for part in rel.parts):
            continue
        try:
            lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        # Find the first function or class definition to skip module headers
        start_offset = 0
        for idx, line in enumerate(lines):
            if re.search(r"\b(def |class )", line):
                start_offset = idx
                break

        effective_lines = lines[start_offset:]
        if len(effective_lines) < _DUPLICATE_BLOCK_SIZE:
            continue

        for i in range(len(effective_lines) - _DUPLICATE_BLOCK_SIZE + 1):
            block = effective_lines[i : i + _DUPLICATE_BLOCK_SIZE]
            normalized = _normalize_block(block)
            h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if h in window_hashes:
                first_file, first_line = window_hashes[h]
                # Only flag cross-file duplicates (same-file is usually pattern, not copy-paste)
                if first_file != py_file:
                    rel_first = str(first_file.relative_to(project_path))
                    rel_second = str(py_file.relative_to(project_path))
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="copy_paste",
                            file=rel_second,
                            line=i + 1,
                            message=f"Potential copy-paste block matches {rel_first}:{first_line}.",
                            suggestion="Extract shared logic into a reusable function or module.",
                        )
                    )
                    # Remove hash to avoid duplicate findings for same block
                    del window_hashes[h]
            else:
                window_hashes[h] = (py_file, i + 1)


def _normalize_block(lines: list[str]) -> str:
    """Strip comments, whitespace, and lowercase for robust comparison.
    Returns empty string if the block is mostly boilerplate (imports, blanks, docstrings)."""
    result: list[str] = []
    meaningful = 0
    in_docstring = False
    for line in lines:
        stripped = line.strip()
        # Detect multi-line docstring boundaries
        if stripped in {'"""', "'''"} or stripped.startswith(('"""', "'''")):
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        # Remove Python comments
        if "#" in stripped:
            stripped = stripped.split("#", 1)[0].strip()
        # Collapse multiple whitespace
        stripped = re.sub(r"\s+", " ", stripped)
        # Skip pure import boilerplate lines and blanks
        if not stripped or stripped.startswith(("import ", "from ")):
            continue
        meaningful += 1
        result.append(stripped.lower())
    # Require at least 80% of the window to be meaningful code
    if meaningful < (_DUPLICATE_BLOCK_SIZE * 8 // 10):
        return ""
    return "\n".join(result)
