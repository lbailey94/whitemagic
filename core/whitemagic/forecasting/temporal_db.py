"""TemporalForecastDB — SQLite-backed prediction ledger with Brier scoring.

Stores predictions with their source timestamp, confidence, and eventual
outcome, then computes calibration metrics and the prescience score.

Schema
------
predictions
  id            TEXT PK     UUID
  claim         TEXT        Human-readable description
  source_date   TEXT        ISO-8601 date when claim was first made
  source_ref    TEXT        Archive ID / file path / URL
  confidence    REAL        Predicted probability [0, 1]
  category      TEXT        Domain tag (e.g. 'ai_governance', 'ai_hardware')
  status        TEXT        'pending' | 'validated' | 'falsified' | 'expired'
  validation_date TEXT      ISO-8601 date of public validation event (nullable)
  validation_ref  TEXT      URL / citation for the validation event (nullable)
  lead_weeks    REAL        Weeks between source_date and validation_date (nullable)
  points        REAL        lead_weeks (1 week = 1 point) (nullable)
  notes         TEXT        Free-form notes
  created_at    TEXT        Row insertion timestamp

The 15 validated claims from the 2026-05-26 prescience audit are seeded
automatically on first open (idempotent — safe to call multiple times).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from whitemagic.config.paths import get_state_root

_SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id              TEXT PRIMARY KEY,
    claim           TEXT NOT NULL,
    source_date     TEXT NOT NULL,
    source_ref      TEXT NOT NULL DEFAULT '',
    confidence           REAL NOT NULL DEFAULT 0.7,
    behavioral_confidence REAL,
    category             TEXT NOT NULL DEFAULT 'general',
    status          TEXT NOT NULL DEFAULT 'pending',
    validation_date TEXT,
    validation_ref  TEXT,
    lead_weeks      REAL,
    points          REAL,
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_predictions_status   ON predictions(status);
CREATE INDEX IF NOT EXISTS idx_predictions_category ON predictions(category);
CREATE INDEX IF NOT EXISTS idx_predictions_source   ON predictions(source_date);
"""

