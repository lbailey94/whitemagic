
with open("whitemagic/autonomous/executor/continuous_executor.py") as f:
    content = f.read()

# Make the wrapper use the rust daemon more completely
content = content.replace(
    """    def has_objectives(self) -> bool:
        \"\"\"Check if there are pending objectives.\"\"\"
        return len(self.objectives) > 0""",
    """    def has_objectives(self) -> bool:
        \"\"\"Check if there are pending objectives.\"\"\"
        return len(self.objectives) > 0

    def get_rust_stats(self) -> dict:
        \"\"\"Get runtime stats from the Rust background daemon.\"\"\"
        if self._rust_daemon and self._rust_daemon.is_running():
            return self._rust_daemon.get_stats()
        return {}"""
)

with open("whitemagic/autonomous/executor/continuous_executor.py", "w") as f:
    f.write(content)
