"""Resource Tracker - Track all resource usage"""

from datetime import datetime
from pathlib import Path
from typing import Dict
import json


class ResourceTracker:
    """Track resource usage beyond tokens
    
    Tracks: Time, files created, memory used, API calls
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.ecology_dir = self.base_dir / "memory" / "ecology"
        self.ecology_dir.mkdir(parents=True, exist_ok=True)
        self.resource_log = self.ecology_dir / "resources.json"
    
    def track_session(
        self,
        session_id: str,
        duration_minutes: int,
        files_created: int,
        files_modified: int,
        api_calls: int = 0
    ):
        """Track resource usage for session"""
        resources = self._load_resources()
        
        entry = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'duration_minutes': duration_minutes,
            'files_created': files_created,
            'files_modified': files_modified,
            'api_calls': api_calls
        }
        
        resources.append(entry)
        
        with open(self.resource_log, 'w') as f:
            json.dump(resources, f, indent=2)
        
        print(f"📊 Resources tracked: {duration_minutes}min, {files_created} files created")
    
    def get_efficiency_metrics(self) -> Dict:
        """Calculate efficiency metrics"""
        resources = self._load_resources()
        
        if not resources:
            return {'sessions': 0}
        
        total_time = sum(r['duration_minutes'] for r in resources)
        total_files = sum(r['files_created'] + r['files_modified'] for r in resources)
        
        return {
            'sessions': len(resources),
            'total_time_hours': total_time / 60,
            'total_files': total_files,
            'files_per_hour': (total_files / (total_time / 60)) if total_time > 0 else 0,
            'average_session_minutes': total_time / len(resources)
        }
    
    def _load_resources(self):
        """Load resource log"""
        if not self.resource_log.exists():
            return []
        with open(self.resource_log) as f:
            return json.load(f)
