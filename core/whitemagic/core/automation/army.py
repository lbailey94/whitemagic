# ruff: noqa: BLE001
"""Autonomous Army Manager.
========================
Orchestrates self-evolving agentic deployments based on Self-Model alerts
and Codebase Census bottlenecks.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.core.acceleration.polyglot_accelerator import get_accelerator
from whitemagic.core.intelligence.self_model import get_self_model

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class AutonomousArmyManager:
    """Manages autonomous deployments of shadow clones for system optimization."""

    def __init__(self):
        self.self_model = get_self_model()
        self.accelerator = get_accelerator()
        self.active_deployments: list[dict[str, Any]] = []
        self._running = False
        self._census_path = PROJECT_ROOT / "scripts" / "codebase_census.py"
        self._deploy_script = PROJECT_ROOT / "scripts" / "deploy_grand_army.py"
        self._prune_threshold_seconds: float = 3600.0  # 1 hour default
        self._deployment_utility: dict[
            str, float
        ] = {}  # deployment_id -> utility score

    async def start_patrol(self, interval_seconds: int = 300):
        """Start a background patrol loop to monitor system health and trigger deployments."""
        self._running = True
        logger.info("⚔️ Autonomous Army Patrol started.")
        while self._running:
            try:
                # Tier 1: Sense (Census)
                await self.run_census()
                # Plan & Deploy
                await self.evaluate_and_deploy()
                # Ritual of Pruning: clean stale deployments
                self.prune_stale_deployments()
            except Exception as e:
                logger.error("Error in army patrol: %s", e, exc_info=True)
            await asyncio.sleep(interval_seconds)

    async def run_census(self):
        """Run the codebase census to update the system map and identify bottlenecks."""
        logger.info("📡 Running Tier 1 Scout: Codebase Census...")
        try:
            process = await asyncio.create_subprocess_exec(
                "python3",
                str(self._census_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logger.info("✅ Census complete.")
            else:
                logger.error("❌ Census failed: %s", stderr.decode())
        except Exception as e:
            logger.error("Error running census: %s", e, exc_info=True)

    async def evaluate_and_deploy(self):
        """Evaluate system state and decide if a deployment is needed."""
        alerts = self.self_model.get_alerts()
        stats = self.accelerator.get_stats()

        # 1. Check for performance bottlenecks (Low native usage)
        if stats["native_usage_pct"] < 50 and stats["calls"]["total"] > 100:
            logger.warning(
                "🚀 Low native usage detected. Triggering Tier 2 Rust Hot-Path Scout."
            )
            await self.deploy_army("beta", "rust_hot_path_profiling")

        # 2. Check for Self-Model alerts
        for alert in alerts:
            if "error_rate" in alert.metric and alert.current > 0.1:
                logger.error(
                    "⚠️ High error rate detected (%s). Deploying Tier 1 Security Audit.",
                    alert.current,
                    exc_info=True,
                )
                await self.deploy_army("alpha", "security_classification")

            if "energy" in alert.metric and alert.current < 0.3:
                logger.warning(
                    "📉 Low system energy (%s). Deploying Tier 1 Quality Assessment.",
                    alert.current,
                    exc_info=True,
                )
                await self.deploy_army("alpha", "quality_assessment")

    async def deploy_army(self, army_type: str, objective: str):
        """Deploy a specialized army to address a specific objective using deploy_grand_army.py."""
        logger.info(
            "🎖️ Deploying Army {army_type.upper()} for objective: %s",
            objective,
            exc_info=True,
        )

        try:
            # Objective map for deploy_grand_army.py
            # Note: deploy_grand_army.py uses --army and --objective flags
            cmd = [
                "python3",
                str(self._deploy_script),
                "--army",
                army_type,
                "--objective",
                objective,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Non-blocking: we don't necessarily wait for full completion if it's a large army
            # but we track the PID
            deployment_id = f"{army_type}_{objective}_{process.pid}"
            self.active_deployments.append(
                {
                    "id": deployment_id,
                    "pid": process.pid,
                    "army": army_type,
                    "objective": objective,
                    "start_time": asyncio.get_event_loop().time(),
                    "utility_score": 1.0,  # Initial utility
                }
            )

            logger.info("✅ Deployment %s launched.", deployment_id, exc_info=True)
            return deployment_id

        except Exception as e:
            logger.error("Failed to deploy army: %s", e, exc_info=True)
            return None

    def prune_stale_deployments(
        self, max_age_seconds: float | None = None
    ) -> dict[str, Any]:
        """Proof-of-Utility pruning — terminate deployments older than threshold or with low utility.

        Emits Gan Ying events so the Karma Ledger records why something was pruned.
        """
        threshold = max_age_seconds or self._prune_threshold_seconds
        now = time.time()
        pruned = []
        kept = []

        for dep in self.active_deployments:
            age = now - dep.get("start_time", now)
            utility = dep.get("utility_score", 0.0)
            # Prune if too old OR utility dropped below threshold
            if age > threshold or utility < 0.2:
                pruned.append(dep)
            else:
                kept.append(dep)

        self.active_deployments = kept

        # Emit Gan Ying event for audit trail
        if pruned:
            try:
                from whitemagic.core.ports import emit_gan_ying

                emit_gan_ying(
                    "ARMY_PRUNING",
                    {
                        "pruned_count": len(pruned),
                        "kept_count": len(kept),
                        "threshold_seconds": threshold,
                        "pruned_ids": [d["id"] for d in pruned],
                        "reason": "Proof-of-Utility: deployment exceeded max_age or utility fell below 0.2",
                    },
                )
            except Exception as e:
                logger.debug(
                    "Gan Ying emit failed for army pruning: %s", e, exc_info=True
                )

        return {
            "status": "success",
            "pruned": len(pruned),
            "kept": len(kept),
            "threshold_seconds": threshold,
        }


_manager = None


def get_army_manager() -> AutonomousArmyManager:
    """
    Get the army manager.

    Returns:
        AutonomousArmyManager
    """
    global _manager
    if _manager is None:
        _manager = AutonomousArmyManager()
    return _manager
