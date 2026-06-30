# ruff: noqa: BLE001
"""Rapid Cognition - Learn every 5 seconds."""

import logging
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
try:
    from ..bindings import get_rust_bridge  # type: ignore[import-not-found]
except ImportError:

    def get_rust_bridge() -> Any:
        """Fallback when Rust bridge is not built — returns None."""
        logger.debug("Rust bridge not available, using Python fallback")
        return None


class RapidCognition:
    """RapidCognition: rapid cognition."""

    def __init__(
        self,
        memory_dir: Path = Path("memory"),
        scan_interval: int = 5,  # seconds between scans (v2.3.5: 3x faster)
        consolidation_threshold: int = 50,  # patterns before consolidation
    ) -> None:
        self.memory_dir = memory_dir
        self.learn_interval = scan_interval
        self.rust = get_rust_bridge()
        self.running = False
        self.cycles_completed = 0
        self.patterns_discovered = 0

    def start_continuous_learning(self) -> Any:
        """
        Perform the start continuous learning operation.

        Returns:
            Any
        """
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._learning_loop, daemon=True)
        self.thread.start()
        logger.info("🧠 Rapid cognition started (every %ss)", self.learn_interval)

    def _learning_loop(self) -> Any:
        while self.running:
            try:
                if self.rust and self.rust.available:
                    result = self.rust.lib.extract_patterns(
                        str(self.memory_dir / "long_term"), 0.6
                    )
                    self.patterns_discovered = result[1]
                self.cycles_completed += 1
                time.sleep(self.learn_interval)
            except Exception as e:
                logger.info("⚠️  Learning cycle error: %s", e, exc_info=True)
                time.sleep(self.learn_interval)

    def get_stats(self) -> dict:
        """
        Get the stats.

        Returns:
            dict
        """
        return {
            "running": self.running,
            "cycles": self.cycles_completed,
            "patterns": self.patterns_discovered,
            "rate": f"Every {self.learn_interval}s",
        }


_instance = None


def get_rapid_learner() -> RapidCognition:
    """
    Get the rapid learner.

    Returns:
        RapidCognition
    """
    global _instance
    if _instance is None:
        _instance = RapidCognition()
    return _instance


def start_rapid_learning(interval_seconds: int = 5) -> Any:
    """
    Perform the start rapid learning operation.

    Args:
        interval_seconds: Parameter description.

    Returns:
        Any
    """
    global _instance
    if not _instance:
        _instance = RapidCognition(scan_interval=interval_seconds)
    elif not _instance.running:
        # Existing stopped instance — restart is not supported; caller should check .running
        logger.debug(
            "RapidCognition instance exists but is stopped; call start() explicitly"
        )

    _instance.start_continuous_learning()
    return _instance
