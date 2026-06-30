# ruff: noqa: BLE001
"""Daily narrative automation — starts daily narrative stream on access."""

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


def check_daily_journal() -> dict[str, str]:
    """Check if daily journal should be started."""
    today = date.today().isoformat()
    try:
        from whitemagic.config.paths import get_state_root

        journal_dir = get_state_root() / "narrative"
        journal_dir.mkdir(parents=True, exist_ok=True)
        journal_file = journal_dir / f"journal_{today}.md"

        if journal_file.exists():
            return {"status": "exists", "date": today, "path": str(journal_file)}

        journal_file.write_text(f"# Daily Narrative — {today}\n\n")
        return {"status": "created", "date": today, "path": str(journal_file)}
    except Exception as e:
        logger.debug("Daily journal check failed: %s", e)
        return {"status": "error", "error": str(e)}
