"""Test watcher - auto-run tests on file changes."""

import subprocess
import time
from pathlib import Path


class TestWatcher:
    """Watch files and auto-run tests on changes."""

    def __init__(self, watch_path: str = ".", pattern: str = "**/*.py"):
        self.watch_path = Path(watch_path)
        self.pattern = pattern

    def watch(self, test_command: str = "pytest -v"):
        """Start watching and running tests.

        Note: Requires inotify-tools (inotifywait) to be installed.
        """
        print(f"👀 Watching {self.watch_path} for changes...")
        print(f"Pattern: {self.pattern}")
        print(f"Test command: {test_command}")
        print("━" * 60)

        # Run tests once at start
        self._run_tests(test_command)

        try:
            while True:
                # Wait for file change
                result = subprocess.run(  # nosec B603
                    ["inotifywait", "-r", "-e", "modify,create", str(self.watch_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    print("\n🔄 Change detected, running tests...")
                    self._run_tests(test_command)
                else:
                    print("⚠️  inotifywait not available, falling back to polling")
                    self._watch_polling(test_command)
                    break

        except KeyboardInterrupt:
            print("\n\n👋 Test watcher stopped")

    def _run_tests(self, command: str):
        """Run test command."""
        result = subprocess.run(command.split(), check=False)  # nosec B603

        if result.returncode == 0:
            print("✅ Tests passed!")
        else:
            print("❌ Tests failed!")

        print("━" * 60)

    def _watch_polling(self, test_command: str, interval: int = 2):
        """Fallback: poll for changes."""
        last_mtime = {}

        while True:
            changed = False

            for file in self.watch_path.rglob(self.pattern):
                if not file.is_file():
                    continue

                mtime = file.stat().st_mtime
                if file not in last_mtime:
                    last_mtime[file] = mtime
                elif last_mtime[file] != mtime:
                    changed = True
                    last_mtime[file] = mtime

            if changed:
                print("\n🔄 Change detected, running tests...")
                self._run_tests(test_command)

            time.sleep(interval)
