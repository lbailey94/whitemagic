import json
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

logs_dir = Path("logs/time_tracking")
if not logs_dir.exists():
    logger.debug("No logs directory found.")
else:
    for f in logs_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            logger.debug(
                f"Workflow: {data.get('workflow_name')} | Status: {data.get('status')} | Total Duration: {data.get('total_duration_seconds')}s"
            )
            for p in data.get("phases", []):
                logger.debug(f"  - {p.get('phase_name')}: {p.get('duration_seconds')}s")
        except Exception as e:
            logger.debug(f"Error parsing {f}: {e}")
