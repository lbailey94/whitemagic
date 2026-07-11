"""Standalone MCP developer tools server — focused dev tools without full WhiteMagic.

This is a lightweight MCP server that exposes common developer tools
(database, files, HTTP, shell, code analysis) without the full cognitive OS.

Usage:
    python -m whitemagic.mcp.dev_tools_server

Or as a module:
    from whitemagic.mcp.dev_tools_server import DevToolsServer
    server = DevToolsServer()
    server.run()

Claude Desktop config (.mcp.json):
    {
      "mcpServers": {
        "wm-devtools": {
          "command": "python",
          "args": ["-m", "whitemagic.mcp.dev_tools_server"]
        }
      }
    }
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Tool definitions for MCP registration
TOOL_DEFINITIONS = [
    {
        "name": "db_query",
        "description": "Run a SQL query on a SQLite database. Returns rows as JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Path to the SQLite database file"},
                "query": {"type": "string", "description": "SQL query to execute"},
                "params": {"type": "array", "description": "Query parameters for ? placeholders"},
            },
            "required": ["db_path", "query"],
        },
    },
    {
        "name": "db_schema",
        "description": "Get the schema of a SQLite database (tables, columns, types).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Path to the SQLite database file"},
            },
            "required": ["db_path"],
        },
    },
    {
        "name": "file_read",
        "description": "Read file contents with line numbers. Supports offset and limit.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file"},
                "offset": {"type": "integer", "description": "Line to start reading from (1-indexed)", "default": 1},
                "limit": {"type": "integer", "description": "Maximum lines to read", "default": 1000},
            },
            "required": ["path"],
        },
    },
    {
        "name": "file_write",
        "description": "Write content to a file. Creates parent directories if needed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file"},
                "content": {"type": "string", "description": "Content to write"},
                "append": {"type": "boolean", "description": "If true, append instead of overwrite", "default": False},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "file_search",
        "description": "Search for a pattern in files using grep. Returns matching lines with file paths.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory to search in"},
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "include": {"type": "string", "description": "File glob pattern (e.g. '*.py')", "default": "*"},
                "ignore_case": {"type": "boolean", "description": "Case-insensitive search", "default": False},
            },
            "required": ["path", "pattern"],
        },
    },
    {
        "name": "file_tree",
        "description": "List directory contents with file sizes and types.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list"},
                "max_depth": {"type": "integer", "description": "Maximum depth to traverse", "default": 2},
            },
            "required": ["path"],
        },
    },
    {
        "name": "http_request",
        "description": "Make an HTTP request and return the response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to request"},
                "method": {"type": "string", "description": "HTTP method", "default": "GET", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]},
                "headers": {"type": "object", "description": "Request headers"},
                "body": {"type": "string", "description": "Request body (for POST/PUT/PATCH)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
            },
            "required": ["url"],
        },
    },
    {
        "name": "http_probe",
        "description": "Test an API endpoint — returns status code, response time, and content type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to probe"},
                "method": {"type": "string", "description": "HTTP method", "default": "GET"},
                "expected_status": {"type": "integer", "description": "Expected status code", "default": 200},
            },
            "required": ["url"],
        },
    },
    {
        "name": "shell_exec",
        "description": "Execute a shell command with timeout. Returns stdout, stderr, and exit code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to execute"},
                "cwd": {"type": "string", "description": "Working directory"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                "env": {"type": "object", "description": "Additional environment variables"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "git_status",
        "description": "Get git repository status (branch, staged, modified, untracked).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to git repository", "default": "."},
            },
        },
    },
    {
        "name": "git_diff",
        "description": "Get git diff (unstaged, staged, or between commits).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to git repository", "default": "."},
                "ref": {"type": "string", "description": "Git ref to diff against (e.g. 'HEAD~1', 'main')", "default": "HEAD"},
                "staged": {"type": "boolean", "description": "If true, show staged changes", "default": False},
            },
        },
    },
    {
        "name": "code_analyze",
        "description": "Run STRATA static analysis checkers on a file or directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File or directory to analyze"},
                "language": {"type": "string", "description": "Language filter (python, javascript, etc.)"},
                "severity": {"type": "string", "description": "Minimum severity (info, warning, error)", "default": "warning"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "env_get",
        "description": "Get environment variable value (must be in allowlist).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Environment variable name"},
            },
            "required": ["name"],
        },
    },
]


class DevToolsServer:
    """Standalone MCP developer tools server.

    Exposes 13 focused developer tools via MCP protocol.
    Can run standalone (without full WhiteMagic) or as part of the WM MCP server.
    """

    ENV_ALLOWLIST = {
        "PATH", "HOME", "USER", "SHELL", "TERM", "LANG", "LC_ALL",
        "PYTHONPATH", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV",
        "NODE_ENV", "RUST_BACKTRACE", "GOPATH", "GOROOT",
    }

    def __init__(self) -> None:
        self._tools = {t["name"]: t for t in TOOL_DEFINITIONS}

    @property
    def tools(self) -> list[dict[str, Any]]:
        return TOOL_DEFINITIONS

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool by name with the given arguments."""
        handler = getattr(self, f"_handle_{name}", None)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return handler(**arguments)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return {"error": str(e)}

    def _handle_db_query(self, db_path: str, query: str, params: list[Any] | None = None) -> dict[str, Any]:
        from whitemagic.core.memory.db_manager import safe_connect

        conn = safe_connect(db_path)
        conn.row_factory = __import__("sqlite3").Row
        try:
            cursor = conn.execute(query, params or [])
            rows = [dict(r) for r in cursor.fetchall()]
            return {"rows": rows, "count": len(rows)}
        finally:
            conn.close()

    def _handle_db_schema(self, db_path: str) -> dict[str, Any]:
        from whitemagic.core.memory.db_manager import safe_connect

        conn = safe_connect(db_path)
        try:
            cursor = conn.execute(
                "SELECT name, type FROM sqlite_master WHERE type IN ('table','index','view') AND name NOT LIKE 'sqlite_%'"
            )
            objects = [{"name": r[0], "type": r[1]} for r in cursor.fetchall()]

            tables: dict[str, Any] = {}
            for obj in objects:
                if obj["type"] == "table":
                    col_cursor = conn.execute(f"PRAGMA table_info({obj['name']})")
                    tables[obj["name"]] = [
                        {"name": r[1], "type": r[2], "not_null": bool(r[3]), "default": r[4], "pk": bool(r[5])}
                        for r in col_cursor.fetchall()
                    ]

            return {"objects": objects, "tables": tables}
        finally:
            conn.close()

    def _handle_file_read(self, path: str, offset: int = 1, limit: int = 1000) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(0, offset - 1)
        end = start + limit
        selected = lines[start:end]
        numbered = [f"{start + i + 1:>6}\t{line}" for i, line in enumerate(selected)]
        return {
            "path": path,
            "total_lines": len(lines),
            "showing": f"{start + 1}-{min(end, len(lines))}",
            "content": "\n".join(numbered),
        }

    def _handle_file_write(self, path: str, content: str, append: bool = False) -> dict[str, Any]:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
        return {"path": path, "bytes_written": len(content), "appended": append}

    def _handle_file_search(
        self, path: str, pattern: str, include: str = "*", ignore_case: bool = False
    ) -> dict[str, Any]:
        import re

        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)
        base = Path(path)
        matches: list[dict[str, Any]] = []

        for file_path in base.rglob(include):
            if not file_path.is_file():
                continue
            if any(part.startswith(".") for part in file_path.relative_to(base).parts):
                continue
            try:
                for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if regex.search(line):
                        matches.append({
                            "file": str(file_path),
                            "line": i,
                            "content": line.strip()[:200],
                        })
                        if len(matches) >= 100:
                            return {"matches": matches, "truncated": True, "count": len(matches)}
            except Exception:
                continue

        return {"matches": matches, "count": len(matches)}

    def _handle_file_tree(self, path: str, max_depth: int = 2) -> dict[str, Any]:
        base = Path(path)
        if not base.exists():
            return {"error": f"Path not found: {path}"}

        def _walk(p: Path, depth: int) -> dict[str, Any]:
            if depth <= 0 or not p.is_dir():
                return {
                    "name": p.name,
                    "type": "file" if p.is_file() else "dir",
                    "size": p.stat().st_size if p.is_file() else 0,
                }
            children = []
            for child in sorted(p.iterdir()):
                if child.name.startswith("."):
                    continue
                children.append(_walk(child, depth - 1))
            return {"name": p.name, "type": "dir", "children": children}

        return _walk(base, max_depth)

    def _handle_http_request(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        import urllib.request

        req = urllib.request.Request(url, method=method)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        if body and method in ("POST", "PUT", "PATCH"):
            req.data = body.encode("utf-8")

        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                elapsed = time.perf_counter() - start
                return {
                    "status": resp.status,
                    "headers": dict(resp.headers),
                    "body": content[:10000],
                    "body_truncated": len(content) > 10000,
                    "elapsed_ms": round(elapsed * 1000, 1),
                }
        except Exception as e:
            elapsed = time.perf_counter() - start
            return {"error": str(e), "elapsed_ms": round(elapsed * 1000, 1)}

    def _handle_http_probe(self, url: str, method: str = "GET", expected_status: int = 200) -> dict[str, Any]:
        import urllib.request

        start = time.perf_counter()
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                elapsed = time.perf_counter() - start
                content_type = resp.headers.get("Content-Type", "unknown")
                return {
                    "url": url,
                    "status": resp.status,
                    "expected": expected_status,
                    "passed": resp.status == expected_status,
                    "content_type": content_type,
                    "elapsed_ms": round(elapsed * 1000, 1),
                }
        except Exception as e:
            elapsed = time.perf_counter() - start
            return {
                "url": url,
                "error": str(e),
                "passed": False,
                "elapsed_ms": round(elapsed * 1000, 1),
            }

    def _handle_shell_exec(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int = 30,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        start = time.perf_counter()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                env=full_env,
            )
            elapsed = time.perf_counter() - start
            return {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout[:10000],
                "stderr": result.stderr[:5000],
                "elapsed_ms": round(elapsed * 1000, 1),
            }
        except subprocess.TimeoutExpired:
            elapsed = time.perf_counter() - start
            return {"command": command, "error": "timeout", "timeout_s": timeout, "elapsed_ms": round(elapsed * 1000, 1)}

    def _handle_git_status(self, path: str = ".") -> dict[str, Any]:
        def _git(args: list[str]) -> str:
            result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=path, timeout=10)
            return result.stdout.strip() if result.returncode == 0 else ""

        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
        staged = _git(["diff", "--cached", "--name-only"])
        modified = _git(["diff", "--name-only"])
        untracked = _git(["ls-files", "--others", "--exclude-standard"])

        return {
            "branch": branch,
            "staged": staged.split("\n") if staged else [],
            "modified": modified.split("\n") if modified else [],
            "untracked": untracked.split("\n") if untracked else [],
        }

    def _handle_git_diff(self, path: str = ".", ref: str = "HEAD", staged: bool = False) -> dict[str, Any]:
        args = ["git", "diff"]
        if staged:
            args.append("--cached")
        args.append(ref)

        result = subprocess.run(args, capture_output=True, text=True, cwd=path, timeout=15)
        diff = result.stdout
        return {
            "ref": ref,
            "staged": staged,
            "diff": diff[:20000],
            "truncated": len(diff) > 20000,
        }

    def _handle_code_analyze(
        self, path: str, language: str | None = None, severity: str = "warning"
    ) -> dict[str, Any]:
        try:
            from whitemagic.tools.strata import run_strata

            results = run_strata(path, language=language, severity=severity)
            return {"findings": results, "count": len(results) if isinstance(results, list) else 0}
        except ImportError:
            return {"error": "STRATA not available. Install with: pip install whitemagic[strata]"}
        except Exception as e:
            return {"error": str(e)}

    def _handle_env_get(self, name: str) -> dict[str, Any]:
        if name not in self.ENV_ALLOWLIST:
            return {"error": f"Variable '{name}' not in allowlist. Allowed: {sorted(self.ENV_ALLOWLIST)}"}
        value = os.environ.get(name, "")
        return {"name": name, "value": value, "exists": bool(value)}


