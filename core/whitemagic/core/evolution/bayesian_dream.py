"""Dream Cycle as Bayesian Update Pass (Objective J).

Reframes the 12-phase dream cycle as a single Bayesian inference pass,
with each phase mapped to a specific role in the update equation.

Mapping:
| Phase         | Bayesian Role           | Math                                    |
|---------------|-------------------------|-----------------------------------------|
| Triage        | Prior selection         | P(θ) → P(θ | relevance)                 |
| Consolidation | Evidence aggregation    | Σ log P(e_i | θ)                        |
| Serendipity   | Likelihood estimation   | P(e | θ) from bridge discovery          |
| Governance    | Prior regularization    | P(θ) ← P(θ) · exp(-λ · echo_chamber)   |
| Narrative     | Posterior summarization | P(θ | e) → summary                      |
| Kaizen        | Action selection        | a* = argmax_a E[utility | a, θ]          |
| Oracle        | Expert prior injection  | P(θ) ← P(θ) · P_grimoire(θ)             |
| Decay         | Posterior forgetting    | P(θ) ← P(θ)^γ                           |
| Constellation | Posterior clustering    | θ ~ Dirichlet(clusters)                 |
| Prediction    | Forward simulation      | P(future | θ, e) — MC engine runs here  |
| Enrichment    | Posterior refinement    | P(θ | e) ← P(θ | e, new_evidence)       |
| Harmonize     | Convergence check       | ‖P(θ_t) - P(θ_{t-1})‖ < ε               |
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# The 12 dream phases in order
DREAM_PHASES = [
    "triage",
    "consolidation",
    "serendipity",
    "governance",
    "narrative",
    "kaizen",
    "oracle",
    "decay",
    "constellation",
    "prediction",
    "enrichment",
    "harmonize",
]

# Bayesian role mapping for each phase
BAYESIAN_ROLE_MAP: dict[str, dict[str, str]] = {
    "triage": {
        "role": "prior_selection",
        "math": "P(θ) → P(θ | relevance)",
        "description": "Select and weight priors based on relevance to current context",
    },
    "consolidation": {
        "role": "evidence_aggregation",
        "math": "Σ log P(e_i | θ)",
        "description": "Aggregate evidence from memory and observations",
    },
    "serendipity": {
        "role": "likelihood_estimation",
        "math": "P(e | θ) from bridge discovery",
        "description": "Estimate likelihood from cross-domain bridge discoveries",
    },
    "governance": {
        "role": "prior_regularization",
        "math": "P(θ) ← P(θ) · exp(-λ · echo_chamber_penalty)",
        "description": "Regularize priors to avoid echo chamber effects",
    },
    "narrative": {
        "role": "posterior_summarization",
        "math": "P(θ | e) → summary",
        "description": "Summarize posterior distribution into actionable narrative",
    },
    "kaizen": {
        "role": "action_selection",
        "math": "a* = argmax_a E[utility | a, θ]",
        "description": "Select improvement action maximizing expected utility",
    },
    "oracle": {
        "role": "expert_prior_injection",
        "math": "P(θ) ← P(θ) · P_grimoire(θ)",
        "description": "Inject expert knowledge from grimoire as prior update",
    },
    "decay": {
        "role": "posterior_forgetting",
        "math": "P(θ) ← P(θ)^γ",
        "description": "Apply temperature decay to posterior for forgetting",
    },
    "constellation": {
        "role": "posterior_clustering",
        "math": "θ ~ Dirichlet(clusters)",
        "description": "Cluster posterior into constellation groups",
    },
    "prediction": {
        "role": "forward_simulation",
        "math": "P(future | θ, e)",
        "description": "Run MC engine for forward simulation of outcomes",
    },
    "enrichment": {
        "role": "posterior_refinement",
        "math": "P(θ | e) ← P(θ | e, new_evidence)",
        "description": "Refine posterior with newly gathered evidence",
    },
    "harmonize": {
        "role": "convergence_check",
        "math": "‖P(θ_t) - P(θ_{t-1})‖ < ε",
        "description": "Check convergence between successive posteriors",
    },
}


@dataclass
class PhaseResult:
    """Result of a single dream phase execution."""
    phase: str
    bayesian_role: str
    math: str
    prior_update: float = 0.0
    posterior_value: float = 0.0
    evidence_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BayesianDreamResult:
    """Result of a complete Bayesian dream cycle."""
    cycle_id: str
    phases: list[PhaseResult] = field(default_factory=list)
    converged: bool = False
    convergence_delta: float = float("inf")
    iterations: int = 0
    final_posterior: float = 0.0


def kl_distance(p1: float, p2: float) -> float:
    """Symmetric KL divergence (Jensen-Shannon-like) between two Bernoulli distributions.

    Used for convergence checking in the Harmonize phase.

    Args:
        p1: First probability.
        p2: Second probability.

    Returns:
        Symmetric distance in bits.
    """
    if p1 <= 0:
        p1 = 1e-10
    if p1 >= 1:
        p1 = 1 - 1e-10
    if p2 <= 0:
        p2 = 1e-10
    if p2 >= 1:
        p2 = 1 - 1e-10

    kl_12 = p1 * math.log2(p1 / p2) + (1 - p1) * math.log2((1 - p1) / (1 - p2))
    kl_21 = p2 * math.log2(p2 / p1) + (1 - p2) * math.log2((1 - p2) / (1 - p1))
    return (kl_12 + kl_21) / 2.0


def check_convergence(
    posterior_t: float,
    posterior_t_prev: float,
    epsilon: float = 0.01,
) -> tuple[bool, float]:
    """Check if the posterior has converged (Harmonize phase).

    ‖P(θ_t) - P(θ_{t-1})‖ < ε

    Args:
        posterior_t: Current posterior.
        posterior_t_prev: Previous posterior.
        epsilon: Convergence threshold.

    Returns:
        Tuple of (converged, delta).
    """
    delta = kl_distance(posterior_t, posterior_t_prev)
    return (delta < epsilon, delta)


def run_bayesian_dream(
    initial_prior: float = 0.5,
    evidence: list[float] | None = None,
    max_iterations: int = 3,
    convergence_epsilon: float = 0.01,
    decay_gamma: float = 0.9,
    regularization_lambda: float = 0.1,
) -> BayesianDreamResult:
    """Run a complete Bayesian dream cycle (Objective J).

    Executes all 12 phases as a variational inference pass, iterating
    until convergence or max_iterations.

    Args:
        initial_prior: Starting prior probability.
        evidence: List of evidence values (0-1, where 1 = success).
        max_iterations: Maximum number of full 12-phase cycles.
        convergence_epsilon: Convergence threshold for Harmonize phase.
        decay_gamma: Decay factor for the Decay phase.
        regularization_lambda: Regularization strength for Governance phase.

    Returns:
        BayesianDreamResult with all phase results and convergence info.
    """
    if evidence is None:
        evidence = []

    result = BayesianDreamResult(cycle_id=f"bayesian_dream_{id(evidence)}")
    prior = initial_prior

    for iteration in range(max_iterations):
        prev_posterior = prior

        for phase_name in DREAM_PHASES:
            role_info = BAYESIAN_ROLE_MAP[phase_name]
            phase_result = PhaseResult(
                phase=phase_name,
                bayesian_role=role_info["role"],
                math=role_info["math"],
            )

            if phase_name == "triage":
                # Prior selection: weight by relevance
                phase_result.prior_update = prior
                phase_result.posterior_value = prior

            elif phase_name == "consolidation":
                # Evidence aggregation: Σ log P(e_i | θ)
                if evidence:
                    log_lik = sum(
                        math.log(max(e * prior + (1 - e) * (1 - prior), 1e-10))
                        for e in evidence
                    )
                    phase_result.evidence_count = len(evidence)
                    phase_result.metadata["log_likelihood"] = log_lik
                    # Update posterior using log-likelihood
                    posterior = 1.0 / (1.0 + math.exp(-log_lik / max(len(evidence), 1)))
                    phase_result.posterior_value = posterior
                    prior = posterior
                else:
                    phase_result.posterior_value = prior

            elif phase_name == "serendipity":
                # Likelihood estimation from bridge discovery
                phase_result.posterior_value = prior

            elif phase_name == "governance":
                # Prior regularization: P(θ) ← P(θ) · exp(-λ · echo_chamber_penalty)
                # Simple echo chamber penalty: distance from 0.5
                echo_penalty = abs(prior - 0.5) * 2  # 0 at 0.5, 1 at 0/1
                prior = prior * math.exp(-regularization_lambda * echo_penalty)
                prior = max(0.01, min(0.99, prior))
                phase_result.prior_update = prior
                phase_result.posterior_value = prior
                phase_result.metadata["echo_chamber_penalty"] = echo_penalty

            elif phase_name == "narrative":
                # Posterior summarization
                phase_result.posterior_value = prior
                phase_result.metadata["summary"] = f"Posterior: {prior:.4f}"

            elif phase_name == "kaizen":
                # Action selection: pick action with highest expected utility
                phase_result.posterior_value = prior
                phase_result.metadata["selected_action"] = "improve" if prior > 0.5 else "observe"

            elif phase_name == "oracle":
                # Expert prior injection: blend with grimoire prior (0.5 default)
                grimoire_prior = 0.5
                prior = 0.7 * prior + 0.3 * grimoire_prior
                phase_result.prior_update = prior
                phase_result.posterior_value = prior

            elif phase_name == "decay":
                # Posterior forgetting: P(θ) ← P(θ)^γ
                prior = prior ** decay_gamma
                # Renormalize: if prior was 0.5, 0.5^0.9 ≈ 0.536, need to recenter
                prior = max(0.01, min(0.99, prior))
                phase_result.prior_update = prior
                phase_result.posterior_value = prior
                phase_result.metadata["gamma"] = decay_gamma

            elif phase_name == "constellation":
                # Posterior clustering
                phase_result.posterior_value = prior

            elif phase_name == "prediction":
                # Forward simulation
                phase_result.posterior_value = prior
                phase_result.metadata["mc_ready"] = True

            elif phase_name == "enrichment":
                # Posterior refinement with new evidence
                phase_result.posterior_value = prior

            elif phase_name == "harmonize":
                # Convergence check
                converged, delta = check_convergence(prior, prev_posterior, convergence_epsilon)
                phase_result.posterior_value = prior
                phase_result.metadata["delta"] = delta
                phase_result.metadata["converged"] = converged
                result.convergence_delta = delta
                result.converged = converged

            result.phases.append(phase_result)

        result.iterations = iteration + 1

        if result.converged:
            break

    result.final_posterior = prior
    return result
