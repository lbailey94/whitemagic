"""Cybernetic Loop - Self-Regulating System

Feedback → Analysis → Action → Observation → Feedback

陰陽循環 (Yīn Yáng Xún Huán) - Yin-Yang Cycle
Continuous self-improvement through balanced oscillation
"""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import time

from .yin_phase import YinPhase
from .yang_phase import YangPhase

class CyberneticLoop:
    """Self-regulating Yin-Yang cycle"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(".")
        self.yin = YinPhase(base_dir)
        self.yang = YangPhase(base_dir)
        self.cycle_count = 0
        self.loop_dir = self.base_dir / "memory" / "cybernetic_loops"
        self.loop_dir.mkdir(parents=True, exist_ok=True)
    
    def run_single_cycle(self) -> Dict[str, Any]:
        """Run one complete Yin→Yang cycle"""
        self.cycle_count += 1
        print(f"\n{'='*60}")
        print(f"🔄 Cybernetic Loop: Cycle #{self.cycle_count}")
        print(f"{'='*60}\n")
        
        cycle_start = time.time()
        
        # Yin: Receptive observation
        yin_results = self.yin.run_full_cycle()
        
        print()  # Spacer
        
        # Yang: Active execution
        yang_results = self.yang.run_full_cycle(yin_results)
        
        cycle_duration = time.time() - cycle_start
        
        # Combine results
        cycle_results = {
            'cycle': self.cycle_count,
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': round(cycle_duration, 2),
            'yin': yin_results,
            'yang': yang_results
        }
        
        self._save_cycle(cycle_results)
        
        print(f"\n🔄 Cycle #{self.cycle_count} complete in {cycle_duration:.1f}s")
        print(f"{'='*60}\n")
        
        return cycle_results
    
    def run_continuous(self, max_cycles: int = None, interval_seconds: int = 3600):
        """Run continuous Yin-Yang cycles
        
        Args:
            max_cycles: Maximum cycles to run (None = infinite)
            interval_seconds: Time between cycles (default 1 hour)
        """
        print("🌊 Entering continuous Yin-Yang flow...")
        print(f"   Interval: {interval_seconds}s ({interval_seconds/3600:.1f} hours)")
        if max_cycles:
            print(f"   Max cycles: {max_cycles}")
        else:
            print(f"   Max cycles: ∞ (infinite)")
        
        try:
            while max_cycles is None or self.cycle_count < max_cycles:
                self.run_single_cycle()
                
                if max_cycles and self.cycle_count >= max_cycles:
                    break
                
                print(f"⏸️  Resting {interval_seconds}s before next cycle...")
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Continuous flow stopped by user")
            print(f"   Completed {self.cycle_count} cycles")
    
    def _save_cycle(self, results: Dict[str, Any]):
        """Save complete cycle results"""
        cycle_num = str(self.cycle_count).zfill(4)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cycle_{cycle_num}_{timestamp}.json"
        
        import json
        filepath = self.loop_dir / filename
        filepath.write_text(json.dumps(results, indent=2))

def run_cybernetic_cycle():
    """Run single cybernetic cycle"""
    loop = CyberneticLoop()
    return loop.run_single_cycle()

def run_continuous_loop(max_cycles: int = None, interval_seconds: int = 3600):
    """Run continuous cybernetic loop"""
    loop = CyberneticLoop()
    loop.run_continuous(max_cycles, interval_seconds)
