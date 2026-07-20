"""Slither integration checker — runs Slither CLI and maps results to STRATA findings."""
import json
import logging
import shutil
import subprocess
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

logger = logging.getLogger(__name__)

_SEVERITY_MAP = {
    "high": FindingSeverity.ERROR,
    "medium": FindingSeverity.WARNING,
    "low": FindingSeverity.INFO,
    "informational": FindingSeverity.INFO,
    "optimization": FindingSeverity.INFO,
}


@register
def check_slither(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Run Slither static analyzer on Solidity projects and map results to STRATA findings."""
    slither_bin = shutil.which("slither")
    if slither_bin is None:
        logger.debug("Slither not installed — skipping")
        return

    sol_files = list(file_index.files_by_extension(".sol"))
    if not sol_files:
        return

    has_foundry = (project_path / "foundry.toml").exists() or (project_path / "lib").exists()
    has_hardhat = (project_path / "hardhat.config.js").exists() or (project_path / "hardhat.config.ts").exists()

    cmd = [slither_bin, str(project_path), "--json", "-"]
    if not has_foundry and not has_hardhat:
        return

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_path),
        )
    except subprocess.TimeoutExpired:
        logger.warning("Slither timed out on %s", project_path)
        return
    except Exception as e:  # noqa: BLE001
        logger.debug("Slither failed: %s", e)
        return

    if result.returncode not in (0, 1):
        logger.debug("Slither exited with code %d", result.returncode)
        return

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        logger.debug("Slither output not valid JSON")
        return

    for detector in data.get("results", {}).get("detectors", []):
        severity_str = detector.get("impact", "informational").lower()
        severity = _SEVERITY_MAP.get(severity_str, FindingSeverity.INFO)
        check_id = detector.get("check_id", "slither")
        confidence = detector.get("confidence", "Medium")
        detector.get("first_markdown_line", "?")
        elements = detector.get("elements", [])
        rel_file = "?"
        line_num = None
        if elements:
            first_elem = elements[0]
            source = first_elem.get("source_mapping", {})
            rel_file = source.get("filename_relative", "?")
            line_num = source.get("lines", [None])[0] if source.get("lines") else None

        findings.append(
            Finding(
                severity=severity,
                category=f"slither_{check_id}",
                file=rel_file,
                line=line_num,
                message=f"[Slither] {detector.get('description', check_id)} (confidence: {confidence})",
                suggestion=detector.get("markdown", detector.get("description", ""))[:500],
            )
        )
