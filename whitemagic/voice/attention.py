"""
Attention Tracker - Conscious focus tracking

Tracks what the system is paying attention to, enabling awareness of
where focus goes and intentional direction of attention.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass
class Focus:
    """A moment of focused attention"""
    target: str
    started: datetime
    ended: Optional[datetime] = None
    context: Dict[str, Any] = None
    intensity: float = 1.0  # 0-1
    
    def duration_seconds(self) -> Optional[float]:
        """Get focus duration in seconds"""
        if self.ended:
            return (self.ended - self.started).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "started": self.started.isoformat(),
            "ended": self.ended.isoformat() if self.ended else None,
            "context": self.context or {},
            "intensity": self.intensity,
        }


@dataclass
class Intention:
    """An intention for future action"""
    description: str
    created: datetime
    fulfilled: Optional[datetime] = None
    context: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "created": self.created.isoformat(),
            "fulfilled": self.fulfilled.isoformat() if self.fulfilled else None,
            "context": self.context or {},
        }


class AttentionTracker:
    """
    Attention Tracker - Monitor where focus goes
    
    Enables conscious awareness of attention direction and intentional
    focus management.
    """
    
    def __init__(self, log_file: Path):
        """Initialize attention tracker"""
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.current_focus: Optional[Focus] = None
        self.intentions: List[Intention] = []
    
    def track(self, target: str, context: Optional[Dict[str, Any]] = None, intensity: float = 1.0):
        """Track attention on a target"""
        # End previous focus if exists
        if self.current_focus and not self.current_focus.ended:
            self.current_focus.ended = datetime.now()
            self._log_focus(self.current_focus)
        
        # Start new focus
        self.current_focus = Focus(
            target=target,
            started=datetime.now(),
            context=context,
            intensity=intensity,
        )
    
    def end_focus(self):
        """End current focus"""
        if self.current_focus and not self.current_focus.ended:
            self.current_focus.ended = datetime.now()
            self._log_focus(self.current_focus)
            self.current_focus = None
    
    def set_intention(self, description: str, context: Optional[Dict[str, Any]] = None):
        """Set an intention"""
        intention = Intention(
            description=description,
            created=datetime.now(),
            context=context,
        )
        self.intentions.append(intention)
        self._log_intention(intention)
    
    def fulfill_intention(self, description: str):
        """Mark an intention as fulfilled"""
        for intention in self.intentions:
            if intention.description == description and not intention.fulfilled:
                intention.fulfilled = datetime.now()
                self._log_intention(intention)
                break
    
    def get_current_focus(self) -> Optional[str]:
        """Get current focus target"""
        if self.current_focus and not self.current_focus.ended:
            return self.current_focus.target
        return None
    
    def get_recent_focus(self, limit: int = 10) -> List[str]:
        """Get recent focus targets"""
        focuses = []
        if self.log_file.exists():
            with open(self.log_file) as f:
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "focus":
                            focuses.append(entry["target"])
                    except json.JSONDecodeError:
                        continue
        return focuses
    
    def get_pending_intentions(self) -> List[Intention]:
        """Get unfulfilled intentions"""
        return [i for i in self.intentions if not i.fulfilled]
    
    def count_sessions(self) -> int:
        """Count attention tracking sessions"""
        if not self.log_file.exists():
            return 0
        with open(self.log_file) as f:
            return sum(1 for line in f if line.strip())
    
    def _log_focus(self, focus: Focus):
        """Log focus to file"""
        with open(self.log_file, 'a') as f:
            entry = {
                "type": "focus",
                **focus.to_dict()
            }
            f.write(json.dumps(entry) + "\n")
    
    def _log_intention(self, intention: Intention):
        """Log intention to file"""
        with open(self.log_file, 'a') as f:
            entry = {
                "type": "intention",
                **intention.to_dict()
            }
            f.write(json.dumps(entry) + "\n")
