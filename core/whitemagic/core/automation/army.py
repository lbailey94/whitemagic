"""Autonomous Army Manager.
========================
Orchestrates self-evolving agentic deployments based on Self-Model alerts
and Codebase Census bottlenecks.
"""

import asyncio
import logging
from pathlib import Path

from whitemagic.core.acceleration.polyglot_accelerator import get_accelerator
from whitemagic.core.intelligence.self_model import get_self_model

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

class AutonomousArmyManager:
    """Manages autonomous deployments of shadow clones for system optimization."""

    def __init__(self):
        self.self_model = get_self_model()
        self.accelerator = get_accelerator()
        self.active_deployments = []
        self._running = False
        self._census_path = PROJECT_ROOT / "scripts" / "codebase_census.py"
        self._deploy_script = PROJECT_ROOT / "scripts" / "deploy_grand_army.py"

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
            except Exception as e:
                logger.error(f"Error in army patrol: {e}")
            await asyncio.sleep(interval_seconds)

    async def run_census(self):
        """Run the codebase census to update the system map and identify bottlenecks."""
        logger.info("📡 Running Tier 1 Scout: Codebase Census...")
        try:
            process = await asyncio.create_subprocess_exec(
                "python3", str(self._census_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logger.info("✅ Census complete.")
            else:
                logger.error(f"❌ Census failed: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Error running census: {e}")

    async def evaluate_and_deploy(self):
        """Evaluate system state and decide if a deployment is needed."""
        alerts = self.self_model.get_alerts()
        stats = self.accelerator.get_stats()

        # 1. Check for performance bottlenecks (Low native usage)
        if stats["native_usage_pct"] < 50 and stats["calls"]["total"] > 100:
            logger.warning("🚀 Low native usage detected. Triggering Tier 2 Rust Hot-Path Scout.")
            await self.deploy_army("beta", "rust_hot_path_profiling")

        # 2. Check for Self-Model alerts
        for alert in alerts:
            if "error_rate" in alert.metric and alert.current > 0.1:
                logger.error(f"⚠️ High error rate detected ({alert.current}). Deploying Tier 1 Security Audit.")
                await self.deploy_army("alpha", "security_classification")

            if "energy" in alert.metric and alert.current < 0.3:
                logger.warning(f"📉 Low system energy ({alert.current}). Deploying Tier 1 Quality Assessment.")
                await self.deploy_army("alpha", "quality_assessment")

    async def deploy_army(self, army_type: str, objective: str):
        """Deploy a specialized army to address a specific objective using deploy_grand_army.py."""
        logger.info(f"🎖️ Deploying Army {army_type.upper()} for objective: {objective}")

        try:
            # Objective map for deploy_grand_army.py
            # Note: deploy_grand_army.py uses --army and --objective flags
            cmd = ["python3", str(self._deploy_script), "--army", army_type, "--objective", objective]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Non-blocking: we don't necessarily wait for full completion if it's a large army
            # but we track the PID
            deployment_id = f"{army_type}_{objective}_{process.pid}"
            self.active_deployments.append({
                "id": deployment_id,
                "pid": process.pid,
                "army": army_type,
                "objective": objective,
                "start_time": asyncio.get_event_loop().time()
            })

            logger.info(f"✅ Deployment {deployment_id} launched.")
            return deployment_id

        except Exception as e:
            logger.error(f"Failed to deploy army: {e}")
            return None

_manager = None

def get_army_manager() -> AutonomousArmyManager:
    global _manager
    if _manager is None:
        _manager = AutonomousArmyManager()
    return _manager
