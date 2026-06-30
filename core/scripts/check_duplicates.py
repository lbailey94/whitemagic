#!/usr/bin/env python3
"""Duplicate code audit — detect structurally similar functions across the codebase.

Uses AST normalization + body hashing to find functions that have identical or
near-identical implementations under different names. Catches the common AI-agent
pattern of reinventing the same utility in a different module.

Checks:
1. Exact duplicate bodies (same AST structure, different function names)
2. Near-duplicate bodies (same structure with minor literal differences)
3. Functions with hardcoded return values that appear in multiple places

Exit 0 if no duplicates found, exit 1 if any detected.
"""

from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass, field

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_ROOT = REPO_ROOT / "core" / "whitemagic"

SKIP_PATHS = {
    "tests",
    "__pycache__",
    "_archived",
    "node_modules",
    ".venv",
    "archive_v",
}

# Minimum body size (in AST nodes) to consider — skips trivial one-liners
MIN_BODY_NODES = 5

# Functions shorter than this (in lines) are too small to flag as duplicates
MIN_FUNCTION_LINES = 4


@dataclass
class FunctionInfo:
    """Metadata about a discovered function."""

    filepath: Path
    lineno: int
    end_lineno: int
    name: str
    module_path: str
    body_hash: str
    body_size: int
    arg_count: int


@dataclass
class DuplicateGroup:
    """A group of functions with similar bodies."""

    body_hash: str
    functions: list[FunctionInfo] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len({f.filepath for f in self.functions})


def should_skip(path: Path) -> bool:
    """Return True if path should be skipped."""
    for part in path.parts:
        if part in SKIP_PATHS:
            return True
    return "test" in path.name


def normalize_body(body: list[ast.stmt]) -> ast.AST:
    """Normalize a function body for comparison.

    Strips:
    - Docstrings
    - Variable names (replaced with _v)
    - Argument names
    - String literal contents (replaced with _s)
    - Number literal values (replaced with _n)

    Preserves:
    - Control flow structure (if/for/while/try/with)
    - Call structure (function calls, attribute access)
    - Operator types
    """
    # Filter out docstrings
    filtered = []
    for stmt in body:
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        filtered.append(stmt)

    class Normalizer(ast.NodeTransformer):
        def visit_arg(self, node: ast.arg) -> ast.arg:
            node = ast.arg(arg="_v", annotation=None)
            return node

        def visit_Name(self, node: ast.Name) -> ast.Name:
            return ast.Name(id="_v", ctx=node.ctx)

        def visit_Constant(self, node: ast.Constant) -> ast.Constant:
            if isinstance(node.value, str):
                return ast.Constant(value="_s")
            if isinstance(node.value, (int, float)):
                return ast.Constant(value=0)
            return node

        def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
            # Keep attribute names — they're semantically meaningful
            self.generic_visit(node)
            return node

        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
            # Don't recurse into nested functions for body hashing
            return node

        def visit_AsyncFunctionDef(
            self, node: ast.AsyncFunctionDef
        ) -> ast.AsyncFunctionDef:
            return node

    normalizer = Normalizer()
    normalized = [normalizer.visit(stmt) for stmt in filtered]
    module = ast.Module(body=normalized, type_ignores=[])
    return module


def hash_body(body: list[ast.stmt]) -> tuple[str, int]:
    """Return (hash, node_count) for a normalized function body."""
    normalized = normalize_body(body)
    try:
        dumped = ast.dump(normalized)
    except Exception:
        return ("", 0)
    h = hashlib.sha256(dumped.encode()).hexdigest()[:16]
    node_count = sum(1 for _ in ast.walk(normalized))
    return (h, node_count)


def extract_functions(filepath: Path) -> list[FunctionInfo]:
    """Extract all function definitions from a Python file."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    rel_path = filepath.relative_to(REPO_ROOT)
    functions = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Skip __init__ (usually trivial), properties, abstractmethods
        if node.name == "__init__":
            continue
        if any(
            (isinstance(d, ast.Name) and d.id == "abstractmethod")
            or (isinstance(d, ast.Attribute) and d.attr == "abstractmethod")
            for d in node.decorator_list
        ):
            continue
        if any(
            (
                isinstance(d, ast.Name)
                and d.id in {"property", "staticmethod", "classmethod"}
            )
            for d in node.decorator_list
        ):
            continue

        end_lineno = getattr(node, "end_lineno", node.lineno)
        line_count = end_lineno - node.lineno
        if line_count < MIN_FUNCTION_LINES:
            continue

        body_hash, body_size = hash_body(node.body)
        if body_size < MIN_BODY_NODES:
            continue

        functions.append(
            FunctionInfo(
                filepath=filepath,
                lineno=node.lineno,
                end_lineno=end_lineno,
                name=node.name,
                module_path=str(rel_path),
                body_hash=body_hash,
                body_size=body_size,
                arg_count=len(node.args.args),
            )
        )

    return functions


def find_duplicates() -> list[DuplicateGroup]:
    """Find all duplicate function groups across the codebase."""
    hash_to_functions: dict[str, list[FunctionInfo]] = defaultdict(list)

    for pyfile in SOURCE_ROOT.rglob("*.py"):
        if should_skip(pyfile):
            continue
        for func in extract_functions(pyfile):
            hash_to_functions[func.body_hash].append(func)

    # Only report groups with 2+ functions in different files
    duplicates = []
    for body_hash, funcs in hash_to_functions.items():
        if len(funcs) < 2:
            continue
        group = DuplicateGroup(body_hash=body_hash, functions=funcs)
        if group.file_count >= 2:
            duplicates.append(group)

    return sorted(duplicates, key=lambda g: -g.file_count)


def main() -> int:
    duplicates = find_duplicates()

    if not duplicates:
        print("No duplicate function bodies detected.")
        return 0

    total_dupes = sum(len(g.functions) for g in duplicates)
    print(f"Found {total_dupes} duplicate functions across {len(duplicates)} groups:\n")

    for i, group in enumerate(duplicates[:30], 1):
        print(f"  Group {i} ({len(group.functions)} copies, {group.file_count} files):")
        for func in sorted(group.functions, key=lambda f: f.module_path):
            print(
                f"    {func.module_path}:{func.lineno} {func.name}() [{func.body_size} nodes]"
            )
        print()

    if len(duplicates) > 30:
        print(f"  ... and {len(duplicates) - 30} more groups")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
