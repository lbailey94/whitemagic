
with open("whitemagic/autonomous/executor/continuous_executor.py") as f:
    content = f.read()

content = content.replace(
    """                if getattr(self, 'current_iteration', 0) % 50 == 0 and getattr(self, 'current_iteration', 0) > 0:
                    self.log("🧠 Triggering Nervous System Pulse")""",
    """                # Update iteration count to properly trigger pulses
                self.current_iteration = getattr(self, 'current_iteration', 0) + 1

                # Homeostasis / Biological Subsystem pulse
                if self.current_iteration % 5 == 0:  # Lowered from 50 to 5 for testing
                    self.log("🧠 Triggering Nervous System Pulse")"""
)

with open("whitemagic/autonomous/executor/continuous_executor.py", "w") as f:
    f.write(content)
