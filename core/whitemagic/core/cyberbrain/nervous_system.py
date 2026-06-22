# Unified Nervous System
# Ties together 7 biological subsystems (Immune, Genetic, Dream, Metabolism, Consciousness, Resonance, Emergence)
# Inspired by the Cyberbrains 7-Layer Architecture and MandalaOS eBPF Nervous System

import logging

logger = logging.getLogger(__name__)


class UnifiedNervousSystem:
    """UnifiedNervousSystem: unified nervous system."""
    def __init__(self, workspace, timescale_sync):
        self.workspace = workspace
        self.timescale = timescale_sync

        self.subsystems = {
            "immune": {"status": "active", "layer": "root", "load": 0.1},
            "metabolism": {"status": "active", "layer": "cerebellum", "load": 0.2},
            "genetic": {"status": "active", "layer": "basal_ganglia", "load": 0.05},
            "dream": {"status": "sleeping", "layer": "limbic", "load": 0.0},
            "consciousness": {"status": "active", "layer": "occipital_temporal", "load": 0.4},
            "resonance": {"status": "active", "layer": "parietal", "load": 0.1},
            "emergence": {"status": "monitoring", "layer": "logos", "load": 0.05}
        }

        # Wire into timescales
        self.timescale.register_hook("reflex", self._check_homeostasis)
        self.timescale.register_hook("planner", self._update_consciousness)
        self.timescale.register_hook("consolidation", self._trigger_dream_cycle)

        # Homeostatic state
        self._error_budget = 1.0
        self._congestion_threshold = 0.8

    def _check_homeostasis(self):
        """10ms reflex loop — Check basic resource budgets (metabolism).

        Monitors subsystem load, error rates, and congestion.
        Returns corrective actions if any subsystem exceeds thresholds.
        """
        actions = []
        total_load = sum(s["load"] for s in self.subsystems.values())
        avg_load = total_load / len(self.subsystems)

        # Check for overloaded subsystems
        for name, data in self.subsystems.items():
            if data["load"] > self._congestion_threshold:
                data["status"] = "congested"
                actions.append(f"throttle:{name}")
                logger.warning("Subsystem %s congested (load=%.2f)", name, data["load"])
            elif data["load"] < 0.01 and data["status"] == "active":
                data["status"] = "idle"

        # Update error budget based on average load
        if avg_load > 0.7:
            self._error_budget = max(0.0, self._error_budget - 0.01)
        else:
            self._error_budget = min(1.0, self._error_budget + 0.005)

        # If error budget depleted, trigger immune response
        if self._error_budget <= 0.0:
            self.subsystems["immune"]["status"] = "alert"
            actions.append("immune:alert")
            logger.error("Error budget depleted — immune system activated")

        return actions

    def _update_consciousness(self):
        """1s planner loop — Gating and habit selection.

        Evaluates which subsystems should receive attention based on
        current load, error budget, and resonance patterns.
        Returns gating decisions for the planner.
        """
        gating = {}

        # Prioritize subsystems by load * importance
        for name, data in self.subsystems.items():
            importance = {
                "immune": 1.0,
                "consciousness": 0.9,
                "resonance": 0.8,
                "metabolism": 0.7,
                "genetic": 0.6,
                "emergence": 0.5,
                "dream": 0.3,
            }.get(name, 0.5)

            priority = data["load"] * importance
            gating[name] = {
                "priority": round(priority, 3),
                "status": data["status"],
                "load": data["load"],
            }

        # Sort by priority descending
        sorted_gating = dict(sorted(gating.items(), key=lambda x: x[1]["priority"], reverse=True))

        # Update consciousness subsystem with current focus
        top_subsystem = next(iter(sorted_gating))
        self.subsystems["consciousness"]["focus"] = top_subsystem

        return {"gating": sorted_gating, "focus": top_subsystem, "error_budget": self._error_budget}

    def _trigger_dream_cycle(self):
        # 1hr loop - Memory consolidation (hippocampal routing)
        self.subsystems["dream"]["status"] = "active"

    def get_system_health(self):
        """
        Get the system health.
        """
        return {name: data["status"] for name, data in self.subsystems.items()}
