"""Confidence learning loop - track predictions vs outcomes, auto-calibrate."""

from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ConfidenceOutcome:
    """Record of a confidence prediction and its actual outcome."""
    
    task_id: str
    task_name: str
    predicted_confidence: float  # 0.0-1.0
    actual_success: bool
    factors: Dict[str, float]  # Individual factor scores
    timestamp: str
    category: str  # "bug-fix", "feature", "refactor", etc.
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConfidenceOutcome":
        """Create from dictionary."""
        return cls(**data)


class ConfidenceLearner:
    """Learn from confidence predictions to improve calibration.
    
    Tracks predicted confidence vs actual outcomes.
    Adjusts confidence weights to minimize prediction error.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.cwd() / ".whitemagic"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.outcomes_file = self.data_dir / "confidence_outcomes.jsonl"
        self.weights_file = self.data_dir / "confidence_weights.json"
        
        self.outcomes: List[ConfidenceOutcome] = []
        self.weights: Dict[str, float] = self._load_weights()
        
        self._load_outcomes()
    
    def _load_outcomes(self):
        """Load historical outcomes from disk."""
        if not self.outcomes_file.exists():
            return
        
        try:
            with open(self.outcomes_file, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self.outcomes.append(ConfidenceOutcome.from_dict(data))
        except Exception:
            pass  # Graceful degradation
    
    def _save_outcome(self, outcome: ConfidenceOutcome):
        """Append outcome to log file."""
        with open(self.outcomes_file, 'a') as f:
            f.write(json.dumps(outcome.to_dict()) + '\n')
    
    def _load_weights(self) -> Dict[str, float]:
        """Load confidence weights from disk."""
        if not self.weights_file.exists():
            # Default weights (from ConfidenceAssessor)
            return {
                "has_tests": 0.25,
                "tests_pass": 0.30,
                "follows_plan": 0.15,
                "is_reversible": 0.10,
                "no_external_deps": 0.10,
                "code_quality": 0.10,
            }
        
        try:
            data = json.loads(self.weights_file.read_text())
            return data.get("weights", {})
        except Exception:
            return {}
    
    def _save_weights(self):
        """Save confidence weights to disk."""
        data = {
            "weights": self.weights,
            "last_updated": datetime.now().isoformat(),
            "total_outcomes": len(self.outcomes),
        }
        self.weights_file.write_text(json.dumps(data, indent=2))
    
    def record_outcome(
        self,
        task_id: str,
        task_name: str,
        predicted_confidence: float,
        actual_success: bool,
        factors: Dict[str, float],
        category: str = "general",
        notes: str = "",
    ):
        """Record a confidence prediction and its actual outcome.
        
        Args:
            task_id: Unique task identifier
            task_name: Human-readable task name
            predicted_confidence: Confidence score that was predicted (0.0-1.0)
            actual_success: Whether the task actually succeeded
            factors: Individual factor scores used in prediction
            category: Task category (for category-specific learning)
            notes: Optional notes about the outcome
        """
        outcome = ConfidenceOutcome(
            task_id=task_id,
            task_name=task_name,
            predicted_confidence=predicted_confidence,
            actual_success=actual_success,
            factors=factors,
            timestamp=datetime.now().isoformat(),
            category=category,
            notes=notes,
        )
        
        self.outcomes.append(outcome)
        self._save_outcome(outcome)
    
    def get_calibration_stats(self) -> Dict[str, float]:
        """Calculate calibration statistics.
        
        Returns:
            Dict with accuracy, over_confidence, under_confidence rates
        """
        if not self.outcomes:
            return {
                "total_predictions": 0,
                "accuracy": 0.0,
                "over_confidence_rate": 0.0,
                "under_confidence_rate": 0.0,
                "mean_error": 0.0,
            }
        
        correct = 0
        over_confident = 0
        under_confident = 0
        total_error = 0.0
        
        for outcome in self.outcomes:
            # Check if prediction matched reality
            predicted_success = outcome.predicted_confidence >= 0.7
            if predicted_success == outcome.actual_success:
                correct += 1
            
            # Check calibration
            if predicted_success and not outcome.actual_success:
                over_confident += 1
            elif not predicted_success and outcome.actual_success:
                under_confident += 1
            
            # Calculate error
            actual_score = 1.0 if outcome.actual_success else 0.0
            error = abs(outcome.predicted_confidence - actual_score)
            total_error += error
        
        n = len(self.outcomes)
        return {
            "total_predictions": n,
            "accuracy": correct / n,
            "over_confidence_rate": over_confident / n,
            "under_confidence_rate": under_confident / n,
            "mean_error": total_error / n,
        }
    
    def analyze_factors(self) -> Dict[str, Dict[str, float]]:
        """Analyze which factors are most predictive.
        
        Returns:
            Dict mapping factor names to their predictive power stats
        """
        if not self.outcomes:
            return {}
        
        factor_analysis = {}
        
        # Collect all factor names
        all_factors = set()
        for outcome in self.outcomes:
            all_factors.update(outcome.factors.keys())
        
        # Analyze each factor
        for factor in all_factors:
            high_success = 0
            high_total = 0
            low_success = 0
            low_total = 0
            
            for outcome in self.outcomes:
                factor_value = outcome.factors.get(factor, 0.5)
                
                if factor_value >= 0.7:  # High factor value
                    high_total += 1
                    if outcome.actual_success:
                        high_success += 1
                elif factor_value <= 0.3:  # Low factor value
                    low_total += 1
                    if outcome.actual_success:
                        low_success += 1
            
            # Calculate success rates
            high_rate = high_success / high_total if high_total > 0 else 0.0
            low_rate = low_success / low_total if low_total > 0 else 0.0
            
            factor_analysis[factor] = {
                "high_success_rate": high_rate,
                "low_success_rate": low_rate,
                "predictive_power": high_rate - low_rate,  # Higher = more predictive
            }
        
        return factor_analysis
    
    def auto_calibrate(self, min_samples: int = 10) -> Dict[str, float]:
        """Auto-adjust confidence weights based on outcomes.
        
        Args:
            min_samples: Minimum number of outcomes before adjusting
            
        Returns:
            Updated weights dictionary
        """
        if len(self.outcomes) < min_samples:
            return self.weights
        
        factor_analysis = self.analyze_factors()
        
        # Adjust weights based on predictive power
        new_weights = {}
        total_power = sum(
            abs(analysis["predictive_power"])
            for analysis in factor_analysis.values()
        )
        
        if total_power > 0:
            for factor, analysis in factor_analysis.items():
                # Weight proportional to predictive power
                power = abs(analysis["predictive_power"])
                new_weights[factor] = power / total_power
        else:
            # Keep existing weights if no clear signal
            new_weights = self.weights.copy()
        
        # Smooth update (80% old, 20% new)
        smoothed_weights = {}
        for factor in set(list(self.weights.keys()) + list(new_weights.keys())):
            old = self.weights.get(factor, 0.5)
            new = new_weights.get(factor, 0.5)
            smoothed_weights[factor] = 0.8 * old + 0.2 * new
        
        # Normalize to sum to 1.0
        total = sum(smoothed_weights.values())
        if total > 0:
            smoothed_weights = {k: v / total for k, v in smoothed_weights.items()}
        
        self.weights = smoothed_weights
        self._save_weights()
        
        return self.weights
    
    def get_category_stats(self, category: str) -> Dict[str, float]:
        """Get calibration stats for a specific category.
        
        Args:
            category: Task category (e.g., "bug-fix", "feature")
            
        Returns:
            Calibration stats for that category
        """
        category_outcomes = [o for o in self.outcomes if o.category == category]
        
        if not category_outcomes:
            return {
                "total_predictions": 0,
                "accuracy": 0.0,
                "mean_confidence": 0.0,
                "success_rate": 0.0,
            }
        
        correct = sum(
            1 for o in category_outcomes
            if (o.predicted_confidence >= 0.7) == o.actual_success
        )
        successes = sum(1 for o in category_outcomes if o.actual_success)
        mean_conf = sum(o.predicted_confidence for o in category_outcomes) / len(category_outcomes)
        
        return {
            "total_predictions": len(category_outcomes),
            "accuracy": correct / len(category_outcomes),
            "mean_confidence": mean_conf,
            "success_rate": successes / len(category_outcomes),
        }


# Global instance
_learner: Optional[ConfidenceLearner] = None


def get_learner(data_dir: Optional[Path] = None) -> ConfidenceLearner:
    """Get global confidence learner instance.
    
    Args:
        data_dir: Data directory (uses .whitemagic if not provided)
        
    Returns:
        Global ConfidenceLearner instance
    """
    global _learner
    
    if _learner is None:
        _learner = ConfidenceLearner(data_dir)
    
    return _learner


def record_outcome(
    task_id: str,
    task_name: str,
    predicted_confidence: float,
    actual_success: bool,
    factors: Dict[str, float],
    category: str = "general",
    notes: str = "",
):
    """Record outcome (convenience function).
    
    Args:
        task_id: Unique task identifier
        task_name: Human-readable task name
        predicted_confidence: Predicted confidence (0.0-1.0)
        actual_success: Whether task succeeded
        factors: Factor scores used in prediction
        category: Task category
        notes: Optional notes
    """
    learner = get_learner()
    learner.record_outcome(
        task_id, task_name, predicted_confidence, actual_success, factors, category, notes
    )


def auto_calibrate(min_samples: int = 10) -> Dict[str, float]:
    """Auto-calibrate confidence weights (convenience function).
    
    Args:
        min_samples: Minimum outcomes before calibrating
        
    Returns:
        Updated weights
    """
    learner = get_learner()
    return learner.auto_calibrate(min_samples)
