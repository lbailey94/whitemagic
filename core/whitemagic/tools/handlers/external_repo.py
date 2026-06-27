# ruff: noqa: BLE001
"""External repository query handlers — bridge to DeepWiki and local repo analysis.

Provides tools for querying external GitHub repositories via DeepWiki MCP
and cloning/scanning repos locally using WhiteMagic's archaeology system.

Designed for Gana Chariot (codebase navigation).
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# DeepWiki MCP is available as an MCP server, not a Python library.
# These handlers provide a local interface that can be called from the
# dispatch pipeline.  When running inside an MCP host that has DeepWiki
# configured, the host can route external.wiki_query directly to the
# mcp0_ask_question tool.  This handler serves as the fallback / cache
# layer and local-repo scanner.


def handle_external_wiki_query(**kwargs: Any) -> dict[str, Any]:
    """Query an external repository's wiki via DeepWiki.

    This is a meta-handler — when DeepWiki MCP is available in the host
    environment, the host should intercept and route to mcp0_ask_question.
    Otherwise, this returns guidance on how to enable DeepWiki.

    Args:
        repo: GitHub repo in owner/repo format (e.g. 'modelcontextprotocol/python-sdk')
        question: Natural language question about the repo
    """
    repo = kwargs.get("repo", "")
    question = kwargs.get("question", "")

    if not repo or not question:
        return {
            "status": "error",
            "error_code": "missing_params",
            "message": "repo and question are required",
        }

    # Check if DeepWiki MCP tools are available in the current environment
    # This is a soft check — the actual routing happens at the MCP host level
    return {
        "status": "success",
        "repo": repo,
        "question": question,
        "answer": None,
        "note": (
            "DeepWiki MCP routing required. If running in an MCP host with "
            "DeepWiki configured, route this call to mcp0_ask_question. "
            f"Otherwise, visit https://deepwiki.com/{repo} to index the repo."
        ),
        "deepwiki_url": f"https://deepwiki.com/{repo}",
    }


def handle_external_repo_scan(**kwargs: Any) -> dict[str, Any]:
    """Clone and scan an external repository using archaeology tools.

    Clones a GitHub repo to a temp directory and runs WhiteMagic's
    archaeology scanner to extract structure, docstrings, and patterns.

    Args:
        repo: GitHub repo in owner/repo format or full URL
        depth: Scan depth (default 3)
        cleanup: Remove clone after scan (default True)
    """
    repo = kwargs.get("repo", "")
    if not repo:
        return {"status": "error", "error_code": "missing_params",
                "message": "repo is required"}

    cleanup = kwargs.get("cleanup", True)

    # Normalize repo to URL
    if repo.startswith("http"):
        url = repo
        repo_name = repo.rstrip("/").split("/")[-1].replace(".git", "")
    elif "/" in repo and not repo.startswith("/"):
        url = f"https://github.com/{repo}.git"
        repo_name = repo.split("/")[-1]
    else:
        return {"status": "error", "error_code": "invalid_repo",
                "message": "Expected owner/repo format or full URL"}

    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(prefix="wm_ext_scan_")
        clone_path = Path(tmpdir) / repo_name

        # Shallow clone for speed
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(clone_path)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return {
                "status": "error",
                "error_code": "clone_failed",
                "message": result.stderr[:500],
                "repo": repo,
            }

        # Run archaeology scan
        from whitemagic.archaeology import get_archaeologist
        arch = get_archaeologist()

        # Temporarily point archaeologist at the cloned repo
        original_root = arch.root_path
        arch.root_path = clone_path
        try:
            arch.find_unread(str(clone_path))
            stats = arch.stats(scan_disk=True)
        finally:
            arch.root_path = original_root

        # Extract module structure
        modules: list[dict[str, Any]] = []
        py_files = list(clone_path.rglob("*.py"))
        exclude = {".git", ".venv", "__pycache__", "node_modules", "tests"}
        for py_file in py_files:
            if set(py_file.parts) & exclude:
                continue
            try:
                content = py_file.read_text(errors="ignore")
                if not content.strip():
                    continue
                rel = py_file.relative_to(clone_path)
                import re
                docstring = ""
                m = re.match(r'^("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', content)
                if m:
                    docstring = m.group(0).strip("\"'").strip()[:200]
                classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
                modules.append({
                    "path": str(rel),
                    "docstring": docstring,
                    "classes": classes[:10],
                    "line_count": content.count("\n") + 1,
                })
            except Exception:
                pass

        return {
            "status": "success",
            "repo": repo,
            "repo_name": repo_name,
            "files_scanned": len(py_files),
            "modules_found": len(modules),
            "modules": modules[:50],
            "disk_usage_mb": round(stats.get("disk_usage_mb", 0), 2),
            "clone_path": str(clone_path) if not cleanup else None,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error_code": "clone_timeout",
                "message": f"Clone of {repo} timed out"}
    except Exception as e:
        logger.error("External repo scan failed: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        if cleanup and tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def handle_external_repo_compare(**kwargs: Any) -> dict[str, Any]:
    """Compare a local module with an external repository's structure.

    Useful for understanding how other projects solve similar problems.

    Args:
        repo: External repo in owner/repo format
        local_module: Local module path to compare
    """
    repo = kwargs.get("repo", "")
    local_module = kwargs.get("local_module", "")

    if not repo or not local_module:
        return {"status": "error", "error_code": "missing_params",
                "message": "repo and local_module are required"}

    # Scan external repo
    ext_result = handle_external_repo_scan(
        repo=repo, cleanup=True, **{k: v for k, v in kwargs.items()
                                     if k in ("depth",)}
    )

    # Scan local module
    from whitemagic.config import PROJECT_ROOT
    local_path = Path(PROJECT_ROOT) / local_module
    if not local_path.exists():
        local_path = Path(local_module)

    local_info: dict[str, Any] = {}
    if local_path.exists():
        if local_path.is_file():
            content = local_path.read_text(errors="ignore")
            local_info = {
                "path": str(local_path),
                "line_count": content.count("\n") + 1,
                "exists": True,
            }
        else:
            py_files = list(local_path.rglob("*.py"))
            local_info = {
                "path": str(local_path),
                "file_count": len(py_files),
                "exists": True,
            }
    else:
        local_info = {"path": str(local_path), "exists": False}

    return {
        "status": "success",
        "repo": repo,
        "local": local_info,
        "external": {
            "status": ext_result.get("status"),
            "modules_found": ext_result.get("modules_found", 0),
            "modules": ext_result.get("modules", [])[:20],
        } if ext_result.get("status") == "success" else ext_result,
    }
