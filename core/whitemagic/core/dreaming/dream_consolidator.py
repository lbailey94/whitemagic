"""Dream Consolidator — Nightly promotion and expiration of dream artifacts.

Scans the dreams directory and:
  1. Promotes high-revisit incubating dreams to memories
  2. Expires old unvisited dreams
  3. Archives dreams that have been reconsidered but not promoted

Usage:
    from whitemagic.core.dreaming.dream_consolidator import DreamConsolidator
    cons = DreamConsolidator()
    report = cons.consolidate()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from whitemagic.core.dreaming.dream_artifacts import (
    _dreams_dir,
    archive_dream,
    expire_dream,
    promote_dream,
)

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationReport:
    """Result of a consolidation pass."""

    promoted: list[str] = field(default_factory=list)
    expired: list[str] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)
    skipped: int = 0
    errors: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "promoted": self.promoted,
            "expired": self.expired,
            "archived": self.archived,
            "skipped": self.skipped,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


class DreamConsolidator:
    """Periodically evaluates dream artifacts and transitions their status."""

    # Configurable thresholds
    PROMOTE_MIN_REVISITS = 3
    PROMOTE_MAX_AGE_DAYS = 7
    EXPIRE_MIN_AGE_DAYS = 30
    ARCHIVE_AFTER_DAYS = 14

    def __init__(
        self,
        promote_min_revisits: int | None = None,
        promote_max_age_days: int | None = None,
        expire_min_age_days: int | None = None,
        archive_after_days: int | None = None,
    ) -> None:
        self.promote_min_revisits = promote_min_revisits or self.PROMOTE_MIN_REVISITS
        self.promote_max_age_days = promote_max_age_days or self.PROMOTE_MAX_AGE_DAYS
        self.expire_min_age_days = expire_min_age_days or self.EXPIRE_MIN_AGE_DAYS
        self.archive_after_days = archive_after_days or self.ARCHIVE_AFTER_DAYS

    def consolidate(self) -> ConsolidationReport:
        """Run one consolidation pass over all dream artifacts."""
        report = ConsolidationReport()
        dreams_dir = _dreams_dir()
        now = datetime.now(UTC)

        import yaml

        for path in dreams_dir.glob("*.yaml"):
            try:
                with open(path, encoding="utf-8") as fp:
                    data = yaml.safe_load(fp)
                if not data:
                    continue

                dream_id = data.get("dream_id", "")
                status = data.get("status", "incubating")
                revisit_count = data.get("revisit_count", 0)
                created_at_str = data.get("created_at")
                last_revisited_str = data.get("last_revisited")

                try:
                    created_at = datetime.fromisoformat(created_at_str) if created_at_str else now
                except Exception:
                    created_at = now

                try:
                    last_revisited = datetime.fromisoformat(last_revisited_str) if last_revisited_str else created_at
                except Exception:
                    last_revisited = created_at

                age_days = (now - created_at).total_seconds() / 86400.0
                idle_days = (now - last_revisited).total_seconds() / 86400.0

                if status == "incubating":
                    if revisit_count >= self.promote_min_revisits and age_days <= self.promote_max_age_days:
                        result = promote_dream(dream_id)
                        if result:
                            report.promoted.append(dream_id)
                            logger.info(f"Promoted dream {dream_id} (revisits={revisit_count})")
                        else:
                            report.errors += 1
                    elif idle_days >= self.archive_after_days:
                        result = archive_dream(dream_id)
                        if result:
                            report.archived.append(dream_id)
                            logger.info(f"Archived dream {dream_id} (idle={idle_days:.1f}d)")
                        else:
                            report.errors += 1
                    else:
                        report.skipped += 1

                elif status == "archived":
                    if age_days >= self.expire_min_age_days:
                        result = expire_dream(dream_id)
                        if result:
                            report.expired.append(dream_id)
                            logger.info(f"Expired dream {dream_id} (age={age_days:.1f}d)")
                        else:
                            report.errors += 1
                    else:
                        report.skipped += 1

                elif status in ("promoted", "expired", "reconsidered"):
                    report.skipped += 1

            except Exception as exc:
                logger.warning(f"Consolidation error for {path.name}: {exc}")
                report.errors += 1

        return report
