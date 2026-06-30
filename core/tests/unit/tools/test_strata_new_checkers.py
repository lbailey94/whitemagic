"""Tests for the new STRATA checkers added during de-sloppification."""

import ast
import tempfile
from pathlib import Path

import pytest

from whitemagic.tools.strata.checkers.fstring_no_placeholder import check_fstring_no_placeholder
from whitemagic.tools.strata.checkers.ambiguous_names import check_ambiguous_variable_names
from whitemagic.tools.strata.checkers.equality_comparison import check_equality_comparison
from whitemagic.tools.strata.checkers.undefined_names import check_undefined_names
from whitemagic.tools.strata.checkers.repetitive_dispatch import check_repetitive_dispatch
from whitemagic.tools.strata.checkers.chained_get import check_chained_get
from whitemagic.tools.strata.models import Finding, FindingSeverity


class _FakeFileIndex:
    """Minimal FileIndex for testing checkers without full STRATA setup."""

    def __init__(self, files: dict[str, str]):
        self._files = files

    def python_files(self):
        return [Path(p) for p in self._files]

    def get_ast(self, path: Path):
        try:
            return ast.parse(self._files[str(path)])
        except (KeyError, SyntaxError):
            return None


def _run_checker(checker, files: dict[str, str], project_path: str = ".") -> list[Finding]:
    """Run a checker on a set of files and return findings."""
    findings: list[Finding] = []
    file_index = _FakeFileIndex(files)
    checker(Path(project_path), file_index, findings)
    return findings


class TestFstringNoPlaceholder:
    def test_detects_fstring_without_placeholders(self):
        files = {"test.py": 'x = f"hello world"\n'}
        findings = _run_checker(check_fstring_no_placeholder, files)
        assert len(findings) == 1
        assert findings[0].category == "fstring_no_placeholder"

    def test_does_not_flag_fstring_with_placeholders(self):
        files = {"test.py": 'x = f"hello {name}"\n'}
        findings = _run_checker(check_fstring_no_placeholder, files)
        assert len(findings) == 0

    def test_does_not_flag_regular_strings(self):
        files = {"test.py": 'x = "hello world"\n'}
        findings = _run_checker(check_fstring_no_placeholder, files)
        assert len(findings) == 0


class TestAmbiguousNames:
    def test_detects_lowercase_l(self):
        files = {"test.py": "l = 42\n"}
        findings = _run_checker(check_ambiguous_variable_names, files)
        assert len(findings) == 1
        assert "Ambiguous" in findings[0].message

    def test_detects_capital_o(self):
        files = {"test.py": "O = 42\n"}
        findings = _run_checker(check_ambiguous_variable_names, files)
        assert len(findings) == 1

    def test_does_not_flag_descriptive_names(self):
        files = {"test.py": "count = 42\n"}
        findings = _run_checker(check_ambiguous_variable_names, files)
        assert len(findings) == 0

    def test_detects_ambiguous_parameter(self):
        files = {"test.py": "def foo(l):\n    return l\n"}
        findings = _run_checker(check_ambiguous_variable_names, files)
        assert len(findings) == 1


class TestEqualityComparison:
    def test_detects_eq_true(self):
        files = {"test.py": "if x == True:\n    pass\n"}
        findings = _run_checker(check_equality_comparison, files)
        assert len(findings) == 1
        assert "is" in findings[0].suggestion

    def test_detects_eq_false(self):
        files = {"test.py": "if x == False:\n    pass\n"}
        findings = _run_checker(check_equality_comparison, files)
        assert len(findings) == 1

    def test_detects_ne_none(self):
        files = {"test.py": "if x != None:\n    pass\n"}
        findings = _run_checker(check_equality_comparison, files)
        assert len(findings) == 1

    def test_does_not_flag_is_comparison(self):
        files = {"test.py": "if x is None:\n    pass\n"}
        findings = _run_checker(check_equality_comparison, files)
        assert len(findings) == 0


class TestUndefinedNames:
    def test_detects_undefined_name(self):
        files = {"test.py": "x = parse_datetime('2024-01-01')\n"}
        findings = _run_checker(check_undefined_names, files)
        assert any(f.category == "undefined_name" and "parse_datetime" in f.message for f in findings)

    def test_does_not_flag_imported_name(self):
        files = {"test.py": "from datetime import datetime\nx = datetime.now()\n"}
        findings = _run_checker(check_undefined_names, files)
        assert not any("datetime" in f.message for f in findings)

    def test_does_not_flag_builtin(self):
        files = {"test.py": "x = len([1, 2, 3])\n"}
        findings = _run_checker(check_undefined_names, files)
        assert not any("len" in f.message for f in findings)


class TestRepetitiveDispatch:
    def test_detects_long_elif_chain(self):
        code = "if x == 'a':\n    pass\n"
        for c in 'bcdefghijk':
            code += f"elif x == '{c}':\n    pass\n"
        files = {"test.py": code}
        findings = _run_checker(check_repetitive_dispatch, files)
        assert len(findings) == 1
        assert findings[0].category == "repetitive_dispatch"

    def test_does_not_flag_short_elif_chain(self):
        code = "if x == 'a':\n    pass\nelif x == 'b':\n    pass\nelif x == 'c':\n    pass\n"
        files = {"test.py": code}
        findings = _run_checker(check_repetitive_dispatch, files)
        assert len(findings) == 0


class TestChainedGet:
    def test_detects_deeply_chained_get(self):
        code = 'x = data.get("a", {}).get("b", {}).get("c", "default")\n'
        files = {"test.py": code}
        findings = _run_checker(check_chained_get, files)
        assert len(findings) == 1
        assert findings[0].category == "chained_get"

    def test_does_not_flag_single_get(self):
        code = 'x = data.get("a", "default")\n'
        files = {"test.py": code}
        findings = _run_checker(check_chained_get, files)
        assert len(findings) == 0
