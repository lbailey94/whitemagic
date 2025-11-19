"""Rapid Cognition - Learn every 5 seconds"""
from pathlib import Path
from typing import Dict
import time, threading
try:
    from ..bindings import get_rust_bridge
except ImportError:
    get_rust_bridge = lambda: None

class RapidCognition:
    def __init__(
        self,
        memory_dir: Path = Path("memory"),
        scan_interval: int = 5,  # seconds between scans (v2.3.5: 3x faster)
        consolidation_threshold: int = 50  # patterns before consolidation
    ):
        self.memory_dir = memory_dir
        self.learn_interval = scan_interval
        self.rust = get_rust_bridge()
        self.running = False
        self.cycles_completed = 0
        self.patterns_discovered = 0
    
    def start_continuous_learning(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._learning_loop, daemon=True)
        self.thread.start()
        print(f"🧠 Rapid cognition started (every {self.learn_interval}s)")
    
    def _learning_loop(self):
        while self.running:
            try:
                if self.rust.available:
                    result = self.rust.lib.extract_patterns(str(self.memory_dir / "long_term"), 0.6)
                    self.patterns_discovered = result[1]
                self.cycles_completed += 1
                time.sleep(self.learn_interval)
            except Exception as e:
                print(f"⚠️  Learning cycle error: {e}")
                time.sleep(self.learn_interval)
    
    def get_stats(self) -> Dict:
        return {
            'running': self.running,
            'cycles': self.cycles_completed,
            'patterns': self.patterns_discovered,
            'rate': f"Every {self.learn_interval}s"
        }

_cognition = None
def start_rapid_learning(interval_seconds: int = 5):
    global _cognition
    if not _cognition:
        _cognition = RapidCognition(learn_interval_seconds=interval_seconds)
    _cognition.start_continuous_learning()
    return _cognition
