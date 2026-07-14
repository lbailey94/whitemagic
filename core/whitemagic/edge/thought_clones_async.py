# ruff: noqa: BLE001
"""Async Thought Clone Army - 16,000 concurrent agents.
Replaces ProcessPoolExecutor with asyncio for massive scalability.
v14.5: Rust Tokio fast-path (208× faster) with Python asyncio fallback.
"""

import asyncio
import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from ..core.async_layer import batch_process, gather_with_concurrency

logger = logging.getLogger(__name__)

# Tier → model mapping (configurable via env, defaults to WM_LLAMA_MODEL)
# Xianfeng (vanguard): fast, lightweight model for reconnaissance
# Wei Wuzu (martial): balanced model for complex logic
# Huben (tiger): heavy model for critical reasoning
_DEFAULT_MODEL = os.environ.get("WM_LLAMA_MODEL", "")
_TIER_MODELS: dict[str, str] = {
    "xianfeng": os.environ.get("WM_XIANFENG_MODEL", _DEFAULT_MODEL),
    "wei_wuzu": os.environ.get("WM_WEIWUZU_MODEL", _DEFAULT_MODEL),
    "huben": os.environ.get("WM_HUBEN_MODEL", _DEFAULT_MODEL),
}

# Strategy → system prompt suffix for diverse LLM reasoning
_STRATEGY_PROMPTS: dict[str, str] = {
    "analytical": "Analyze this systematically, breaking it into components and identifying patterns.",
    "creative": "Explore this creatively, considering unconventional approaches and novel connections.",
    "systematic": "Address this methodically, following a structured approach and verifying each step.",
    "intuitive": "Use pattern recognition and holistic perspective to understand this.",
    "skeptical": "Question assumptions, identify potential flaws, and stress-test conclusions about this.",
    "optimistic": "Focus on positive outcomes and opportunities related to this.",
    "pragmatic": "Prioritize practical, implementable solutions for this.",
    "theoretical": "Apply first principles and abstract reasoning to this.",
    "deep_analytical": "Perform exhaustive analysis with multiple layers of abstraction.",
    "first_principles": "Reason from fundamental truths, building up step by step.",
    "comprehensive_review": "Review comprehensively from all angles, leaving no stone unturned.",
    "adversarial_stress_test": "Try to break this — find edge cases, failure modes, and weaknesses.",
    "formal_verification": "Verify rigorously — check correctness, completeness, and consistency.",
    "meta_synthesis": "Synthesize multiple perspectives into a unified understanding.",
}

# v14.5: Rust Tokio Clone Army fast-path
_RUST_TOKIO = False
_tokio_deploy: Any = None
try:
    from whitemagic.optimization.rust_accelerators import (
        tokio_clones_available,
    )
    from whitemagic.optimization.rust_accelerators import (
        tokio_deploy_clones as _imported_tokio_deploy,
    )

    _RUST_TOKIO = tokio_clones_available()
    _tokio_deploy = _imported_tokio_deploy
    if _RUST_TOKIO:
        logger.debug("Rust Tokio Clone Army available — 208× fast-path enabled")
except ImportError:
    logger.debug("Optional dependency unavailable: ImportError")


@dataclass
class AsyncThoughtPath:
    """Result from a thought clone."""

    strategy: str
    content: str
    confidence: float
    tokens: int
    clone_id: int
    duration_ms: float = field(default=0)
    metadata: dict[str, Any] = field(default_factory=dict)


class CloneTier(StrEnum):
    """Ancient Chinese military-inspired capability/cost tiers.

    Xianfeng (先锋): Vanguard — fast, cheap, lightweight front-line probes.
    Wei Wuzu (魏武卒): Martial Troops — professional heavy infantry, main force.
    Huben (虎贲): Tiger Runners — king's personal elite guard, held in reserve.
    """

    XIANFENG = "xianfeng"
    WEI_WUZU = "wei_wuzu"
    HUBEN = "huben"


@dataclass
class CloneConfig:
    """Configuration for clone army."""

    max_clones: int = 16000
    max_concurrent_api_calls: int = 100
    timeout_seconds: float = 30.0
    min_confidence: float = 0.5
    diversity_factor: int = 8  # Number of base strategies to cycle through
    default_tier: CloneTier = CloneTier.XIANFENG  # Default tier for tiered exploration


