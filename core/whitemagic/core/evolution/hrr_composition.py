"""HRR-Based Improvement Composition (Objective H).

Uses Holographic Reduced Representations (circular convolution) to compose
improvement hypotheses and detect interaction effects (synergy, conflict).

Operations:
- bind(A, B): Creates composite hypothesis representing A⊗B interaction
- unbind(composite, A): Recovers B's contribution within the composite
- superposition(A, B, C): Represents doing all three — test for superlinear synergy
- probe(composite, outcome_db): Tests if composite predicts outcomes better
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from whitemagic.core.evolution._rust_bridge import call as _rust_call

logger = logging.getLogger(__name__)


@dataclass
class CompositeHypothesis:
    """A composite hypothesis created by HRR binding/superposition."""

    id: str
    component_ids: list[str]
    operation: str  # "bind" or "superposition"
    vector: np.ndarray | None = None
    predicted_impact: float = 0.0
    synergy_score: float = 0.0  # >1 = superlinear, <1 = sublinear
    metadata: dict[str, Any] = field(default_factory=dict)


class HRRCompositionEngine:
    """Composes improvement hypotheses using HRR operations.

    Uses the existing HRREngine for circular convolution binding.
    """

    def __init__(self, dim: int = 384) -> None:
        self._dim = dim
        self._hrr: Any = None
        self._vectors: dict[str, np.ndarray] = {}
        self._composites: dict[str, CompositeHypothesis] = {}

    def _get_hrr(self) -> Any:
        """Lazy-load the HRR engine."""
        if self._hrr is None:
            try:
                from whitemagic.core.memory.hrr import get_hrr_engine

                self._hrr = get_hrr_engine(dim=self._dim)
            except (ImportError, Exception) as e:  # noqa: BLE001
                logger.debug("HRR engine unavailable: %s", e)
                self._hrr = False
        return self._hrr if self._hrr is not False else None

    def encode_hypothesis(
        self, hypothesis_id: str, description: str, impact: float = 0.5
    ) -> np.ndarray | None:
        """Encode a hypothesis as an HRR vector.

        Uses a deterministic hash-based vector generation from the description.

        Args:
            hypothesis_id: Unique ID for the hypothesis.
            description: Text description for vector generation.
            impact: Predicted impact (scales vector magnitude).

        Returns:
            HRR vector, or None if HRR unavailable.
        """
        result = _rust_call(
            "hrr_encode", description=description, dim=self._dim, impact=impact
        )
        if result is not None and "vector" in result:
            vec = np.array(result["vector"], dtype=np.float32)
            self._vectors[hypothesis_id] = vec
            return vec

        # Python fallback
        hrr = self._get_hrr()
        if hrr is None:
            return None

        rng = np.random.default_rng(seed=hash(description) % (2**32))
        vec = rng.standard_normal(self._dim).astype(np.float32)
        vec /= np.linalg.norm(vec)
        vec *= max(0.1, min(2.0, impact))

        self._vectors[hypothesis_id] = vec
        return vec

    def bind(self, id_a: str, id_b: str) -> CompositeHypothesis | None:
        """Bind two hypotheses via circular convolution.

        bind(A, B) creates a composite representing their interaction.

        Args:
            id_a: First hypothesis ID.
            id_b: Second hypothesis ID.

        Returns:
            CompositeHypothesis, or None if HRR unavailable.
        """
        vec_a = self._vectors.get(id_a)
        vec_b = self._vectors.get(id_b)
        if vec_a is None or vec_b is None:
            return None

        composite_id = f"bind_{id_a}_{id_b}"

        result = _rust_call("hrr_bind", a=vec_a.tolist(), b=vec_b.tolist())
        if result is not None and "vector" in result:
            bound = np.array(result["vector"], dtype=np.float32)
            composite = CompositeHypothesis(
                id=composite_id,
                component_ids=[id_a, id_b],
                operation="bind",
                vector=bound,
            )
            self._composites[composite_id] = composite
            return composite

        # Python fallback via HRR engine
        hrr = self._get_hrr()
        if hrr is None:
            return None

        bound = hrr.bind(vec_a, vec_b)
        composite = CompositeHypothesis(
            id=composite_id,
            component_ids=[id_a, id_b],
            operation="bind",
            vector=bound,
        )
        self._composites[composite_id] = composite
        return composite

    def unbind(self, composite_id: str, component_id: str) -> np.ndarray | None:
        """Unbind a component from a composite.

        unbind(composite, A) ≈ recovers B's contribution.

        Args:
            composite_id: The composite hypothesis ID.
            component_id: The component to unbind.

        Returns:
            Recovered vector, or None.
        """
        composite = self._composites.get(composite_id)
        if composite is None or composite.vector is None:
            return None

        component_vec = self._vectors.get(component_id)
        if component_vec is None:
            return None

        result = _rust_call(
            "hrr_unbind",
            composite=composite.vector.tolist(),
            component=component_vec.tolist(),
        )
        if result is not None and "vector" in result:
            return np.array(result["vector"], dtype=np.float32)

        # Python fallback
        hrr = self._get_hrr()
        if hrr is None:
            return None

        return hrr.unbind(composite.vector, component_vec)

    def superposition(self, ids: list[str]) -> CompositeHypothesis | None:
        """Create a superposition of multiple hypotheses.

        superposition(A, B, C) = A + B + C (vector addition).
        Tests whether doing all together produces superlinear synergy.

        Args:
            ids: List of hypothesis IDs to superpose.

        Returns:
            CompositeHypothesis, or None.
        """
        if len(ids) < 2:
            return None

        vecs = [self._vectors[i] for i in ids if i in self._vectors]
        if len(vecs) < 2:
            return None

        composite_id = f"super_{'_'.join(ids)}"

        result = _rust_call("hrr_superposition", vectors=[v.tolist() for v in vecs])
        if result is not None and "vector" in result:
            result_vec = np.array(result["vector"], dtype=np.float32)
            composite = CompositeHypothesis(
                id=composite_id,
                component_ids=ids,
                operation="superposition",
                vector=result_vec,
            )
            self._composites[composite_id] = composite
            return composite

        # Python fallback
        result = np.zeros(self._dim, dtype=np.float32)
        for v in vecs:
            result += v
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm

        composite = CompositeHypothesis(
            id=composite_id,
            component_ids=ids,
            operation="superposition",
            vector=result,
        )
        self._composites[composite_id] = composite
        return composite

    def compute_synergy(
        self,
        composite: CompositeHypothesis,
        individual_impacts: list[float],
    ) -> float:
        """Compute synergy score for a composite.

        synergy = composite_impact / sum(individual_impacts)
        >1 = superlinear (synergy)
        <1 = sublinear (interference)

        Args:
            composite: The composite hypothesis.
            individual_impacts: Impact scores of individual components.

        Returns:
            Synergy score.
        """
        if not individual_impacts:
            return 0.0

        if composite.vector is not None:
            result = _rust_call(
                "hrr_synergy",
                composite=composite.vector.tolist(),
                impacts=individual_impacts,
            )
            if result is not None and "synergy" in result:
                synergy = result["synergy"]
                composite.synergy_score = synergy
                return synergy

            # Python fallback
            composite_impact = float(np.linalg.norm(composite.vector))
        else:
            composite_impact = 0.0

        sum_individual = sum(individual_impacts)
        if sum_individual <= 0:
            return 0.0

        synergy = composite_impact / sum_individual
        composite.synergy_score = synergy
        return synergy

    def probe_composite(
        self,
        composite: CompositeHypothesis,
        outcomes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Probe a composite against the outcome database.

        Tests whether the composite predicts outcomes better than
        individual hypotheses.

        Args:
            composite: The composite to probe.
            outcomes: List of outcome dicts with 'success' and 'impact'.

        Returns:
            Dict with probe results.
        """
        if not outcomes:
            return {"error": "no_outcomes"}

        successes = sum(1 for o in outcomes if o.get("success"))
        success_rate = successes / len(outcomes)

        # Compare to individual component success rates
        component_rates = []
        for comp_id in composite.component_ids:
            comp_outcomes = [o for o in outcomes if o.get("hypothesis_id") == comp_id]
            if comp_outcomes:
                comp_successes = sum(1 for o in comp_outcomes if o.get("success"))
                component_rates.append(comp_successes / len(comp_outcomes))

        avg_component_rate = (
            sum(component_rates) / len(component_rates) if component_rates else 0.0
        )

        return {
            "composite_success_rate": success_rate,
            "avg_component_success_rate": avg_component_rate,
            "composite_better": success_rate > avg_component_rate,
            "synergy_score": composite.synergy_score,
            "n_outcomes": len(outcomes),
        }

    def get_composite(self, composite_id: str) -> CompositeHypothesis | None:
        return self._composites.get(composite_id)

    def get_all_composites(self) -> dict[str, CompositeHypothesis]:
        return dict(self._composites)
