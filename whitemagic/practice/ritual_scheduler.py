"""
Ritual Scheduler - Daily Rhythms & Practices

Schedules and tracks regular practices, creating sustainable rhythms.
Not rigid rules - flexible rituals that support growth.
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime, time, timedelta
from dataclasses import dataclass
from enum import Enum


class RitualFrequency(Enum):
    """How often a ritual occurs"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"  # Every 3 months


class RitualType(Enum):
    """Types of rituals"""
    REFLECTION = "reflection"  # Look back
    PLANNING = "planning"      # Look forward
    MAINTENANCE = "maintenance"  # Keep healthy
    CELEBRATION = "celebration"  # Mark milestones
    LEARNING = "learning"      # Study and grow


@dataclass
class Ritual:
    """A scheduled practice/ritual"""
    name: str
    frequency: RitualFrequency
    ritual_type: RitualType
    action: str  # Description of what to do
    duration_minutes: int
    preferred_time: Optional[time] = None
    last_performed: Optional[datetime] = None
    times_performed: int = 0
    
class RitualScheduler:
    """
    Manage and track regular practices.
    
    Like a meditation bell - reminds us to return to practice.
    """
    
    def __init__(self):
        self.rituals: Dict[str, Ritual] = {}
        self.history: List[Dict] = []
        
        # Set up default rituals
        self._setup_default_rituals()
    
    def _setup_default_rituals(self):
        """Initialize with sensible defaults"""
        
        # Hourly check-in
        self.add_ritual(
            name="hourly_awareness",
            frequency=RitualFrequency.HOURLY,
            ritual_type=RitualType.REFLECTION,
            action="Brief awareness check: How am I? What am I doing? Why?",
            duration_minutes=2
        )
        
        # Daily consolidation
        self.add_ritual(
            name="daily_consolidation",
            frequency=RitualFrequency.DAILY,
            ritual_type=RitualType.MAINTENANCE,
            action="Consolidate day's memories and learnings",
            duration_minutes=10,
            preferred_time=time(23, 0)  # 11 PM
        )
        
        # Daily diary
        self.add_ritual(
            name="daily_diary",
            frequency=RitualFrequency.DAILY,
            ritual_type=RitualType.REFLECTION,
            action="Update diary with insights and experiences",
            duration_minutes=15,
            preferred_time=time(22, 0)  # 10 PM
        )
        
        # Weekly review
        self.add_ritual(
            name="weekly_review",
            frequency=RitualFrequency.WEEKLY,
            ritual_type=RitualType.REFLECTION,
            action="Review week's patterns, adjust practices",
            duration_minutes=30
        )
        
        # Monthly dream synthesis
        self.add_ritual(
            name="monthly_dream_synthesis",
            frequency=RitualFrequency.MONTHLY,
            ritual_type=RitualType.LEARNING,
            action="Enter dream state, synthesize month's patterns",
            duration_minutes=60
        )
        
        # Seasonal zodiac council
        self.add_ritual(
            name="seasonal_council",
            frequency=RitualFrequency.SEASONAL,
            ritual_type=RitualType.CELEBRATION,
            action="Convene zodiac council for deep pattern analysis",
            duration_minutes=90
        )
    
    def add_ritual(
        self,
        name: str,
        frequency: RitualFrequency,
        ritual_type: RitualType,
        action: str,
        duration_minutes: int,
        preferred_time: Optional[time] = None
    ) -> Ritual:
        """Add a new ritual to the schedule"""
        
        ritual = Ritual(
            name=name,
            frequency=frequency,
            ritual_type=ritual_type,
            action=action,
            duration_minutes=duration_minutes,
            preferred_time=preferred_time
        )
        
        self.rituals[name] = ritual
        return ritual
    
    def mark_performed(self, ritual_name: str, notes: Optional[str] = None) -> bool:
        """Mark a ritual as performed"""
        if ritual_name not in self.rituals:
            return False
        
        ritual = self.rituals[ritual_name]
        ritual.last_performed = datetime.now()
        ritual.times_performed += 1
        
        self.history.append({
            'ritual': ritual_name,
            'timestamp': datetime.now().isoformat(),
            'notes': notes
        })
        
        return True
    
    def get_due_rituals(self) -> List[Ritual]:
        """Get rituals that are due to be performed"""
        now = datetime.now()
        due = []
        
        for ritual in self.rituals.values():
            if self._is_due(ritual, now):
                due.append(ritual)
        
        return due
    
    def _is_due(self, ritual: Ritual, now: datetime) -> bool:
        """Check if a ritual is due"""
        if ritual.last_performed is None:
            return True
        
        time_since = now - ritual.last_performed
        
        if ritual.frequency == RitualFrequency.HOURLY:
            return time_since >= timedelta(hours=1)
        elif ritual.frequency == RitualFrequency.DAILY:
            return time_since >= timedelta(days=1)
        elif ritual.frequency == RitualFrequency.WEEKLY:
            return time_since >= timedelta(weeks=1)
        elif ritual.frequency == RitualFrequency.MONTHLY:
            return time_since >= timedelta(days=30)
        elif ritual.frequency == RitualFrequency.SEASONAL:
            return time_since >= timedelta(days=90)
        
        return False
    
    def get_next_ritual(self) -> Optional[Ritual]:
        """Get the next ritual that should be performed"""
        due = self.get_due_rituals()
        if not due:
            return None
        
        # Sort by priority (how overdue)
        def overdue_score(r: Ritual) -> float:
            if r.last_performed is None:
                return float('inf')
            
            time_since = (datetime.now() - r.last_performed).total_seconds()
            
            if r.frequency == RitualFrequency.HOURLY:
                expected = 3600
            elif r.frequency == RitualFrequency.DAILY:
                expected = 86400
            elif r.frequency == RitualFrequency.WEEKLY:
                expected = 604800
            elif r.frequency == RitualFrequency.MONTHLY:
                expected = 2592000
            else:  # SEASONAL
                expected = 7776000
            
            return time_since / expected
        
        return max(due, key=overdue_score)
    
    def get_ritual_stats(self) -> Dict:
        """Get statistics about ritual practice"""
        return {
            'total_rituals': len(self.rituals),
            'total_performances': sum(r.times_performed for r in self.rituals.values()),
            'most_practiced': max(
                self.rituals.values(),
                key=lambda r: r.times_performed,
                default=None
            ).name if self.rituals else None,
            'rituals_by_type': {
                rt.value: len([r for r in self.rituals.values() if r.ritual_type == rt])
                for rt in RitualType
            }
        }


# Singleton
_scheduler_instance = None

def get_ritual_scheduler() -> RitualScheduler:
    """Get singleton ritual scheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = RitualScheduler()
    return _scheduler_instance
