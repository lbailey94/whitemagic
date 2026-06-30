"""Tests for fast_write handler — atomic file writing with syntax validation."""

import os
import tempfile
from pathlib import Path

from whitemagic.tools.handlers.fast_write import (
    _is_path_safe,
    handle_fast_write_append,
    handle_fast_write_batch,
    handle_fast_write_validate,
    handle_fast_write_write,
)


class TestPathSafety:
    def test_safe_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed, _ = _is_path_safe(os.path.join(tmpdir, "test.py"))
            assert allowed

    def test_protected_path(self):
        allowed, reason = _is_path_safe("/etc/passwd")
        assert not allowed
        assert "protected" in reason.lower()

    def test_venv_protected(self):
        allowed, reason = _is_path_safe("/some/path/.venv/lib/python.py")
        assert not allowed


class TestWrite:
    def test_write_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            result = handle_fast_write_write(path=path, content="x = 1\n")
            assert result["status"] == "success"
            assert Path(path).read_text() == "x = 1\n"

    def test_write_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            Path(path).write_text("old = 1\n")
            result = handle_fast_write_write(path=path, content="new = 2\n")
            assert result["status"] == "success"
            assert Path(path).read_text() == "new = 2\n"

    def test_write_with_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            Path(path).write_text("old = 1\n")
            result = handle_fast_write_write(
                path=path, content="new = 2\n", backup=True
            )
            assert result["status"] == "success"
            assert result["backup"] is not None
            assert Path(result["backup"]).read_text() == "old = 1\n"

    def test_write_syntax_error_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            result = handle_fast_write_write(path=path, content="def broken(:\n")
            assert result["status"] == "error"
            assert "SyntaxError" in result["error"]

    def test_write_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            result = handle_fast_write_write(path=path, content="x = 1\n", dry_run=True)
            assert result["status"] == "success"
            assert result["mode"] == "dry_run"
            assert not Path(path).exists()

    def test_write_no_path(self):
        result = handle_fast_write_write(content="x = 1\n")
        assert result["status"] == "error"

    def test_write_non_python_no_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.md")
            result = handle_fast_write_write(path=path, content="# Hello\n")
            assert result["status"] == "success"
            assert result["validation"] is None

    def test_write_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "test.py")
            result = handle_fast_write_write(path=path, content="x = 1\n")
            assert result["status"] == "success"
            assert Path(path).exists()


class TestAppend:
    def test_append_to_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            Path(path).write_text("x = 1\n")
            result = handle_fast_write_append(path=path, content="y = 2\n")
            assert result["status"] == "success"
            assert Path(path).read_text() == "x = 1\ny = 2\n"

    def test_append_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            result = handle_fast_write_append(path=path, content="x = 1\n")
            assert result["status"] == "error"

    def test_append_syntax_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            Path(path).write_text("x = 1\n")
            result = handle_fast_write_append(path=path, content="def broken(:\n")
            assert result["status"] == "error"


class TestBatch:
    def test_batch_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = {
                os.path.join(tmpdir, "a.py"): "x = 1\n",
                os.path.join(tmpdir, "b.py"): "y = 2\n",
            }
            result = handle_fast_write_batch(files=files)
            assert result["status"] == "success"
            assert result["written"] == 2
            assert result["errors"] == 0

    def test_batch_partial_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = {
                os.path.join(tmpdir, "good.py"): "x = 1\n",
                os.path.join(tmpdir, "bad.py"): "def broken(:\n",
            }
            result = handle_fast_write_batch(files=files)
            assert result["status"] == "partial_success"
            assert result["written"] == 1
            assert result["errors"] == 1

    def test_batch_too_many(self):
        files = {f"path{i}.py": "x = 1\n" for i in range(51)}
        result = handle_fast_write_batch(files=files)
        assert result["status"] == "error"


class TestValidate:
    def test_validate_valid_python(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            Path(path).write_text("x = 1\n")
            result = handle_fast_write_validate(path=path)
            assert result["status"] == "success"
            assert result["valid"] is True

    def test_validate_invalid_python(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.py")
            Path(path).write_text("def broken(:\n")
            result = handle_fast_write_validate(path=path)
            assert result["status"] == "success"
            assert result["valid"] is False

    def test_validate_nonexistent(self):
        result = handle_fast_write_validate(path="/nonexistent/file.py")
        assert result["status"] == "error"


class TestRegistry:
    def test_tools_registered(self):
        from whitemagic.tools.registry import get_tool

        for name in (
            "fast_write.write",
            "fast_write.append",
            "fast_write.batch",
            "fast_write.validate",
        ):
            tool = get_tool(name)
            assert tool is not None, f"{name} not found in registry"
            assert tool.name == name
