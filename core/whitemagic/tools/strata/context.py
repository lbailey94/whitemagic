import ast
import re
from pathlib import Path
from typing import Optional

__all__ = ["ContextEnricher"]


class ContextEnricher:
    """Find the enclosing function/class for a given file and line."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self._cache: dict = {}

    def _get_python_context(self, file_path: Path, line: int) -> Optional[str]:
        """Use AST to find enclosing function/class in Python."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except (SyntaxError, OSError, UnicodeDecodeError):
            return None

        best_match: Optional[str] = None
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

    def _get_regex_context(self, file_path: Path, line: int, patterns: list) -> Optional[str]:
        """Use regex to find enclosing scope for non-Python files."""
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (OSError, UnicodeDecodeError):
            return None

        best_match: Optional[str] = None
        for i, text in enumerate(lines[:line], 1):
            for pattern, prefix in patterns:
                m = pattern.search(text)
                if m:
                    best_match = f"{prefix} {m.group(1)}"
        return best_match

    def enrich(self, file_rel: str, line: int) -> Optional[str]:
        """Return a context string like 'def foo' or 'class Bar' for the given location."""
        file_path = self.project_path / file_rel
        if not file_path.exists():
            return None

        cache_key = (file_rel, line)
        if cache_key in self._cache:
            return self._cache[cache_key]

        ext = file_path.suffix.lower()
        result: Optional[str] = None

        if ext == ".py":
            result = self._get_python_context(file_path, line)
        elif ext in {".rs", ".go"}:
            result = self._get_regex_context(file_path, line, [
                (re.compile(r'\bfn\s+(\w+)'), "fn"),
                (re.compile(r'\bfunc\s+(\w+)'), "func"),
            ])
        elif ext in {".js", ".ts", ".jsx", ".tsx"}:
            result = self._get_regex_context(file_path, line, [
                (re.compile(r'\bfunction\s+(\w+)'), "function"),
                (re.compile(r'\bclass\s+(\w+)'), "class"),
                (re.compile(r'\b(?:const|let|var)\s+(\w+)\s*=\s*\('), "arrow"),
            ])
        elif ext in {".c", ".cpp", ".cc", ".h", ".hpp"}:
            _cpp_keywords = {"if", "while", "for", "switch", "return", "sizeof", "else", "catch", "try", "do", "new", "delete"}
            result = self._get_regex_context(file_path, line, [
                (re.compile(r'\b(?!' + "|".join(_cpp_keywords) + r'\b)(\w+)\s*\('), "function"),
                (re.compile(r'\bclass\s+(\w+)'), "class"),
                (re.compile(r'\bstruct\s+(\w+)'), "struct"),
            ])
        elif ext == ".zig":
            result = self._get_regex_context(file_path, line, [
                (re.compile(r'\bfn\s+(\w+)'), "fn"),
            ])
        elif ext == ".lua":
            result = self._get_regex_context(file_path, line, [
                (re.compile(r'\bfunction\s+(?:\w+[:.])?(\w+)'), "function"),
            ])
        elif ext in {".java", ".kt"}:
            result = self._get_regex_context(file_path, line, [
                (re.compile(r'\b(?:public|private|protected|static|final|\s)+\s*(?:\w+)\s+(\w+)\s*\('), "method"),
                (re.compile(r'\bclass\s+(\w+)'), "class"),
                (re.compile(r'\bfun\s+(\w+)'), "fun"),
            ])

        self._cache[cache_key] = result
        return result
