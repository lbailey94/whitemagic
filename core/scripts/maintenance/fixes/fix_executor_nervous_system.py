
with open("whitemagic/autonomous/executor/continuous_executor.py") as f:
    content = f.read()

# Replace individual subsystems with UnifiedNervousSystem
content = content.replace(
    """        # Load biological subsystems for unified nervous system
        try:
            from whitemagic.core.intelligence.dream_cycle import DreamCycle
            self.dream_cycle = DreamCycle()
        except ImportError:
            self.dream_cycle = None

        try:
            from whitemagic.core.intelligence.hologram.consolidation import HolographicConsolidator
            self.consolidator = HolographicConsolidator()
        except ImportError:
            self.consolidator = None

        try:
            from whitemagic.core.intelligence.reconsolidation import MemoryReconsolidator
            self.reconsolidator = MemoryReconsolidator()
        except ImportError:
            self.reconsolidator = None""",
    """        # Load Unified Nervous System
        try:
            from whitemagic.core.intelligence.nervous_system import get_nervous_system
            self.nervous_system = get_nervous_system()
        except ImportError:
            self.nervous_system = None"""
)

# Update run_continuous pulse
content = content.replace(
    """                # Homeostasis / Biological Subsystem pulse
                if getattr(self, 'current_iteration', 0) % 50 == 0 and getattr(self, 'current_iteration', 0) > 0:
                    self.log("🧘 Triggering Homeostasis Pulse (Metabolism/Dreams)")
                    if self.consolidator:
                        try:
                            import asyncio
                            asyncio.create_task(self.consolidator.consolidate(dry_run=True))
                        except Exception:
                            pass

                    if self.reconsolidator:
                        try:
                            self.reconsolidator.reconsolidate_all()
                        except Exception:
                            pass""",
    """                # Homeostasis / Biological Subsystem pulse
                if getattr(self, 'current_iteration', 0) % 50 == 0 and getattr(self, 'current_iteration', 0) > 0:
                    self.log("🧠 Triggering Nervous System Pulse")
                    if self.nervous_system:
                        try:
                            self.nervous_system.pulse()
                        except Exception as e:
                            self.log(f"Nervous system pulse failed: {e}", "WARN")"""
)

with open("whitemagic/autonomous/executor/continuous_executor.py", "w") as f:
    f.write(content)
