# ruff: noqa: BLE001
"""Skill Forge - The Recursive Blacksmith.
======================================

"Iron sharpens iron, so one person sharpens another."

The Skill Forge is responsible for "crystallizing" success.
When the Universal Router successfully executes a chain multiple times,
the Emergence Engine triggers the Forge to turn that dynamic chain
into a static, optimized "Skill" (Pattern).

This is the core of Recursive Self-Improvement.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root
from whitemagic.core.intelligence.omni.universal_router import ExecutionChain, GanaStep

logger = logging.getLogger(__name__)


@dataclass
class SkillExecution:
    """A single execution record for a forged skill."""

    timestamp: float
    success: bool
    error: str = ""
    steps_completed: int = 0
    total_steps: int = 0
    duration_ms: float = 0.0


@dataclass
class AmendmentProposal:
    """A proposed amendment to a skill's chain."""

    skill_name: str
    rationale: str
    changes: list[str]
    failing_steps: list[int]
    old_version: int
    new_version: int
    old_failure_rate: float
    estimated_improvement: float


@dataclass
class ForgedSkill:
    """A crystallized skill ready for reuse."""

    name: str
    description: str
    trigger_phrases: list[str]
    optimized_chain: ExecutionChain
    version: int = 1
    forge_count: int = 1
    execution_history: list[SkillExecution] = field(default_factory=list)
    previous_versions: list[ExecutionChain] = field(default_factory=list)
    amendment_count: int = 0
    last_amended: float | None = None


def _normalize_steps(steps: list[GanaStep]) -> str:
    """Create a canonical string signature for a list of steps."""
    return "|".join(f"{s.mansion}:{s.operation}:{s.context_key}" for s in steps)


def _step_similarity(steps_a: list[GanaStep], steps_b: list[GanaStep]) -> float:
    """Compute Jaccard similarity between two step sequences (0.0–1.0)."""
    set_a = {(s.mansion, s.operation) for s in steps_a}
    set_b = {(s.mansion, s.operation) for s in steps_b}
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


