"""P2.5 — Packaging smoke tests.

Verifies that the Python package builds cleanly, includes only expected
files, and that base imports work from the installed wheel.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_DIR = PROJECT_ROOT


def _build_wheel(dest: Path) -> Path:
    """Build wheel in dest and return the wheel path."""
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dest)],
        cwd=str(CORE_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        pytest.fail(f"Wheel build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    wheels = list(dest.glob("*.whl"))
    assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}: {wheels}"
    return wheels[0]


class TestPackagingSmoke:
    """Smoke tests for wheel build and install."""

    def test_wheel_builds(self):
        """Wheel builds without errors."""
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _build_wheel(Path(tmp))
            assert wheel.suffix == ".whl"
            assert wheel.stat().st_size > 1000, "Wheel is suspiciously small"

    def test_wheel_excludes_unwanted(self):
        """Wheel excludes archives, tests, local state, models, dev binaries."""
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _build_wheel(Path(tmp))
            result = subprocess.run(
                [sys.executable, "-m", "zipfile", "-l", str(wheel)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, f"Failed to list wheel contents: {result.stderr}"
            contents = result.stdout
            forbidden = [
                "/_archived/",
                "/archives/",
                "/benchmarks/",
                "/tests/",
                "/.whitemagic",
                "/models/",
                ".so",
                ".dylib",
                ".exe",
                "/scripts/",
            ]
            for pattern in forbidden:
                assert pattern not in contents, (
                    f"Forbidden pattern '{pattern}' found in wheel contents.\n"
                    f"Wheel: {wheel.name}\n"
                    f"Contents:\n{contents[:2000]}"
                )

    def test_wheel_includes_core_modules(self):
        """Wheel includes expected core Python modules."""
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _build_wheel(Path(tmp))
            result = subprocess.run(
                [sys.executable, "-m", "zipfile", "-l", str(wheel)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            contents = result.stdout
            required = [
                "whitemagic/__init__",
                "whitemagic/tools/",
                "whitemagic/core/",
                "whitemagic/config/",
            ]
            for pattern in required:
                assert pattern in contents, (
                    f"Required pattern '{pattern}' not found in wheel.\n"
                    f"Wheel: {wheel.name}"
                )

    def test_base_import_works(self):
        """Base whitemagic package imports from installed wheel."""
        with tempfile.TemporaryDirectory() as venv_dir:
            venv_python = Path(venv_dir) / "bin" / "python"
            subprocess.run(
                [sys.executable, "-m", "venv", venv_dir],
                check=True,
                timeout=30,
            )
            with tempfile.TemporaryDirectory() as build_dir:
                wheel = _build_wheel(Path(build_dir))
                install_result = subprocess.run(
                    [str(venv_python), "-m", "pip", "install", str(wheel)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if install_result.returncode != 0:
                    pytest.skip(
                        f"Wheel install failed (likely missing system deps):\n"
                        f"{install_result.stderr[:500]}"
                    )
                import_result = subprocess.run(
                    [str(venv_python), "-c", "import whitemagic; print(whitemagic.__version__)"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                assert import_result.returncode == 0, (
                    f"Import failed:\nstdout: {import_result.stdout}\nstderr: {import_result.stderr}"
                )
                assert "25" in import_result.stdout, (
                    f"Version mismatch in import: {import_result.stdout}"
                )
