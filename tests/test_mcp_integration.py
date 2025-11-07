#!/usr/bin/env python3
"""
MCP Integration Smoke Tests

Tests the WhiteMagic MCP server end-to-end:
- Server startup
- Basic tool operations (create, search, context)
- Clean shutdown

This ensures the MCP integration doesn't break between releases.
"""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


class MCPIntegrationTests(unittest.TestCase):
    """End-to-end tests for WhiteMagic MCP server."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.project_root = Path(__file__).parent.parent
        cls.mcp_dist = cls.project_root / "whitemagic-mcp" / "dist" / "index.js"

        # Verify MCP server is built
        if not cls.mcp_dist.exists():
            raise FileNotFoundError(
                f"MCP server not built. Run 'npm run build' in whitemagic-mcp/\n"
                f"Expected: {cls.mcp_dist}"
            )

    def setUp(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp(prefix="whitemagic_test_")
        self.base_path = Path(self.temp_dir)

        # Create memory directories
        for subdir in ["memory/short_term", "memory/long_term", "memory/archive"]:
            (self.base_path / subdir).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mcp_server_startup_and_ping(self):
        """Test that MCP server starts successfully and responds to ping."""
        # Start MCP server
        env = os.environ.copy()
        env["WM_BASE_PATH"] = str(self.base_path)

        process = subprocess.Popen(
            ["node", str(self.mcp_dist)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )

        try:
            # Wait for server to initialize
            time.sleep(2)

            # Check if process is still running
            poll_result = process.poll()
            if poll_result is not None:
                stderr_output = process.stderr.read()
                self.fail(
                    f"MCP server exited prematurely with code {poll_result}\nStderr: {stderr_output}"
                )

            # Server should be running
            self.assertIsNone(process.poll(), "MCP server should still be running")

        finally:
            # Clean shutdown
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            # Close all pipes
            if process.stdin:
                process.stdin.close()
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

    def test_mcp_server_can_import_whitemagic(self):
        """Test that MCP server can successfully import whitemagic package."""
        # Start MCP server
        env = os.environ.copy()
        env["WM_BASE_PATH"] = str(self.project_root)

        process = subprocess.Popen(
            ["node", str(self.mcp_dist)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )

        try:
            # Collect stderr output to check for import errors
            stderr_lines = []
            start_time = time.time()

            # Wait up to 5 seconds for initialization
            while time.time() - start_time < 5:
                if process.poll() is not None:
                    # Process exited
                    break

                # Read available stderr
                import select

                readable, _, _ = select.select([process.stderr], [], [], 0.1)
                if readable:
                    line = process.stderr.readline()
                    if line:
                        stderr_lines.append(line)

                        # Check for success messages
                        if "Connected to WhiteMagic" in line:
                            # Success!
                            return

                        # Check for import errors
                        if "ModuleNotFoundError" in line or "ImportError" in line:
                            self.fail(
                                f"MCP server failed to import whitemagic:\n{''.join(stderr_lines)}"
                            )

            # Check if server is still running (good sign)
            poll_result = process.poll()
            if poll_result is not None and poll_result != 0:
                self.fail(
                    f"MCP server exited with error code {poll_result}:\n{''.join(stderr_lines)}"
                )

            # If we got here and process is running, that's success
            if process.poll() is None:
                # Server is running, import was successful
                pass

        finally:
            # Clean shutdown
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            # Close all pipes
            if process.stdin:
                process.stdin.close()
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

    def test_python_wrapper_creates_memory(self):
        """Test that the Python wrapper can create a memory via direct call."""
        # Test the Python wrapper code directly
        python_code = f"""
import sys
import json
from pathlib import Path

# Add whitemagic to path
sys.path.insert(0, '{self.project_root}')

from whitemagic import MemoryManager

manager = MemoryManager(base_dir='{self.base_path}')

# Create a test memory
path = manager.create_memory(
    title='Smoke Test',
    content='This is a smoke test memory',
    memory_type='short_term',
    tags=['test']
)

print(json.dumps({{'success': True, 'path': str(path)}}))
"""

        result = subprocess.run(
            ["python3", "-c", python_code], capture_output=True, text=True, timeout=5
        )

        # Check execution was successful
        self.assertEqual(result.returncode, 0, f"Python wrapper failed:\n{result.stderr}")

        # Parse output
        try:
            output = json.loads(result.stdout.strip())
            self.assertTrue(output["success"], "Memory creation should succeed")
            self.assertIn("path", output, "Should return path")
        except json.JSONDecodeError as e:
            self.fail(f"Invalid JSON output: {result.stdout}\nError: {e}")

        # Verify memory file was created
        memory_files = list((self.base_path / "memory" / "short_term").glob("*.md"))
        self.assertEqual(len(memory_files), 1, "Should create exactly one memory file")

    def test_mcp_server_with_node_installed(self):
        """Verify Node.js is available for MCP server."""
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)

        self.assertEqual(result.returncode, 0, "Node.js should be installed")

        # Parse version
        version = result.stdout.strip()
        self.assertTrue(version.startswith("v"), f"Expected node version, got: {version}")

        # Check minimum version (v18 or higher)
        major_version = int(version.split(".")[0][1:])
        self.assertGreaterEqual(major_version, 18, "Node.js v18+ required for MCP server")


class MCPServerLifecycleTests(unittest.TestCase):
    """Test MCP server lifecycle: start, restart, shutdown."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.project_root = Path(__file__).parent.parent
        cls.mcp_dist = cls.project_root / "whitemagic-mcp" / "dist" / "index.js"

    def test_server_can_restart_multiple_times(self):
        """Test that MCP server can be started, stopped, and restarted."""
        temp_dir = tempfile.mkdtemp(prefix="whitemagic_test_")
        base_path = Path(temp_dir)

        try:
            # Create memory directories
            for subdir in ["memory/short_term", "memory/long_term", "memory/archive"]:
                (base_path / subdir).mkdir(parents=True, exist_ok=True)

            env = os.environ.copy()
            env["WM_BASE_PATH"] = str(self.project_root)

            # Start and stop 3 times
            for i in range(3):
                process = subprocess.Popen(
                    ["node", str(self.mcp_dist)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=1,
                )

                try:
                    time.sleep(1.5)

                    # Verify running
                    self.assertIsNone(process.poll(), f"Server should be running (iteration {i+1})")

                finally:
                    # Ensure proper cleanup
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

                    # Close all pipes to prevent resource warnings
                    if process.stdin:
                        process.stdin.close()
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()

                    # Small delay between restarts
                    time.sleep(0.5)

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
