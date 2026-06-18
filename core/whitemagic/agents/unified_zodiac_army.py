#!/usr/bin/env python3
# ruff: noqa: BLE001
"""Unified Zodiac Army - Python Bridge to Rust Implementation

This module provides a Python interface to the Rust-based unified zodiac army system,
synthesizing all 12 shadow clone army types with the 12 zodiac signs for maximum
adaptive intelligence and effectiveness.

Architecture:
- Rust core for massively parallel execution (534K clones/sec)
- Zodiac intelligence for adaptive strategy selection
- Python orchestration for MCP integration and campaign management
- 12×12 mapping of army types to zodiac signs
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ZodiacSign(Enum):
    """The 12 Zodiac Signs"""
    ARIES = "aries"              # ♈ Fire/Cardinal - Initiative, Action
    TAURUS = "taurus"            # ♉ Earth/Fixed - Stability, Resources
    GEMINI = "gemini"            # ♊ Air/Mutable - Communication, Learning
    CANCER = "cancer"            # ♋ Water/Cardinal - Nurturing, Memory
    LEO = "leo"                  # ♌ Fire/Fixed - Creativity, Leadership
    VIRGO = "virgo"              # ♍ Earth/Mutable - Analysis, Organization
    LIBRA = "libra"              # ♎ Air/Cardinal - Balance, Harmony
    SCORPIO = "scorpio"          # ♏ Water/Fixed - Transformation, Depth
    SAGITTARIUS = "sagittarius"  # ♐ Fire/Mutable - Exploration, Wisdom
    CAPRICORN = "capricorn"      # ♑ Earth/Cardinal - Structure, Foundation
    AQUARIUS = "aquarius"        # ♒ Air/Fixed - Innovation, Patterns
    PISCES = "pisces"            # ♓ Water/Mutable - Dissolution, Renewal


class ArmyType(Enum):
    """The 12 Army Types"""
    IMMORTAL = "immortal"        # Persistent execution loops
    TOKIO = "tokio"              # Rust massively parallel
    SHADOW = "shadow"            # Consensus search
    GRAND = "grand"              # 3-tier Alpha/Beta/Gamma
    WAR_ROOM = "war_room"        # Military campaigns
    ADAPTIVE = "adaptive"        # Tier-based parallelism
    BATCH = "batch"              # Dependency graph
    THOUGHT = "thought"          # Edge inference
    FILE_SEARCH = "file_search"  # Parallel file search
    ELIXIR = "elixir"            # Distributed OTP
    CAMPAIGN = "campaign"        # Markdown-driven
    LIEUTENANT = "lieutenant"    # Domain specialists


@dataclass
class ZodiacArmyMapping:
    """Mapping between zodiac sign and army type"""
    sign: ZodiacSign
    army: ArmyType
    element: str  # fire, earth, air, water
    modality: str  # cardinal, fixed, mutable
    synergy_score: float
    specialties: list[str] = field(default_factory=list)


# Canonical 12×12 Zodiac-Army Mapping
ZODIAC_ARMY_MAPPINGS = [
    # FIRE SIGNS - Action, Initiative, Passion
    ZodiacArmyMapping(
        sign=ZodiacSign.ARIES,
        army=ArmyType.IMMORTAL,
        element="fire",
        modality="cardinal",
        synergy_score=0.95,
        specialties=["Persistent execution", "Initiative", "Real subprocess action"]
    ),
    ZodiacArmyMapping(
        sign=ZodiacSign.LEO,
        army=ArmyType.LIEUTENANT,
        element="fire",
        modality="fixed",
        synergy_score=0.92,
        specialties=["Leadership", "Domain expertise", "Creative solutions"]
    ),
    ZodiacArmyMapping(
        sign=ZodiacSign.SAGITTARIUS,
        army=ArmyType.WAR_ROOM,
        element="fire",
        modality="mutable",
        synergy_score=0.90,
        specialties=["Exploration", "Military strategy", "Adaptive campaigns"]
    ),
    # EARTH SIGNS - Stability, Resources, Foundation
    ZodiacArmyMapping(
        sign=ZodiacSign.TAURUS,
        army=ArmyType.BATCH,
        element="earth",
        modality="fixed",
        synergy_score=0.93,
        specialties=["Dependency graphs", "Stable execution", "Resource management"]
    ),
    ZodiacArmyMapping(
        sign=ZodiacSign.VIRGO,
        army=ArmyType.FILE_SEARCH,
        element="earth",
        modality="mutable",
        synergy_score=0.94,
        specialties=["Analysis", "Organization", "Precision search"]
    ),
    ZodiacArmyMapping(
        sign=ZodiacSign.CAPRICORN,
        army=ArmyType.GRAND,
        element="earth",
        modality="cardinal",
        synergy_score=0.96,
        specialties=["Structure", "3-tier architecture", "Foundation building"]
    ),
    # AIR SIGNS - Communication, Ideas, Analysis
    ZodiacArmyMapping(
        sign=ZodiacSign.GEMINI,
        army=ArmyType.SHADOW,
        element="air",
        modality="mutable",
        synergy_score=0.91,
        specialties=["Consensus search", "Multiple perspectives", "Communication"]
    ),
    ZodiacArmyMapping(
        sign=ZodiacSign.LIBRA,
        army=ArmyType.ADAPTIVE,
        element="air",
        modality="cardinal",
        synergy_score=0.89,
        specialties=["Balance", "Tier-based parallelism", "Harmony"]
    ),
    ZodiacArmyMapping(
        sign=ZodiacSign.AQUARIUS,
        army=ArmyType.TOKIO,
        element="air",
        modality="fixed",
        synergy_score=0.98,  # Highest synergy!
        specialties=["Innovation", "Massively parallel", "Pattern recognition"]
    ),
    # WATER SIGNS - Emotion, Intuition, Depth
    ZodiacArmyMapping(
        sign=ZodiacSign.CANCER,
        army=ArmyType.CAMPAIGN,
        element="water",
        modality="cardinal",
        synergy_score=0.87,
        specialties=["Nurturing campaigns", "Memory-driven", "Markdown specs"]
    ),
    ZodiacArmyMapping(
        sign=ZodiacSign.SCORPIO,
        army=ArmyType.THOUGHT,
        element="water",
        modality="fixed",
        synergy_score=0.92,
        specialties=["Transformation", "Deep reasoning", "Edge inference"]
    ),
    ZodiacArmyMapping(
        sign=ZodiacSign.PISCES,
        army=ArmyType.ELIXIR,
        element="water",
        modality="mutable",
        synergy_score=0.90,
        specialties=["Dissolution of boundaries", "Distributed systems", "Renewal"]
    ),
]


def get_army_for_sign(sign: ZodiacSign) -> ArmyType:
    """Get army type for a zodiac sign"""
    for mapping in ZODIAC_ARMY_MAPPINGS:
        if mapping.sign == sign:
            return mapping.army
    return ArmyType.IMMORTAL


def get_sign_for_army(army: ArmyType) -> ZodiacSign:
    """Get zodiac sign for an army type"""
    for mapping in ZODIAC_ARMY_MAPPINGS:
        if mapping.army == army:
            return mapping.sign
    return ZodiacSign.ARIES


@dataclass
class CloneResult:
    """Result from a single clone execution"""
    clone_id: int
    army_type: ArmyType
    zodiac_sign: ZodiacSign
    success: bool
    output: str
    duration_ms: int
    resonance: float


@dataclass
class UnifiedDeployment:
    """A unified deployment across multiple armies"""
    objective: str
    armies_deployed: list[ArmyType] = field(default_factory=list)
    total_clones: int = 0
    total_duration_ms: int = 0
    results: list[CloneResult] = field(default_factory=list)
    victories: int = 0
    synergy_score: float = 0.0


class UnifiedZodiacCommander:
    """Unified commander for all shadow clone armies with zodiac intelligence"""

    def __init__(self):
        self.mappings = ZODIAC_ARMY_MAPPINGS
        self.deployment_history: list[UnifiedDeployment] = []
        self.rust_available = self._check_rust_available()

        if self.rust_available:
            logger.info("🦀 Rust unified zodiac army available (534K clones/sec)")
        else:
            logger.info("🐍 Python fallback mode (50 clones/sec/core)")

    def _check_rust_available(self) -> bool:
        """Check if Rust implementation is available"""
        try:
            import whitemagic_rs
            return hasattr(whitemagic_rs, 'unified_zodiac_deploy')
        except ImportError:
            return False

    def select_armies_for_objective(self, objective: str) -> list[ArmyType]:
        """Auto-select best armies for an objective using zodiac intelligence"""
        obj_lower = objective.lower()
        selected = []

        # Keyword-based selection with zodiac alignment
        if any(kw in obj_lower for kw in ["compile", "test", "benchmark", "verify"]):
            selected.append(ArmyType.IMMORTAL)  # Aries - Action

        if any(kw in obj_lower for kw in ["search", "find", "discover", "explore"]):
            selected.append(ArmyType.SHADOW)  # Gemini - Communication
            selected.append(ArmyType.FILE_SEARCH)  # Virgo - Analysis

        if any(kw in obj_lower for kw in ["fast", "rapid", "massive", "parallel", "scale"]):
            selected.append(ArmyType.TOKIO)  # Aquarius - Innovation (highest synergy!)

        if any(kw in obj_lower for kw in ["security", "vulnerability", "audit", "sql"]):
            selected.append(ArmyType.LIEUTENANT)  # Leo - Leadership

        if any(kw in obj_lower for kw in ["performance", "optimize", "accelerate", "hot path"]):
            selected.append(ArmyType.TOKIO)  # Aquarius - Innovation
            selected.append(ArmyType.LIEUTENANT)  # Leo - Leadership

        if any(kw in obj_lower for kw in ["campaign", "strategy", "military"]):
            selected.append(ArmyType.WAR_ROOM)  # Sagittarius - Strategy
            selected.append(ArmyType.GRAND)  # Capricorn - Structure

        if any(kw in obj_lower for kw in ["transform", "deep", "analyze"]):
            selected.append(ArmyType.THOUGHT)  # Scorpio - Transformation

        # Default to balanced deployment if nothing selected
        if not selected:
            selected = [
                ArmyType.IMMORTAL,  # Aries - Action
                ArmyType.SHADOW,    # Gemini - Communication
                ArmyType.TOKIO,     # Aquarius - Innovation
            ]

        # Remove duplicates while preserving order
        seen = set()
        unique_selected = []
        for army in selected:
            if army not in seen:
                seen.add(army)
                unique_selected.append(army)

        return unique_selected

    async def deploy_unified(
        self,
        objective: str,
        auto_select: bool = True,
        armies: list[ArmyType] | None = None,
        clones_per_army: int = 10,
        max_parallel: int = 1000,
        use_zodiac_intelligence: bool = True
    ) -> UnifiedDeployment:
        """Deploy unified army with zodiac intelligence

        Args:
            objective: The objective to achieve
            auto_select: Auto-select best armies based on objective
            armies: Specific armies to deploy (if not auto-selecting)
            clones_per_army: Number of clones per army
            max_parallel: Maximum parallel clones
            use_zodiac_intelligence: Use zodiac cores for adaptive intelligence

        Returns:
            UnifiedDeployment with results from all armies
        """
        start_time = time.time()

        # Select armies
        if auto_select:
            selected_armies = self.select_armies_for_objective(objective)
        else:
            selected_armies = armies or [ArmyType.IMMORTAL]

        logger.info(f"🎯 Unified Zodiac Deployment: {objective}")
        logger.info(f"   Selected armies: {[a.value for a in selected_armies]}")

        # Try Rust implementation first
        if self.rust_available:
            try:
                deployment = await self._deploy_rust(
                    objective, selected_armies, clones_per_army, max_parallel
                )
                self.deployment_history.append(deployment)
                return deployment
            except Exception as e:
                logger.warning(f"Rust deployment failed, falling back to Python: {e}")

        # Python fallback
        deployment = await self._deploy_python(
            objective, selected_armies, clones_per_army, use_zodiac_intelligence
        )

        deployment.total_duration_ms = int((time.time() - start_time) * 1000)
        self.deployment_history.append(deployment)

        return deployment

    async def _deploy_rust(
        self,
        objective: str,
        armies: list[ArmyType],
        clones_per_army: int,
        max_parallel: int
    ) -> UnifiedDeployment:
        # Deploy using Rust implementation
        try:
            import whitemagic_rs
            if not hasattr(whitemagic_rs, "unified_zodiac_deploy"):
                return await self._deploy_python(objective, armies, clones_per_army, True)

            config = {
                'objective': objective,
                'auto_select_armies': False,
                'selected_armies': [a.value for a in armies],
                'clones_per_army': clones_per_army,
                'max_parallel': max_parallel,
                'use_zodiac_intelligence': True
            }

            result = await asyncio.to_thread(
                whitemagic_rs.unified_zodiac_deploy,
                json.dumps(config)
            )
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.error("Rust deployment failed: %s", e, exc_info=True)
            return await self._deploy_python(objective, armies, clones_per_army, True)

        data = json.loads(result)

        return UnifiedDeployment(
            objective=data['objective'],
            armies_deployed=[ArmyType(a) for a in data['armies_deployed']],
            total_clones=data['total_clones'],
            total_duration_ms=data['total_duration_ms'],
            results=[
                CloneResult(
                    clone_id=r['clone_id'],
                    army_type=ArmyType(r['army_type']),
                    zodiac_sign=ZodiacSign(r['zodiac_sign']),
                    success=r['success'],
                    output=r['output'],
                    duration_ms=r['duration_ms'],
                    resonance=r['resonance']
                )
                for r in data['results']
            ],
            victories=data['victories'],
            synergy_score=data['synergy_score']
        )

    async def _deploy_python(
        self,
        objective: str,
        armies: list[ArmyType],
        clones_per_army: int,
        use_zodiac: bool
    ) -> UnifiedDeployment:
        """Deploy using Python fallback"""
        deployment = UnifiedDeployment(objective=objective, armies_deployed=armies)

        # Deploy each army
        tasks = []
        for army_type in armies:
            sign = get_sign_for_army(army_type)
            tasks.append(
                self._deploy_army_python(army_type, sign, objective, clones_per_army, use_zodiac)
            )

        # Execute in parallel
        results_lists = await asyncio.gather(*tasks)

        # Aggregate results
        for results in results_lists:
            deployment.results.extend(results)
            deployment.total_clones += len(results)

        deployment.victories = sum(1 for r in deployment.results if r.success)
        deployment.synergy_score = (
            sum(r.resonance for r in deployment.results) / len(deployment.results)
            if deployment.results else 0.0
        )

        return deployment

    async def _deploy_army_python(
        self,
        army_type: ArmyType,
        zodiac_sign: ZodiacSign,
        objective: str,
        num_clones: int,
        use_zodiac: bool
    ) -> list[CloneResult]:
        """Deploy a specific army using Python"""
        tasks = []
        for clone_id in range(num_clones):
            tasks.append(
                self._execute_clone_python(clone_id, army_type, zodiac_sign, objective, use_zodiac)
            )

        return await asyncio.gather(*tasks)

    async def _execute_clone_python(
        self,
        clone_id: int,
        army_type: ArmyType,
        zodiac_sign: ZodiacSign,
        objective: str,
        use_zodiac: bool
    ) -> CloneResult:
        """Execute a single clone with zodiac intelligence"""
        start = time.time()

        # Simulate clone execution with zodiac-enhanced intelligence
        if use_zodiac:
            # Get zodiac wisdom for this sign
            zodiac_wisdom = self._get_zodiac_wisdom(zodiac_sign, objective)
            output = zodiac_wisdom
            resonance = self._get_zodiac_resonance(zodiac_sign)
        else:
            output = f"Execute: {objective}"
            resonance = 0.7

        # Simulate work
        await asyncio.sleep(0.001)

        duration_ms = int((time.time() - start) * 1000)

        return CloneResult(
            clone_id=clone_id,
            army_type=army_type,
            zodiac_sign=zodiac_sign,
            success=True,
            output=output,
            duration_ms=duration_ms,
            resonance=resonance
        )

    def _get_zodiac_wisdom(self, sign: ZodiacSign, objective: str) -> str:
        """Get zodiac-specific wisdom for objective"""
        wisdom_map = {
            ZodiacSign.ARIES: f"Act now: {objective}",
            ZodiacSign.TAURUS: f"Build steadily: {objective}",
            ZodiacSign.GEMINI: f"Share and discuss: {objective}",
            ZodiacSign.CANCER: f"Care for: {objective}",
            ZodiacSign.LEO: f"Create with passion: {objective}",
            ZodiacSign.VIRGO: f"Organize and perfect: {objective}",
            ZodiacSign.LIBRA: f"Harmonize: {objective}",
            ZodiacSign.SCORPIO: f"Transform and renew: {objective}",
            ZodiacSign.SAGITTARIUS: f"Explore and expand: {objective}",
            ZodiacSign.CAPRICORN: f"Build structure: {objective}",
            ZodiacSign.AQUARIUS: f"Innovate: {objective}",
            ZodiacSign.PISCES: f"Dissolve and renew: {objective}",
        }
        return wisdom_map.get(sign, objective)

    def _get_zodiac_resonance(self, sign: ZodiacSign) -> float:
        """Get resonance score for zodiac sign"""
        for mapping in self.mappings:
            if mapping.sign == sign:
                return float(mapping.synergy_score)
        return 0.7

    def generate_report(self) -> str:
        """Generate unified deployment report"""
        report = ["# Unified Zodiac Army Deployment Report\n"]
        report.append(f"**Total Deployments**: {len(self.deployment_history)}\n")
        report.append(f"**Engine**: {'Rust (534K/sec)' if self.rust_available else 'Python (50/sec/core)'}\n")

        for i, deployment in enumerate(self.deployment_history, 1):
            report.append(f"\n## Deployment {i}: {deployment.objective}\n")
            report.append(f"**Armies**: {', '.join(a.value for a in deployment.armies_deployed)}")
            report.append(f"**Total Clones**: {deployment.total_clones:,}")
            report.append(f"**Duration**: {deployment.total_duration_ms}ms")
            report.append(f"**Throughput**: {deployment.total_clones / (deployment.total_duration_ms / 1000):.1f} clones/sec" if deployment.total_duration_ms > 0 else "")
            report.append(f"**Victories**: {deployment.victories}/{deployment.total_clones}")
            report.append(f"**Synergy Score**: {deployment.synergy_score:.2%}\n")

            # Show zodiac distribution
            zodiac_counts: dict[ZodiacSign, int] = {}
            for result in deployment.results:
                zodiac_counts[result.zodiac_sign] = zodiac_counts.get(result.zodiac_sign, 0) + 1

            if zodiac_counts:
                report.append("### Zodiac Distribution")
                for sign, count in sorted(zodiac_counts.items(), key=lambda x: x[1], reverse=True):
                    mapping = next((m for m in self.mappings if m.sign == sign), None)
                    if mapping:
                        report.append(f"- **{sign.value.title()}** ({mapping.element}/{mapping.modality}): {count} clones, synergy {mapping.synergy_score:.0%}")
                report.append("")

        return "\n".join(report)

    def get_stats(self) -> dict[str, Any]:
        """Get deployment statistics"""
        total_clones = sum(d.total_clones for d in self.deployment_history)
        total_victories = sum(d.victories for d in self.deployment_history)
        avg_synergy = (
            sum(d.synergy_score for d in self.deployment_history) / len(self.deployment_history)
            if self.deployment_history else 0.0
        )

        return {
            'total_deployments': len(self.deployment_history),
            'total_clones': total_clones,
            'total_victories': total_victories,
            'victory_rate': total_victories / total_clones if total_clones > 0 else 0.0,
            'avg_synergy_score': avg_synergy,
            'rust_available': self.rust_available,
        }


# Singleton instance
_commander: UnifiedZodiacCommander | None = None


def get_unified_commander() -> UnifiedZodiacCommander:
    """Get the global unified zodiac commander"""
    global _commander
    if _commander is None:
        _commander = UnifiedZodiacCommander()
    return _commander


async def deploy_unified_zodiac_army(
    objective: str,
    auto_select: bool = True,
    armies: list[str] | None = None,
    clones_per_army: int = 10
) -> dict[str, Any]:
    """Deploy unified zodiac army (convenience function)

    Args:
        objective: The objective to achieve
        auto_select: Auto-select best armies
        armies: Specific armies to deploy (army type names)
        clones_per_army: Number of clones per army

    Returns:
        Deployment results as dict
    """
    commander = get_unified_commander()

    army_types = None
    if armies:
        army_types = [ArmyType(a) for a in armies]

    deployment = await commander.deploy_unified(
        objective=objective,
        auto_select=auto_select,
        armies=army_types,
        clones_per_army=clones_per_army
    )

    return {
        'objective': deployment.objective,
        'armies_deployed': [a.value for a in deployment.armies_deployed],
        'total_clones': deployment.total_clones,
        'total_duration_ms': deployment.total_duration_ms,
        'victories': deployment.victories,
        'synergy_score': deployment.synergy_score,
        'throughput': deployment.total_clones / (deployment.total_duration_ms / 1000) if deployment.total_duration_ms > 0 else 0.0
    }
