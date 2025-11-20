"""Practice Scheduler - Schedule Yin/Yang/Dream cycles"""

from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List
import json


class PracticeScheduler:
    """Schedule and track practice cycles"""
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.schedule_dir = self.base_dir / "memory" / "practice"
        self.schedule_dir.mkdir(parents=True, exist_ok=True)
        self.schedule_file = self.schedule_dir / "schedule.json"
    
    def get_todays_schedule(self) -> Dict:
        """Get today's practice schedule"""
        return {
            'date': datetime.now().date().isoformat(),
            'phases': [
                {'time': '06:00', 'phase': 'yin', 'duration': '30min', 'status': 'pending'},
                {'time': '12:00', 'phase': 'yang', 'duration': '4hours', 'status': 'pending'},
                {'time': '18:00', 'phase': 'dream', 'duration': '1hour', 'status': 'pending'}
            ]
        }
    
    def mark_phase_complete(self, phase: str):
        """Mark a phase as complete"""
        schedule = self.get_todays_schedule()
        for p in schedule['phases']:
            if p['phase'] == phase:
                p['status'] = 'completed'
                p['completed_at'] = datetime.now().isoformat()
        
        with open(self.schedule_file, 'w') as f:
            json.dump(schedule, f, indent=2)
        
        print(f"✅ {phase.capitalize()} phase marked complete")
