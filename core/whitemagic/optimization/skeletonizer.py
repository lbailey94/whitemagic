# ruff: noqa: BLE001
"""
Skeletonization Engine — AST Context Compression (G002)
=====================================================

Extracts structural skeletons from source code (Python, etc.) to provide
LLMs with full architectural context at a fraction of the token cost.

Replaces function bodies with `...` or pass, preserves signatures,
classes, and docstrings (summarized).
"""

import ast
from pathlib import Path


class Skeletonizer:
    """AST-based code skeletonizer for Python."""

    def __init__(self) -> None:
        pass

    def skeletonize(self, code: str) -> str:
        """Parse code and return its skeleton."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Fallback for invalid syntax or non-Python files
            return (
                "\n".join(code.splitlines()[:50])
                + "\n# ... (syntax error or non-python, truncated)"
            )

        transformer = SkeletonTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)

    def skeletonize_file(self, file_path: str | Path) -> str:
        """Read file and skeletonize it."""
        path = Path(file_path)
        if not path.exists():
            return f"# File not found: {path}"

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if path.suffix == ".py":
                return self.skeletonize(content)
            else:
                # Naive line truncation for non-Python for now
                lines = content.splitlines()
                head = lines[:20]
                return (
                    "\n".join(head) + f"\n\n# ... ({len(lines) - 20} lines hidden) ..."
                )
        except Exception as e:
            return f"# Error skeletonizing {path}: {e}"


class SkeletonTransformer(ast.NodeTransformer):
    """AST Transformer that strips bodies from functions and classes."""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Keep signature, strip body."""

        docstring = ast.get_docstring(node)
        new_body: list[ast.stmt] = []
        if docstring:
            # Keep first line of docstring
            summary = docstring.split("\n")[0].strip()
            new_body.append(ast.Expr(value=ast.Constant(value=summary + " ...")))

        new_body.append(ast.Expr(value=ast.Constant(value=...)))

        node.body = new_body
        return node

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        """Handle async functions same as sync."""
        docstring = ast.get_docstring(node)
        new_body: list[ast.stmt] = []
        if docstring:
            summary = docstring.split("\n")[0].strip()
            new_body.append(ast.Expr(value=ast.Constant(value=summary + " ...")))

        new_body.append(ast.Expr(value=ast.Constant(value=...)))
        node.body = new_body
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Keep class structure, visit methods recursively."""
        # Docstring
        ast.get_docstring(node)

        # Recurse into body to process methods
        self.generic_visit(node)

        if not node.body:
            node.body = [ast.Pass()]

        return node


def skeletonize(code: str) -> str:
    """Convenience function."""
    return Skeletonizer().skeletonize(code)


def skeletonize_file(file_path: str | Path) -> str:
    """Convenience function."""
    return Skeletonizer().skeletonize_file(file_path)
