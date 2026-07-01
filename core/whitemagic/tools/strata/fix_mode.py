"""STRATA Fix Mode — apply auto-fixable findings.

Tier 1 fixes (behavior-preserving, low risk):
- trivial_comment: Remove comments that restate code
- narrative_comment: Remove decorative separators and step markers
- meta_comment: Remove AI-agent meta comments
- print_debug: Replace print() with logger.debug() (only if logger already exists)
- range_len_loop: Convert for i in range(len(x)) to enumerate
- mutable_default: Manual fix needed (0 findings currently)
"""

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _fix_trivial_comments(source: str, findings: list[dict]) -> str:
    lines = source.splitlines(keepends=True)
    remove_lines: set[int] = set()
    for f in findings:
        if f["category"] == "trivial_comment":
            remove_lines.add(f["line"] - 1)
    if not remove_lines:
        return source
    result = []
    for i, line in enumerate(lines):
        if i in remove_lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            else:
                in_str = False
                str_char = None
                for j, c in enumerate(line):
                    if in_str:
                        if c == str_char and (j == 0 or line[j-1] != '\\'):
                            in_str = False
                    else:
                        if c in ('"', "'"):
                            in_str = True
                            str_char = c
                        elif c == '#':
                            line = line[:j].rstrip() + '\n'
                            break
        result.append(line)
    return ''.join(result)


def _fix_narrative_comments(source: str, findings: list[dict]) -> str:
    lines = source.splitlines(keepends=True)
    remove_lines: set[int] = set()
    for f in findings:
        if f["category"] in ("narrative_comment", "meta_comment"):
            remove_lines.add(f["line"] - 1)
    if not remove_lines:
        return source
    result = []
    for i, line in enumerate(lines):
        if i in remove_lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
        result.append(line)
    return ''.join(result)


def _fix_print_debug(source: str, findings: list[dict]) -> str:
    if not any(f["category"] == "print_debug" for f in findings):
        return source
    has_logger = bool(re.search(r'^\s*logger\s*=\s*logging\.getLogger', source, re.MULTILINE))
    if not has_logger:
        return source
    lines = source.splitlines(keepends=True)
    fix_lines: set[int] = set()
    for f in findings:
        if f["category"] == "print_debug":
            fix_lines.add(f["line"] - 1)
    result = []
    for i, line in enumerate(lines):
        if i in fix_lines:
            new_line = re.sub(r'\bprint\s*\(', 'logger.debug(', line)
            result.append(new_line)
        else:
            result.append(line)
    return ''.join(result)


def _fix_range_len_loop(source: str, findings: list[dict]) -> str:
    if not any(f["category"] == "range_len_loop" for f in findings):
        return source
    pattern = re.compile(r'for\s+(\w+)\s+in\s+range\(len\((\w+)\)\)\s*:')
    def replacer_enum(m):
        idx_var = m.group(1)
        iter_name = m.group(2)
        item_var = iter_name.rstrip('s') if iter_name.endswith('s') else f"{iter_name}_item"
        return f'for {idx_var}, {item_var} in enumerate({iter_name}):'
    lines = source.splitlines(keepends=True)
    fix_lines: set[int] = set()
    for f in findings:
        if f["category"] == "range_len_loop":
            fix_lines.add(f["line"] - 1)
    result = []
    for i, line in enumerate(lines):
        if i in fix_lines:
            new_line = pattern.sub(replacer_enum, line)
            result.append(new_line)
        else:
            result.append(line)
    return ''.join(result)


def _fix_mutable_default(source: str, findings: list[dict]) -> str:
    return source


def apply_fixes(project_path: Path, findings: list[dict],
                categories: set[str] | None = None) -> dict:
    auto_fixable = {
        "trivial_comment", "narrative_comment", "meta_comment",
        "print_debug", "range_len_loop", "mutable_default",
    }
    if categories is None:
        categories = auto_fixable
    by_file: dict[str, list[dict]] = {}
    for f in findings:
        if f["category"] in categories:
            rel = f["file"]
            by_file.setdefault(rel, []).append(f)
    stats = {"files_changed": 0, "findings_fixed": 0, "errors": []}
    for rel_path, file_findings in by_file.items():
        abs_path = project_path / rel_path
        if not abs_path.exists():
            stats["errors"].append(f"File not found: {rel_path}")
            continue
        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            stats["errors"].append(f"Cannot read {rel_path}: {e}")
            continue
        original = source
        if "trivial_comment" in categories:
            source = _fix_trivial_comments(source, file_findings)
        if "narrative_comment" in categories or "meta_comment" in categories:
            source = _fix_narrative_comments(source, file_findings)
        if "print_debug" in categories:
            source = _fix_print_debug(source, file_findings)
        if "range_len_loop" in categories:
            source = _fix_range_len_loop(source, file_findings)
        if "mutable_default" in categories:
            source = _fix_mutable_default(source, file_findings)
        if source != original:
            try:
                ast.parse(source)
            except SyntaxError as e:
                stats["errors"].append(f"Syntax error after fix in {rel_path}: {e}")
                continue
            try:
                abs_path.write_text(source, encoding="utf-8")
                stats["files_changed"] += 1
                stats["findings_fixed"] += len(file_findings)
            except OSError as e:
                stats["errors"].append(f"Cannot write {rel_path}: {e}")
    return stats
