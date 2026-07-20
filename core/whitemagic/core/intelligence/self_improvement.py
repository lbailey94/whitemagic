# ruff: noqa: BLE001
"""Recursive Self-Improvement Pipeline.

Wires together:
- ParallelReasoningTree: Explores multiple implementation approaches
- CodeGenome/GeneseedVault: Generates code from the best approach
- STRATA: Static analysis on generated code
- Monte Carlo: Scores confidence in the result
- AutonomousLearner: Persists lessons from each iteration

The pipeline:
1. ParallelReasoningTree explores approaches to the prompt
2. Best-scoring branch's strategy feeds into CodeGenome
3. CodeGenome generates code (with LLM refinement if available)
4. STRATA analyzes the generated code
5. Monte Carlo scores confidence based on STRATA findings
6. If score is low, STRATA issues feed back as revision triggers
7. Iterate up to max_iterations
8. AutonomousLearner persists lessons from each iteration

Usage:
    from whitemagic.core.intelligence.self_improvement import (
        SelfImprovementPipeline, run_self_improvement
    )

    result = run_self_improvement(
        prompt="I need a FastAPI endpoint for user authentication",
        max_iterations=3,
    )
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    """Result of a single self-improvement iteration."""

    iteration: int
    code: str = ""
    strata_issues: list[dict[str, Any]] = field(default_factory=list)
    strata_score: float = 0.0
    mc_confidence: float = 0.0
    reasoning_branch: str = ""
    reasoning_score: float = 0.0
    improved: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "code_length": len(self.code),
            "strata_issues": len(self.strata_issues),
            "strata_score": round(self.strata_score, 3),
            "mc_confidence": round(self.mc_confidence, 3),
            "reasoning_branch": self.reasoning_branch,
            "reasoning_score": round(self.reasoning_score, 3),
            "improved": self.improved,
            "timestamp": self.timestamp,
        }


@dataclass
class SelfImprovementResult:
    """Final result from the self-improvement pipeline."""

    prompt: str
    iterations: list[IterationResult] = field(default_factory=list)
    final_code: str = ""
    final_score: float = 0.0
    total_strata_issues: int = 0
    lessons_learned: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    success: bool = False
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "iterations": [i.to_dict() for i in self.iterations],
            "final_code_length": len(self.final_code),
            "final_score": round(self.final_score, 3),
            "total_strata_issues": self.total_strata_issues,
            "lessons_learned": self.lessons_learned,
            "duration_ms": round(self.duration_ms, 1),
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class SelfImprovementPipeline:
    """Recursive self-improvement pipeline for code generation.

    Combines parallel reasoning, code generation, static analysis,
    and Monte Carlo scoring into an iterative improvement loop.
    """

    def __init__(
        self,
        max_iterations: int = 3,
        score_threshold: float = 0.8,
        repo_path: str | None = None,
    ) -> None:
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.repo_path = repo_path
        self._lessons: list[str] = []

    async def run(self, prompt: str) -> SelfImprovementResult:
        """Run the self-improvement pipeline.

        Args:
            prompt: Natural language code generation prompt

        Returns:
            SelfImprovementResult with all iterations and final code
        """
        start = time.monotonic()
        result = SelfImprovementResult(prompt=prompt)

        try:
            for i in range(1, self.max_iterations + 1):
                iteration = await self._run_iteration(prompt, i, result.iterations)
                result.iterations.append(iteration)

                if iteration.strata_score >= self.score_threshold:
                    logger.info(
                        "Self-improvement converged at iteration %d (score=%.2f)",
                        i,
                        iteration.strata_score,
                    )
                    break

                if i < self.max_iterations:
                    # Feed STRATA issues back as revision context
                    prompt = self._build_revision_prompt(prompt, iteration)

            # Set final results
            if result.iterations:
                best = max(result.iterations, key=lambda x: x.strata_score)
                result.final_code = best.code
                result.final_score = best.strata_score
                result.total_strata_issues = sum(
                    len(i.strata_issues) for i in result.iterations
                )
                result.success = result.final_score >= self.score_threshold

            # Persist lessons
            self._persist_lessons()

        except Exception as e:
            result.error = str(e)
            logger.error("Self-improvement pipeline error: %s", e, exc_info=True)

        result.duration_ms = (time.monotonic() - start) * 1000
        result.lessons_learned = list(self._lessons)
        return result

    async def _run_iteration(
        self,
        prompt: str,
        iteration_num: int,
        previous_iterations: list[IterationResult],
    ) -> IterationResult:
        """Run a single iteration of the pipeline."""
        result = IterationResult(iteration=iteration_num)

        reasoning_result = await self._run_reasoning(prompt)
        result.reasoning_branch = reasoning_result.get("best_branch", "")
        result.reasoning_score = reasoning_result.get("best_score", 0.0)

        code = self._generate_code(prompt, reasoning_result)
        result.code = code

        if not code:
            return result

        strata_result = self._run_strata(code)
        result.strata_issues = strata_result.get("issues", [])
        result.strata_score = strata_result.get("score", 0.5)

        result.mc_confidence = self._run_monte_carlo(
            result.strata_score, len(result.strata_issues)
        )

        if previous_iterations:
            prev_best = max(previous_iterations, key=lambda x: x.strata_score)
            result.improved = result.strata_score > prev_best.strata_score
        else:
            result.improved = True

        self._extract_lessons(result)

        return result

    async def _run_reasoning(self, prompt: str) -> dict[str, Any]:
        """Run ParallelReasoningTree to explore implementation approaches."""
        try:
            from whitemagic.core.intelligence.parallel_reasoning import (
                ParallelReasoningTree,
            )

            tree = ParallelReasoningTree(question=f"Best approach for: {prompt}")
            result = await tree.explore(max_branches=4, max_depth=4)

            return {
                "best_branch": result.best_branch_id,
                "best_score": max(b.score for b in result.branches)
                if result.branches
                else 0.0,
                "synthesis": result.synthesis[:500],
                "branch_count": len(result.branches),
            }
        except Exception as e:
            logger.debug("Reasoning step skipped: %s", e)
            return {
                "best_branch": "default",
                "best_score": 0.5,
                "synthesis": "",
                "branch_count": 0,
            }

    def _generate_code(self, prompt: str, reasoning: dict[str, Any]) -> str:
        """Generate code using CodeGenome/GeneseedVault."""
        try:
            from whitemagic.codegenome.vault import get_geneseed_vault

            vault = get_geneseed_vault()

            # Use reasoning synthesis as additional context
            synthesis = reasoning.get("synthesis", "")
            enhanced_prompt = f"{prompt}" + (
                f"\nContext: {synthesis[:200]}" if synthesis else ""
            )

            result = vault.vibe_render(enhanced_prompt)
            if result.get("status") == "success":
                return result.get("code", "")
            return ""
        except Exception as e:
            logger.debug("Code generation skipped: %s", e)
            return ""

    def _run_strata(self, code: str) -> dict[str, Any]:
        """Run STRATA static analysis on generated code."""
        try:
            from whitemagic.core.ports import get_strata

            # Write code to temp file for analysis
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_path = f.name

            Strata = get_strata()
            strata = Strata(Path(temp_path))
            report = strata.analyze()

            issues = []
            if hasattr(report, "issues"):
                for issue in report.issues[:20]:
                    issues.append(
                        {
                            "rule": getattr(issue, "rule", "unknown"),
                            "message": getattr(issue, "message", ""),
                            "severity": getattr(issue, "severity", "info"),
                        }
                    )

            # Score: fewer issues = higher score
            issue_count = len(issues)
            score = max(0.0, 1.0 - (issue_count * 0.1))

            import os

            os.unlink(temp_path)

            return {"issues": issues, "score": score, "issue_count": issue_count}
        except Exception as e:
            logger.debug("STRATA analysis skipped: %s", e)
            return {"issues": [], "score": 0.5, "issue_count": 0}

    def _run_monte_carlo(self, strata_score: float, issue_count: int) -> float:
        """Run Monte Carlo confidence scoring on the generated code."""
        try:
            from whitemagic.forecasting.mc_integration import MCForecastEnhancer

            enhancer = MCForecastEnhancer()
            # Create a claim representing our confidence in the code
            claims = [
                {
                    "id": f"codegen_{int(time.time())}",
                    "claim": "Generated code meets quality standards",
                    "confidence": strata_score,
                    "outcome": 1.0 if strata_score >= 0.7 else 0.0,
                    "status": "validated" if strata_score >= 0.7 else "falsified",
                    "category": "code_quality",
                }
            ]

            result = enhancer.run_calibrated(claims, n_trials=1000)
            mc_result = result.get("mc_result", {})
            bss = mc_result.get("brier_skill_score", {}).get("mean", 0.0)
            confidence = max(0.0, min(1.0, (bss + 1.0) / 2.0))
            return confidence
        except Exception as e:
            logger.debug("Monte Carlo scoring skipped: %s", e)
            return strata_score

    def _build_revision_prompt(
        self, original_prompt: str, iteration: IterationResult
    ) -> str:
        """Build a revised prompt incorporating STRATA feedback."""
        issues_text = "; ".join(
            f"{i.get('rule', '')}: {i.get('message', '')[:60]}"
            for i in iteration.strata_issues[:5]
        )
        return f"{original_prompt}\n\nFix these issues from previous iteration: {issues_text}"

    def _extract_lessons(self, iteration: IterationResult) -> None:
        """Extract lessons from an iteration."""
        if iteration.improved:
            self._lessons.append(
                f"Iteration {iteration.iteration}: Improved score to {iteration.strata_score:.2f}"
            )
        else:
            self._lessons.append(
                f"Iteration {iteration.iteration}: Score {iteration.strata_score:.2f} did not improve"
            )

        if iteration.strata_issues:
            top_issue = iteration.strata_issues[0]
            self._lessons.append(
                f"Common issue: {top_issue.get('rule', 'unknown')} - {top_issue.get('message', '')[:80]}"
            )

    def _persist_lessons(self) -> None:
        """Persist lessons to AutonomousLearner."""
        try:
            from whitemagic.core.patterns.pattern_consciousness.autonomous_learner import (
                get_autonomous_learner,
            )

            learner = get_autonomous_learner()
            for lesson in self._lessons:
                if "Improved" in lesson:
                    learner.learn_from_success(lesson, lesson)
                else:
                    learner.learn_from_mistake(lesson, lesson)
        except Exception as e:
            logger.debug("Lesson persistence skipped: %s", e)


def run_self_improvement(
    prompt: str,
    max_iterations: int = 3,
    score_threshold: float = 0.8,
    repo_path: str | None = None,
) -> dict[str, Any]:
    """Run the self-improvement pipeline synchronously.

    Args:
        prompt: Natural language code generation prompt
        max_iterations: Maximum improvement iterations
        score_threshold: Score at which to stop iterating
        repo_path: Optional repo path for context

    Returns:
        Dict with final code, score, iterations, and lessons
    """
    pipeline = SelfImprovementPipeline(
        max_iterations=max_iterations,
        score_threshold=score_threshold,
        repo_path=repo_path,
    )

    try:
        asyncio.get_running_loop()
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(asyncio.run, pipeline.run(prompt)).result()
    except RuntimeError:
        result = asyncio.run(pipeline.run(prompt))

    return result.to_dict()