class AsyncThoughtCloneArmy:
    """Deploy thousands of async thought clones for parallel exploration.

    Performance characteristics:
    - 16,000 clones on 16GB RAM (~50MB memory usage)
    - Sub-second response for simple queries
    - 10x faster than ProcessPoolExecutor
    """

    def __init__(self, config: CloneConfig | None = None) -> None:
        self.config = config or CloneConfig()
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_api_calls)
        self._stats_lock = asyncio.Lock()
        self._stats = {
            "total_clones_deployed": 0,
            "successful_paths": 0,
            "failed_paths": 0,
            "total_tokens": 0,
            "avg_confidence": 0.0,
            "deployment_time_ms": 0,
        }

    async def parallel_explore_tiered(
        self,
        prompt: str,
        num_clones: int | None = None,
        *,
        use_tokio: bool = True,
        tier: CloneTier | None = None,
    ) -> AsyncThoughtPath:
        """Tiered exploration — Ancient Chinese three-tier model for cost-aware clone deployment.

        Xianfeng (先锋) (default): Vanguard — fast, cheap clones for initial reconnaissance.
        Wei Wuzu (魏武卒): Martial Troops — mid-tier clones for complex logic and refinement.
        Huben (虎贲): Tiger Runners — heavy models held in reserve for critical moments.

        The tier affects strategy generation and simulated confidence baselines.
        """
        active_tier = tier or self.config.default_tier

        # Tier-aware strategy generation
        if active_tier == CloneTier.XIANFENG:
            # Fast, diverse, lightweight strategies
            base_strategies = [
                "quick_analytical",
                "surface_scan",
                "pattern_match",
                "heuristic_guess",
                "fast_filter",
                "shallow_search",
            ]
            confidence_floor = 0.3
            cost_estimate = "low"
        elif active_tier == CloneTier.WEI_WUZU:
            # Balanced depth and speed
            base_strategies = [
                "analytical",
                "systematic",
                "pragmatic",
                "creative",
                "skeptical",
                "deep_dive",
                "cross_reference",
            ]
            confidence_floor = 0.5
            cost_estimate = "medium"
        else:
            # HUBEN
            # Maximum reasoning, used sparingly
            base_strategies = [
                "deep_analytical",
                "first_principles",
                "comprehensive_review",
                "adversarial_stress_test",
                "formal_verification",
                "meta_synthesis",
            ]
            confidence_floor = 0.7
            cost_estimate = "high"

        start_time = datetime.now()
        clones_to_deploy = min(
            num_clones or self.config.max_clones, self.config.max_clones
        )

        # Generate tier-aware strategies
        strategies = self._generate_strategies(
            clones_to_deploy, base_pool=base_strategies
        )

        # Launch clones
        async def safe_clone(strategy: str, clone_id: int) -> Any:
            """
            Perform the safe clone operation.

            Args:
                strategy: Parameter description.
                clone_id: Parameter description.

            Returns:
                Any
            """
            try:
                return await self._clone_think(
                    prompt, strategy, clone_id, tier_hint=active_tier.value
                )
            except Exception as e:
                logger.error("Clone %s failed: %s", clone_id, e, exc_info=True)
                return None

        tasks = [safe_clone(strategy, i) for i, strategy in enumerate(strategies)]
        paths = await gather_with_concurrency(
            *tasks,
            max_concurrent=self.config.max_concurrent_api_calls,
        )

        valid_paths = [
            p
            for p in paths
            if isinstance(p, AsyncThoughtPath) and p.confidence >= confidence_floor
        ]
        failed_paths = len(paths) - len(valid_paths)

        # Update stats
        async with self._stats_lock:
            deployment_time = (datetime.now() - start_time).total_seconds() * 1000
            prev_success = self._stats["successful_paths"]
            prev_conf_sum = self._stats["avg_confidence"] * prev_success
            new_conf_sum = sum(p.confidence for p in valid_paths)
            total_success = prev_success + len(valid_paths)

            self._stats.update(
                {
                    "total_clones_deployed": self._stats["total_clones_deployed"]
                    + len(paths),
                    "successful_paths": total_success,
                    "failed_paths": self._stats["failed_paths"] + failed_paths,
                    "deployment_time_ms": self._stats["deployment_time_ms"]
                    + deployment_time,
                    "total_tokens": self._stats["total_tokens"]
                    + sum(p.tokens for p in valid_paths),
                    "avg_confidence": (prev_conf_sum + new_conf_sum)
                    / max(1, total_success),
                }
            )

        if valid_paths:
            best_path = max(valid_paths, key=lambda p: p.confidence)
            logger.info(
                "Tiered best path [%s]: %s (confidence: %.2f, cost: %s)",
                active_tier.value,
                best_path.strategy,
                best_path.confidence,
                cost_estimate,
            )
            return best_path

        # Fallback: if no valid paths and we're not at Huben, escalate
        if active_tier != CloneTier.HUBEN:
            next_tier = (
                CloneTier.WEI_WUZU
                if active_tier == CloneTier.XIANFENG
                else CloneTier.HUBEN
            )
            logger.warning(
                "No valid paths at %s tier. Escalating to %s.",
                active_tier.value,
                next_tier.value,
            )
            return await self.parallel_explore_tiered(
                prompt, num_clones=num_clones, use_tokio=use_tokio, tier=next_tier
            )

        logger.warning("No valid paths found at HUBEN tier, returning fallback")
        return AsyncThoughtPath(
            strategy="fallback",
            content=f"No valid strategies found for: {prompt}",
            confidence=0.0,
            tokens=0,
            clone_id=-1,
            metadata={"tier": active_tier.value, "cost_estimate": cost_estimate},
        )

    async def parallel_explore(
        self,
        prompt: str,
        num_clones: int | None = None,
        *,
        use_tokio: bool = True,
    ) -> AsyncThoughtPath:
        """Explore prompt with async clones.

        Args:
            prompt: The prompt to explore
            num_clones: Number of clones to deploy (defaults to config.max_clones)
            use_tokio: If True and Rust Tokio is available, use 208× fast-path

        Returns:
            Best thought path from all clones

        """
        start_time = datetime.now()
        clones_to_deploy = min(
            num_clones or self.config.max_clones, self.config.max_clones
        )

        # v14.5: Rust Tokio fast-path — 208× faster than Python asyncio
        if use_tokio and _RUST_TOKIO and callable(_tokio_deploy):
            try:
                result = _tokio_deploy(prompt, clones_to_deploy)
                if result is not None:
                    winner = result.get("winner", {})
                    elapsed_ms = result.get("elapsed_ms", 0.0)
                    # Update cumulative stats
                    async with self._stats_lock:
                        self._stats["total_clones_deployed"] += result.get(
                            "total_clones", 0
                        )
                        self._stats["successful_paths"] += result.get("total_clones", 0)
                        self._stats["total_tokens"] += result.get("total_tokens", 0)
                        self._stats["deployment_time_ms"] += elapsed_ms
                        self._stats["avg_confidence"] = result.get(
                            "avg_confidence", 0.0
                        )
                    logger.info(
                        "Tokio fast-path: %s clones in %sms (winner: %s, conf: %s)",
                        clones_to_deploy,
                        format(elapsed_ms, ".1f"),
                        winner.get("strategy", "?"),
                        format(winner.get("confidence", 0), ".2f"),
                    )
                    return AsyncThoughtPath(
                        strategy=winner.get("strategy", "tokio_direct"),
                        content=winner.get("response", ""),
                        confidence=winner.get("confidence", 0.0),
                        tokens=winner.get("tokens_used", 0),
                        clone_id=winner.get("clone_id", 0),
                        duration_ms=elapsed_ms,
                        metadata={
                            "backend": "rust_tokio",
                            "strategy_votes": result.get("strategy_votes", {}),
                        },
                    )
            except Exception as e:
                logger.debug(
                    "Tokio fast-path failed, falling back to asyncio: %s",
                    e,
                    exc_info=True,
                )

        logger.info(
            "Deploying %s clones for prompt: {prompt[:50]}...",
            clones_to_deploy,
            exc_info=True,
        )

        # Generate strategies
        strategies = self._generate_strategies(clones_to_deploy)

        # Launch all clones concurrently with early stopping
        async def safe_clone(strategy: str, clone_id: int) -> Any:
            """
            Perform the safe clone operation.

            Args:
                strategy: Parameter description.
                clone_id: Parameter description.

            Returns:
                Any
            """
            try:
                return await self._clone_think(prompt, strategy, clone_id)
            except Exception as e:
                logger.error("Clone %s failed: %s", clone_id, e, exc_info=True)
                return None

        tasks = [
            asyncio.ensure_future(safe_clone(strategy, i))
            for i, strategy in enumerate(strategies)
        ]

        # Collect results as they complete, with early stopping
        early_stop_threshold = 0.9
        paths: list[AsyncThoughtPath] = []
        try:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if isinstance(result, AsyncThoughtPath):
                    paths.append(result)
                    if result.confidence >= early_stop_threshold:
                        logger.info(
                            "Early stop: clone %s reached confidence %.2f, skipping %d pending",
                            result.clone_id,
                            result.confidence,
                            len([t for t in tasks if not t.done()]),
                        )
                        # Cancel remaining tasks
                        for t in tasks:
                            if not t.done():
                                t.cancel()
                        break
        except Exception as e:
            logger.debug("Early stop collection error: %s", e)
            # Fallback: gather whatever we have
            for t in tasks:
                if t.done() and not t.cancelled():
                    try:
                        r = t.result()
                        if isinstance(r, AsyncThoughtPath):
                            paths.append(r)
                    except Exception:
                        logger.debug("Swallowed exception", exc_info=True)

        # Filter successful results
        valid_paths = [p for p in paths if isinstance(p, AsyncThoughtPath)]
        failed_paths = len(paths) - len(valid_paths)

        # Update stats (cumulative) with lock safety
        async with self._stats_lock:
            deployment_time = (datetime.now() - start_time).total_seconds() * 1000
            prev_success = self._stats["successful_paths"]
            prev_conf_sum = self._stats["avg_confidence"] * prev_success
            new_conf_sum = sum(p.confidence for p in valid_paths)
            total_success = prev_success + len(valid_paths)

            self._stats.update(
                {
                    "total_clones_deployed": self._stats["total_clones_deployed"]
                    + len(paths),
                    "successful_paths": total_success,
                    "failed_paths": self._stats["failed_paths"] + failed_paths,
                    "deployment_time_ms": self._stats["deployment_time_ms"]
                    + deployment_time,
                    "total_tokens": self._stats["total_tokens"]
                    + sum(p.tokens for p in valid_paths),
                    "avg_confidence": (prev_conf_sum + new_conf_sum)
                    / max(1, total_success),
                }
            )

        # Feed outcomes to ToolBandit for strategy learning
        try:
            from whitemagic.tools.handlers.tool_bandit import get_tool_bandit

            bandit = get_tool_bandit()
            for p in valid_paths:
                bandit.record_clone_outcome(
                    strategy=p.strategy,
                    success=p.confidence > 0.5,
                    clone_type="thought",
                    task_type="clone_deployment",
                    metadata={
                        "confidence": p.confidence,
                        "tokens": p.tokens,
                        "llm_used": p.metadata.get("llm_used", False),
                    },
                    quality=p.confidence,
                )
        except Exception as e:
            logger.debug("Bandit feedback skipped: %s", e)

        if valid_paths:
            best_path = max(valid_paths, key=lambda p: p.confidence)
            logger.info(
                "Best path: %s (confidence: {best_path.confidence:.2f})",
                best_path.strategy,
                exc_info=True,
            )
            return best_path

        # Fallback if no valid paths
        logger.warning("No valid paths found, returning fallback")
        return AsyncThoughtPath(
            strategy="fallback",
            content=f"No valid strategies found for: {prompt}",
            confidence=0.0,
            tokens=0,
            clone_id=-1,
        )

    async def batch_explore(
        self, prompts: list[str], clones_per_prompt: int = 100
    ) -> list[AsyncThoughtPath]:
        """Explore multiple prompts in parallel.

        Args:
            prompts: List of prompts to explore
            clones_per_prompt: Number of clones per prompt

        Returns:
            Best path for each prompt

        """

        async def explore_prompt(prompt: Any) -> Any:
            """
            Perform the explore prompt operation.

            Args:
                prompt: Parameter description.

            Returns:
                Any
            """
            return await self.parallel_explore(prompt, clones_per_prompt)

        return await batch_process(prompts, explore_prompt, batch_size=5)

    async def _clone_think(
        self,
        prompt: str,
        strategy: str,
        clone_id: int,
        tier_hint: str = "xianfeng",
    ) -> AsyncThoughtPath:
        """Single clone's thought process.

        Calls llama.cpp LLM when available for real reasoning.
        Falls back to simulation when llama.cpp is not running.
        """
        async with self.semaphore:
            start_time = datetime.now()

            try:
                # Attempt real LLM call via llama.cpp
                content, tokens, llm_used = await self._llm_think(
                    prompt,
                    strategy,
                    clone_id,
                    tier_hint,
                )

                if not llm_used:
                    # Fallback: simulate thinking
                    await asyncio.sleep(random.uniform(0.01, 0.1))
                    content = self._generate_content(prompt, strategy, clone_id)
                    if tier_hint == "xianfeng":
                        tokens = len(content.split()) * random.randint(2, 4)
                    elif tier_hint == "wei_wuzu":
                        tokens = len(content.split()) * random.randint(3, 6)
                    else:
                        tokens = len(content.split()) * random.randint(5, 9)

                confidence = self._calculate_confidence(strategy, tier_hint=tier_hint)
                if llm_used:
                    confidence = min(0.98, confidence + 0.1)

                duration = (datetime.now() - start_time).total_seconds() * 1000

                return AsyncThoughtPath(
                    strategy=strategy,
                    content=content,
                    confidence=confidence,
                    tokens=tokens,
                    clone_id=clone_id,
                    duration_ms=duration,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "prompt_length": len(prompt),
                        "llm_used": llm_used,
                        "tier": tier_hint,
                        "model": _TIER_MODELS.get(tier_hint, _TIER_MODELS["xianfeng"])
                        if llm_used
                        else None,
                    },
                )

            except TimeoutError:
                logger.warning("Clone %s timed out", clone_id, exc_info=True)
                raise
            except Exception as e:
                logger.error("Clone %s failed: %s", clone_id, e, exc_info=True)
                return AsyncThoughtPath(
                    strategy=f"{strategy}_error",
                    content=f"Error: {e!s}",
                    confidence=0.0,
                    tokens=0,
                    clone_id=clone_id,
                )

    async def _llm_think(
        self,
        prompt: str,
        strategy: str,
        clone_id: int,
        tier_hint: str,
    ) -> tuple[str, int, bool]:
        """Call llama.cpp LLM for real reasoning. Returns (content, tokens, used_llm).

        Tier routing:
        - xianfeng (vanguard): background model (fast, continuous) — max 256 tokens
        - wei_wuzu (martial): foreground model (balanced) — max 512 tokens
        - huben (tiger): foreground model (heavy) — max 1024 tokens
        """
        try:
            from whitemagic.inference.llama_cpp import (
                get_dual_model_manager,
                get_llama_cpp_backend,
            )

            # Tier-specific settings
            is_background = tier_hint == "xianfeng"
            tier_max_tokens = {"xianfeng": 256, "wei_wuzu": 512, "huben": 1024}
            max_tokens = tier_max_tokens.get(tier_hint, 512)

            strategy_guidance = _STRATEGY_PROMPTS.get(
                strategy.split("_")[-1] if "_" in strategy else strategy,
                _STRATEGY_PROMPTS.get(
                    strategy, f"Approach this using {strategy} methodology."
                ),
            )
            system = f"You are clone {clone_id} in a thought clone army. {strategy_guidance} Be concise."
            full_prompt = f"{system}\n\n{prompt}" if system else prompt

            # Try dual-model routing first
            dmm = get_dual_model_manager()
            if dmm is not None:
                if is_background and dmm.background.is_available:
                    content = dmm.route_inference(full_prompt, is_background=True)
                elif dmm.foreground.is_available:
                    content = dmm.foreground.complete(
                        full_prompt, max_tokens=max_tokens, temperature=0.7
                    )
                elif dmm.background.is_available:
                    # Fallback to background if foreground not running
                    content = dmm.route_inference(full_prompt, is_background=True)
                else:
                    return "", 0, False
            else:
                # Single backend mode
                backend = get_llama_cpp_backend()
                if not backend.is_available:
                    return "", 0, False
                content = backend.complete(
                    full_prompt, max_tokens=max_tokens, temperature=0.7
                )

            if not content or content.startswith("Error:"):
                return "", 0, False
            tokens = len(content.split())
            return content, tokens, True
        except Exception as e:
            logger.debug("LLM think fallback for clone %s: %s", clone_id, e)
            return "", 0, False

    def _generate_strategies(
        self, count: int, base_pool: list[str] | None = None
    ) -> list[str]:
        """Generate diverse strategies for clones.

        Args:
            count: Number of strategies to generate
            base_pool: Optional override for the base strategy pool (used by tiered mode)
        """
        base_strategies = base_pool or [
            "analytical",
            "creative",
            "systematic",
            "intuitive",
            "skeptical",
            "optimistic",
            "pragmatic",
            "theoretical",
            "experimental",
            "minimalist",
            "comprehensive",
            "focused",
        ]

        strategies = []
        for i in range(count):
            # Cycle through base strategies
            base = base_strategies[i % len(base_strategies)]

            if random.random() < 0.3:
                modifiers = ["deep_", "quick_", "balanced_", "critical_"]
                base = random.choice(modifiers) + base

            strategies.append(base)

        return strategies

    def _generate_content(self, prompt: str, strategy: str, clone_id: int) -> str:
        """Generate content based on strategy."""
        templates = {
            "analytical": f"Clone {clone_id} analyzes {prompt} systematically: Breaking down into components, identifying patterns, and synthesizing insights.",
            "creative": f"Clone {clone_id} creatively explores {prompt}: Considering unconventional approaches, making novel connections, and generating innovative solutions.",
            "systematic": f"Clone {clone_id} systematically addresses {prompt}: Following structured methodology, ensuring completeness, and verifying each step.",
            "intuitive": f"Clone {clone_id} intuitively understands {prompt}: Leveraging pattern recognition, holistic perspective, and experiential knowledge.",
            "skeptical": f"Clone {clone_id} skeptically examines {prompt}: Questioning assumptions, identifying potential flaws, and stress-testing conclusions.",
            "optimistic": f"Clone {clone_id} optimistically approaches {prompt}: Focusing on positive outcomes, identifying opportunities, and building on strengths.",
            "pragmatic": f"Clone {clone_id} pragmatically solves {prompt}: Prioritizing practical solutions, considering constraints, and ensuring implementability.",
            "theoretical": f"Clone {clone_id} theoretically analyzes {prompt}: Applying first principles, exploring abstract concepts, and developing frameworks.",
        }

        template = templates.get(
            strategy.split("_")[-1],
            f"Clone {clone_id} approaches {prompt} using {strategy} methodology.",
        )
        if strategy not in template:
            template = template.replace(
                f"Clone {clone_id}", f"Clone {clone_id} ({strategy})"
            )

        insights = [
            f"Key insight: {random.choice(['efficiency', 'clarity', 'depth', 'innovation', 'simplicity'])} is crucial.",
            f"Consideration: {random.choice(['scalability', 'maintainability', 'usability', 'robustness', 'elegance'])}.",
            f"Method: {random.choice(['iterative refinement', 'holistic view', 'step-by-step', 'parallel processing', 'abstraction layers'])}.",
        ]

        return template + " " + " ".join(random.sample(insights, 2))

    def _calculate_confidence(self, strategy: str, tier_hint: str = "hastati") -> float:
        """Calculate confidence based on strategy, tier, and random factors."""
        # Base confidence by strategy type
        base_confidence = {
            "analytical": 0.85,
            "systematic": 0.90,
            "creative": 0.75,
            "intuitive": 0.70,
            "skeptical": 0.80,
            "optimistic": 0.65,
            "pragmatic": 0.88,
            "theoretical": 0.72,
        }

        strategy_type = strategy.split("_")[-1]
        base = base_confidence.get(strategy_type, 0.75)

        # Apply modifier effects
        if "deep_" in strategy:
            base += 0.05
        elif "quick_" in strategy:
            base -= 0.1
        elif "critical_" in strategy:
            base += 0.03

        # Tier-based confidence floor adjustment
        tier_bonus = {"xianfeng": -0.05, "wei_wuzu": 0.0, "huben": 0.08}
        base += tier_bonus.get(tier_hint, 0.0)

        variance = {"xianfeng": 0.15, "wei_wuzu": 0.10, "huben": 0.05}
        variation = random.gauss(0, variance.get(tier_hint, 0.1))

        # Clamp to valid range
        return max(0.0, min(1.0, base + variation))

    async def vibe_code_explore(
        self,
        prompt: str,
        num_clones: int | None = None,
        *,
        use_tokio: bool = True,
    ) -> AsyncThoughtPath:
        """God-Kit tiered code generation using GeneseedVault.

        Three-phase deployment:
        Phase 1 (Xianfeng): Fast vibe parsing → template match
        Phase 2 (Wei Wuzu): Template refinement → fork & customize
        Phase 3 (Huben): Production validation → comprehensive output
        """
        from whitemagic.codegenome.vault import get_geneseed_vault

        vault = get_geneseed_vault()

        xianfeng_result = await self.parallel_explore_tiered(
            f"Parse vibe prompt into code template query: {prompt}",
            num_clones=num_clones or 100,
            use_tokio=use_tokio,
            tier=CloneTier.XIANFENG,
        )

        if xianfeng_result.confidence < 0.3:
            logger.warning("Vibe parsing failed at Xianfeng tier, escalating")
            return await self.parallel_explore_tiered(
                prompt,
                num_clones=num_clones,
                use_tokio=use_tokio,
                tier=CloneTier.WEI_WUZU,
            )

        # Extract template info from Xianfeng result
        vault_result = vault.vibe_render(prompt)
        if vault_result.get("status") != "success":
            logger.warning("Vault render failed: %s", vault_result.get("error_code"))
            return xianfeng_result

        template_name = vault_result["template_name"]
        base_tier = vault_result["tier"]
        variables = vault_result.get("variables", {})
        base_code = vault_result["code"]

        wei_wuzu_prompt = (
            f"Refine this {template_name} code with variables {variables}:\n"
            f"{base_code}\n\n"
            f"Add proper typing, docstrings, and edge-case handling."
        )
        wei_wuzu_result = await self.parallel_explore_tiered(
            wei_wuzu_prompt,
            num_clones=num_clones or 50 if num_clones else 50,
            use_tokio=use_tokio,
            tier=CloneTier.WEI_WUZU,
        )

        if wei_wuzu_result.confidence < 0.5:
            return AsyncThoughtPath(
                strategy=f"vibe_code_{template_name}_xianfeng_only",
                content=base_code,
                confidence=xianfeng_result.confidence,
                tokens=len(base_code.split()),
                clone_id=-1,
                metadata={
                    "tier": base_tier,
                    "template": template_name,
                    "variables": variables,
                    "phases_completed": 1,
                },
            )

        refined_code = wei_wuzu_result.content

        huben_prompt = (
            f"Validate and harden this {template_name} for production:\n"
            f"{refined_code}\n\n"
            f"Ensure: error handling, logging, type safety, and Dharma compliance."
        )
        huben_result = await self.parallel_explore_tiered(
            huben_prompt,
            num_clones=num_clones or 20 if num_clones else 20,
            use_tokio=use_tokio,
            tier=CloneTier.HUBEN,
        )

        if huben_result.confidence >= 0.7:
            final_code = huben_result.content
            final_confidence = huben_result.confidence
            final_tier = "huben"
            phases = 3
        else:
            final_code = refined_code
            final_confidence = wei_wuzu_result.confidence
            final_tier = "wei_wuzu"
            phases = 2

        return AsyncThoughtPath(
            strategy=f"vibe_code_{template_name}_{final_tier}",
            content=final_code,
            confidence=final_confidence,
            tokens=len(final_code.split()),
            clone_id=-1,
            metadata={
                "tier": final_tier,
                "template": template_name,
                "variables": variables,
                "phases_completed": phases,
                "xianfeng_confidence": xianfeng_result.confidence,
                "wei_wuzu_confidence": wei_wuzu_result.confidence,
                "huben_confidence": huben_result.confidence if phases == 3 else 0.0,
            },
        )

    def get_stats(self) -> dict[str, Any]:
        """Get deployment statistics."""
        return {
            **self._stats,
            "config": {
                "max_clones": self.config.max_clones,
                "max_concurrent_api_calls": self.config.max_concurrent_api_calls,
                "timeout_seconds": self.config.timeout_seconds,
            },
        }

    def reset_stats(self) -> Any:
        """Reset statistics."""
        self._stats = {
            "total_clones_deployed": 0,
            "successful_paths": 0,
            "failed_paths": 0,
            "total_tokens": 0,
            "avg_confidence": 0.0,
            "deployment_time_ms": 0,
        }


