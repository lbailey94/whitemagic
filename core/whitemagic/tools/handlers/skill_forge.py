# ruff: noqa: BLE001
"""Handler for SkillForge MCP operations.

Exposes skill listing, invocation, seeding, and export via MCP.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_skill_list(**kwargs: Any) -> dict[str, Any]:
    """List all forged skills in the library."""
    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        skills = []
        for name, skill in sorted(forge.known_skills.items()):
            skills.append({
                "name": skill.name,
                "description": skill.description,
                "triggers": skill.trigger_phrases[:3],
                "step_count": len(skill.optimized_chain.steps),
                "forge_count": skill.forge_count,
                "intent": skill.optimized_chain.intent,
            })
        return {
            "status": "success",
            "total": len(skills),
            "skills": skills,
        }
    except Exception as e:
        logger.debug("skill.list error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_list_failed", "message": str(e)}


def handle_skill_invoke(**kwargs: Any) -> dict[str, Any]:
    """Invoke a forged skill by name — returns its execution chain for replay."""
    name = kwargs.get("name") or kwargs.get("skill_name") or ""
    if not name:
        return {"status": "error", "error_code": "missing_name", "message": "name required"}

    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        chain = forge.invoke_skill(name)
        if chain is None:
            return {"status": "error", "error_code": "skill_not_found", "message": f"Skill '{name}' not found"}

        return {
            "status": "success",
            "skill_name": name,
            "intent": chain.intent,
            "steps": [
                {
                    "mansion": s.mansion,
                    "operation": s.operation,
                    "context": s.context_key,
                }
                for s in chain.steps
            ],
            "step_count": len(chain.steps),
            "complexity": chain.estimated_complexity,
        }
    except Exception as e:
        logger.debug("skill.invoke error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_invoke_failed", "message": str(e)}


def handle_skill_seed(**kwargs: Any) -> dict[str, Any]:
    """Seed common high-value skill chains into the library."""
    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        seeded = forge.seed_common_skills()
        return {
            "status": "success",
            "seeded_count": len(seeded),
            "seeded_names": [s.name for s in seeded],
            "total_skills": len(forge.known_skills),
        }
    except Exception as e:
        logger.debug("skill.seed error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_seed_failed", "message": str(e)}


def handle_skill_export_all(**kwargs: Any) -> dict[str, Any]:
    """Export all skills as portable SKILL.md files."""
    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        paths = forge.export_all_skills_md()
        return {
            "status": "success",
            "exported_count": len(paths),
            "export_dir": str(paths[0].parent) if paths else "",
            "files": [str(p.name) for p in paths],
        }
    except Exception as e:
        logger.debug("skill.export_all error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_export_failed", "message": str(e)}


def handle_skill_import(**kwargs: Any) -> dict[str, Any]:
    """Import a portable SKILL.md file as a ForgedSkill."""
    path = kwargs.get("path") or kwargs.get("file_path") or ""
    if not path:
        return {"status": "error", "error_code": "missing_path", "message": "path required"}

    try:
        from pathlib import Path

        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        skill = forge.import_skill_md(Path(path))
        if skill is None:
            return {"status": "error", "error_code": "import_failed", "message": "Could not parse SKILL.md"}

        return {
            "status": "success",
            "skill_name": skill.name,
            "description": skill.description,
            "step_count": len(skill.optimized_chain.steps),
        }
    except Exception as e:
        logger.debug("skill.import error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_import_failed", "message": str(e)}


def handle_skill_amend(**kwargs: Any) -> dict[str, Any]:
    """Amend a skill based on its failure history.

    Analyzes execution history to find failing steps, then proposes and
    applies a revised chain. This is the Inspect → Amend step of the
    self-improvement loop.
    """
    name = kwargs.get("name") or kwargs.get("skill_name") or ""
    if not name:
        return {"status": "error", "error_code": "missing_name", "message": "name required"}

    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        proposal = forge.amend(name)
        if proposal is None:
            return {
                "status": "success",
                "amended": False,
                "message": f"Skill '{name}' does not need amendment (insufficient failures or history)",
            }

        return {
            "status": "success",
            "amended": True,
            "skill_name": proposal.skill_name,
            "rationale": proposal.rationale,
            "changes": proposal.changes,
            "failing_steps": proposal.failing_steps,
            "old_version": proposal.old_version,
            "new_version": proposal.new_version,
            "old_failure_rate": round(proposal.old_failure_rate, 3),
        }
    except Exception as e:
        logger.debug("skill.amend error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_amend_failed", "message": str(e)}


def handle_skill_history(**kwargs: Any) -> dict[str, Any]:
    """Get execution history and health metrics for skills.

    Returns per-skill health data including failure rates, execution counts,
    version info, and amendment status. Skills with high failure rates are
    flagged as needing amendment.
    """
    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        health = forge.get_skill_health()

        needs_amendment = [s for s in health if s["needs_amendment"]]

        return {
            "status": "success",
            "total_skills": len(health),
            "skills": health,
            "needs_amendment": needs_amendment,
            "needs_amendment_count": len(needs_amendment),
        }
    except Exception as e:
        logger.debug("skill.history error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_history_failed", "message": str(e)}


def handle_skill_rollback(**kwargs: Any) -> dict[str, Any]:
    """Roll back a skill to its previous version.

    This is the Evaluate safety net — if an amendment made things worse,
    restore the previous chain.
    """
    name = kwargs.get("name") or kwargs.get("skill_name") or ""
    if not name:
        return {"status": "error", "error_code": "missing_name", "message": "name required"}

    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        success = forge.rollback(name)
        if not success:
            return {
                "status": "error",
                "error_code": "no_previous_version",
                "message": f"Skill '{name}' has no previous version to rollback to",
            }

        return {
            "status": "success",
            "skill_name": name,
            "rolled_back": True,
            "message": f"Skill '{name}' rolled back to previous version",
        }
    except Exception as e:
        logger.debug("skill.rollback error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_rollback_failed", "message": str(e)}


def handle_skill_evaluate(**kwargs: Any) -> dict[str, Any]:
    """Evaluate whether the last amendment improved outcomes.

    Compares failure rates before and after the most recent amendment
    and recommends whether to keep or rollback the change.
    """
    name = kwargs.get("name") or kwargs.get("skill_name") or ""
    if not name:
        return {"status": "error", "error_code": "missing_name", "message": "name required"}

    try:
        from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge

        forge = get_skill_forge()
        evaluation = forge.evaluate_amendment(name)

        return {
            "status": "success",
            **evaluation,
        }
    except Exception as e:
        logger.debug("skill.evaluate error: %s", e, exc_info=True)
        return {"status": "error", "error_code": "skill_evaluate_failed", "message": str(e)}