# Claude Desktop config template
CLAUDE_DESKTOP_CONFIG = {
    "mcpServers": {
        "wm-devtools": {
            "command": "python",
            "args": ["-m", "whitemagic.mcp.dev_tools_server"],
            "env": {},
        }
    }
}

# OpenAI Codex config template
OPENAI_CODEX_CONFIG = {
    "mcpServers": {
        "wm-devtools": {
            "command": "python",
            "args": ["-m", "whitemagic.mcp.dev_tools_server"],
        }
    }
}


def generate_configs(output_dir: str | Path = ".") -> None:
    """Generate Claude Desktop and OpenAI Codex config files."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    (output / "claude_desktop_config.json").write_text(
        json.dumps(CLAUDE_DESKTOP_CONFIG, indent=2), encoding="utf-8"
    )
    (output / "openai_codex_config.json").write_text(
        json.dumps(OPENAI_CODEX_CONFIG, indent=2), encoding="utf-8"
    )

    dockerfile = """FROM python:3.12-slim
RUN pip install whitemagic[mcp]
COPY . /app
WORKDIR /app
CMD ["python", "-m", "whitemagic.mcp.dev_tools_server"]
"""
    (output / "Dockerfile").write_text(dockerfile, encoding="utf-8")

    docker_compose = """version: "3.8"
