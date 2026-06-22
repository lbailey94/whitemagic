
with open("whitemagic/autonomous/executor/continuous_executor.py") as f:
    content = f.read()

# Add rust imports
content = content.replace(
    "from .objective_generator import ObjectiveGenerator",
    "from .objective_generator import ObjectiveGenerator\n        try:\n            import whitemagic_rust as rs\n            self._rust_daemon = rs.ContinuousDaemon()\n        except ImportError:\n            self._rust_daemon = None"
)

# Update run_continuous to start rust daemon
content = content.replace(
    """    async def run_continuous(self) -> None:
        \"\"\"Run the execution loop continuously until stopped.\"\"\"
        self.log("🤖 Starting autonomous execution")""",
    """    async def run_continuous(self) -> None:
        \"\"\"Run the execution loop continuously until stopped.\"\"\"
        self.log("🤖 Starting autonomous execution")
        if self._rust_daemon and not self._rust_daemon.is_running():
            self.log("🚀 Starting Rust background daemon")
            self._rust_daemon.start()"""
)

# Stop rust daemon on exit
content = content.replace(
    """                # Check limits
                should_stop, reason = self.should_stop()
                if should_stop:
                    self.log(f"Stopping: {reason}", "WARN")
                    break""",
    """                # Check limits
                should_stop, reason = self.should_stop()
                if should_stop:
                    self.log(f"Stopping: {reason}", "WARN")
                    if self._rust_daemon and self._rust_daemon.is_running():
                        self._rust_daemon.stop()
                    break"""
)

with open("whitemagic/autonomous/executor/continuous_executor.py", "w") as f:
    f.write(content)
