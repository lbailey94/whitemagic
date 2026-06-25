"""STRATA — Codebase analysis and archaeology handlers for Chariot gana.

Exposes STRATA's static analysis (80+ checkers across 15 languages) and
archaeology kit (excavate, fossil, extinction, composition, temper) as
WhiteMagic MCP tools.

Tools exposed:
  strata.analyze     — Run static analysis checkers on a codebase
  strata.survey      — Fast surface survey using file metadata and git history
  strata.archaeology — Code archaeology subcommands (excavate/fossil/extinction/composition/temper)
  strata.list_checks — List all registered checker categories
"""
# ruff: noqa: BLE001

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def handle_strata_analyze(**kwargs: Any) -> dict[str, Any]:
    """Run STRATA static analysis on a codebase.

    Args:
        path: Project root directory to analyze
        format: Output format — 'json' (default), 'text', 'sarif', 'html'
        parallel: Run checkers in parallel (default: False)
        incremental: Skip unchanged files via content hash cache
        disable: List of check categories to disable
        context: Include enclosing function/class in findings
        since_ref: Only analyze files changed since this git ref
        diff_base: Only report findings on lines changed since this git ref
    """
    path = kwargs.get("path", "")
    if not path:
        return {"status": "error", "error": "path is required"}

    fmt = kwargs.get("format", "json")
    parallel = bool(kwargs.get("parallel", False))
    incremental = bool(kwargs.get("incremental", False))
    disable = kwargs.get("disable", [])
    context = bool(kwargs.get("context", False))
    since_ref = kwargs.get("since_ref")
    diff_base = kwargs.get("diff_base")

    try:
        from whitemagic.tools.strata import Strata

        strata = Strata(
            path,
            disabled_categories=disable if isinstance(disable, list) else [disable] if disable else None,
            since_ref=since_ref,
            diff_base=diff_base,
        )
        findings = strata.analyze(parallel=parallel, incremental=incremental)

        if fmt == "json":
            results = [
                {
                    "severity": f.severity.value,
                    "category": f.category,
                    "file": f.file,
                    "line": f.line,
                    "message": f.message,
                    "suggestion": f.suggestion,
                }
                for f in findings
            ]
            severity_counts = {"error": 0, "warning": 0, "info": 0}
            for f in findings:
                severity_counts[f.severity.value] += 1
            return {
                "status": "success",
                "path": path,
                "findings": results,
                "count": len(results),
                "severity_counts": severity_counts,
            }
        else:
            report = strata.report(format=fmt, context=context)
            return {
                "status": "success",
                "path": path,
                "report": report,
                "format": fmt,
                "count": len(findings),
            }
    except Exception as e:
        logger.exception("STRATA analyze failed")
        return {"status": "error", "error": str(e)}


def handle_strata_survey(**kwargs: Any) -> dict[str, Any]:
    """Run a fast surface survey using file metadata and git history.

    Args:
        path: Project root directory
    """
    path = kwargs.get("path", "")
    if not path:
        return {"status": "error", "error": "path is required"}

    try:
        from whitemagic.tools.strata.survey import SurveyReport

        report = SurveyReport(Path(path))
        rendered = report.render()
        return {
            "status": "success",
            "path": path,
            "report": rendered,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_strata_archaeology(**kwargs: Any) -> dict[str, Any]:
    """Run code archaeology subcommands on git history.

    Args:
        path: Project root directory
        subcommand: One of 'excavate', 'fossil', 'extinction', 'composition', 'temper'
        layer: Time layer for excavate (YYYY, YYYY-QN, or YYYY-MM)
        file: File path for fossil
        top: Number of results for composition/temper
        commits: Max commits for fossil
    """
    path = kwargs.get("path", "")
    subcommand = kwargs.get("subcommand", "temper")
    if not path:
        return {"status": "error", "error": "path is required"}

    try:
        from whitemagic.tools.strata.archaeology import (
            excavate,
            fossil,
            extinction,
            composition,
            temper,
        )

        project_path = Path(path).resolve()

        if subcommand == "excavate":
            layer = kwargs.get("layer", "")
            if not layer:
                return {"status": "error", "error": "layer is required for excavate"}
            result = excavate(project_path, layer, file_filter=kwargs.get("file"))
            return {"status": "success", "subcommand": "excavate", "layer": layer, "result": result}

        elif subcommand == "fossil":
            file_path = kwargs.get("file", "")
            if not file_path:
                return {"status": "error", "error": "file is required for fossil"}
            max_commits = int(kwargs.get("commits", 20))
            result = fossil(project_path, file_path, max_commits=max_commits)
            return {"status": "success", "subcommand": "fossil", "file": file_path, "result": result}

        elif subcommand == "extinction":
            result = extinction(project_path)
            return {"status": "success", "subcommand": "extinction", "result": result}

        elif subcommand == "composition":
            top = int(kwargs.get("top", 10))
            result = composition(project_path, top_n=top)
            return {"status": "success", "subcommand": "composition", "result": result}

        elif subcommand == "temper":
            top = int(kwargs.get("top", 10))
            file_filter = kwargs.get("file")
            result = temper(project_path, file_path=file_filter, top_n=top)
            return {"status": "success", "subcommand": "temper", "result": result}

        else:
            return {"status": "error", "error": f"Unknown subcommand: {subcommand}"}

    except Exception as e:
        logger.exception("STRATA archaeology failed")
        return {"status": "error", "error": str(e)}


def handle_strata_list_checks(**kwargs: Any) -> dict[str, Any]:
    """List all registered STRATA checker categories."""
    try:
        import inspect
        import re

        from whitemagic.tools.strata.checkers import get_checkers

        checkers_info = []
        for checker in get_checkers():
            name = checker.__name__
            doc = (checker.__doc__ or "").strip().splitlines()[0] if checker.__doc__ else ""
            try:
                source = inspect.getsource(checker)
                categories = sorted(set(re.findall(r'category\s*=\s*"([^"]+)"', source)))
            except (OSError, TypeError):
                categories = []
            checkers_info.append({
                "name": name,
                "description": doc,
                "categories": categories,
            })
        return {
            "status": "success",
            "checkers": checkers_info,
            "count": len(checkers_info),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