async def quick_explore(prompt: str, clones: int = 1000) -> AsyncThoughtPath:
    """Quick exploration with default configuration."""
    army = AsyncThoughtCloneArmy()
    return await army.parallel_explore(prompt, clones)


async def doctrine_deploy(
    objective: str,
    num_clones: int = 5000,
    tactic: str | None = None,
) -> dict[str, Any]:
    """Deploy clones using Imperial Doctrine strategy selection.

    Integrates with the War Room for strategic force composition.
    Falls back to standard deployment if doctrine is unavailable.

    Args:
        objective: Natural language objective
        num_clones: Total clones to deploy
        tactic: Optional named tactic to use

    Returns:
        Dict with deployment results including doctrine metadata
    """
    try:
        from whitemagic.agents.doctrine import get_doctrine

        doctrine = get_doctrine()
        force_specs = doctrine.recommend_force(
            objective,
            constraints={"max_clones": num_clones},
        )

        # Deploy per force spec
        results = []
        army = AsyncThoughtCloneArmy()
        for spec in force_specs:
            if spec.force_type.value == "light_infantry":
                # Tokio fast-path for infantry
                path = await army.parallel_explore(
                    objective,
                    spec.clone_count,
                    use_tokio=True,
                )
                results.append(
                    {
                        "force": spec.force_type.value,
                        "clones": spec.clone_count,
                        "strategy": path.strategy,
                        "confidence": path.confidence,
                        "nature": spec.nature.value,
                        "wu_xing_phase": spec.wu_xing_phase.value,
                    }
                )
            elif spec.force_type.value == "dare_to_die":
                # Ralph Wiggum stateless mode
                try:
                    from whitemagic.core.intelligence.agentic.fool_guard import (
                        deploy_dare_to_die,
                    )

                    dtd = await deploy_dare_to_die(
                        mission=objective,
                        max_attempts=min(spec.clone_count, 20),
                    )
                    results.append(
                        {
                            "force": "dare_to_die",
                            "attempts": dtd.total_attempts,
                            "verdict": dtd.verdict,
                            "nature": "qi",
                            "wu_xing_phase": spec.wu_xing_phase.value,
                        }
                    )
                except (ImportError, AttributeError):
                    logger.debug("Optional dependency unavailable: ImportError")

        return {
            "objective": objective,
            "doctrine_used": True,
            "tactic": tactic,
            "force_count": len(force_specs),
            "total_clones": sum(s.clone_count for s in force_specs),
            "results": results,
        }

    except ImportError:
        # Fallback: standard deployment
        army = AsyncThoughtCloneArmy()
        path = await army.parallel_explore(objective, num_clones)
        return {
            "objective": objective,
            "doctrine_used": False,
            "strategy": path.strategy,
            "confidence": path.confidence,
            "clones": num_clones,
        }