services:
  wm-devtools:
    build: .
    ports:
      - "8770:8770"
    environment:
      - WM_MCP_HTTP=1
    restart: unless-stopped
"""
    (output / "docker-compose.yml").write_text(docker_compose, encoding="utf-8")

    logger.info("Generated config files in %s", output)


def run_mcp_server() -> None:
    """Run the dev tools MCP server via stdio transport."""
    server = DevToolsServer()

    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool

        mcp_server = Server("wm-devtools")

        @mcp_server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=t["inputSchema"],
                )
                for t in server.tools
            ]

        @mcp_server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            result = server.call_tool(name, arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        import asyncio
        asyncio.run(stdio_server(mcp_server))

    except ImportError:
        logger.info("MCP SDK not available. Running in JSON-RPC mode on stdio.")
        _run_jsonrpc(server)


def _run_jsonrpc(server: DevToolsServer) -> None:
    """Fallback JSON-RPC over stdio when MCP SDK is not available."""
    import sys

    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            if req.get("method") == "tools/list":
                response = {"jsonrpc": "2.0", "id": req.get("id"), "result": {"tools": server.tools}}
            elif req.get("method") == "tools/call":
                name = req["params"]["name"]
                args = req["params"].get("arguments", {})
                result = server.call_tool(name, args)
                response = {"jsonrpc": "2.0", "id": req.get("id"), "result": {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}}
            else:
                response = {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": "Method not found"}}
            print(json.dumps(response), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}), flush=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_mcp_server()
