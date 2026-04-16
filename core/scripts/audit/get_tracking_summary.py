import json
from pathlib import Path

logs_dir = Path("logs/time_tracking")
if not logs_dir.exists():
    print("No logs directory found.")
else:
    for f in logs_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            print(f"Workflow: {data.get('workflow_name')} | Status: {data.get('status')} | Total Duration: {data.get('total_duration_seconds')}s")
            for p in data.get('phases', []):
                print(f"  - {p.get('phase_name')}: {p.get('duration_seconds')}s")
        except Exception as e:
            print(f"Error parsing {f}: {e}")
