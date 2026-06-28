# ruff: noqa: BLE001
"""Parallel Test Runner — DEPRECATED, use pytest-xdist instead.

This module is kept for backward compatibility but emits a DeprecationWarning
on import. All test parallelization should go through pytest-xdist via:

    pytest -n auto --dist=loadgroup --progress

The custom subprocess-per-file approach in this module is strictly inferior:
- No shared fixture caching (each subprocess reimports everything)
- No loadgroup scheduling (can't group stateful tests)
- 60s per-file timeout is too coarse
- No progress bar integration

Version: 2.7.0 "Ganapati Day — Retired"
"""

import logging
import warnings

logger = logging.getLogger(__name__)

warnings.warn(
    "whitemagic.parallel.runner is deprecated. Use pytest-xdist instead: "
    "pytest -n auto --dist=loadgroup --progress",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export dataclasses for backward compat
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from whitemagic.config.concurrency import TEST_RUNNER_WORKERS


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    passed: bool
    duration: float
    output: str = ""
    error: str = ""


@dataclass
class TestSuiteResult:
    """Result of running a test suite."""

    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_seconds: float
    results: list[TestResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


def _run_single_test_file_worker(test_file: str, test_root: str) -> TestResult:
    start = time.time()
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(test_root),
        )
        passed = result.returncode == 0
        duration = time.time() - start
        return TestResult(
            name=Path(test_file).name,
            passed=passed,
            duration=duration,
            output=result.stdout[-500:] if result.stdout else "",
            error=result.stderr[-200:] if result.stderr else "",
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            name=Path(test_file).name,
            passed=False,
            duration=60.0,
            error="Test timed out after 60 seconds",
        )
    except Exception as e:
        return TestResult(
            name=Path(test_file).name,
            passed=False,
            duration=time.time() - start,
            error=str(e),
        )


class ParallelTestRunner:
    """DEPRECATED: Use pytest-xdist instead.

    Run tests in parallel using multiple workers.

    Deprecated since v23.3.1. Use pytest-xdist:
        pytest -n auto --dist=loadgroup --progress
    """

    def __init__(
        self,
        max_workers: int = 64,
        test_dir: str = "tests",
        use_processes: bool = False,
    ):
        warnings.warn(
            "ParallelTestRunner is deprecated. Use pytest-xdist: "
            "pytest -n auto --dist=loadgroup --progress",
            DeprecationWarning,
            stacklevel=2,
        )
        self.max_workers = max_workers
        self.test_dir = Path(test_dir)
        self.use_processes = use_processes

    def _discover_tests(self, pattern: str = "test_*.py") -> list[Path]:
        return list(self.test_dir.rglob(pattern))

    def _run_single_test_file(self, test_file: Path) -> TestResult:
        start = time.time()
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", str(test_file), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.test_dir.parent),
            )
            passed = result.returncode == 0
            duration = time.time() - start
            return TestResult(
                name=test_file.name,
                passed=passed,
                duration=duration,
                output=result.stdout[-500:] if result.stdout else "",
                error=result.stderr[-200:] if result.stderr else "",
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                name=test_file.name,
                passed=False,
                duration=60.0,
                error="Test timed out after 60 seconds",
            )
        except Exception as e:
            return TestResult(
                name=test_file.name,
                passed=False,
                duration=time.time() - start,
                error=str(e),
            )

    def run_all(self, pattern: str = "test_*.py") -> TestSuiteResult:
        start_time = time.time()
        test_files = self._discover_tests(pattern)

        results = []
        passed = 0
        failed = 0
        errors = 0

        Executor = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        max_workers = min(self.max_workers, len(test_files))
        if self.use_processes:
            max_workers = min(max_workers, TEST_RUNNER_WORKERS)

        with Executor(max_workers=max_workers) as executor:
            if self.use_processes:
                test_root = str(self.test_dir.parent)
                future_to_test = {
                    executor.submit(_run_single_test_file_worker, str(tf), test_root): tf
                    for tf in test_files
                }
            else:
                future_to_test = {
                    executor.submit(self._run_single_test_file, tf): tf
                    for tf in test_files
                }

            for future in as_completed(future_to_test):
                try:
                    result = future.result()
                    results.append(result)
                    if result.passed:
                        passed += 1
                    elif result.error:
                        errors += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    errors += 1

        duration = time.time() - start_time
        return TestSuiteResult(
            total_tests=len(test_files),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=0,
            duration_seconds=duration,
            results=results,
        )

    def run_fast(self) -> TestSuiteResult:
        all_tests = self._discover_tests()
        quick_tests = sorted(all_tests, key=lambda f: f.stat().st_size)[:20]
        results = []
        for tf in quick_tests[:10]:
            results.append(self._run_single_test_file(tf))
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            total_tests=len(results),
            passed=passed,
            failed=len(results) - passed,
            errors=0,
            skipped=0,
            duration_seconds=sum(r.duration for r in results),
            results=results,
        )


def run_tests_parallel(test_dir: str = "tests", workers: int = 64) -> TestSuiteResult:
    """DEPRECATED: Use pytest-xdist. Convenience function kept for compat."""
    runner = ParallelTestRunner(max_workers=workers, test_dir=test_dir)
    return runner.run_all()
