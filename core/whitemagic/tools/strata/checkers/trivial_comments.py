"""Detect trivial comments that just restate the code.

Trivial comments add no value — they describe what the code does rather than
*why* it does it. They accumulate in AI-generated code and make maintenance
harder by adding noise.
"""

import ast
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

_TRIVIAL_PATTERNS = [
    re.compile(r"^#\s*(import|from)\s", re.I),
    re.compile(r"^#\s*(return|returns)\s", re.I),
    re.compile(r"^#\s*(initialize|init)\s", re.I),
    re.compile(r"^#\s*(set|assign|define)\s+(the\s+)?(variable|value|counter|result|data|list|dict|config)", re.I),
    re.compile(r"^#\s*create\s+(the\s+)?(new\s+)?(object|instance|list|dict|set|variable)", re.I),
    re.compile(r"^#\s*(start|begin|end|finish)\s", re.I),
    re.compile(r"^#\s*(call|invoke|execute|run)\s", re.I),
    re.compile(r"^#\s*(check|verify|test|validate)\s", re.I),
    re.compile(r"^#\s*(print|log|output|display)\s", re.I),
    re.compile(r"^#\s*(load|save|store|fetch|get)\s", re.I),
    re.compile(r"^#\s*(update|modify|change|set)\s+(the\s+)?(value|field|key|attribute|property)", re.I),
    re.compile(r"^#\s*(add|remove|delete|clear)\s", re.I),
    re.compile(r"^#\s*(open|close|connect|disconnect)\s", re.I),
    re.compile(r"^#\s*(parse|process|handle|convert|transform)\s", re.I),
    re.compile(r"^#\s*(raise|throw)\s", re.I),
    re.compile(r"^#\s*(try|except|catch)\s", re.I),
    re.compile(r"^#\s*(if|else|elif|while|for)\s", re.I),
    re.compile(r"^#\s*(break|continue|pass)\s*$", re.I),
    re.compile(r"^#\s*(class|def|function)\s", re.I),
]

_SKIP_PATTERNS = [
    re.compile(r"noqa", re.I),
    re.compile(r"type:\s*ignore", re.I),
    re.compile(r"pyright:", re.I),
    re.compile(r"mypy:", re.I),
    re.compile(r"ruff:", re.I),
    re.compile(r"because|why|reason|hack|workaround|note|warning|important|caution", re.I),
    re.compile(r"TODO|FIXME|HACK|XXX|BUG", re.I),
    re.compile(r"side.effect|registration|trigger", re.I),
    re.compile(r"intentional|deliberate|by design", re.I),
    re.compile(r"graceful|fallback|degrad", re.I),
]


def _is_trivial(comment_text: str) -> bool:
    text = comment_text.lstrip("#").strip()
    if not text:
        return False
    full = comment_text.strip()
    for pat in _SKIP_PATTERNS:
        if pat.search(full):
            return False
    for pat in _TRIVIAL_PATTERNS:
        if pat.match(full):
            return True
    if len(text) <= 20 and text.endswith(("statement", "block", "clause", "loop", "handler")):
        return True
    return False


@register
def check_trivial_comments(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect comments that trivially restate the following code."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))
        if file_index.is_test_file(py_file):
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = source.splitlines()

        # Build set of line numbers that are inside string literals
        string_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Constant,)) and isinstance(node.value, str):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                        string_lines.add(ln)

        for i, line in enumerate(lines, start=1):
            if i in string_lines:
                continue
            stripped = line.lstrip()
            if not stripped.startswith("#"):
                continue
            # Skip shebang and encoding declarations
            if i <= 2 and (stripped.startswith("#!") or "coding" in stripped or "encoding" in stripped):
                continue
            if _is_trivial(stripped):
                findings.append(Finding(
                    severity=FindingSeverity.INFO,
                    category="trivial_comment",
                    file=rel,
                    line=i,
                    message="Trivial comment restates the code — consider removing or explaining why.",
                    suggestion="Remove the comment or replace with a 'why' explanation.",
                ))
