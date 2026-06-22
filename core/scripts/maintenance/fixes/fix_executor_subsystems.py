
with open("whitemagic/autonomous/executor/continuous_executor.py") as f:
    content = f.read()

content = content.replace(
    """                # Homeostasis / Biological Subsystem pulse
                if self.current_iteration % 50 == 0:""",
    """                # Homeostasis / Biological Subsystem pulse
                if getattr(self, 'current_iteration', 0) % 50 == 0 and getattr(self, 'current_iteration', 0) > 0:"""
)

with open("whitemagic/autonomous/executor/continuous_executor.py", "w") as f:
    f.write(content)
