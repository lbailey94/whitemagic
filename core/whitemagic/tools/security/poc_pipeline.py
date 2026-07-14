"""PoC verification pipeline — template → render → compile → execute → verify."""
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from whitemagic.codegenome.engine import get_codegenome_engine
from whitemagic.tools.security.foundry_bridge import get_foundry_bridge

logger = logging.getLogger(__name__)


@dataclass
class PoCResult:
    success: bool
    template_name: str
    rendered_code: str
    compiled: bool
    test_passed: bool
    output: str
    error: str
    elapsed_s: float
    governance_approved: bool = True


def _check_governance(target: str, scope: str = "bounty") -> bool:
    """Violet governance check — verify target is in scope before PoC execution.

    Strict by default under violet profile. Permissive only when:
    - WM_POC_AUTO_APPROVE=1 is set (explicit override)
    - Target is in WM_POC_APPROVED list
    """
    approved = os.environ.get("WM_POC_APPROVED", "").split(",")
    if target and target in approved:
        return True
    if os.environ.get("WM_POC_AUTO_APPROVE", "0") == "1":
        return True
    # Check Dharma profile — violet requires explicit approval
    try:
        from whitemagic.dharma.rules import get_rules_engine
        engine = get_rules_engine()
        if engine.get_profile() == "violet":
            logger.info(
                "Governance: PoC target %s not in approved list for scope %s (violet profile — strict mode)",
                target, scope,
            )
            return False
    except (ImportError, ModuleNotFoundError):
        logger.debug("Optional dependency unavailable: ImportError")
    # Non-violet profiles: permissive by default
    logger.info("Governance: PoC target %s not in approved list for scope %s", target, scope)
    return True


def generate_poc(
    template_name: str,
    variables: dict[str, str],
    tier: str | None = None,
) -> str:
    """Render a PoC template with variables."""
    engine = get_codegenome_engine()
    template = engine.get_template(template_name)
    if not template:
        raise ValueError(f"Template not found: {template_name}")
    rendered = engine.render(template_name, tier=tier or "default", **variables)
    return rendered


def verify_poc(
    template_name: str,
    variables: dict[str, str],
    project_dir: str,
    tier: str = "huben",
    target: str = "",
    governance_scope: str = "bounty",
) -> PoCResult:
    """Full PoC pipeline: governance check → render → write → compile → test → verify."""
    start = time.time()

    # 1. Governance check
    gov_approved = _check_governance(target, governance_scope)
    if not gov_approved:
        return PoCResult(
            success=False,
            template_name=template_name,
            rendered_code="",
            compiled=False,
            test_passed=False,
            output="",
            error="Governance: target not approved for PoC execution",
            elapsed_s=time.time() - start,
            governance_approved=False,
        )

    # 2. Render template
    try:
        code = generate_poc(template_name, variables, tier=tier)
    except Exception as e:
        return PoCResult(
            success=False,
            template_name=template_name,
            rendered_code="",
            compiled=False,
            test_passed=False,
            output="",
            error=f"Template render failed: {e}",
            elapsed_s=time.time() - start,
        )

    # 3. Write to Foundry test directory
    test_dir = Path(project_dir) / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / f"PoC_{template_name}_{int(time.time())}.t.sol"
    test_file.write_text(code)

    # 4. Compile
    bridge = get_foundry_bridge(project_dir)
    build_result = bridge.build(silent=True)
    compiled = build_result.success

    if not compiled:
        return PoCResult(
            success=False,
            template_name=template_name,
            rendered_code=code,
            compiled=False,
            test_passed=False,
            output=build_result.stdout,
            error=build_result.stderr,
            elapsed_s=time.time() - start,
        )

    # 5. Run test
    test_result = bridge.test(match=f"PoC_{template_name}")
    test_passed = test_result.success

    return PoCResult(
        success=test_passed,
        template_name=template_name,
        rendered_code=code,
        compiled=True,
        test_passed=test_passed,
        output=test_result.stdout[-2000:],
        error=test_result.stderr[-500:],
        elapsed_s=time.time() - start,
        governance_approved=True,
    )


def contest_prepare(
    repo_url: str,
    project_dir: str,
    checkers: list[str] | None = None,
) -> dict[str, Any]:
    """One-command contest setup: clone → scan → filter → prioritize."""
    try:
        from whitemagic.tools.strata.engine import StrataEngine
    except ImportError:
        return {
            "success": False,
            "error": "StrataEngine not yet implemented — use strata.archaeology for codebase analysis",
            "elapsed_s": 0.0,
        }
    from whitemagic.tools.security.contest_pipeline import get_contest_pipeline
    from whitemagic.tools.security.vuln_knowledge import get_vuln_knowledge_base

    start = time.time()

    # 1. Clone if needed
    project_path = Path(project_dir)
    if not project_path.exists():
        result = subprocess.run(
            ["git", "clone", repo_url, str(project_path)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return {"success": False, "error": f"Clone failed: {result.stderr}", "elapsed_s": time.time() - start}

    # 2. Run STRATA analysis
    engine = StrataEngine()
    findings = engine.scan(project_path, checkers=checkers)

    # 3. Convert to contest findings
    pipeline = get_contest_pipeline()
    finding_dicts = [
        {
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "category": f.category,
            "file": f.file,
            "line": f.line,
            "message": f.message,
            "suggestion": f.suggestion,
        }
        for f in findings
    ]
    added = pipeline.add_from_strata(finding_dicts)

    # 4. Match against known patterns
    kb = get_vuln_knowledge_base()
    matched = kb.match_findings(finding_dicts)

    return {
        "success": True,
        "total_findings": len(findings),
        "contest_findings": added,
        "matched_patterns": len(matched),
        "matched_details": matched[:10],
        "elapsed_s": time.time() - start,
    }
