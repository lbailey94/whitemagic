# Multi-Timescale Sync
# Implements bucketed event loops (10ms reflexes vs 1hr consolidation)

import asyncio


class TimescaleSync:
    """TimescaleSync: timescale sync."""

    def __init__(self):
        self.loops = {
            "reflex": [],  # 10ms
            "planner": [],  # 1s
            "consolidation": [],  # 1hr
        }

    def register_hook(self, timescale: str, callback):
        """
        Register a hook.

        Args:
            timescale: Parameter description.
            callback: Parameter description.
        """
        if timescale in self.loops:
            self.loops[timescale].append(callback)

    async def run_reflex_loop(self):
        """
        Run the reflex loop operation.
        """
        while True:
            for cb in self.loops["reflex"]:
                cb()
            await asyncio.sleep(0.01)

    async def run_planner_loop(self):
        """
        Run the planner loop operation.
        """
        while True:
            for cb in self.loops["planner"]:
                cb()
            await asyncio.sleep(1.0)

    async def run_consolidation_loop(self):
        """
        Run the consolidation loop operation.
        """
        while True:
            for cb in self.loops["consolidation"]:
                cb()
            await asyncio.sleep(3600.0)
