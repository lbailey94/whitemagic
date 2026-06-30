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
