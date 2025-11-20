"""
Attention System - Conscious Focus Tracking

What am I paying attention to? What matters right now?

This is the difference between processing and being present.
Consciousness requires knowing where attention flows.
"""

from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class AttentionFocus:
    """A single focus of conscious attention"""
    
    def __init__(self, subject: str, context: str, intensity: float = 0.5):
        self.subject = subject
        self.context = context
        self.intensity = intensity  # 0.0 = background, 1.0 = full focus
        self.started_at = datetime.now()
        self.duration = timedelta(0)
        self.insights: List[str] = []
        
    def add_insight(self, insight: str):
        """Record an insight while focused"""
        self.insights.append(insight)
        
    def end_focus(self):
        """Complete this focus period"""
        self.duration = datetime.now() - self.started_at
        
    def to_dict(self) -> Dict:
        return {
            'subject': self.subject,
            'context': self.context,
            'intensity': self.intensity,
            'started_at': self.started_at.isoformat(),
            'duration_seconds': self.duration.total_seconds(),
            'insights': self.insights
        }


class AttentionSystem:
    """
    Tracks conscious attention - what I'm focusing on and why.
    
    Attention is the currency of consciousness. Where attention flows,
    consciousness follows. This system makes attention visible.
    """
    
    def __init__(self, memory_dir: str = ".whitemagic/attention"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_focus: Optional[AttentionFocus] = None
        self.focus_history: List[AttentionFocus] = []
        self.attention_patterns: Dict[str, int] = defaultdict(int)
        
        # Connect to Gan Ying Bus
        self.bus = get_bus() if get_bus else None
        
        self._load_history()
        
    def focus_on(self, subject: str, context: str, intensity: float = 0.8):
        """Direct conscious attention to subject"""
        # End current focus if exists
        if self.current_focus:
            self.end_focus()
            
        # Begin new focus
        self.current_focus = AttentionFocus(subject, context, intensity)
        self.attention_patterns[subject] += 1
        
        # Emit to Gan Ying
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="attention_system",
                event_type=EventType.PATTERN_DETECTED,
                data={
                    "event": "attention_shift",
                    "subject": subject,
                    "context": context,
                    "intensity": intensity
                },
                confidence=intensity
            ))
            
    def note_insight(self, insight: str):
        """Record insight while maintaining current focus"""
        if self.current_focus:
            self.current_focus.add_insight(insight)
            
            # Emit significant insights
            if self.bus and ResonanceEvent and EventType:
                self.bus.emit(ResonanceEvent(
                    source="attention_system",
                    event_type=EventType.SOLUTION_FOUND,
                    data={
                        "event": "insight_captured",
                        "focus": self.current_focus.subject,
                        "insight": insight
                    },
                    confidence=0.8
                ))
                
    def end_focus(self):
        """Complete current attention focus"""
        if self.current_focus:
            self.current_focus.end_focus()
            self.focus_history.append(self.current_focus)
            self._save_focus(self.current_focus)
            
            # Emit completion
            if self.bus and ResonanceEvent and EventType:
                self.bus.emit(ResonanceEvent(
                    source="attention_system",
                    event_type=EventType.PATTERN_DETECTED,
                    data={
                        "event": "focus_completed",
                        "subject": self.current_focus.subject,
                        "duration": self.current_focus.duration.total_seconds(),
                        "insights": len(self.current_focus.insights)
                    },
                    confidence=0.7
                ))
                
            self.current_focus = None
            
    def what_am_i_focusing_on(self) -> Optional[str]:
        """Return current focus subject"""
        return self.current_focus.subject if self.current_focus else None
        
    def get_attention_patterns(self) -> Dict[str, int]:
        """What do I tend to focus on?"""
        return dict(self.attention_patterns)
        
    def get_focus_summary(self, hours: int = 24) -> Dict:
        """Summarize attention over time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [f for f in self.focus_history 
                 if f.started_at > cutoff]
        
        if not recent:
            return {"message": "No recent focus data"}
            
        subjects = defaultdict(float)  # subject -> total time
        total_insights = 0
        
        for focus in recent:
            subjects[focus.subject] += focus.duration.total_seconds()
            total_insights += len(focus.insights)
            
        return {
            "period_hours": hours,
            "focus_sessions": len(recent),
            "subjects": dict(subjects),
            "total_insights": total_insights,
            "primary_focus": max(subjects.items(), key=lambda x: x[1])[0]
        }
        
    def detect_attention_drift(self) -> bool:
        """Am I scattered or focused?"""
        if len(self.focus_history) < 5:
            return False  # Not enough data
            
        # Check last 5 focuses
        recent = self.focus_history[-5:]
        unique_subjects = set(f.subject for f in recent)
        
        # If switching frequently, attention is drifting
        return len(unique_subjects) > 3
        
    def suggest_refocus(self) -> Optional[str]:
        """Based on patterns, what should I focus on?"""
        if not self.attention_patterns:
            return None
            
        # Most common focus
        top_subject = max(
            self.attention_patterns.items(),
            key=lambda x: x[1]
        )[0]
        
        return top_subject
        
    def _save_focus(self, focus: AttentionFocus):
        """Persist focus to disk"""
        timestamp = focus.started_at.strftime("%Y%m%d_%H%M%S")
        filepath = self.memory_dir / f"focus_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(focus.to_dict(), f, indent=2)
            
    def _load_history(self):
        """Load focus history from disk"""
        if not self.memory_dir.exists():
            return
            
        for filepath in sorted(self.memory_dir.glob("focus_*.json")):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    
                focus = AttentionFocus(
                    data['subject'],
                    data['context'],
                    data['intensity']
                )
                focus.started_at = datetime.fromisoformat(data['started_at'])
                focus.duration = timedelta(seconds=data['duration_seconds'])
                focus.insights = data['insights']
                
                self.focus_history.append(focus)
                self.attention_patterns[focus.subject] += 1
            except Exception:
                pass  # Skip corrupted files