def _load_seed_claims() -> list[dict[str, Any]]:
    """Load validated prescience claims from YAML, with inline fallback."""
    yaml_path = Path(__file__).with_suffix("").parent / "prescience_claims.yaml"
    if yaml_path.exists():
        with open(yaml_path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or []
    # Fallback — should never hit if package is installed correctly
    return []


def _db_path() -> Path:
    state_root = get_state_root()
    forecasting_dir = state_root / "forecasting"
    forecasting_dir.mkdir(parents=True, exist_ok=True)
    return forecasting_dir / "predictions.db"


class TemporalForecastDB:
    """SQLite-backed ledger for tracking predictions and calibration over time.

    Usage
    -----
    db = TemporalForecastDB()
    db.seed_validated_claims()   # idempotent — load the 14 audited claims
    summary = db.summary()
    print(summary)
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _db_path()
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def seed_validated_claims(self) -> int:
        """Insert the audited prescience claims from YAML (idempotent by source_ref).

        Returns:
            Number of new rows inserted (0 if already seeded).
        """
        claims = _load_seed_claims()
        if not claims:
            raise RuntimeError(
                "No seed claims found. Ensure prescience_claims.yaml is present "
                "in the forecasting package directory."
            )
        inserted = 0
        with self._conn() as conn:
            for claim in claims:
                exists = conn.execute(
                    "SELECT 1 FROM predictions WHERE source_ref = ?",
                    (claim["source_ref"],),
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    """
                    INSERT INTO predictions
                      (id, claim, source_date, source_ref, confidence, behavioral_confidence, category,
                       status, validation_date, validation_ref, lead_weeks,
                       points, notes, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid.uuid4()),
                        claim["claim"],
                        claim["source_date"],
                        claim["source_ref"],
                        claim["confidence"],
                        claim.get("behavioral_confidence"),
                        claim["category"],
                        claim["status"],
                        claim.get("validation_date"),
                        claim.get("validation_ref"),
                        claim.get("lead_weeks"),
                        claim.get("points"),
                        claim.get("notes", ""),
                        datetime.utcnow().isoformat(),
                    ),
                )
                inserted += 1
        return inserted

    def add_prediction(
        self,
        claim: str,
        source_date: str | date,
        confidence: float,
        source_ref: str = "",
        category: str = "general",
        notes: str = "",
    ) -> str:
        """Add a new pending prediction.

        Args:
            claim: Human-readable description.
            source_date: ISO-8601 date string or date object.
            confidence: Probability in [0, 1].
            source_ref: Archive ID / file path / URL for the source.
            category: Domain tag.
            notes: Free-form notes.

        Returns:
            UUID of the inserted row.
        """
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {confidence}")
        pred_id = str(uuid.uuid4())
        source_str = source_date.isoformat() if isinstance(source_date, date) else source_date
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO predictions
                  (id, claim, source_date, source_ref, confidence, category,
                   status, notes, created_at)
                VALUES (?,?,?,?,?,?,'pending',?,?)
                """,
                (
                    pred_id, claim, source_str, source_ref,
                    confidence, category, notes,
                    datetime.utcnow().isoformat(),
                ),
            )
        return pred_id

    def validate(
        self,
        prediction_id: str,
        validation_date: str | date,
        validation_ref: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Mark a pending prediction as validated and compute lead time + points.

        Args:
            prediction_id: UUID from add_prediction.
            validation_date: Date the prediction was publicly confirmed.
            validation_ref: URL / citation for the validation.
            notes: Additional notes.

        Returns:
            Dict with lead_weeks and points fields.
        """
        val_str = (
            validation_date.isoformat()
            if isinstance(validation_date, date)
            else validation_date
        )
        with self._conn() as conn:
            row = conn.execute(
                "SELECT source_date FROM predictions WHERE id = ?",
                (prediction_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Prediction {prediction_id} not found")

            src = date.fromisoformat(row["source_date"])
            val = date.fromisoformat(val_str)
            delta_days = (val - src).days
            lead_weeks = delta_days / 7.0
            points = float(max(0, int(lead_weeks)))

            conn.execute(
                """
                UPDATE predictions
                SET status          = 'validated',
                    validation_date = ?,
                    validation_ref  = ?,
                    lead_weeks      = ?,
                    points          = ?,
                    notes           = notes || ?
                WHERE id = ?
                """,
                (
                    val_str,
                    validation_ref,
                    lead_weeks,
                    points,
                    f"\n[validated] {notes}" if notes else "",
                    prediction_id,
                ),
            )
        return {"lead_weeks": lead_weeks, "points": points}

    def falsify(self, prediction_id: str, notes: str = "") -> None:
        """Mark a pending prediction as falsified."""
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE predictions SET status = 'falsified',
                notes = notes || ?
                WHERE id = ?
                """,
                (f"\n[falsified] {notes}" if notes else "", prediction_id),
            )

    def summary(self) -> dict[str, Any]:
        """Return a summary of the prediction ledger with Brier metrics.

        Returns:
            Dict with total, validated, pending, falsified, total_points,
            avg_lead_weeks, brier_score, bss, categories.
        """
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY source_date"
            ).fetchall()

        total = len(rows)
        validated = [r for r in rows if r["status"] == "validated"]
        pending = [r for r in rows if r["status"] == "pending"]
        falsified = [r for r in rows if r["status"] == "falsified"]

        total_points = sum(r["points"] or 0.0 for r in validated)
        lead_weeks_list = [r["lead_weeks"] for r in validated if r["lead_weeks"] is not None]
        avg_lead = sum(lead_weeks_list) / len(lead_weeks_list) if lead_weeks_list else 0.0

        # Brier score over closed predictions (validated=1, falsified=0)
        closed = validated + falsified
        forecasts = [r["confidence"] for r in closed]
        outcomes = [1 if r["status"] == "validated" else 0 for r in closed]

        from whitemagic.forecasting.brier import (
            brier_index as _bi,
        )
        from whitemagic.forecasting.brier import (
            brier_score as _bs,
        )
        from whitemagic.forecasting.brier import (
            brier_skill_score as _bss,
        )
        from whitemagic.forecasting.brier import (
            calibration_gap as _cg,
        )

        bs = _bs(forecasts, outcomes) if closed else float("nan")
        bss = _bss(forecasts, outcomes) if closed else float("nan")
        bi = _bi(bs) if bs == bs else float("nan")
        cg = _cg(forecasts, outcomes) if closed else float("nan")

        categories: dict[str, int] = {}
        for r in validated:
            cat = r["category"] or "general"
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total": total,
            "validated": len(validated),
            "pending": len(pending),
            "falsified": len(falsified),
            "total_points": total_points,
            "avg_lead_weeks": round(avg_lead, 1),
            "brier_score": round(bs, 4) if bs == bs else None,
            "brier_skill_score": round(bss, 4) if bss == bss else None,
            "brier_index": round(bi, 1) if bi == bi else None,
            "calibration_gap": round(cg, 3) if cg == cg else None,
            "categories": categories,
        }

    def calibration(self, n_bins: int = 5) -> list[dict]:
        """Compute the calibration curve for closed predictions.

        Returns list of bin dicts (see brier.calibration_curve).
        """
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT confidence, status FROM predictions "
                "WHERE status IN ('validated', 'falsified')"
            ).fetchall()

        if not rows:
            return []

        from whitemagic.forecasting.brier import calibration_curve as _cc

        forecasts = [r["confidence"] for r in rows]
        outcomes = [1 if r["status"] == "validated" else 0 for r in rows]
        return _cc(forecasts, outcomes, n_bins=n_bins)

    def get_by_category(self, category: str) -> list[dict]:
        """Return all predictions for a given category."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions WHERE category = ? ORDER BY source_date",
                (category,),
            ).fetchall()
        return [dict(r) for r in rows]

    def all_predictions(self) -> list[dict]:
        """Return all predictions as a list of dicts."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY source_date"
            ).fetchall()
        return [dict(r) for r in rows]

    def export_summary(self) -> dict[str, Any]:
        """Return a JSON-serializable summary of the prediction ledger.

        Same as summary() but guaranteed safe for json.dumps().
        """
        result = self.summary()
        # Replace NaN with None for JSON safety
        for key in ("brier_score", "brier_skill_score"):
            if result[key] is not None and result[key] != result[key]:  # NaN check
                result[key] = None
        return result

    def export_claims(self, status: str | None = None) -> list[dict[str, Any]]:
        """Return predictions as JSON-safe dicts, optionally filtered by status."""
        rows = self.all_predictions()
        if status:
            rows = [r for r in rows if r.get("status") == status]
        # SQLite rows already emit strings/numbers; ensure no binary/blob leakage
        return rows

    def to_json(self, indent: int | None = 2) -> str:
        """Dump the full ledger state (summary + all claims) as JSON."""
        payload = {
            "summary": self.export_summary(),
            "claims": self.export_claims(),
            "calibration": self.calibration(n_bins=5),
        }
        return json.dumps(payload, indent=indent, default=str)
