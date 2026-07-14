"""ParameterMapper: Learns mapping from introspective to external sim params.

Part of Phase 7 (Adaptive Recursive Cycle). Uses a simple GP trained on
the Research DAG's experiment history. Each past recursive cycle provides
a training pair: (introspective_best_params → external_optimal_params).

With fewer than 3 observations, falls back to heuristic mapping.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ParameterMapper:
    """Learns the mapping from introspective optimal params to external sim params.

    Uses a simple nearest-neighbor interpolation approach. Each past recursive
    cycle provides a training pair: (intro_params → ext_params + outcome).
    After 3+ observations, the mapper predicts external params from introspective
    params by weighted nearest-neighbor interpolation.

    With fewer than 3 observations, uses a heuristic linear scaling.
    """

    def __init__(self) -> None:
        self._training_pairs: list[tuple[list[float], list[float], float]] = []
        self._fitted = False

    def add_observation(
        self,
        intro_params: dict[str, float],
        ext_params: dict[str, float],
        ext_outcome: float,
    ) -> None:
        """Record a recursive cycle observation.

        Args:
            intro_params: Introspective optimal parameters.
            ext_params: External simulation parameters that were used.
            ext_outcome: The outcome (fitness) achieved.
        """
        intro_vec = list(intro_params.values())
        ext_vec = list(ext_params.values())
        self._training_pairs.append((intro_vec, ext_vec, ext_outcome))
        if len(self._training_pairs) >= 3:
            self._fitted = True
        logger.debug(
            "ParameterMapper: added observation #%d (fitted=%s)",
            len(self._training_pairs), self._fitted,
        )

    def predict_external_params(
        self,
        intro_params: dict[str, float],
        ext_param_names: list[str],
    ) -> dict[str, float]:
        """Predict optimal external params from introspective optimal params.

        Args:
            intro_params: Introspective optimal parameters.
            ext_param_names: Names of external parameters to predict.

        Returns:
            Dict mapping external param names to predicted values.
        """
        if len(self._training_pairs) < 3:
            return self._heuristic_map(intro_params, ext_param_names)

        intro_vec = list(intro_params.values())

        # Weighted nearest-neighbor interpolation
        # Weight = outcome * similarity (better outcomes weighted higher)
        weights: list[float] = []
        ext_vecs: list[list[float]] = []

        for train_intro, train_ext, train_outcome in self._training_pairs:
            # Cosine similarity
            dot = sum(a * b for a, b in zip(intro_vec, train_intro))
            na = sum(a * a for a in intro_vec) ** 0.5
            nb = sum(b * b for b in train_intro) ** 0.5
            if na < 1e-15 or nb < 1e-15:
                sim = 0.0
            else:
                sim = dot / (na * nb)
            # Weight by outcome (higher outcome = more trustworthy)
            weight = max(0.01, sim) * max(0.01, train_outcome)
            weights.append(weight)
            ext_vecs.append(train_ext)

        total_weight = sum(weights)
        if total_weight < 1e-15:
            return self._heuristic_map(intro_params, ext_param_names)

        # Weighted average
        predicted = [0.0] * len(ext_param_names)
        for w, ev in zip(weights, ext_vecs):
            for i in range(min(len(predicted), len(ev))):
                predicted[i] += w * ev[i]

        predicted = [p / total_weight for p in predicted]

        return dict(zip(ext_param_names, predicted))

    def _heuristic_map(
        self,
        intro_params: dict[str, float],
        ext_param_names: list[str],
    ) -> dict[str, float]:
        """Heuristic mapping when insufficient training data.

        Uses a simple linear scaling: external params = intro params * scale.
        """
        intro_vals = list(intro_params.values())
        result: dict[str, float] = {}

        for i, name in enumerate(ext_param_names):
            if i < len(intro_vals):
                # Scale by 100 (matching the old placeholder: x0 = best_params * 100)
                result[name] = intro_vals[i] * 100.0
            else:
                result[name] = 50.0  # Default mid-range

        return result

    @property
    def is_fitted(self) -> bool:
        """True if the mapper has enough training data for predictions."""
        return self._fitted

    @property
    def n_observations(self) -> int:
        """Number of training observations."""
        return len(self._training_pairs)

    def reset(self) -> None:
        """Clear all training data."""
        self._training_pairs.clear()
        self._fitted = False


_mapper: ParameterMapper | None = None


def get_parameter_mapper() -> ParameterMapper:
    """Get the singleton ParameterMapper instance."""
    global _mapper
    if _mapper is None:
        _mapper = ParameterMapper()
    return _mapper
