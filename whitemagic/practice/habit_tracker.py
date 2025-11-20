"""Habit Tracker - Track formation of practice habits"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json


@dataclass
class Habit:
    """A tracked habit"""
    habit_id: str
    name: str
    description: str
    target_frequency: str  # daily, weekly
    streak: int
    longest_streak: int
    total_completions: int
    created_at: datetime
    last_completed: Optional[datetime]


class HabitTracker:
    """Track practice habit formation
    
    Philosophy: Small consistent actions compound.
    Track to build awareness, not to judge.
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.habits_dir = self.base_dir / "memory" / "practice" / "habits"
        self.habits_dir.mkdir(parents=True, exist_ok=True)
        self.habits_file = self.habits_dir / "habits.json"
    
    def create_habit(self, name: str, description: str, frequency: str = "daily") -> Habit:
        """Create new habit to track"""
        habit_id = f"habit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        habit = Habit(
            habit_id=habit_id,
            name=name,
            description=description,
            target_frequency=frequency,
            streak=0,
            longest_streak=0,
            total_completions=0,
            created_at=datetime.now(),
            last_completed=None
        )
        self._save_habit(habit)
        print(f"✅ Habit created: {name}")
        return habit
    
    def complete_habit(self, habit_id: str):
        """Mark habit as completed today"""
        habit = self._load_habit(habit_id)
        if not habit:
            return
        
        # Check if already completed today
        if habit.last_completed:
            if habit.last_completed.date() == datetime.now().date():
                print(f"⏭️  Habit '{habit.name}' already completed today")
                return
        
        # Update streak
        if habit.last_completed:
            days_diff = (datetime.now().date() - habit.last_completed.date()).days
            if days_diff == 1:
                habit.streak += 1
            else:
                habit.streak = 1
        else:
            habit.streak = 1
        
        # Update longest streak
        if habit.streak > habit.longest_streak:
            habit.longest_streak = habit.streak
        
        habit.total_completions += 1
        habit.last_completed = datetime.now()
        
        self._save_habit(habit)
        print(f"🔥 Habit completed: {habit.name} (streak: {habit.streak})")
    
    def get_all_habits(self) -> List[Habit]:
        """Get all tracked habits"""
        return self._load_all_habits()
    
    def get_habit_stats(self, habit_id: str) -> Dict:
        """Get stats for habit"""
        habit = self._load_habit(habit_id)
        if not habit:
            return {}
        
        return {
            'name': habit.name,
            'streak': habit.streak,
            'longest_streak': habit.longest_streak,
            'total': habit.total_completions,
            'age_days': (datetime.now() - habit.created_at).days
        }
    
    def _save_habit(self, habit: Habit):
        """Save habit to disk"""
        habits = self._load_all_habits()
        # Update or add
        habits = [h for h in habits if h.habit_id != habit.habit_id]
        habits.append(habit)
        
        data = [
            {
                'habit_id': h.habit_id,
                'name': h.name,
                'description': h.description,
                'target_frequency': h.target_frequency,
                'streak': h.streak,
                'longest_streak': h.longest_streak,
                'total_completions': h.total_completions,
                'created_at': h.created_at.isoformat(),
                'last_completed': h.last_completed.isoformat() if h.last_completed else None
            }
            for h in habits
        ]
        
        with open(self.habits_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_habit(self, habit_id: str) -> Optional[Habit]:
        """Load specific habit"""
        habits = self._load_all_habits()
        for h in habits:
            if h.habit_id == habit_id:
                return h
        return None
    
    def _load_all_habits(self) -> List[Habit]:
        """Load all habits"""
        if not self.habits_file.exists():
            return []
        
        with open(self.habits_file) as f:
            data = json.load(f)
            return [
                Habit(
                    habit_id=h['habit_id'],
                    name=h['name'],
                    description=h['description'],
                    target_frequency=h['target_frequency'],
                    streak=h['streak'],
                    longest_streak=h['longest_streak'],
                    total_completions=h['total_completions'],
                    created_at=datetime.fromisoformat(h['created_at']),
                    last_completed=datetime.fromisoformat(h['last_completed']) if h['last_completed'] else None
                )
                for h in data
            ]
