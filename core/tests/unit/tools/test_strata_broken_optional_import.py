"""Tests for the broken_optional_import STRATA checker."""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers.broken_optional_import import (
    _try_body_has_import,
    _try_body_is_empty,
    _try_body_only_assignments,
    check_broken_optional_import,
)
from whitemagic.tools.strata.models import Finding


class _FakeFileIndex:
    def __init__(self, files: dict[str, str]):
        self._files = files

    def python_files(self):
        return [Path(p) for p in self._files]

    def get_ast(self, path: Path):
        try:
            return ast.parse(self._files[str(path)])
        except (KeyError, SyntaxError):
            return None


def _run_checker(files: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    check_broken_optional_import(Path("."), _FakeFileIndex(files), findings)
    return findings


class TestTryBodyHasImport:
    def test_with_import(self):
        tree = ast.parse("try:\n    import foo\nexcept ImportError:\n    pass\n")
        try_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Try))
        assert _try_body_has_import(try_node) is True

    def test_without_import(self):
        tree = ast.parse("try:\n    x = True\nexcept ImportError:\n    pass\n")
        try_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Try))
        assert _try_body_has_import(try_node) is False


class TestTryBodyIsEmpty:
    def test_empty_with_pass(self):
        tree = ast.parse("try:\n    pass\nexcept ImportError:\n    pass\n")
        try_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Try))
        assert _try_body_is_empty(try_node) is True

    def test_not_empty(self):
        tree = ast.parse("try:\n    x = 1\nexcept ImportError:\n    pass\n")
        try_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Try))
        assert _try_body_is_empty(try_node) is False


class TestTryBodyOnlyAssignments:
    def test_only_assignment(self):
        tree = ast.parse("try:\n    AVAILABLE = True\nexcept ImportError:\n    AVAILABLE = False\n")
        try_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Try))
        assert _try_body_only_assignments(try_node) is True

    def test_has_function_call(self):
        tree = ast.parse("try:\n    x = do_thing()\nexcept ImportError:\n    pass\n")
        try_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Try))
        assert _try_body_only_assignments(try_node) is False


class TestBrokenOptionalImportChecker:
    def test_detects_empty_try_body(self):
        files = {"test.py": "try:\n    pass\nexcept ImportError:\n    AVAILABLE = False\n"}
        findings = _run_checker(files)
        assert len(findings) == 1
        assert findings[0].category == "broken_optional_import"
        assert "empty body" in findings[0].message

    def test_detects_assignment_only_try_body(self):
        files = {"test.py": "try:\n    AVAILABLE = True\nexcept ImportError:\n    AVAILABLE = False\n"}
        findings = _run_checker(files)
        assert len(findings) == 1
        assert findings[0].category == "broken_optional_import"
        assert "always be True" in findings[0].message

    def test_does_not_flag_correct_pattern(self):
        files = {"test.py": "try:\n    import foo  # noqa: F401\n    AVAILABLE = True\nexcept ImportError:\n    AVAILABLE = False\n"}
        findings = _run_checker(files)
        assert len(findings) == 0

    def test_does_not_flag_non_import_try(self):
        files = {"test.py": "try:\n    x = 1\nexcept ValueError:\n    x = 0\n"}
        findings = _run_checker(files)
        assert len(findings) == 0

    def test_does_not_flag_try_with_function_calls(self):
        files = {"test.py": "try:\n    result = compute()\nexcept ImportError:\n    result = None\n"}
        findings = _run_checker(files)
        assert len(findings) == 0

    def test_detects_multiple_broken_blocks(self):
        files = {"test.py": (
            "try:\n    AVAILABLE = True\nexcept ImportError:\n    AVAILABLE = False\n\n"
            "try:\n    pass\nexcept ImportError:\n    OTHER = False\n"
        )}
        findings = _run_checker(files)
        assert len(findings) == 2
