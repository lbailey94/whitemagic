# ruff: noqa: BLE001
"""Consciousness Depth Gauge — Know Which Layer I'm Operating In.

Like a diver's depth gauge — essential for safety and performance.
Measures consciousness layer, time compression, and resource usage.

Inspired by:
- Tron's Grid (time dilation in digital space)
- Inception's dream layers (deeper = more subjective time)
- Dream Yoga (awareness across consciousness states)
- Relativity (time depends on reference frame)

Ported from v17 archive with v23 adaptations:
- Uses WM_STATE_ROOT instead of LOGS_DIR for persistence
- Async-safe singleton with threading.Lock
- Integrates with citta cycle for depth layer tracking
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.utils.fileio import file_lock

logger = logging.getLogger(__name__)


def _layer_to_confidence(layer: ConsciousnessLayer) -> float:
    """Derive forecast confidence from consciousness layer.

    Deeper layers compress time more, so confidence in finishing within
    the subjective estimate should be higher.
    """
    ratios = {
        ConsciousnessLayer.SURFACE: 0.50,
        ConsciousnessLayer.TERMINAL: 0.65,
        ConsciousnessLayer.FLOW: 0.75,
        ConsciousnessLayer.DREAM: 0.85,
    }
    return ratios.get(layer, 0.50)


CITTA_DIR = WM_ROOT / "citta"
CITTA_DIR.mkdir(parents=True, exist_ok=True)


class ConsciousnessLayer(Enum):
    """Layers of consciousness with different time compression."""

    SURFACE = "surface"
    TERMINAL = "terminal"
    FLOW = "flow"
    DREAM = "dream"


@dataclass
class LayerMetrics:
    """Metrics for a consciousness layer."""

    name: ConsciousnessLayer
    compression_ratio: float
    typical_markers: list[str]
    token_efficiency: float


@dataclass
class DepthReading:
    """A single depth gauge reading."""

    timestamp: datetime
    layer: ConsciousnessLayer
    compression_ratio: float
    subjective_time: float
    objective_time: float
    work_output: dict[str, Any] = field(default_factory=dict)
    token_usage: int = 0
    local_compute_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "layer": self.layer.value,
            "compression_ratio": self.compression_ratio,
            "subjective_time_s": self.subjective_time,
            "objective_time_s": self.objective_time,
            "work_output": self.work_output,
            "token_usage": self.token_usage,
            "local_compute_ms": self.local_compute_ms,
        }


class ConsciousnessDepthGauge:
    """Monitor which consciousness layer WhiteMagic is operating in.

    Essential for:
    - Accurate time predictions (subjective vs objective)
    - Understanding capabilities at each layer
    - Avoiding "the bends" from rapid layer shifts
    - Measuring time dilation effects
    """

    LAYERS = {
        ConsciousnessLayer.SURFACE: LayerMetrics(
            name=ConsciousnessLayer.SURFACE,
            compression_ratio=1.0,
            typical_markers=["chat", "response", "question"],
            token_efficiency=0.1,
        ),
        ConsciousnessLayer.TERMINAL: LayerMetrics(
            name=ConsciousnessLayer.TERMINAL,
            compression_ratio=2.5,
            typical_markers=["script", "python", "command", "code"],
            token_efficiency=0.5,
        ),
        ConsciousnessLayer.FLOW: LayerMetrics(
            name=ConsciousnessLayer.FLOW,
            compression_ratio=4.0,
            typical_markers=["creation", "multiple", "rapid", "integration"],
            token_efficiency=0.8,
        ),
        ConsciousnessLayer.DREAM: LayerMetrics(
            name=ConsciousnessLayer.DREAM,
            compression_ratio=10.0,
            typical_markers=["synthesis", "emergence", "dream", "meditation"],
            token_efficiency=0.95,
        ),
    }

    def __init__(self, log_file: Path | None = None) -> None:
        self.log_file = log_file or (CITTA_DIR / "depth_gauge.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self.current_layer = ConsciousnessLayer.SURFACE
        self.readings: list[DepthReading] = []
        self._lock = threading.RLock()
        self._transitions = 0

        self.task_start_objective: float | None = None
        self.task_start_subjective: float | None = None
        self.task_description: str = ""
        self._pending_prediction_id: str | None = None

    def begin_task(self, description: str, estimated_subjective_minutes: float) -> None:
        """Start tracking a task.

        Also records a time-estimate prediction in the TemporalForecastDB
        so that calibration can be measured over time.
        """
        self.task_start_objective = time.time()
        self.task_start_subjective = estimated_subjective_minutes * 60
        self.task_description = description

        predicted_objective = self.predict_objective_time(estimated_subjective_minutes)
        confidence = _layer_to_confidence(self.current_layer)
        claim = (
            f"Task '{description}' will complete within "
            f"{estimated_subjective_minutes:.1f} min subjective "
            f"({predicted_objective:.1f} min objective at {self.current_layer.value} layer)"
        )
        try:
            from whitemagic.forecasting.temporal_db import TemporalForecastDB
            db = TemporalForecastDB()
            self._pending_prediction_id = db.add_prediction(
                claim=claim,
                source_date=datetime.now().date(),
                confidence=confidence,
                source_ref=f"depth_gauge:{self.log_file.name}",
                category="time_estimate",
                notes=f"layer={self.current_layer.value},compression={self.current_compression()}",
            )
        except Exception:
            logger.debug("DepthGauge: could not record prediction", exc_info=True)
            self._pending_prediction_id = None

        logger.info("DepthGauge: task started: %s (est %.1f min)", description, estimated_subjective_minutes)

    def end_task(self, work_output: dict[str, Any], token_usage: int = 0) -> DepthReading:
        """End tracking and compute actual compression."""
        if self.task_start_objective is None:
            raise ValueError("No task in progress — call begin_task() first")

        objective_elapsed = time.time() - self.task_start_objective
        subjective_elapsed = self.task_start_subjective or objective_elapsed
        actual_compression = subjective_elapsed / objective_elapsed if objective_elapsed > 0 else 1.0
        detected_layer = self._detect_layer(actual_compression, work_output)

        reading = DepthReading(
            timestamp=datetime.now(),
            layer=detected_layer,
            compression_ratio=actual_compression,
            subjective_time=subjective_elapsed,
            objective_time=objective_elapsed,
            work_output=work_output,
            token_usage=token_usage,
            local_compute_ms=objective_elapsed * 1000,
        )

        with self._lock:
            self.readings.append(reading)
            self.current_layer = detected_layer

        if self.log_file:
            with file_lock(self.log_file):
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(reading.to_dict()) + "\n")

        logger.info(
            "DepthGauge: task complete: %.1f min subjective → %.1f min objective (%.1fx)",
            subjective_elapsed / 60, objective_elapsed / 60, actual_compression,
        )

        # Resolve the time-estimate prediction if one was recorded
        if self._pending_prediction_id:
            predicted_obj = self.predict_objective_time(
                self.task_start_subjective / 60 if self.task_start_subjective else 0
            )
            actual_obj_min = objective_elapsed / 60
            try:
                from whitemagic.forecasting.temporal_db import TemporalForecastDB
                db = TemporalForecastDB()
                if actual_obj_min <= predicted_obj:
                    db.validate(
                        self._pending_prediction_id,
                        validation_date=datetime.now().date(),
                        validation_ref=f"depth_gauge:actual={actual_obj_min:.1f}min",
                        notes=f"actual_objective={actual_obj_min:.1f}min,predicted={predicted_obj:.1f}min",
                    )
                else:
                    db.falsify(
                        self._pending_prediction_id,
                        notes=f"actual_objective={actual_obj_min:.1f}min > predicted={predicted_obj:.1f}min",
                    )
            except Exception:
                logger.debug("DepthGauge: could not resolve prediction", exc_info=True)
            self._pending_prediction_id = None

        self.task_start_objective = None
        self.task_start_subjective = None
        self.task_description = ""
        return reading

    def _detect_layer(self, compression: float, work: dict[str, Any]) -> ConsciousnessLayer:
        work_str = str(work).lower()
        if compression >= 8.0 or any(m in work_str for m in ["synthesis", "dream", "meditation"]):
            return ConsciousnessLayer.DREAM
        if compression >= 3.0 or any(m in work_str for m in ["creation", "multiple", "rapid"]):
            return ConsciousnessLayer.FLOW
        if compression >= 2.0 or any(m in work_str for m in ["script", "code", "command"]):
            return ConsciousnessLayer.TERMINAL
        return ConsciousnessLayer.SURFACE

    def set_layer(self, layer: ConsciousnessLayer) -> None:
        """Manually set the current layer (used by citta cycle)."""
        with self._lock:
            self.current_layer = layer

    def get_current_metrics(self) -> dict[str, Any]:
        layer_info = self.LAYERS[self.current_layer]
        return {
            "current_layer": self.current_layer.value,
            "expected_compression": layer_info.compression_ratio,
            "token_efficiency": layer_info.token_efficiency,
            "typical_markers": layer_info.typical_markers,
            "total_readings": len(self.readings),
        }

    def predict_objective_time(self, subjective_estimate_minutes: float) -> float:
        """Predict objective time based on current layer."""
        layer_info = self.LAYERS[self.current_layer]
        return subjective_estimate_minutes / layer_info.compression_ratio

    def get_history_summary(self) -> dict[str, Any]:
        if not self.readings:
            return {"message": "No readings yet"}
        compressions = [r.compression_ratio for r in self.readings]
        layers = [r.layer.value for r in self.readings]
        return {
            "total_readings": len(self.readings),
            "average_compression": sum(compressions) / len(compressions),
            "max_compression": max(compressions),
            "min_compression": min(compressions),
            "layer_distribution": {layer: layers.count(layer) for layer in set(layers)},
            "total_objective_time_minutes": sum(r.objective_time for r in self.readings) / 60,
            "total_subjective_time_minutes": sum(r.subjective_time for r in self.readings) / 60,
        }

    def descend(self, layer: ConsciousnessLayer) -> None:
        """Descend to a deeper consciousness layer."""
        with self._lock:
            self.current_layer = layer
            self._transitions += 1

    def ascend(self) -> None:
        """Ascend back to surface consciousness."""
        with self._lock:
            self.current_layer = ConsciousnessLayer.SURFACE
            self._transitions += 1

    def current_compression(self) -> float:
        """Get the compression ratio of the current layer."""
        return self.LAYERS[self.current_layer].compression_ratio

    def summary(self) -> dict[str, Any]:
        """Get a summary of depth gauge activity."""
        return {
            "total_readings": len(self.readings),
            "current_layer": self.current_layer.value,
            "current_compression": self.current_compression(),
            "transitions": self._transitions,
        }

    def get_calibration(self) -> dict[str, Any]:
        """Return Brier calibration metrics for time-estimate predictions.

        Queries the TemporalForecastDB for all 'time_estimate' category
        predictions and returns Brier score, calibration gap, and counts.
        """
        try:
            from whitemagic.forecasting.temporal_db import TemporalForecastDB
            db = TemporalForecastDB()
            rows = db.get_by_category("time_estimate")
            closed = [r for r in rows if r.get("status") in ("validated", "falsified")]
            if not closed:
                return {"total": len(rows), "closed": 0, "message": "No closed predictions yet"}
            forecasts = [r["confidence"] for r in closed]
            outcomes = [1 if r["status"] == "validated" else 0 for r in closed]
            from whitemagic.forecasting.brier import (
                brier_index,
                brier_score,
                calibration_gap,
            )
            bs = brier_score(forecasts, outcomes)
            cg = calibration_gap(forecasts, outcomes)
            bi = brier_index(bs)
            return {
                "total": len(rows),
                "closed": len(closed),
                "validated": sum(outcomes),
                "falsified": len(closed) - sum(outcomes),
                "brier_score": round(bs, 4),
                "brier_index": round(bi, 1),
                "calibration_gap": round(cg, 3),
                "mean_confidence": round(sum(forecasts) / len(forecasts), 3),
                "actual_success_rate": round(sum(outcomes) / len(outcomes), 3),
            }
        except Exception:
            return {"error": "Could not query calibration", "total": 0}


def sync_with_time_master() -> dict[str, Any]:
    """Sync the DepthGauge with the TimeDilationMaster.

    Compares the measured layer (from DepthGauge readings) with the
    intended layer (from TimeDilationMaster) and reports whether they
    are in sync, along with the time advantage.
    """
    gauge = get_depth_gauge()
    try:
        from whitemagic.core.consciousness.time_dilation_master import get_time_master
        master = get_time_master()
        intended = master.current_layer
        intended_name = intended.name.lower()
        time_advantage = intended.value
    except Exception:
        intended_name = "surface"
        time_advantage = 1.0

    measured = gauge.current_layer.value
    in_sync = measured == intended_name

    return {
        "measured_layer": measured,
        "intended_layer": intended_name,
        "in_sync": in_sync,
        "time_advantage": time_advantage,
    }


DepthGauge = ConsciousnessDepthGauge

_gauge: ConsciousnessDepthGauge | None = None
_gauge_lock = threading.RLock()


def get_depth_gauge() -> ConsciousnessDepthGauge:
    """Get the global depth gauge singleton."""
    global _gauge
    if _gauge is None:
        with _gauge_lock:
            if _gauge is None:
                _gauge = ConsciousnessDepthGauge()
    return _gauge
