"""Pre-commit auto-fix loop - eliminate manual fixes."""

import signal
import subprocess
import sys
from typing import List, Tuple


class PreCommitAutoFix:
    """Automatically fix pre-commit issues and retry."""

    def __init__(self, max_attempts: int = 3, timeout: int = 300):
        self.max_attempts = max_attempts
        self.timeout = timeout  # 5 minutes default
        self._interrupted = False

        # Set up Ctrl+C handler
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\n⚠️  Interrupted by user. Cleaning up...")
        self._interrupted = True
        sys.exit(1)

    def run_with_autofix(self, files: List[str] = None) -> Tuple[bool, str]:
        """Run pre-commit, auto-fix issues, retry.

        Returns:
            (success, message)
        """
        for attempt in range(1, self.max_attempts + 1):
            print(f"🔄 Pre-commit attempt {attempt}/{self.max_attempts}")

            # Run pre-commit
            result = self._run_precommit(files)

            if result["success"]:
                return True, "✅ All pre-commit checks passed!"

            # Try to auto-fix
            fixed = self._auto_fix(result["failures"])

            if not fixed:
                return False, f"❌ Pre-commit failed:\n{result['output']}"

            print(f"🔧 Auto-fixed {len(fixed)} issues, retrying...")

        return False, "❌ Max attempts reached, manual fix needed"

    def _run_precommit(self, files: List[str] = None) -> dict:
        """Run pre-commit hooks."""
        cmd = ["pre-commit", "run"]
        if files:
            cmd.extend(["--files"] + files)
        else:
            cmd.append("--all-files")

        print(f"⏳ Running pre-commit hooks (timeout: {self.timeout}s)...")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=self.timeout
            )  # nosec B603
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": f"❌ Pre-commit timed out after {self.timeout}s",
                "failures": ["timeout"],
            }

        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr,
            "failures": self._parse_failures(result.stdout),
        }

    def _parse_failures(self, output: str) -> List[str]:
        """Parse which hooks failed."""
        failures = []
        for line in output.split("\n"):
            if "Failed" in line or "FAILED" in line:
                # Extract hook name
                parts = line.split(".")
                if parts:
                    failures.append(parts[0].strip())
        return failures

    def _auto_fix(self, failures: List[str]) -> List[str]:
        """Auto-fix known issues."""
        fixed = []

        for failure in failures:
            if "black" in failure.lower():
                if self._run_black():
                    fixed.append("black")

            elif "ruff" in failure.lower():
                if self._run_ruff():
                    fixed.append("ruff")

            elif "isort" in failure.lower():
                if self._run_isort():
                    fixed.append("isort")

        return fixed

    def _run_black(self) -> bool:
        """Run black formatter."""
        print("  🔧 Running black formatter...")
        try:
            result = subprocess.run(
                ["black", "."], capture_output=True, check=False, timeout=60
            )  # nosec B603
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("  ⚠️  Black timed out")
            return False

    def _run_ruff(self) -> bool:
        """Run ruff with auto-fix."""
        print("  🔧 Running ruff auto-fix...")
        try:
            result = subprocess.run(  # nosec B603
                ["ruff", "check", ".", "--fix"], capture_output=True, check=False, timeout=60
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("  ⚠️  Ruff timed out")
            return False

    def _run_isort(self) -> bool:
        """Run isort."""
        print("  🔧 Running isort...")
        try:
            result = subprocess.run(
                ["isort", "."], capture_output=True, check=False, timeout=60
            )  # nosec B603
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("  ⚠️  Isort timed out")
            return False
