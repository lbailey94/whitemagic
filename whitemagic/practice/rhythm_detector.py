"""Rhythm Detector - Detect natural work rhythms"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import json


class RhythmDetector:
    """Detect natural work rhythms and patterns
    
    Philosophy: Honor natural rhythms rather than forcing schedules.
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.rhythm_dir = self.base_dir / "memory" / "practice"
        self.rhythm_dir.mkdir(parents=True, exist_ok=True)
        self.activity_log = self.rhythm_dir / "activity_log.json"
    
    def log_activity(self, activity_type: str, duration_minutes: int):
        """Log an activity"""
        entry = {
            'type': activity_type,
            'timestamp': datetime.now().isoformat(),
            'duration': duration_minutes,
            'hour': datetime.now().hour
        }
        
        activities = self._load_activities()
        activities.append(entry)
        
        with open(self.activity_log, 'w') as f:
            json.dump(activities, f, indent=2)
    
    def detect_peak_hours(self) -> Dict[str, List[int]]:
        """Detect peak productivity hours"""
        activities = self._load_activities()
        if not activities:
            return {'peak_hours': []}
        
        # Count activities by hour
        hour_counts = {}
        for activity in activities:
            hour = activity.get('hour', 0)
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Find peak hours (top 3)
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        peak_hours = [h for h, _ in sorted_hours[:3]]
        
        return {
            'peak_hours': peak_hours,
            'distribution': hour_counts
        }
    
    def suggest_optimal_schedule(self) -> Dict[str, str]:
        """Suggest optimal schedule based on detected rhythms"""
        peak = self.detect_peak_hours()
        peak_hours = peak['peak_hours']
        
        if not peak_hours:
            return {
                'yin': '6:00-12:00',
                'yang': '12:00-18:00',
                'dream': '18:00-23:00'
            }
        
        # Align phases with detected peaks
        return {
            'yin': 'Morning reflection',
            'yang': f'Peak hours: {peak_hours}',
            'dream': 'Evening synthesis',
            'recommendation': f'Focus deep work during hours: {peak_hours}'
        }
    
    def _load_activities(self) -> List[Dict]:
        """Load activity log"""
        if not self.activity_log.exists():
            return []
        with open(self.activity_log) as f:
            return json.load(f)