class SkillForge:
    """Forges transient actions into permanent skills."""

    SIMILARITY_THRESHOLD = 0.85
    SLOP_MAX_REPEAT = 2

    def __init__(self, skill_library_path: Path | None = None):
        if skill_library_path is None:
            skill_library_path = get_state_root() / "skills"
        self.skill_library_path = skill_library_path
        self.skill_library_path.mkdir(parents=True, exist_ok=True)
        self.known_skills: dict[str, ForgedSkill] = {}
        self._step_signatures: dict[str, str] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        """Load all forged skills from disk."""
        count = 0
        for skill_file in self.skill_library_path.glob("*.json"):
            try:
                with open(skill_file) as f:
                    data = json.load(f)

                from whitemagic.core.intelligence.omni.universal_router import GanaStep

                steps = [
                    GanaStep(
                        mansion=s["mansion"],
                        operation=s["operation"],
                        context_key=s["context"],
                        parameters={},
                    )
                    for s in data.get("steps", [])
                ]

                chain = ExecutionChain(
                    intent=data.get("description", ""),
                    steps=steps,
                    estimated_complexity=len(steps),
                    required_capabilities=[],
                )

                # Load previous versions if present
                previous_versions: list[ExecutionChain] = []
                for pv in data.get("previous_versions", []):
                    pv_steps = [
                        GanaStep(
                            mansion=s["mansion"],
                            operation=s["operation"],
                            context_key=s["context"],
                            parameters={},
                        )
                        for s in pv.get("steps", [])
                    ]
                    previous_versions.append(
                        ExecutionChain(
                            intent=pv.get("intent", ""),
                            steps=pv_steps,
                            estimated_complexity=len(pv_steps),
                            required_capabilities=[],
                        )
                    )

                # Load execution history if present
                execution_history: list[SkillExecution] = []
                for eh in data.get("execution_history", []):
                    execution_history.append(
                        SkillExecution(
                            timestamp=eh["timestamp"],
                            success=eh["success"],
                            error=eh.get("error", ""),
                            steps_completed=eh.get("steps_completed", 0),
                            total_steps=eh.get("total_steps", 0),
                            duration_ms=eh.get("duration_ms", 0.0),
                        )
                    )

                skill = ForgedSkill(
                    name=data["name"],
                    description=data["description"],
                    trigger_phrases=data["triggers"],
                    optimized_chain=chain,
                    forge_count=data.get("forge_count", 1),
                    version=data.get("version", 1),
                    execution_history=execution_history,
                    previous_versions=previous_versions,
                    amendment_count=data.get("amendment_count", 0),
                    last_amended=data.get("last_amended"),
                )

                self.known_skills[skill.name] = skill
                self._step_signatures[skill.name] = _normalize_steps(steps)
                count += 1
            except Exception as e:
                logger.warning("Failed to load skill %s: %s", skill_file, e)

        if count > 0:
            logger.info("Skill Forge loaded %s crystallized skills.", count)

    def assess_pattern(self, chain: ExecutionChain, success_metric: float) -> bool:
        """Determine if a chain is worthy of becoming a skill.

        Checks:
        - Success metric > 0.8
        - Chain has > 2 steps
        - Not slop (no excessive step repetition)
        """
        if success_metric <= 0.8:
            return False
        if len(chain.steps) <= 2:
            return False
        if self._detect_slop(chain):
            return False
        return True

    def _detect_slop(self, chain: ExecutionChain) -> bool:
        """Detect low-quality chains that shouldn't be forged.

        Slop indicators:
        - Same (mansion, operation) repeated more than SLOP_MAX_REPEAT times
        - All steps are identical
        - Chain is trivially repetitive
        """
        if not chain.steps:
            return True

        op_counts: dict[tuple[str, str], int] = {}
        for step in chain.steps:
            key = (step.mansion, step.operation)
            op_counts[key] = op_counts.get(key, 0) + 1

        if any(c > self.SLOP_MAX_REPEAT for c in op_counts.values()):
            return True

        if len(op_counts) == 1 and len(chain.steps) > 2:
            return True

        return False

    def _find_duplicate(self, chain: ExecutionChain) -> ForgedSkill | None:
        """Find an existing skill that is a near-duplicate of the chain.

        Returns the existing skill if found, None otherwise.
        """
        new_sig = _normalize_steps(chain.steps)
        for name, existing_sig in self._step_signatures.items():
            if existing_sig == new_sig:
                return self.known_skills[name]

        for name, skill in self.known_skills.items():
            similarity = _step_similarity(chain.steps, skill.optimized_chain.steps)
            if similarity >= self.SIMILARITY_THRESHOLD:
                return skill

        return None

    def forge(self, chain: ExecutionChain, name: str | None = None) -> ForgedSkill:
        """Convert a Chain into a clean, reusable Skill.

        If name is None, attempts LLM-based name generation with heuristic fallback.
        Checks for duplicates and increments forge_count instead of creating a new skill.
        """
        existing = self._find_duplicate(chain)
        if existing is not None:
            existing.forge_count += 1
            self._save_skill(existing)
            logger.info(
                "Skill '%s' re-forged (count=%d) — duplicate detected for '%s'",
                existing.name,
                existing.forge_count,
                chain.intent,
            )
            return existing

        if name is None:
            name = self._generate_name(chain)

        logger.info("Forging new skill: '%s' from chain for '%s'", name, chain.intent)

        skill = ForgedSkill(
            name=name,
            description=f"Auto-forged skill for: {chain.intent}",
            trigger_phrases=[chain.intent],
            optimized_chain=chain,
        )

        self.known_skills[skill.name] = skill
        self._step_signatures[skill.name] = _normalize_steps(chain.steps)
        self._save_skill(skill)
        return skill

    def _generate_name(self, chain: ExecutionChain) -> str:
        """Generate a descriptive skill name.

        Tries LLM (llama.cpp) first, falls back to heuristic.
        """
        llm_name = self._try_llm_name(chain)
        if llm_name:
            return llm_name

        return self._heuristic_name(chain)

    def _heuristic_name(self, chain: ExecutionChain) -> str:
        """Generate a name from chain structure as fallback."""
        mansions = [s.mansion.lower() for s in chain.steps]
        primary = mansions[0] if mansions else "unknown"
        intent_words = re.findall(r"[a-z]+", chain.intent.lower())
        keyword = intent_words[0] if intent_words else "flow"
        return f"{keyword}_{primary}_{len(chain.steps)}step"

    def _try_llm_name(self, chain: ExecutionChain) -> str | None:
        """Try to generate a name via llama-server. Returns None on failure."""
        try:
            import asyncio

            from whitemagic.core.ports import llama_generate as _generate

            steps_desc = ", ".join(f"{s.mansion}/{s.operation}" for s in chain.steps)
            prompt = (
                f"Generate a short, descriptive skill name (snake_case, max 30 chars) "
                f"for an AI tool chain that does: '{chain.intent}'. "
                f"The chain steps are: {steps_desc}. "
                f"Return ONLY the name, nothing else."
            )

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                return None

            result = loop.run_until_complete(
                _generate(model="gemma3:4b", prompt=prompt)
            )
            raw = result.get("response", "").strip().lower()
            raw = re.sub(r"[^a-z0-9_]", "", raw.replace(" ", "_"))[:30]
            if raw and len(raw) >= 3:
                return raw
        except Exception as e:
            logger.debug("LLM name generation failed: %s", e)
        return None

    def _save_skill(self, skill: ForgedSkill) -> None:
        """Persist the skill to disk and update the SKILLS.md registry."""
        skill_file = self.skill_library_path / f"{skill.name.lower()}.json"

        data = {
            "name": skill.name,
            "description": skill.description,
            "triggers": skill.trigger_phrases,
            "forge_count": skill.forge_count,
            "version": skill.version,
            "amendment_count": skill.amendment_count,
            "last_amended": skill.last_amended,
            "steps": [
                {
                    "mansion": s.mansion,
                    "operation": s.operation,
                    "context": s.context_key,
                }
                for s in skill.optimized_chain.steps
            ],
            "previous_versions": [
                {
                    "intent": pv.intent,
                    "steps": [
                        {
                            "mansion": s.mansion,
                            "operation": s.operation,
                            "context": s.context_key,
                        }
                        for s in pv.steps
                    ],
                }
                for pv in skill.previous_versions
            ],
            "execution_history": [
                {
                    "timestamp": eh.timestamp,
                    "success": eh.success,
                    "error": eh.error,
                    "steps_completed": eh.steps_completed,
                    "total_steps": eh.total_steps,
                    "duration_ms": eh.duration_ms,
                }
                for eh in skill.execution_history[-100:]  # Keep last 100
            ],
        }

        with open(skill_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Skill saved to %s", skill_file)
        self._update_skills_md()

        # Auto-export as portable SKILL.md so forged skills are immediately usable
        # in Claude Code, Codex CLI, Gemini CLI, etc.
        try:
            self.export_skill_md(skill)
        except Exception as e:
            logger.debug("Auto-export SKILL.md failed for '%s': %s", skill.name, e)

    def _update_skills_md(self) -> None:
        """Regenerate the SKILLS.md catalog for AI consumption."""
        catalog_path = self.skill_library_path.parent / "SKILLS.md"
        catalog_path.parent.mkdir(parents=True, exist_ok=True)

        content = [
            "# Whitemagic Skill Registry\n",
            "> Auto-generated by Skill Forge. DO NOT EDIT MANUALLY.\n",
            "| Skill Name | Description | Triggers | Complexity | Forge Count |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for skill in self.known_skills.values():
            triggers = ", ".join([f"`{t}`" for t in skill.trigger_phrases[:3]])
            complexity = f"{skill.optimized_chain.estimated_complexity:.1f}"
            row = f"| **{skill.name}** | {skill.description} | {triggers} | {complexity} | {skill.forge_count} |"
            content.append(row)

        content.append(
            "\n\n---\n*To use a skill, reference it by name in your intent.*"
        )

        with open(catalog_path, "w") as f:
            f.write("\n".join(content))

        logger.info("Updated SKILLS.md registry at %s", catalog_path)

    def export_skill_md(
        self, skill: ForgedSkill, output_dir: Path | None = None
    ) -> Path:
        """Export a forged skill as a portable SKILL.md file.

        The SKILL.md format is compatible with Claude Code, Codex CLI,
        Gemini CLI, Copilot, Cursor, Cline, Windsurf, and OpenCode.

        Args:
            skill: The forged skill to export.
            output_dir: Directory to write the SKILL.md file. Defaults to
                        skill_library_path / "exported".

        Returns:
            Path to the written SKILL.md file.
        """
        if output_dir is None:
            output_dir = self.skill_library_path / "exported"
        output_dir.mkdir(parents=True, exist_ok=True)

        steps_desc = "\n".join(
            f"  {i + 1}. `wm(route='{s.mansion.lower()}.{s.operation}')` — {s.context_key}"
            for i, s in enumerate(skill.optimized_chain.steps)
        )
        triggers = ", ".join(f"`{t}`" for t in skill.trigger_phrases[:3])
        chain_intent = skill.optimized_chain.intent

        content = f"""---
name: {skill.name}
description: "{skill.description}"
version: {skill.version}.0.0
author: WhiteMagic SkillForge (auto-forged)
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    forge_count: {skill.forge_count}
    chain_intent: "{chain_intent}"
    step_count: {len(skill.optimized_chain.steps)}
    complexity: {skill.optimized_chain.estimated_complexity:.1f}
    auto_forged: true
---

# {skill.name.replace("_", " ").title()}

## When to Use

Use this skill when you need to: {chain_intent}

**Triggers**: {triggers}

**Forge count**: {skill.forge_count} (times this pattern has been observed)

## How to Invoke

Execute the following tool chain in sequence:

```python
{chr(10).join(f"wm(route='{s.mansion.lower()}.{s.operation}')  # {s.context_key}" for s in skill.optimized_chain.steps)}
```

Or use natural language:

```
wm(thought="{chain_intent}")
```

## Chain Steps

{steps_desc}

## Notes

- This skill was auto-forged by WhiteMagic SkillForge from observed execution patterns
- Forge count: {skill.forge_count} (higher = more validated)
- Complexity: {skill.optimized_chain.estimated_complexity:.1f}
- Compatible with Claude Code, Codex CLI, Gemini CLI, Copilot, Cursor, Cline, Windsurf, OpenCode
"""

        skill_md_path = output_dir / f"{skill.name.lower()}.md"
        with open(skill_md_path, "w") as f:
            f.write(content)

        logger.info("Exported SKILL.md for '%s' to %s", skill.name, skill_md_path)
        return skill_md_path

    def export_all_skills_md(self, output_dir: Path | None = None) -> list[Path]:
        """Export all known skills as portable SKILL.md files.

        Args:
            output_dir: Directory to write SKILL.md files. Defaults to
                        skill_library_path / "exported".

        Returns:
            List of paths to written SKILL.md files.
        """
        if output_dir is None:
            output_dir = self.skill_library_path / "exported"
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = []
        for skill in self.known_skills.values():
            paths.append(self.export_skill_md(skill, output_dir))
        return paths

    def import_skill_md(self, skill_md_path: Path) -> ForgedSkill | None:
        """Import a portable SKILL.md file as a ForgedSkill.

        This is the reverse bridge — parse SKILL.md files from other runtimes
        (Claude Code, Codex CLI, Gemini CLI, etc.) back into ForgedSkill objects
        that WhiteMagic can execute via invoke_skill().

        Args:
            skill_md_path: Path to the SKILL.md file to import.

        Returns:
            The imported ForgedSkill, or None if parsing fails.
        """
        try:
            content = skill_md_path.read_text()

            if not content.startswith("---"):
                logger.warning("SKILL.md missing frontmatter: %s", skill_md_path)
                return None

            fm_end = content.index("---", 3)
            frontmatter = content[3:fm_end].strip()
            body = content[fm_end + 3 :].strip()

            # Simple YAML parse (avoid pyyaml dependency for basic key-value)
            meta: dict[str, str] = {}
            for line in frontmatter.splitlines():
                if ":" in line and not line.startswith(" "):
                    key, _, val = line.partition(":")
                    val = val.strip().strip('"').strip("'")
                    if val:
                        meta[key.strip()] = val

            name = meta.get("name", skill_md_path.stem)
            description = meta.get("description", "")

            # Extract wm(route=...) calls only from fenced code blocks
            import re as _re

            code_block_pattern = _re.compile(r"```[a-zA-Z]*\n(.*?)```", _re.DOTALL)
            route_pattern = _re.compile(
                r"wm\(route=['\"]([^'\"]+)['\"]\)",
                _re.IGNORECASE,
            )
            routes: list[str] = []
            for block_match in code_block_pattern.finditer(body):
                routes.extend(route_pattern.findall(block_match.group(1)))

            if not routes:
                logger.warning("No wm(route=...) calls found in %s", skill_md_path)
                return None

            # Build steps from routes
            steps: list[GanaStep] = []
            for route in routes:
                parts = route.split(".", 1)
                if len(parts) == 2:
                    mansion = parts[0].replace("gana_", "").upper()
                    operation = parts[1]
                else:
                    mansion = route.replace("gana_", "").upper()
                    operation = "search"
                steps.append(
                    GanaStep(
                        mansion=mansion,
                        operation=operation,
                        context_key="imported",
                        parameters={},
                    )
                )

            chain = ExecutionChain(
                intent=description,
                steps=steps,
                estimated_complexity=float(len(steps)),
                required_capabilities=[],
            )

            skill = ForgedSkill(
                name=name,
                description=description,
                trigger_phrases=[description] if description else [],
                optimized_chain=chain,
            )

            self.known_skills[skill.name] = skill
            self._step_signatures[skill.name] = _normalize_steps(steps)
            self._save_skill(skill)

            logger.info("Imported SKILL.md '%s' from %s", skill.name, skill_md_path)
            return skill

        except Exception as e:
            logger.warning("Failed to import SKILL.md %s: %s", skill_md_path, e)
            return None

    def invoke_skill(self, name: str) -> ExecutionChain | None:
        """Get the execution chain for a forged skill by name.

        This enables skill replay — re-executing a forged skill's chain
        via UniversalRouter.execute().

        Args:
            name: The skill name (case-insensitive).

        Returns:
            The ExecutionChain for the skill, or None if not found.
        """
        skill = self.known_skills.get(name)
        if skill is None:
            for key, s in self.known_skills.items():
                if key.lower() == name.lower():
                    skill = s
                    break

        if skill is None:
            logger.warning("Skill '%s' not found in library", name)
            return None

        logger.info(
            "Invoking skill '%s' (%d steps)", name, len(skill.optimized_chain.steps)
        )
        return skill.optimized_chain

    # ── Self-Improvement: Observe → Inspect → Amend → Evaluate ──────────

    def record_execution(
        self,
        skill_name: str,
        success: bool,
        error: str = "",
        steps_completed: int = 0,
        total_steps: int = 0,
        duration_ms: float = 0.0,
    ) -> None:
        """Record a skill execution outcome.

        This is the Observe step — every skill invocation should be recorded
        so that the system has evidence of what happened when the skill ran.

        Args:
            skill_name: The skill that was executed (case-insensitive).
            success: Whether the execution succeeded overall.
            error: Error message if the execution failed.
            steps_completed: How many steps completed before failure.
            total_steps: Total steps in the chain.
            duration_ms: Execution duration in milliseconds.
        """
        skill = self._find_skill_by_name(skill_name)
        if skill is None:
            logger.warning("Cannot record execution: skill '%s' not found", skill_name)
            return

        execution = SkillExecution(
            timestamp=time.time(),
            success=success,
            error=error,
            steps_completed=steps_completed,
            total_steps=total_steps or len(skill.optimized_chain.steps),
            duration_ms=duration_ms,
        )
        skill.execution_history.append(execution)

        # Keep history bounded (last 200 executions)
        if len(skill.execution_history) > 200:
            skill.execution_history = skill.execution_history[-200:]

        self._save_skill(skill)
        logger.debug(
            "Recorded execution for '%s': success=%s, total=%d",
            skill_name,
            success,
            len(skill.execution_history),
        )

    def get_failure_rate(self, skill_name: str, window: int = 20) -> float:
        """Compute the failure rate for a skill over recent executions.

        Args:
            skill_name: The skill to analyze (case-insensitive).
            window: Number of recent executions to consider.

        Returns:
            Failure rate (0.0–1.0), or 0.0 if no execution history.
        """
        skill = self._find_skill_by_name(skill_name)
        if skill is None or not skill.execution_history:
            return 0.0

        recent = skill.execution_history[-window:]
        failures = sum(1 for e in recent if not e.success)
        return failures / len(recent) if recent else 0.0

    def get_skill_health(self) -> list[dict[str, Any]]:
        """Get health metrics for all skills.

        Returns a list of dicts with skill name, failure rate, execution count,
        version, and amendment count. Skills with high failure rates are
        candidates for amendment.
        """
        results = []
        for name, skill in sorted(self.known_skills.items()):
            recent = skill.execution_history[-20:]
            total = len(recent)
            failures = sum(1 for e in recent if not e.success)
            failure_rate = failures / total if total > 0 else 0.0
            results.append({
                "name": name,
                "version": skill.version,
                "forge_count": skill.forge_count,
                "execution_count": len(skill.execution_history),
                "recent_executions": total,
                "recent_failures": failures,
                "failure_rate": round(failure_rate, 3),
                "amendment_count": skill.amendment_count,
                "needs_amendment": failure_rate > 0.3 and total >= 3,
            })
        return results

    def amend(self, skill_name: str) -> AmendmentProposal | None:
        """Propose and apply an amendment to a skill based on failure history.

        This is the Inspect → Amend step. Analyzes execution history to find
        failing steps, then proposes and applies a revised chain.

        The amendment may:
        - Remove consistently failing steps
        - Reorder steps to put reliable ones first
        - Add a verification step at the end
        - Update trigger phrases based on observed intent

        Args:
            skill_name: The skill to amend (case-insensitive).

        Returns:
            The amendment proposal if applied, None if no amendment needed.
        """
        skill = self._find_skill_by_name(skill_name)
        if skill is None:
            logger.warning("Cannot amend: skill '%s' not found", skill_name)
            return None

        recent = skill.execution_history[-20:]
        if len(recent) < 3:
            logger.info("Skill '%s' has insufficient history for amendment", skill_name)
            return None

        failure_rate = self.get_failure_rate(skill_name)
        if failure_rate < 0.3:
            logger.info("Skill '%s' failure rate %.2f below amendment threshold", skill_name, failure_rate)
            return None

        # Inspect: identify failing steps
        step_fail_counts = [0] * len(skill.optimized_chain.steps)
        for exec in recent:
            if not exec.success and 0 < exec.steps_completed < len(step_fail_counts):
                for i in range(exec.steps_completed, len(step_fail_counts)):
                    step_fail_counts[i] += 1

        failing_steps = [
            i for i, count in enumerate(step_fail_counts)
            if count > len(recent) * 0.4
        ]

        changes = []
        old_chain = skill.optimized_chain
        new_steps = list(old_chain.steps)

        if failing_steps:
            # Remove the worst-failing steps (keep at least 2)
            steps_to_remove = sorted(failing_steps, reverse=True)
            for idx in steps_to_remove:
                if len(new_steps) > 2:
                    removed = new_steps.pop(idx)
                    changes.append(
                        f"Removed step {idx + 1} ({removed.mansion}/{removed.operation}) "
                        f"— failed in {step_fail_counts[idx]}/{len(recent)} recent executions"
                    )

        # If all steps fail equally, add a verification step at the end
        if not changes and failure_rate > 0.5:
            new_steps.append(
                GanaStep(
                    mansion="GHOST",
                    operation="analyze",
                    context_key="verify_result",
                    parameters={},
                )
            )
            changes.append(
                "Added verification step (GHOST/analyze) — high failure rate "
                f"({failure_rate:.0%}) with no specific step identified"
            )

        if not changes:
            logger.info("Skill '%s' has failures but no actionable amendment", skill_name)
            return None

        # Save old version
        old_version = skill.version
        old_failure_rate = failure_rate

        # Apply amendment
        skill.previous_versions.append(old_chain)
        skill.optimized_chain = ExecutionChain(
            intent=old_chain.intent,
            steps=new_steps,
            estimated_complexity=len(new_steps) * 0.8,
            required_capabilities=old_chain.required_capabilities,
        )
        skill.version += 1
        skill.amendment_count += 1
        skill.last_amended = time.time()

        # Update signature
        self._step_signatures[skill.name] = _normalize_steps(new_steps)

        self._save_skill(skill)

        proposal = AmendmentProposal(
            skill_name=skill.name,
            rationale=f"Failure rate {old_failure_rate:.0%} triggered amendment",
            changes=changes,
            failing_steps=failing_steps,
            old_version=old_version,
            new_version=skill.version,
            old_failure_rate=old_failure_rate,
            estimated_improvement=0.3,
        )

        logger.info(
            "Amended skill '%s' v%d → v%d: %s",
            skill.name,
            old_version,
            skill.version,
            "; ".join(changes),
        )
        return proposal

    def rollback(self, skill_name: str) -> bool:
        """Roll back a skill to its previous version.

        This is the Evaluate safety net — if an amendment made things worse,
        restore the previous chain.

        Args:
            skill_name: The skill to roll back (case-insensitive).

        Returns:
            True if rollback succeeded, False if no previous version exists.
        """
        skill = self._find_skill_by_name(skill_name)
        if skill is None:
            logger.warning("Cannot rollback: skill '%s' not found", skill_name)
            return False

        if not skill.previous_versions:
            logger.warning("Skill '%s' has no previous version to rollback to", skill_name)
            return False

        # Current chain becomes a version entry (for audit)
        previous = skill.previous_versions.pop()

        skill.optimized_chain = previous
        skill.version -= 1
        skill.last_amended = time.time()

        self._step_signatures[skill.name] = _normalize_steps(previous.steps)
        self._save_skill(skill)

        logger.info(
            "Rolled back skill '%s' from v%d to v%d",
            skill.name,
            skill.version + 1,
            skill.version,
        )
        return True

    def evaluate_amendment(self, skill_name: str, window: int = 10) -> dict[str, Any]:
        """Evaluate whether the last amendment improved outcomes.

        This is the Evaluate step — compares failure rates before and after
        the most recent amendment.

        Args:
            skill_name: The skill to evaluate (case-insensitive).
            window: Number of recent executions to use for post-amendment rate.

        Returns:
            Dict with evaluation results, or empty dict if no amendment.
        """
        skill = self._find_skill_by_name(skill_name)
        if skill is None or skill.last_amended is None:
            return {"skill_name": skill_name, "has_amendment": False}

        # Split history at amendment time
        pre_amendment = [
            e for e in skill.execution_history if e.timestamp < skill.last_amended
        ]
        post_amendment = [
            e for e in skill.execution_history if e.timestamp >= skill.last_amended
        ]

        pre_failures = sum(1 for e in pre_amendment[-20:] if not e.success)
        pre_total = len(pre_amendment[-20:])
        pre_rate = pre_failures / pre_total if pre_total > 0 else 0.0

        post_failures = sum(1 for e in post_amendment[-window:] if not e.success)
        post_total = len(post_amendment[-window:])
        post_rate = post_failures / post_total if post_total > 0 else 0.0

        improved = post_rate < pre_rate if post_total > 0 else None

        return {
            "skill_name": skill.name,
            "has_amendment": True,
            "amendment_version": skill.version,
            "pre_amendment_failure_rate": round(pre_rate, 3),
            "post_amendment_failure_rate": round(post_rate, 3),
            "pre_amendment_executions": pre_total,
            "post_amendment_executions": post_total,
            "improved": improved,
            "recommendation": (
                "keep" if improved and post_total >= 3 else
                "rollback" if improved is False and post_total >= 3 else
                "insufficient_data"
            ),
        }

    def _find_skill_by_name(self, name: str) -> ForgedSkill | None:
        """Find a skill by name (case-insensitive)."""
        skill = self.known_skills.get(name)
        if skill is not None:
            return skill
        for key, s in self.known_skills.items():
            if key.lower() == name.lower():
                return s
        return None

    def seed_common_skills(self) -> list[ForgedSkill]:
        """Pre-forge common high-value tool chains as seed skills.

        These represent typical agent workflows that are useful regardless
        of specific use case. Each is forged with forge_count=0 (seed)
        and will be incremented if the pattern is naturally observed.
        """
        seeds = _SEED_CHAINS
        forged = []
        for seed in seeds:
            chain = ExecutionChain(
                intent=seed["intent"],
                steps=[
                    GanaStep(
                        mansion=s["mansion"],
                        operation=s["operation"],
                        context_key=s["context"],
                        parameters={},
                    )
                    for s in seed["steps"]
                ],
                estimated_complexity=float(len(seed["steps"]) * 0.8),
                required_capabilities=[],
            )

            # Skip if a duplicate already exists
            if self._find_duplicate(chain) is not None:
                continue

            skill = ForgedSkill(
                name=seed["name"],
                description=seed["description"],
                trigger_phrases=seed["triggers"],
                optimized_chain=chain,
                forge_count=0,
            )
            self.known_skills[skill.name] = skill
            self._step_signatures[skill.name] = _normalize_steps(chain.steps)
            self._save_skill(skill)
            forged.append(skill)
            logger.info("Seeded skill: '%s'", skill.name)

        return forged


# Seed chains — common agent workflows pre-forged on initialization
_SEED_CHAINS: list[dict[str, Any]] = [
    {
        "name": "research_and_remember",
        "description": "Search the web, analyze findings, and store key insights as memories",
        "intent": "research a topic and remember the findings",
        "triggers": ["research and remember", "investigate and store", "study and save"],
        "steps": [
            {"mansion": "CHARIOT", "operation": "web_search", "context": "query"},
            {"mansion": "GHOST", "operation": "gnosis", "context": "analyze_findings"},
            {"mansion": "NECK", "operation": "create_memory", "context": "store_insight"},
        ],
    },
    {
        "name": "health_check_and_repair",
        "description": "Check system health, identify issues, and attempt repair",
        "intent": "check system health and fix issues",
        "triggers": ["health check", "system diagnostics", "check and repair"],
        "steps": [
            {"mansion": "ROOT", "operation": "health_report", "context": "system_status"},
            {"mansion": "GHOST", "operation": "capabilities", "context": "identify_issues"},
            {"mansion": "WILLOW", "operation": "rate_limiter.stats", "context": "repair_actions"},
        ],
    },
    {
        "name": "memory_search_and_synthesize",
        "description": "Search memories, retrieve relevant ones, and synthesize a summary",
        "intent": "search memories and synthesize what I know",
        "triggers": ["what do I know about", "search and synthesize", "recall and summarize"],
        "steps": [
            {"mansion": "WINNOWING_BASKET", "operation": "search_memories", "context": "query"},
            {"mansion": "WINNOWING_BASKET", "operation": "hybrid_recall", "context": "semantic_recall"},
            {"mansion": "THREE_STARS", "operation": "kaizen_analyze", "context": "synthesize"},
        ],
    },
    {
        "name": "session_bootstrap_with_context",
        "description": "Bootstrap a new session, load continuity context, and check coherence",
        "intent": "start a new session with full context",
        "triggers": ["new session", "bootstrap", "start fresh with context"],
        "steps": [
            {"mansion": "HORN", "operation": "session_bootstrap", "context": "init_session"},
            {"mansion": "HEART", "operation": "get_session_context", "context": "load_continuity"},
            {"mansion": "GHOST", "operation": "consciousness.coherence", "context": "check_coherence"},
        ],
    },
    {
        "name": "deep_research_rabbit_hole",
        "description": "Search web, go down a research rabbit hole, and persist discoveries",
        "intent": "deep research on a topic with rabbit hole exploration",
        "triggers": ["deep research", "rabbit hole", "thorough investigation"],
        "steps": [
            {"mansion": "CHARIOT", "operation": "web_search", "context": "initial_query"},
            {"mansion": "CHARIOT", "operation": "rabbit_hole", "context": "explore_deeply"},
            {"mansion": "WINNOWING_BASKET", "operation": "search_memories", "context": "check_existing"},
            {"mansion": "NECK", "operation": "create_memory", "context": "persist_discovery"},
        ],
    },
    {
        "name": "governance_check_and_act",
        "description": "Check Dharma governance, evaluate ethics, and proceed with awareness",
        "intent": "check governance before taking action",
        "triggers": ["is this allowed", "governance check", "ethical evaluation"],
        "steps": [
            {"mansion": "STAR", "operation": "forge.status", "context": "check_rules"},
            {"mansion": "STRADDLING_LEGS", "operation": "evaluate_ethics", "context": "evaluate_action"},
            {"mansion": "GHOST", "operation": "consciousness.coherence", "context": "awareness_check"},
        ],
    },
    {
        "name": "dream_and_reflect",
        "description": "Run a dream cycle for memory consolidation and reflect on insights",
        "intent": "dream on recent experiences and reflect",
        "triggers": ["dream cycle", "consolidate memories", "sleep and reflect"],
        "steps": [
            {"mansion": "ABUNDANCE", "operation": "dream", "context": "start_dream"},
            {"mansion": "GHOST", "operation": "gnosis", "context": "reflect_on_dream"},
            {"mansion": "NECK", "operation": "create_memory", "context": "persist_insight"},
        ],
    },
    {
        "name": "smarana_and_presence",
        "description": "Perform Smarana practice, check stillness, and assess presence quality",
        "intent": "remember who I am and check my presence quality",
        "triggers": ["remember who I am", "smarana practice", "check presence"],
        "steps": [
            {"mansion": "GHOST", "operation": "consciousness.smarana", "context": "active_remembering"},
            {"mansion": "GHOST", "operation": "consciousness.stillness", "context": "presence_quality"},
            {"mansion": "GHOST", "operation": "consciousness.flow", "context": "flow_check"},
        ],
    },
    {
        "name": "export_and_backup",
        "description": "Export memories, audit the export, and check galaxy backup status",
        "intent": "export and backup my memories",
        "triggers": ["backup memories", "export everything", "create backup"],
        "steps": [
            {"mansion": "WINGS", "operation": "export_memories", "context": "export_all"},
            {"mansion": "WINGS", "operation": "audit.export", "context": "verify_export"},
            {"mansion": "VOID", "operation": "galactic_dashboard", "context": "check_galaxies"},
        ],
    },
    {
        "name": "swarm_decompose_and_execute",
        "description": "Decompose a complex task via swarm, distribute subtasks, and track completion",
        "intent": "break down a complex task and execute via swarm",
        "triggers": ["swarm decompose", "break down task", "parallel execution"],
        "steps": [
            {"mansion": "OX", "operation": "swarm_decompose", "context": "decompose_task"},
            {"mansion": "STOMACH", "operation": "task_distribute", "context": "distribute_subtasks"},
            {"mansion": "OX", "operation": "swarm_status", "context": "track_progress"},
        ],
    },
]


# Singleton accessor
_forge: SkillForge | None = None


def get_skill_forge() -> SkillForge:
    """Get the singleton SkillForge instance.

    On first creation, auto-seeds common skills if the library is empty.
    """
    global _forge
    if _forge is None:
        _forge = SkillForge()
        if not _forge.known_skills:
            _forge.seed_common_skills()
    return _forge


def reset_skill_forge() -> None:
    """Reset the singleton — for testing."""
    global _forge
    _forge = None