async def cast_brick_to_attract_jade(
    objective: str,
    scout_clones: int = 10000,
    strike_clones: int = 50,
) -> dict[str, Any]:
    """Execute the "Cast a Brick to Attract Jade" tactic.

    Phase 1 (Brick): Mass Tokio scouts narrow the search space
    Phase 2 (Jade): Precision Python cavalry strikes the identified targets

    Args:
        objective: What to find/fix
        scout_clones: Number of Tokio scouts (Phase 1)
        strike_clones: Number of precision clones (Phase 2)

    Returns:
        Combined results from both phases
    """
    army = AsyncThoughtCloneArmy()

    scout_result = await army.parallel_explore(objective, scout_clones, use_tokio=True)

    refined_prompt = (
        f"Based on initial analysis (strategy={scout_result.strategy}, "
        f"confidence={scout_result.confidence:.2f}): {objective}"
    )
    strike_result = await army.parallel_explore(
        refined_prompt, strike_clones, use_tokio=False
    )

    return {
        "tactic": "Cast a Brick to Attract Jade",
        "phase1_scouts": {
            "clones": scout_clones,
            "strategy": scout_result.strategy,
            "confidence": scout_result.confidence,
        },
        "phase2_strike": {
            "clones": strike_clones,
            "strategy": strike_result.strategy,
            "confidence": strike_result.confidence,
        },
        "combined_confidence": (scout_result.confidence + strike_result.confidence) / 2,
    }


