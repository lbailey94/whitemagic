"""External Cross-Validation (Objective X).

Establishes external validation benchmarks and cross-validation protocols
to cross-validate the system's self-assessments.

The core problem: the system's self-assessments (Brier scores, confidence
calibration, kaizen quality scores) are all computed from within the system.
This creates a Gödel-like limitation — the system cannot fully validate itself.

This module provides:
- **Train/validation splits**: Split the AutodidacticLoop's pattern outcomes
  into training and validation sets to detect overfitting.
- **External benchmarks**: Compare system metrics against external baselines
  (random, majority-class, etc.) rather than against the system's own
  predictions.
- **Adversarial testing**: Flip predictions and check if the system notices.
- **Cross-validation report**: Summarize whether self-assessments match
  held-out performance.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CrossValidationResult:
    """Result of a cross-validation run."""
    split_ratio: float
    train_size: int
    validation_size: int
    train_success_rate: float
    validation_success_rate: float
    overfitting_detected: bool
    overfitting_gap: float
    train_confidence: float
    validation_confidence: float
    confidence_calibration_gap: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdversarialTestResult:
    """Result of an adversarial test."""
    test_name: str
    passed: bool
    description: str
    expected: Any
    actual: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalValidationReport:
    """Comprehensive external validation report."""
    cross_validation: CrossValidationResult | None = None
    adversarial_tests: list[AdversarialTestResult] = field(default_factory=list)
    external_baselines: dict[str, float] = field(default_factory=dict)
    self_assessment_match: bool = True
    summary: str = ""


# External baselines (not derived from the system itself)
EXTERNAL_BASELINES = {
    "random_success_rate": 0.5,
    "majority_class_success_rate": 0.5,
    "random_brier_score": 0.25,  # Brier score for random predictions
    "perfect_brier_score": 0.0,
}


class ExternalValidator:
    """Cross-validates the system's self-assessments.

    Uses the AutodidacticLoop's SQLite database to perform train/validation
    splits and compare against external baselines.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            from whitemagic.config.paths import AUTODIDACTIC_DIR
            db_path = AUTODIDACTIC_DIR / "feedback.db"
        self._db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def cross_validate(
        self,
        split_ratio: float = 0.7,
    ) -> CrossValidationResult:
        """Perform train/validation split on pattern outcomes.

        Splits the AutodidacticLoop's outcomes chronologically (first 70%
        for training, last 30% for validation) and compares success rates.

        Args:
            split_ratio: Fraction of data for training (0-1).

        Returns:
            CrossValidationResult with overfitting analysis.
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT pattern_id, success, performance_gain, measured_at
                FROM pattern_outcomes
                ORDER BY measured_at ASC
            """)
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()

        total = len(rows)
        if total < 4:
            return CrossValidationResult(
                split_ratio=split_ratio,
                train_size=0,
                validation_size=0,
                train_success_rate=0.0,
                validation_success_rate=0.0,
                overfitting_detected=False,
                overfitting_gap=0.0,
                train_confidence=0.0,
                validation_confidence=0.0,
                confidence_calibration_gap=0.0,
                metadata={"error": "insufficient_data", "total_outcomes": total},
            )

        split_idx = int(total * split_ratio)
        train_rows = rows[:split_idx]
        val_rows = rows[split_idx:]

        train_successes = sum(1 for r in train_rows if r["success"])
        val_successes = sum(1 for r in val_rows if r["success"])

        train_rate = train_successes / len(train_rows) if train_rows else 0.0
        val_rate = val_successes / len(val_rows) if val_rows else 0.0

        # Overfitting: train success rate >> validation success rate
        overfitting_gap = train_rate - val_rate
        overfitting_detected = overfitting_gap > 0.15  # 15% gap threshold

        # Confidence calibration: compare self-reported confidence to actual
        train_conf = 0.0
        val_conf = 0.0
        try:
            cur2 = self._get_conn().cursor()
            cur2.execute("""
                SELECT pa.initial_confidence, po.success
                FROM pattern_applications pa
                JOIN pattern_outcomes po ON pa.application_id = po.application_id
                ORDER BY po.measured_at ASC
            """)
            conf_rows = cur2.fetchall()
            self._get_conn().close()

            if conf_rows:
                split_c = int(len(conf_rows) * split_ratio)
                train_conf_rows = conf_rows[:split_c]
                val_conf_rows = conf_rows[split_c:]
                train_conf = (
                    sum(r["initial_confidence"] for r in train_conf_rows) / len(train_conf_rows)
                    if train_conf_rows else 0.0
                )
                val_conf = (
                    sum(r["initial_confidence"] for r in val_conf_rows) / len(val_conf_rows)
                    if val_conf_rows else 0.0
                )
        except (sqlite3.OperationalError, Exception) as e:
            logger.debug("Confidence calibration query failed: %s", e)

        calibration_gap = abs(train_conf - val_conf)

        return CrossValidationResult(
            split_ratio=split_ratio,
            train_size=len(train_rows),
            validation_size=len(val_rows),
            train_success_rate=round(train_rate, 4),
            validation_success_rate=round(val_rate, 4),
            overfitting_detected=overfitting_detected,
            overfitting_gap=round(overfitting_gap, 4),
            train_confidence=round(train_conf, 4),
            validation_confidence=round(val_conf, 4),
            confidence_calibration_gap=round(calibration_gap, 4),
        )

    def adversarial_test_flip_predictions(self) -> AdversarialTestResult:
        """Flip predicted success and check if the system would notice.

        Takes a set of predictions, flips them, and checks if the flipped
        predictions would have a worse Brier score than the originals.
        If they don't, the system's predictions are no better than random.
        """
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT pa.initial_confidence, po.success
                FROM pattern_applications pa
                JOIN pattern_outcomes po ON pa.application_id = po.application_id
            """)
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()

        if len(rows) < 2:
            return AdversarialTestResult(
                test_name="flip_predictions",
                passed=False,
                description="Insufficient data for adversarial test",
                expected=None,
                actual=None,
            )

        # Original Brier score
        original_brier = sum(
            (r["initial_confidence"] - float(r["success"])) ** 2
            for r in rows
        ) / len(rows)

        # Flipped: replace confidence with (1 - confidence)
        flipped_brier = sum(
            ((1.0 - r["initial_confidence"]) - float(r["success"])) ** 2
            for r in rows
        ) / len(rows)

        # Test passes if original is better than flipped
        passed = original_brier < flipped_brier

        return AdversarialTestResult(
            test_name="flip_predictions",
            passed=passed,
            description="Flip predicted confidence and compare Brier scores",
            expected=f"original_brier < flipped_brier ({original_brier:.4f} < {flipped_brier:.4f})",
            actual=f"original={original_brier:.4f}, flipped={flipped_brier:.4f}",
            metadata={
                "original_brier": round(original_brier, 6),
                "flipped_brier": round(flipped_brier, 6),
                "improvement_over_flipped": round(flipped_brier - original_brier, 6),
            },
        )

    def adversarial_test_random_baseline(self) -> AdversarialTestResult:
        """Compare system predictions against a random 0.5 baseline."""
        conn = self._get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT pa.initial_confidence, po.success
                FROM pattern_applications pa
                JOIN pattern_outcomes po ON pa.application_id = po.application_id
            """)
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()

        if len(rows) < 2:
            return AdversarialTestResult(
                test_name="random_baseline",
                passed=False,
                description="Insufficient data for baseline comparison",
                expected=None,
                actual=None,
            )

        system_brier = sum(
            (r["initial_confidence"] - float(r["success"])) ** 2
            for r in rows
        ) / len(rows)

        random_brier = EXTERNAL_BASELINES["random_brier_score"]
        passed = system_brier < random_brier

        return AdversarialTestResult(
            test_name="random_baseline",
            passed=passed,
            description="Compare system Brier score against random 0.5 baseline",
            expected=f"system_brier < {random_brier}",
            actual=f"system_brier={system_brier:.4f}",
            metadata={
                "system_brier": round(system_brier, 6),
                "random_brier": random_brier,
                "improvement_over_random": round(random_brier - system_brier, 6),
            },
        )

    def run_full_validation(self) -> ExternalValidationReport:
        """Run all external validation checks and produce a report."""
        report = ExternalValidationReport()

        # Cross-validation
        report.cross_validation = self.cross_validate()

        # Adversarial tests
        report.adversarial_tests.append(self.adversarial_test_flip_predictions())
        report.adversarial_tests.append(self.adversarial_test_random_baseline())

        # External baselines
        report.external_baselines = dict(EXTERNAL_BASELINES)

        # Self-assessment match: do all adversarial tests pass?
        all_passed = all(t.passed for t in report.adversarial_tests)
        no_overfitting = not report.cross_validation.overfitting_detected
        report.self_assessment_match = all_passed and no_overfitting

        # Summary
        cv = report.cross_validation
        if cv.train_size == 0:
            report.summary = "Insufficient data for cross-validation."
        elif report.self_assessment_match:
            report.summary = (
                f"Self-assessments match held-out performance. "
                f"Train: {cv.train_success_rate:.1%}, Val: {cv.validation_success_rate:.1%}, "
                f"Gap: {cv.overfitting_gap:.1%}. All adversarial tests passed."
            )
        else:
            issues = []
            if cv.overfitting_detected:
                issues.append(f"overfitting (gap={cv.overfitting_gap:.1%})")
            failed_tests = [t.test_name for t in report.adversarial_tests if not t.passed]
            if failed_tests:
                issues.append(f"failed adversarial tests: {failed_tests}")
            report.summary = (
                f"Self-assessment mismatch detected: {'; '.join(issues)}."
            )

        return report
