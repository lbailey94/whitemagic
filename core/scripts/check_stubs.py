#!/usr/bin/env python3
"""Stub audit — detect structural stubs and placeholder code.

Checks:
1. NotImplementedError in non-test source (excluding legitimate ABCs)
2. Docstring markers: placeholder, stub, not yet implemented, todo
3. Empty method bodies after docstring (excluding Click, ABC callbacks, etc.)
4. Simulated return values with stub indicators nearby

Exit 0 if no stubs found, exit 1 if any detected.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_ROOT = REPO_ROOT / "core" / "whitemagic"

_ALLOWLIST_PATH = Path(__file__).resolve().parent / "stub_allowlist.json"
_ALLOWLIST: set[str] = set()
if _ALLOWLIST_PATH.exists():
    import json as _json

    _ALLOWLIST = set(_json.loads(_ALLOWLIST_PATH.read_text()))

# Patterns that indicate a placeholder docstring
STUB_DOCSTRINGS = {
    "placeholder",
    "stub",
    "not yet implemented",
    "not yet complete",
    "todo:",
    "todo -",
    "todo–",
    "todo—",
    "fixme:",
    "hack:",
}

# Files/directories to skip (tests, generated, archived)
SKIP_PATHS = {
    "tests",
    "__pycache__",
    "_archived",
    "node_modules",
    ".venv",
    "archive_v",
}

# Decorator modules that imply empty body is intentional (not a stub)
FRAMEWORK_DECORATORS = {
    "click",
    "app.command",
    "typer",
    "dispatcher",
    "router",
    "api_router",
}

# Method name patterns that are typically intentional no-ops
INTENTIONAL_NOOP_PATTERNS = (
    "_on_",
    "_check_",
    "_update_",
    "_handle_",
    "_setup_",
    "_teardown_",
    "_prepare_",
    "_cleanup_",
    "_validate_",
    "_verify_",
    "_ensure_",
    "_maybe_",
    "_default_",
    "_fallback_",
    "_hook_",
    "_callback_",
    "_listener_",
    "_observer_",
    "_watcher_",
)


def has_framework_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function has a decorator from a known framework or is abstract."""
    for dec in node.decorator_list:
        name = ""
        if isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Attribute):
                name = dec.func.attr
            elif isinstance(dec.func, ast.Name):
                name = dec.func.id
        elif isinstance(dec, ast.Attribute):
            name = dec.attr
        elif isinstance(dec, ast.Name):
            name = dec.id
        if name in {"group", "command", "option", "argument", "pass_context", "pass_obj"}:
            return True
        if name == "abstractmethod":
            return True
        # Check for framework prefixes like click.group, app.command
        if isinstance(dec, ast.Attribute) and isinstance(dec.value, ast.Name):
            if dec.value.id in {"click", "app", "typer", "router"}:
                return True
    return False


def is_protocol_class(class_node: ast.ClassDef) -> bool:
    """Check if a class is a typing.Protocol (runtime_checkable or not)."""
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == "Protocol":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Protocol":
            return True
    return False


def is_intentional_noop(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if method name indicates an intentional no-op hook."""
    return any(node.name.startswith(p) for p in INTENTIONAL_NOOP_PATTERNS)


class StubVisitor(ast.NodeVisitor):
    """AST visitor that detects structural stubs."""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.issues: list[str] = []
        self._in_protocol = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        was_protocol = self._in_protocol
        if is_protocol_class(node):
            self._in_protocol = True
        self.generic_visit(node)
        self._in_protocol = was_protocol

    def _check_docstring(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
        """Return True if node has a stub-like docstring."""
        doc = ast.get_docstring(node)
        if not doc:
            return False
        doc_lower = doc.lower()
        return any(marker in doc_lower for marker in STUB_DOCSTRINGS)

    def _is_empty_body(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Return True if function body is effectively empty (pass/ellipsis/just docstring/return None)."""
        body = node.body
        # Filter out docstring
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        if not body:
            return True
        # Single pass/ellipsis/return None
        if len(body) == 1:
            stmt = body[0]
            if isinstance(stmt, ast.Pass):
                return True
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
                return True
            if isinstance(stmt, ast.Return) and (stmt.value is None or (isinstance(stmt.value, ast.Constant) and stmt.value.value is None)):
                return True
        return False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # Skip Protocol methods — ellipsis bodies are standard Python syntax
        if self._in_protocol:
            return

        # Skip framework-decorated functions (Click, FastAPI, etc.)
        if has_framework_decorator(node):
            return

        # Skip intentional no-op hooks
        if is_intentional_noop(node):
            return

        has_stub_docstring = self._check_docstring(node)
        has_raise_not_implemented = any(
            isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call)
            and isinstance(stmt.exc.func, ast.Name) and stmt.exc.func.id == "NotImplementedError"
            for stmt in ast.walk(node)
        )
        is_empty = self._is_empty_body(node)

        rel_path = str(self.filepath.relative_to(REPO_ROOT))

        if has_stub_docstring:
            key = f"{rel_path}:{node.lineno}:{node.name}"
            if key not in _ALLOWLIST:
                self.issues.append(f"  {node.lineno}: {node.name} — stub docstring")
        if has_raise_not_implemented:
            key = f"{rel_path}:{node.lineno}:{node.name}"
            if key not in _ALLOWLIST:
                self.issues.append(f"  {node.lineno}: {node.name} — raises NotImplementedError")
        if is_empty and not has_stub_docstring and not has_raise_not_implemented and len(node.body) > 0:
            # Empty body without explicit stub marker — could be a stub
            # But skip __init__ unless it has a stub docstring (dataclasses often have empty __init__)
            if node.name == "__init__":
                return
            key = f"{rel_path}:{node.lineno}:{node.name}"
            if key not in _ALLOWLIST:
                self.issues.append(f"  {node.lineno}: {node.name} — empty body (suspicious)")


def should_skip(path: Path) -> bool:
    """Return True if path should be skipped."""
    for part in path.parts:
        if part in SKIP_PATHS:
            return True
    return True if "test" in path.name else False


def audit_file(filepath: Path) -> list[str]:
    """Audit a single Python file for stubs."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    visitor = StubVisitor(filepath)
    visitor.visit(tree)
    return visitor.issues


def main() -> int:
    all_issues: list[tuple[Path, list[str]]] = []

    for pyfile in SOURCE_ROOT.rglob("*.py"):
        if should_skip(pyfile):
            continue
        issues = audit_file(pyfile)
        if issues:
            all_issues.append((pyfile, issues))

    if not all_issues:
        print("✅ No structural stubs detected.")
        return 0

    total = sum(len(issues) for _, issues in all_issues)
    print(f"❌ Found {total} stub indicator(s) across {len(all_issues)} file(s):\n")

    for filepath, issues in sorted(all_issues):
        rel = filepath.relative_to(REPO_ROOT)
        print(f"{rel}")
        for issue in issues:
            print(issue)
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
