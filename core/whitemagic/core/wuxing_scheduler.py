"""
Wu Xing Waking Scheduler (G007)
===============================

5-Phase State Machine that governs the AI's operational mode.
Wood -> Fire -> Earth -> Metal -> Water cycle.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class Phase(Enum):
    """Phase: phase.

    Enumeration.

    Members:
        WOOD
        FIRE
        EARTH
        METAL
        WATER"""
    WOOD = "wood"   # Expansion, brainstorming, creation
    FIRE = "fire"   # Execution, parallel processing, action
    EARTH = "earth" # Integration, stabilization, testing
    METAL = "metal" # Refinement, optimization, pruning
    WATER = "water" # Reflection, storage, rest

@dataclass
class PhaseState:
    """PhaseState: phase state.

    Value object: equality and repr are field-based."""
    current: Phase
    start_time: datetime
    duration_minutes: float = 0.0
    energy_level: float = 1.0  # 0.0 to 1.0

class WuXingScheduler:
    """
    Manages the 5-phase operational cycle.
    """

    TRANSITIONS = {
        Phase.WOOD: Phase.FIRE,
        Phase.FIRE: Phase.EARTH,
        Phase.EARTH: Phase.METAL,
        Phase.METAL: Phase.WATER,
        Phase.WATER: Phase.WOOD
    }

    PHASE_DURATION_DEFAULTS = {
        Phase.WOOD: 15,  # 15 min brainstorming
        Phase.FIRE: 45,  # 45 min execution
        Phase.EARTH: 20, # 20 min integration
        Phase.METAL: 20, # 20 min optimization
        Phase.WATER: 10  # 10 min reflection
    }

    def __init__(self):
        self.state = PhaseState(
            current=Phase.WOOD,
            start_time=datetime.now()
        )
        self.manual_override = False

    def get_current_phase(self) -> Phase:
        """
        Get the current phase.

        Returns:
            Phase
        """
        res = self.state.current
        if isinstance(res, Phase):
            return res
        return Phase.WOOD

    def update(self, metrics: dict[str, Any]) -> Phase:
        """
        Update state based on time and metrics.
        Returns potentially new phase.
        """
        if self.manual_override:
            res = self.state.current
            return res if isinstance(res, Phase) else Phase.WOOD

        now = datetime.now()
        elapsed = (now - self.state.start_time).total_seconds() / 60.0
        self.state.duration_minutes = elapsed

        target_duration = self.PHASE_DURATION_DEFAULTS[self.state.current]

        # Check for emergency transitions based on metrics
        if self._check_emergency_earth(metrics):
            self.transition_to(Phase.EARTH, reason="High error rate emergency")
            return Phase.EARTH

        # Check for natural time-based transition
        if elapsed >= target_duration:
            next_phase = self.TRANSITIONS[self.state.current]
            self.transition_to(next_phase, reason="Time complete")
            return next_phase

        res = self.state.current
        return res if isinstance(res, Phase) else Phase.WOOD

    def transition_to(self, phase: Phase, reason: str = ""):
        """Force transition to a specific phase."""
        logger.info(f"Transitioning {self.state.current.value} -> {phase.value} ({reason})")
        self.state.current = phase
        self.state.start_time = datetime.now()
        self.state.duration_minutes = 0.0
        # Reset manual override if set
        self.manual_override = False

    def set_manual_phase(self, phase: Phase):
        """Manually set phase and lock it until explicitly changed or reset."""
        self.transition_to(phase, reason="Manual override")
        self.manual_override = True

    def _check_emergency_earth(self, metrics: dict[str, Any]) -> bool:
        """Return True if metrics indicate need for immediate stabilization."""
        # Example: if recent error rate is high
        error_rate = metrics.get("error_rate", 0.0)
        res = error_rate > 0.2 and self.state.current != Phase.EARTH
        return bool(res)

    def get_allowed_actions(self) -> list[str]:
        """Return list of allowed action types for current phase."""
        if self.state.current == Phase.WOOD:
            return ["create_file", "plan", "brainstorm", "list_files"]
        elif self.state.current == Phase.FIRE:
            return ["execute_command", "write_file", "deploy_clones", "run_script"]
        elif self.state.current == Phase.EARTH:
            return ["run_tests", "compile", "verify", "type_check"]
        elif self.state.current == Phase.METAL:
            return ["lint", "optimize", "delete_file", "refactor"]
        elif self.state.current == Phase.WATER:
            return ["save_memory", "summarize", "log", "archive"]
        return []

    def status(self) -> dict[str, Any]:
        """Return scheduler status."""
        return {
            "phase": self.state.current.value,
            "duration_min": round(self.state.duration_minutes, 1),
            "target_duration": self.PHASE_DURATION_DEFAULTS[self.state.current],
            "allowed_actions": self.get_allowed_actions(),
            "manual_override": self.manual_override
        }
