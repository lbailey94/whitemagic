# ruff: noqa: BLE001
"""v24.3 Tool Handlers — Transaction Firewall, Bounty Connector, Auto-Optimizer,
Ambient Sensorium, WASM Verifier, Network State, Genetic Harness.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Transaction Firewall ─────────────────────────────────────────────


def handle_tx_firewall_status(**kwargs: Any) -> dict[str, Any]:
    """Get transaction firewall status."""
    from whitemagic.security.transaction_firewall import get_transaction_firewall

    return {"status": "success", "firewall": get_transaction_firewall().get_status()}


def handle_tx_firewall_set_policy(**kwargs: Any) -> dict[str, Any]:
    """Set a per-agent transaction policy."""
    from whitemagic.security.transaction_firewall import (
        TransactionPolicy,
        get_transaction_firewall,
    )

    agent_id = kwargs.get("agent_id", "")
    if not agent_id:
        return {"status": "error", "message": "agent_id required"}

    policy = TransactionPolicy(
        max_single_transaction=float(kwargs.get("max_single", 100.0)),
        daily_limit=float(kwargs.get("daily_limit", 1000.0)),
        rate_limit_per_minute=int(kwargs.get("rate_limit", 10)),
        dharma_check_required=bool(kwargs.get("dharma_check", True)),
        dharma_threshold=float(kwargs.get("dharma_threshold", 0.5)),
    )
    if kwargs.get("allowed_recipients"):
        policy.allowed_recipients = set(kwargs["allowed_recipients"])
    if kwargs.get("blocked_recipients"):
        policy.blocked_recipients = set(kwargs["blocked_recipients"])

    get_transaction_firewall().set_policy(agent_id, policy)
    return {"status": "success", "agent_id": agent_id}


# ── Bounty Connector ─────────────────────────────────────────────────


def handle_bounty_scan(**kwargs: Any) -> dict[str, Any]:
    """Scan external bounty platforms and match to agents."""
    from whitemagic.agents.bounty_connector import get_bounty_connector

    connector = get_bounty_connector()
    matched = connector.scan_and_match()
    return {
        "status": "success",
        "matched_count": len(matched),
        "matched": [
            {
                "platform": m.bounty.platform,
                "external_id": m.bounty.external_id,
                "title": m.bounty.title,
                "reward": m.estimated_reward,
                "best_agent": m.best_agent_id,
                "match_score": m.capability_match_score,
            }
            for m in matched
        ],
    }


def handle_bounty_auto_claim(**kwargs: Any) -> dict[str, Any]:
    """Run full scan → match → claim cycle."""
    from whitemagic.agents.bounty_connector import get_bounty_connector

    connector = get_bounty_connector()
    result = connector.run_cycle()
    return {"status": "success", **result}


def handle_bounty_connector_status(**kwargs: Any) -> dict[str, Any]:
    """Get bounty connector status."""
    from whitemagic.agents.bounty_connector import get_bounty_connector

    return {"status": "success", "connector": get_bounty_connector().get_status()}


# ── Model Auto-Optimizer ─────────────────────────────────────────────


def handle_model_optimize(**kwargs: Any) -> dict[str, Any]:
    """Run model auto-optimization loop."""
    from whitemagic.inference.auto_optimizer import get_auto_optimizer
    from whitemagic.inference.llama_cpp import LlamaCppBackend, LlamaCppConfig

    iterations = int(kwargs.get("iterations", 3))
    model_path = kwargs.get("model_path", "")

    config = LlamaCppConfig(model_path=model_path)
    backend = LlamaCppBackend(model_path=model_path, auto_start=False)

    if not backend.is_available:
        return {"status": "error", "message": "Model backend not available"}

    optimizer = get_auto_optimizer()
    best = optimizer.optimize(backend, config, iterations=iterations)

    # Persist optimal config
    if hasattr(best, "config_snapshot"):
        optimal_config = optimizer._dict_to_config(best.config_snapshot, config)
        optimizer.apply_optimal(optimal_config)

    return {
        "status": "success",
        "best_tps": best.tokens_per_second,
        "best_fitness": best.fitness(),
        "best_config": best.config_snapshot,
    }


def handle_model_optimize_status(**kwargs: Any) -> dict[str, Any]:
    """Get auto-optimizer status."""
    from whitemagic.inference.auto_optimizer import get_auto_optimizer

    return {"status": "success", "optimizer": get_auto_optimizer().get_status()}


# ── Ambient Sensorium ────────────────────────────────────────────────


def handle_ambient_state(**kwargs: Any) -> dict[str, Any]:
    """Get current ambient sensorium state."""
    from whitemagic.core.consciousness.ambient_sensorium import get_ambient_sensorium

    sensorium = get_ambient_sensorium()
    state = sensorium.compute_ambient_state()
    return {
        "status": "success",
        "state": state.to_dict(),
        "should_proact": sensorium.should_proact(),
        "suggested_actions": sensorium.suggest_actions(),
    }


def handle_ambient_status(**kwargs: Any) -> dict[str, Any]:
    """Get sensorium background status."""
    from whitemagic.core.consciousness.ambient_sensorium import get_ambient_sensorium

    return {"status": "success", "sensorium": get_ambient_sensorium().get_status()}


# ── WASM Verifier ────────────────────────────────────────────────────


def handle_wasm_verify_status(**kwargs: Any) -> dict[str, Any]:
    """Get WASM verifier status."""
    from whitemagic.security.wasm_verifier import get_wasm_verifier

    return {"status": "success", "verifier": get_wasm_verifier().get_status()}


# ── Network State ────────────────────────────────────────────────────


def handle_network_state_status(**kwargs: Any) -> dict[str, Any]:
    """Get network state profile status."""
    from whitemagic.core.identity.network_state import get_network_state

    return {"status": "success", "network_state": get_network_state().get_status()}


def handle_network_state_create_identity(**kwargs: Any) -> dict[str, Any]:
    """Create a sovereign agent identity."""
    from whitemagic.core.identity.network_state import get_network_state

    agent_id = kwargs.get("agent_id", "")
    display_name = kwargs.get("display_name", "")
    capabilities = kwargs.get("capabilities", [])
    bio = kwargs.get("bio", "")

    if not agent_id or not display_name:
        return {"status": "error", "message": "agent_id and display_name required"}

    identity = get_network_state().create_identity(agent_id, display_name, capabilities, bio)
    return {"status": "success", "identity": identity.to_dict()}


def handle_network_state_propose(**kwargs: Any) -> dict[str, Any]:
    """Create a governance proposal."""
    from whitemagic.core.identity.network_state import get_network_state

    title = kwargs.get("title", "")
    description = kwargs.get("description", "")
    proposer = kwargs.get("proposer", "")
    execution_tool = kwargs.get("execution_tool")

    if not title or not proposer:
        return {"status": "error", "message": "title and proposer required"}

    proposal = get_network_state().create_proposal(title, description, proposer, execution_tool)
    return {"status": "success", "proposal": proposal.to_dict()}


def handle_network_state_vote(**kwargs: Any) -> dict[str, Any]:
    """Vote on a governance proposal."""
    from whitemagic.core.identity.network_state import get_network_state

    proposal_id = kwargs.get("proposal_id", "")
    agent_id = kwargs.get("agent_id", "")
    support = bool(kwargs.get("support", True))
    confidence = float(kwargs.get("confidence", 1.0))

    if not proposal_id or not agent_id:
        return {"status": "error", "message": "proposal_id and agent_id required"}

    result = get_network_state().vote(proposal_id, agent_id, support, confidence)
    return result


def handle_network_state_resolve(**kwargs: Any) -> dict[str, Any]:
    """Resolve a governance proposal."""
    from whitemagic.core.identity.network_state import get_network_state

    proposal_id = kwargs.get("proposal_id", "")
    if not proposal_id:
        return {"status": "error", "message": "proposal_id required"}

    result = get_network_state().resolve_proposal(proposal_id)
    return result


# ── Genetic Harness ──────────────────────────────────────────────────


def handle_genetic_run(**kwargs: Any) -> dict[str, Any]:
    """Run a genetic algorithm optimization."""
    from whitemagic.core.evolution.genetic_harness import (
    GeneticConfig,
    GeneticHarness,
)

    gene_bounds_str = kwargs.get("gene_bounds", {})
    generations = int(kwargs.get("generations", 50))
    population_size = int(kwargs.get("population_size", 20))
    mutation_rate = float(kwargs.get("mutation_rate", 0.1))
    crossover_rate = float(kwargs.get("crossover_rate", 0.7))
    elitism = int(kwargs.get("elitism", 2))
    fitness_mode = kwargs.get("fitness_mode", "sum")

    # Parse gene bounds: {"x": [0, 10], "y": [0, 10]}
    gene_bounds: dict[str, tuple[float, float]] = {}
    for name, bounds in gene_bounds_str.items():
        if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
            gene_bounds[name] = (float(bounds[0]), float(bounds[1]))

    if not gene_bounds:
        return {"status": "error", "message": "gene_bounds required"}

    config = GeneticConfig(
        population_size=population_size,
        mutation_rate=mutation_rate,
        crossover_rate=crossover_rate,
        elitism=elitism,
        max_generations=generations,
        gene_bounds=gene_bounds,
    )

    if fitness_mode == "sum":

        def fitness(chrom):
            return sum(chrom.genes.values())

    elif fitness_mode == "product":

        def fitness(chrom):
            result = 1.0
            for v in chrom.genes.values():
                result *= max(v, 0.001)
            return result

    else:
        return {"status": "error", "message": f"Unknown fitness_mode: {fitness_mode}"}

    harness = GeneticHarness(config, fitness)
    harness.initialize_population()
    best = harness.run(generations=generations)

    return {
        "status": "success",
        "best_fitness": best.fitness,
        "best_genes": best.genes,
        "generation": best.generation,
        "history": harness.get_history()[-5:],  # Last 5 generations
    }


def handle_genetic_status(**kwargs: Any) -> dict[str, Any]:
    """Get genetic harness status (not stateless — returns last run info)."""
    return {
        "status": "success",
        "message": "Genetic harness is stateless. Use genetic.run to start optimization.",
    }
