import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _is_in_try_except(node: ast.AST, tree: ast.AST) -> bool:
    """Check if an import node is inside a try/except block (lazy/optional import)."""
    for sub in ast.walk(tree):
        if isinstance(sub, ast.Try):
            for child in ast.walk(sub):
                if child is node:
                    return True
    return False


def _is_in_function(node: ast.AST, tree: ast.AST) -> bool:
    """Check if an import node is inside a function body (lazy import)."""
    for sub in ast.walk(tree):
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(sub):
                if child is node:
                    return True
    return False


def _is_in_type_checking(node: ast.AST, tree: ast.AST) -> bool:
    """Check if an import node is inside an `if TYPE_CHECKING:` block."""
    for sub in ast.walk(tree):
        if isinstance(sub, ast.If):
            test = sub.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                for child in ast.walk(sub):
                    if child is node:
                        return True
            elif isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
                for child in ast.walk(sub):
                    if child is node:
                        return True
    return False


def _has_noqa_f401(node: ast.AST, source_lines: list) -> bool:
    """Check if the import line has a # noqa: F401 comment (explicit re-export)."""
    if hasattr(node, "lineno") and node.lineno <= len(source_lines):
        line = source_lines[node.lineno - 1]
        return "noqa" in line and "F401" in line
    return False


@register
def check_unused_imports(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect unused imports in Python files.

    Skips false positives:
    - __init__.py files (re-export surfaces by convention)
    - `from __future__ import annotations` (PEP 604 directive)
    - Imports inside try/except (optional/graceful degradation)
    - Imports inside function bodies (lazy imports)
    """
    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        # Skip __init__.py — these are re-export surfaces by convention
        if py_file.name == "__init__.py":
            continue
        # Skip garden zodiac re-export files (backward compat pattern)
        rel = py_file.relative_to(project_path)
        if "zodiac" in rel.parts and "gardens" in rel.parts:
            continue
        # Skip MCP API bridge — large re-export surface for external consumers
        if py_file.name == "mcp_api_bridge.py":
            continue
        # Skip backward-compat shim modules (re-export surfaces)
        rel_str = str(rel)
        if any(kw in rel_str.lower() for kw in ("shim", "compat", "backward")):
            continue
        # Skip known re-export shim files (docstrings say "shim" or "compatibility" but filename doesn't)
        _SHIM_FILES = {
            "core/intelligence/quantum.py",
            "core/intelligence/heart.py",
            "core/intelligence/quantum_engine.py",
            "core/intelligence/quantum_graph_adapter.py",
            "core/intelligence/quantum_inspired_graph.py",
            "core/intelligence/reconsolidation.py",
            "core/resonance/gan_ying.py",
            "core/resonance/gan_ying_enhanced.py",
            "core/resonance/harmony_vector.py",
            "gardens/wisdom/wu_xing.py",
        }
        if any(rel_str.endswith(s) for s in _SHIM_FILES):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        source_lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()

        imports: dict[str, tuple[int, str]] = {}  # name -> (line, original_import)
        used_names: set = set()
        # Track which import nodes are in try/except or function scope
        skipped_names: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Skip __future__ imports
                    if alias.name == "__future__":
                        continue
                    name = alias.asname or alias.name
                    # Skip if inside try/except, function body, or TYPE_CHECKING block
                    if (
                        _is_in_try_except(node, tree)
                        or _is_in_function(node, tree)
                        or _is_in_type_checking(node, tree)
                    ):
                        skipped_names.add(name)
                        continue
                    # Skip if has # noqa: F401 comment (explicit re-export)
                    if _has_noqa_f401(node, source_lines):
                        skipped_names.add(name)
                        continue
                    imports[name] = (node.lineno, alias.name)
            elif isinstance(node, ast.ImportFrom):
                # Skip __future__ imports
                if node.module == "__future__":
                    continue
                if any(alias.name == "*" for alias in node.names):
                    continue  # Skip star imports
                for alias in node.names:
                    name = alias.asname or alias.name
                    # Skip if inside try/except, function body, or TYPE_CHECKING block
                    if (
                        _is_in_try_except(node, tree)
                        or _is_in_function(node, tree)
                        or _is_in_type_checking(node, tree)
                    ):
                        skipped_names.add(name)
                        continue
                    # Skip if has # noqa: F401 comment (explicit re-export)
                    if _has_noqa_f401(node, source_lines):
                        skipped_names.add(name)
                        continue
                    imports[name] = (node.lineno, alias.name)
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                root = node
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name):
                    used_names.add(root.id)

        for name, (line_num, original) in imports.items():
            if name not in used_names:
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="unused_import",
                        file=str(py_file.relative_to(project_path)),
                        line=line_num,
                        message=f"Import '{original}' appears unused.",
                        suggestion="Remove the import or verify it is used dynamically.",
                    )
                )