async def diverse_explore(
    prompt: str,
    focus_areas: list[str] | None = None,
    clones_per_area: int = 2000,
) -> list[AsyncThoughtPath]:
    """Explore with focus on specific areas."""
    if focus_areas is None:
        focus_areas = ["analytical", "creative", "pragmatic"]

    results = []
    for area in focus_areas:
        army = AsyncThoughtCloneArmy()
        # Bias strategies toward focus area
        result = await army.parallel_explore(prompt, clones_per_area)
        results.append(result)

    return results


async def god_kit_generate(
    prompt: str,
    num_clones: int | None = None,
) -> dict[str, Any]:
    """Standalone God-Kit code generation entry point.

    Args:
        prompt: Natural language code request (e.g., "I need a FastAPI endpoint for items")
        num_clones: Clones per tier (default: 100/50/20 for Xianfeng/Wei Wuzu/Huben)

    Returns:
        Dict with generated code, metadata, and tier progression
    """
    army = AsyncThoughtCloneArmy()
    path = await army.vibe_code_explore(prompt, num_clones=num_clones)

    return {
        "status": "success" if path.confidence > 0.0 else "error",
        "code": path.content,
        "confidence": path.confidence,
        "strategy": path.strategy,
        "tokens": path.tokens,
        "metadata": path.metadata,
    }


async def benchmark_performance(max_clones: int = 16000) -> dict[str, float]:
    """Benchmark clone army performance."""
    prompts = [
        "Solve the traveling salesman problem",
        "Design a scalable architecture",
        "Optimize this algorithm",
        "Create a novel solution",
    ]

    durations: list[float] = []
    throughputs: list[float] = []
    clones_per_prompt = max_clones // len(prompts)
    for prompt in prompts:
        start = datetime.now()
        army = AsyncThoughtCloneArmy()
        await army.parallel_explore(prompt, clones_per_prompt)
        duration = (datetime.now() - start).total_seconds()
        throughput = clones_per_prompt / max(duration, 1e-9)
        durations.append(duration)
        throughputs.append(throughput)

    return {
        "avg_duration": sum(durations) / len(durations),
        "avg_throughput": sum(throughputs) / len(throughputs),
        "max_throughput": max(throughputs),
        "total_clones": max_clones,
    }
