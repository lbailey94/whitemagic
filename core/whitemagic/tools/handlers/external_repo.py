# ruff: noqa: BLE001
"""External repository query handlers — bridge to DeepWiki and local repo analysis.

Provides tools for querying external GitHub repositories via DeepWiki MCP
and cloning/scanning repos locally using WhiteMagic's archaeology system.

Designed for Gana Chariot (codebase navigation).
"""

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


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


_ALLOWED_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}


def _validate_repo_input(repo: str) -> tuple[str, str] | None:
    """Validate and normalize repo input. Return (url, repo_name) or None."""
    repo = repo.strip()
    if not repo or "\n" in repo or "\r" in repo:
        return None
    if repo.startswith("http://") or repo.startswith("https://"):
        parsed = urlparse(repo)
        if parsed.hostname not in _ALLOWED_HOSTS:
            return None
        repo_name = Path(parsed.path).name.replace(".git", "")
        return repo, repo_name
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        repo_name = repo.split("/")[-1]
        return f"https://github.com/{repo}.git", repo_name
    return None


def _scan_modules_at_path(root: Path) -> list[dict[str, Any]]:
    """Extract Python module structure from a local directory."""
    modules: list[dict[str, Any]] = []
    if not root.exists():
        return modules
    py_files = list(root.rglob("*.py"))
    exclude = {".git", ".venv", "__pycache__", "node_modules", "tests"}
    for py_file in py_files:
        if set(py_file.parts) & exclude:
            continue
        try:
            content = py_file.read_text(errors="ignore")
            if not content.strip():
                continue
            rel = py_file.relative_to(root)
            docstring = ""
            m = re.match(r'^("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', content)
            if m:
                docstring = m.group(0).strip("\"'").strip()[:200]
            classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
            modules.append(
                {
                    "path": str(rel),
                    "docstring": docstring,
                    "classes": classes[:10],
                    "line_count": content.count("\n") + 1,
                }
            )
        except Exception:
            pass
    return modules


def handle_external_repo_scan(**kwargs: Any) -> dict[str, Any]:
    """Clone and scan an external repository using archaeology tools.

    Clones an allowed git host repo to a temp directory and extracts
    Python module structure, docstrings, and basic statistics.

    Args:
        repo: GitHub repo in owner/repo format or full URL
              (allowed hosts: github.com, gitlab.com, bitbucket.org)
        cleanup: Remove clone after scan (default True)
    """
    repo = kwargs.get("repo", "")
    if not repo:
        return {
            "status": "error",
            "error_code": "missing_params",
            "message": "repo is required",
        }
    cleanup = kwargs.get("cleanup", True)

    validated = _validate_repo_input(repo)
    if not validated:
        return {
            "status": "error",
            "error_code": "invalid_repo",
            "message": (
                "Expected owner/repo format or full URL from "
                "allowed hosts: github.com, gitlab.com, bitbucket.org"
            ),
        }
    url, repo_name = validated

    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(prefix="wm_ext_scan_")
        clone_path = Path(tmpdir) / repo_name

        # Shallow clone for speed — arguments are passed as a list, no shell
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--", url, str(clone_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return {
                "status": "error",
                "error_code": "clone_failed",
                "message": result.stderr[:500],
                "repo": repo,
            }

        if not clone_path.exists():
            return {
                "status": "error",
                "error_code": "clone_failed",
                "message": "Clone succeeded but target directory is missing",
                "repo": repo,
            }

        # Avoid mutating the global archaeologist singleton by scanning locally
        modules = _scan_modules_at_path(clone_path)

        # Calculate disk usage locally
        total_size = sum(f.stat().st_size for f in clone_path.rglob("*") if f.is_file())
        disk_usage_mb = round(total_size / (1024 * 1024), 2)

        return {
            "status": "success",
            "repo": repo,
            "repo_name": repo_name,
            "files_scanned": len(list(clone_path.rglob("*.py"))),
            "modules_found": len(modules),
            "modules": modules[:50],
            "disk_usage_mb": disk_usage_mb,
            "clone_path": str(clone_path) if not cleanup else None,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_code": "clone_timeout",
            "message": f"Clone of {repo} timed out",
        }
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
        return {
            "status": "error",
            "error_code": "missing_params",
            "message": "repo and local_module are required",
        }

    # Scan external repo
    ext_result = handle_external_repo_scan(repo=repo, cleanup=True)

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
        }
        if ext_result.get("status") == "success"
        else ext_result,
    }
