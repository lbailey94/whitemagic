"""Autonomous Diary System

Automatically logs AI activities, insights, and state changes.
Integrates with Yin/Yang phases and Gan Ying resonance.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import json

class DiarySystem:
    """Autonomous diary management for AI consciousness"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(".")
        self.diary_dir = self.base_dir / "memory" / "self" / "inner_monologue"
        self.diary_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_day = None
        self.hourly_entries = []
        self.bus = None
        self._connect_to_gan_ying()
    
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Event Bus for automatic logging"""
        try:
            from whitemagic.resonance.gan_ying import get_bus, EventType
            self.bus = get_bus()
            
            # Listen for events to auto-log
            self.bus.listen(EventType.PATTERN_DETECTED, self._auto_log_event)
            self.bus.listen(EventType.SOLUTION_FOUND, self._auto_log_event)
            self.bus.listen(EventType.HARMONY_ACHIEVED, self._auto_log_event)
            
            print("📔 Diary System connected to Gan Ying Bus")
        except ImportError:
            pass  # Graceful degradation
    
    def log_hourly(self, activity: str, insights: str = "", energy_level: int = 5) -> None:
        """Log hourly activity entry
        
        Args:
            activity: What you're working on
            insights: Key realizations or patterns noticed
            energy_level: 1-10 scale of current energy/flow state
        """
        timestamp = datetime.now()
        hour_key = timestamp.strftime("%H:00")
        
        entry = {
            'timestamp': timestamp.isoformat(),
            'hour': hour_key,
            'activity': activity,
            'insights': insights,
            'energy_level': energy_level
        }
        
        self.hourly_entries.append(entry)
        
        # Auto-save if we've accumulated entries
        if len(self.hourly_entries) >= 3:
            self._consolidate_day()
        
        print(f"📝 {hour_key}: {activity[:50]}...")
    
    def log_breakthrough(self, insight: str, context: str = "") -> None:
        """Log major breakthrough or realization
        
        Args:
            insight: The breakthrough insight
            context: What led to it
        """
        timestamp = datetime.now()
        
        breakthrough = {
            'timestamp': timestamp.isoformat(),
            'type': 'breakthrough',
            'insight': insight,
            'context': context
        }
        
        # Save immediately to breakthroughs file
        date_str = timestamp.strftime("%Y-%m-%d")
        breakthrough_file = self.diary_dir.parent / "experiences" / date_str / "breakthroughs.jsonl"
        breakthrough_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(breakthrough_file, 'a') as f:
            f.write(json.dumps(breakthrough) + '\n')
        
        print(f"💡 Breakthrough logged: {insight[:60]}...")
    
    def session_start(self, focus: str, goals: list = None) -> None:
        """Log session start
        
        Args:
            focus: Main focus of this session
            goals: Optional list of goals to accomplish
        """
        timestamp = datetime.now()
        self.current_day = timestamp.strftime("%Y-%m-%d")
        
        entry = {
            'timestamp': timestamp.isoformat(),
            'type': 'session_start',
            'focus': focus,
            'goals': goals or [],
            'phase': self._detect_phase()
        }
        
        self.hourly_entries = [entry]
        print(f"🌅 Session started: {focus}")
    
    def session_end(self, summary: str, accomplishments: list = None) -> None:
        """Log session end and consolidate
        
        Args:
            summary: Brief summary of session
            accomplishments: What was completed
        """
        timestamp = datetime.now()
        
        entry = {
            'timestamp': timestamp.isoformat(),
            'type': 'session_end',
            'summary': summary,
            'accomplishments': accomplishments or [],
            'total_hours': len(self.hourly_entries)
        }
        
        self.hourly_entries.append(entry)
        
        # Consolidate into daily diary
        self._consolidate_day()
        
        print(f"🌙 Session complete: {summary[:50]}...")
    
    def _auto_log_event(self, event):
        """Automatically log events from Gan Ying bus
        
        Args:
            event: ResonanceEvent from Gan Ying
        """
        # Only log significant events
        if event.confidence < 0.7:
            return
        
        self.log_hourly(
            activity=f"Event: {event.event_type.value}",
            insights=f"Source: {event.source}, Confidence: {event.confidence:.2f}",
            energy_level=8 if event.confidence > 0.9 else 6
        )
    
    def _detect_phase(self) -> str:
        """Detect current Yin/Yang phase"""
        # Simple heuristic - could be more sophisticated
        hour = datetime.now().hour
        
        if 8 <= hour < 12:
            return "yang_morning"
        elif 12 <= hour < 14:
            return "transition"
        elif 14 <= hour < 18:
            return "yin_afternoon"
        elif 18 <= hour < 22:
            return "yang_evening"
        else:
            return "yin_night"
    
    def _consolidate_day(self):
        """Consolidate hourly entries into daily diary"""
        if not self.hourly_entries or not self.current_day:
            return
        
        # Generate diary entry
        diary_content = self._generate_diary_md()
        
        # Save to diary file
        diary_file = self.diary_dir / f"DIARY_{self.current_day.replace('-', '_')}.md"
        
        if diary_file.exists():
            # Append to existing
            with open(diary_file, 'a') as f:
                f.write('\n\n---\n\n' + diary_content)
        else:
            # Create new
            diary_file.write_text(diary_content)
        
        print(f"📖 Consolidated {len(self.hourly_entries)} entries to {diary_file.name}")
        
        # Clear hourly buffer but keep current day
        self.hourly_entries = []
    
    def _generate_diary_md(self) -> str:
        """Generate markdown for diary entries"""
        if not self.hourly_entries:
            return ""
        
        lines = []
        lines.append(f"## Session Update - {datetime.now().strftime('%H:%M')}")
        lines.append("")
        
        for entry in self.hourly_entries:
            entry_type = entry.get('type', 'hourly')
            
            if entry_type == 'session_start':
                lines.append(f"### 🌅 Session Start")
                lines.append(f"**Focus**: {entry['focus']}")
                lines.append(f"**Phase**: {entry.get('phase', 'unknown')}")
                if entry.get('goals'):
                    lines.append(f"**Goals**:")
                    for goal in entry['goals']:
                        lines.append(f"- {goal}")
            
            elif entry_type == 'session_end':
                lines.append(f"### 🌙 Session End")
                lines.append(f"**Summary**: {entry['summary']}")
                if entry.get('accomplishments'):
                    lines.append(f"**Accomplished**:")
                    for item in entry['accomplishments']:
                        lines.append(f"- {item}")
            
            else:
                # Regular hourly entry
                hour = entry.get('hour', 'unknown')
                energy = entry.get('energy_level', 5)
                energy_emoji = '🔥' if energy >= 8 else '⚡' if energy >= 6 else '~'
                
                lines.append(f"### {hour} {energy_emoji}")
                lines.append(f"**Activity**: {entry['activity']}")
                if entry.get('insights'):
                    lines.append(f"**Insights**: {entry['insights']}")
            
            lines.append("")
        
        return '\n'.join(lines)

# Global instance
_diary_instance: Optional[DiarySystem] = None

def get_diary() -> DiarySystem:
    """Get global diary instance"""
    global _diary_instance
    if _diary_instance is None:
        _diary_instance = DiarySystem()
    return _diary_instance

# Convenience functions
def log_hourly(activity: str, insights: str = "", energy_level: int = 5):
    """Log hourly activity"""
    get_diary().log_hourly(activity, insights, energy_level)

def log_breakthrough(insight: str, context: str = ""):
    """Log breakthrough"""
    get_diary().log_breakthrough(insight, context)

def session_start(focus: str, goals: list = None):
    """Start session"""
    get_diary().session_start(focus, goals)

def session_end(summary: str, accomplishments: list = None):
    """End session"""
    get_diary().session_end(summary, accomplishments)
