
with open("whitemagic/autonomous/executor/continuous_executor.py") as f:
    content = f.read()

content = content.replace(
    """        # Load Unified Nervous System
        try:
            from whitemagic.core.intelligence.nervous_system import get_nervous_system
            self.nervous_system = get_nervous_system()
        except ImportError:
            self.nervous_system = None""",
    """        # Load Unified Nervous System
        try:
            from whitemagic.core.intelligence.nervous_system import get_nervous_system
            self.nervous_system = get_nervous_system()
            if self.nervous_system and not self.nervous_system.is_active:
                self.nervous_system.start()
        except ImportError:
            self.nervous_system = None"""
)

with open("whitemagic/autonomous/executor/continuous_executor.py", "w") as f:
    f.write(content)
