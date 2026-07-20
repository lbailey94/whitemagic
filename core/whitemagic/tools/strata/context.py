import ast
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["ContextEnricher"]


class ContextEnricher:
    """Find the enclosing function/class for a given file and line.

    Uses the CodeStructureGraph when available for cross-file, cross-language
    context lookup. Falls back to AST (Python) or regex (other languages).
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self._cache: dict = {}

    def _try_code_graph(self, file_rel: str, line: int) -> str | None:
        """Try to get context from the CodeStructureGraph.

        Returns None if graph not built or symbol not found, so caller
        can fall back to AST/regex.
        """
        try:
            from whitemagic.core.intelligence.code_structure_graph import (
                get_code_structure_graph,
            )
            g = get_code_structure_graph()
            if g.stats()["node_count"] == 0:
                return None

            # Find the node whose line range contains the given line
            best_match: str | None = None
            best_start = 0
            for node in g._nodes.values():
                if node.file_path == file_rel and node.node_type in ("function", "class", "interface"):
                    if node.line_start <= line <= node.line_end and node.line_start >= best_start:
                        best_start = node.line_start
                        prefix = {
                            "function": "def" if node.language == "python" else "fn" if node.language == "rust" else "function",
                            "class": "class",
                            "interface": "interface",
                        }.get(node.node_type, node.node_type)
                        best_match = f"{prefix} {node.name}"
            return best_match
        except Exception:  # noqa: BLE001
            return None

    def _get_python_context(self, file_path: Path, line: int) -> str | None:
        """Use AST to find enclosing function/class in Python."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except (SyntaxError, OSError, UnicodeDecodeError):
            return None

        best_match: str | None = None
        best_start = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                if start <= line <= end and start >= best_start:
                    best_start = start
                    prefix = "class" if isinstance(node, ast.ClassDef) else "def"
                    best_match = f"{prefix} {node.name}"
        return best_match

    def _get_regex_context(
        self, file_path: Path, line: int, patterns: list
    ) -> str | None:
        """Use regex to find enclosing scope for non-Python files."""
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (OSError, UnicodeDecodeError):
            return None

        best_match: str | None = None
        for i, text in enumerate(lines[:line], 1):
            for pattern, prefix in patterns:
                m = pattern.search(text)
                if m:
                    best_match = f"{prefix} {m.group(1)}"
        return best_match

    def enrich(self, file_rel: str, line: int) -> str | None:
        """Return a context string like 'def foo' or 'class Bar' for the given location.

        Tries the CodeStructureGraph first (cross-file, pre-parsed),
        then falls back to AST/regex parsing.
        """
        cache_key = (file_rel, line)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try code graph first
        result = self._try_code_graph(file_rel, line)
        if result is not None:
            self._cache[cache_key] = result
            return result

        # Fall back to AST/regex
        file_path = self.project_path / file_rel
        if not file_path.exists():
            return None

        ext = file_path.suffix.lower()
        result: str | None = None

        if ext == ".py":
            result = self._get_python_context(file_path, line)
        elif ext in {".rs", ".go"}:
            result = self._get_regex_context(
                file_path,
                line,
                [
                    (re.compile(r"\bfn\s+(\w+)"), "fn"),
                    (re.compile(r"\bfunc\s+(\w+)"), "func"),
                ],
            )
        elif ext in {".js", ".ts", ".jsx", ".tsx"}:
            result = self._get_regex_context(
                file_path,
                line,
                [
                    (re.compile(r"\bfunction\s+(\w+)"), "function"),
                    (re.compile(r"\bclass\s+(\w+)"), "class"),
                    (re.compile(r"\b(?:const|let|var)\s+(\w+)\s*=\s*\("), "arrow"),
                ],
            )
        elif ext in {".c", ".cpp", ".cc", ".h", ".hpp"}:
            _cpp_keywords = {
                "if",
                "while",
                "for",
                "switch",
                "return",
                "sizeof",
                "else",
                "catch",
                "try",
                "do",
                "new",
                "delete",
            }
            result = self._get_regex_context(
                file_path,
                line,
                [
                    (
                        re.compile(
                            r"\b(?!" + "|".join(_cpp_keywords) + r"\b)(\w+)\s*\("
                        ),
                        "function",
                    ),
                    (re.compile(r"\bclass\s+(\w+)"), "class"),
                    (re.compile(r"\bstruct\s+(\w+)"), "struct"),
                ],
            )
        elif ext == ".zig":
            result = self._get_regex_context(
                file_path,
                line,
                [
                    (re.compile(r"\bfn\s+(\w+)"), "fn"),
                ],
            )
        elif ext == ".lua":
            result = self._get_regex_context(
                file_path,
                line,
                [
                    (re.compile(r"\bfunction\s+(?:\w+[:.])?(\w+)"), "function"),
                ],
            )
        elif ext in {".java", ".kt"}:
            result = self._get_regex_context(
                file_path,
                line,
                [
                    (
                        re.compile(
                            r"\b(?:public|private|protected|static|final|\s)+\s*(?:\w+)\s+(\w+)\s*\("
                        ),
                        "method",
                    ),
                    (re.compile(r"\bclass\s+(\w+)"), "class"),
                    (re.compile(r"\bfun\s+(\w+)"), "fun"),
                ],
            )

        self._cache[cache_key] = result
        return result
