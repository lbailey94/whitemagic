
with open("whitemagic/autonomous/executor/continuous_executor.py") as f:
    content = f.read()

# Make the integration with Rust daemon robust
content = content.replace(
    """        try:
            import whitemagic_rust as rs
            self._rust_daemon = rs.ContinuousDaemon()
        except ImportError:
            self._rust_daemon = None""",
    """        try:
            import whitemagic_rust as rs
            if hasattr(rs, 'ContinuousDaemon'):
                self._rust_daemon = rs.ContinuousDaemon()
            else:
                self._rust_daemon = None
        except Exception:
            self._rust_daemon = None"""
)

with open("whitemagic/autonomous/executor/continuous_executor.py", "w") as f:
    f.write(content)
