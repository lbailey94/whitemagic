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


def handle_bounty_scan_all(**kwargs: Any) -> dict[str, Any]:
    """Scan all registered bounty platforms and return aggregated results.

    Optionally filter by min_reward, ecosystem, or language.
    """
    from whitemagic.agents.bounty_platforms import scan_all_platforms

    limit_per = int(kwargs.get("limit_per_platform", 30))
    min_reward = float(kwargs.get("min_reward", 0))
    ecosystem_filter = kwargs.get("ecosystem", "").lower()
    language_filter = kwargs.get("language", "").lower()

    raw = scan_all_platforms(limit_per_platform=limit_per)

    # Flatten and filter
    all_bounties = []
    platform_counts = {}
    for platform_name, bounties in raw.items():
        platform_counts[platform_name] = len(bounties)
        for b in bounties:
            if b.reward < min_reward:
                continue
            # Apply ecosystem/language filters on extra metadata if available
            extra = getattr(b, "_extra", {})
            if ecosystem_filter:
                ecosystems = [e.lower() for e in extra.get("ecosystems", [])]
                if ecosystem_filter not in ecosystems:
                    continue
            if language_filter:
                languages = [l.lower() for l in extra.get("languages", [])]
                if language_filter not in languages:
                    continue
            all_bounties.append({
                "platform": b.platform,
                "external_id": b.external_id,
                "title": b.title,
                "reward": b.reward,
                "currency": b.currency,
                "url": b.url,
                "deadline": b.deadline,
                "description": b.description[:200],
                "required_capabilities": b.required_capabilities,
            })

    # Sort by reward descending
    all_bounties.sort(key=lambda x: x["reward"], reverse=True)

    return {
        "status": "success",
        "platforms_scanned": len(raw),
        "platform_counts": platform_counts,
        "total_bounties": len(all_bounties),
        "bounties": all_bounties[:100],  # Cap at 100 for response size
    }


def handle_bounty_poc_generate(**kwargs: Any) -> dict[str, Any]:
    """Generate a Foundry exploit PoC from a vulnerability type or finding.

    Either pass vuln_type + contract_name + function_name directly,
    or pass a finding dict from slither.scan / strata results.
    """
    from whitemagic.tools.security.poc_generator import (
        generate_exploit_poc,
        generate_poc_from_finding,
        list_vuln_types,
    )

    finding = kwargs.get("finding")
    if finding:
        result = generate_poc_from_finding(finding, project_dir=kwargs.get("project_dir"))
    else:
        result = generate_exploit_poc(
            vuln_type=kwargs.get("vuln_type", "generic"),
            contract_name=kwargs.get("contract_name", "TargetContract"),
            function_name=kwargs.get("function_name", "vulnerableFunction"),
            description=kwargs.get("description", ""),
            target_address=kwargs.get("target_address", ""),
            project_dir=kwargs.get("project_dir"),
        )

    return {
        "status": "success" if result.success else "error",
        "vuln_type": result.vuln_type,
        "contract_name": result.contract_name,
        "test_code": result.test_code,
        "test_file": result.test_file,
        "error": result.error,
        "supported_types": list_vuln_types() if not result.success else [],
    }


def handle_bounty_report_generate(**kwargs: Any) -> dict[str, Any]:
    """Generate a professional bounty submission report for a specific platform."""
    from whitemagic.tools.security.poc_generator import generate_bounty_report

    report = generate_bounty_report(
        title=kwargs.get("title", ""),
        severity=kwargs.get("severity", "medium"),
        description=kwargs.get("description", ""),
        impact=kwargs.get("impact", ""),
        proof_of_concept=kwargs.get("proof_of_concept", ""),
        mitigation=kwargs.get("mitigation", ""),
        platform=kwargs.get("platform", "immunefi"),
    )
    return {"status": "success", "report": report, "platform": kwargs.get("platform", "immunefi")}


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


# ── v24.3.2: Extended Bounty Platform Tools ──────────────────────────


def handle_bounty_platforms(**kwargs: Any) -> dict[str, Any]:
    """List all registered bounty platforms with metadata."""
    from whitemagic.agents.bounty_platforms import get_all_platforms

    platforms = get_all_platforms()
    result = []
    for p in platforms:
        result.append({
            "name": p.platform_name,
            "url": getattr(p, "_OPPORTUNITIES_URL", getattr(p, "_BOUNTIES_URL", getattr(p, "_PROGRAMS_URL", ""))),
            "api_url": getattr(p, "_API_URL", getattr(p, "_API_BASE", "")),
            "supports_claim": hasattr(p, "claim_bounty"),
            "supports_submit": hasattr(p, "submit_result"),
        })
    return {"status": "success", "platforms": result, "count": len(result)}


def handle_bounty_scan_platform(**kwargs: Any) -> dict[str, Any]:
    """Scan a single specific platform by name."""
    from whitemagic.agents.bounty_platforms import get_all_platforms

    platform_name = kwargs.get("platform", "").lower()
    if not platform_name:
        return {"status": "error", "message": "platform parameter required"}

    limit = int(kwargs.get("limit", 30))
    min_reward = float(kwargs.get("min_reward", 0))

    for p in get_all_platforms():
        if p.platform_name == platform_name:
            bounties = p.scan_bounties(limit=limit)
            filtered = [b for b in bounties if b.reward >= min_reward]
            return {
                "status": "success",
                "platform": platform_name,
                "count": len(filtered),
                "bounties": [
                    {
                        "external_id": b.external_id,
                        "title": b.title,
                        "reward": b.reward,
                        "currency": b.currency,
                        "url": b.url,
                        "deadline": b.deadline,
                        "description": b.description[:200],
                        "required_capabilities": b.required_capabilities,
                    }
                    for b in filtered
                ],
            }
    return {"status": "error", "message": f"Platform '{platform_name}' not found"}


def handle_bounty_match(**kwargs: Any) -> dict[str, Any]:
    """Match scanned bounties to registered agent capabilities without auto-claiming."""
    from whitemagic.agents.bounty_connector import get_bounty_connector

    connector = get_bounty_connector()
    matched = connector.scan_and_match()
    min_score = float(kwargs.get("min_score", 0.0))
    limit = int(kwargs.get("limit", 50))

    results = [
        {
            "platform": m.bounty.platform,
            "external_id": m.bounty.external_id,
            "title": m.bounty.title,
            "reward": m.estimated_reward,
            "currency": m.bounty.currency,
            "best_agent": m.best_agent_id,
            "match_score": m.capability_match_score,
            "url": m.bounty.url,
        }
        for m in matched
        if m.capability_match_score >= min_score
    ]
    return {"status": "success", "matched_count": len(results), "matched": results[:limit]}


def handle_bounty_deadlines(**kwargs: Any) -> dict[str, Any]:
    """Get upcoming bounty deadlines across all platforms, sorted by urgency."""
    from whitemagic.agents.bounty_platforms import scan_all_platforms
    import time

    limit = int(kwargs.get("limit", 30))
    days_ahead = int(kwargs.get("days_ahead", 30))
    now = time.time()
    cutoff = now + (days_ahead * 86400)

    raw = scan_all_platforms(limit_per_platform=50)
    upcoming = []
    for _platform_name, bounties in raw.items():
        for b in bounties:
            if b.deadline and now <= b.deadline <= cutoff:
                upcoming.append({
                    "platform": b.platform,
                    "title": b.title,
                    "reward": b.reward,
                    "currency": b.currency,
                    "deadline": b.deadline,
                    "days_left": round((b.deadline - now) / 86400, 1),
                    "url": b.url,
                })
    upcoming.sort(key=lambda x: x["deadline"])
    return {
        "status": "success",
        "count": len(upcoming),
        "deadlines": upcoming[:limit],
        "days_ahead": days_ahead,
    }


def handle_bounty_stats(**kwargs: Any) -> dict[str, Any]:
    """Aggregate statistics across all bounty platforms."""
    from whitemagic.agents.bounty_platforms import scan_all_platforms

    raw = scan_all_platforms(limit_per_platform=50)
    platform_stats = {}
    total_bounties = 0
    total_reward = 0.0
    by_currency: dict[str, float] = {}

    for platform_name, bounties in raw.items():
        count = len(bounties)
        reward_sum = sum(b.reward for b in bounties)
        max_reward = max((b.reward for b in bounties), default=0)
        platform_stats[platform_name] = {
            "count": count,
            "total_reward": reward_sum,
            "max_reward": max_reward,
        }
        total_bounties += count
        total_reward += reward_sum
        for b in bounties:
            by_currency[b.currency] = by_currency.get(b.currency, 0) + b.reward

    return {
        "status": "success",
        "total_platforms": len(raw),
        "total_bounties": total_bounties,
        "total_reward_usd_est": total_reward,
        "by_platform": platform_stats,
        "by_currency": by_currency,
    }


def handle_bounty_earnings(**kwargs: Any) -> dict[str, Any]:
    """Query tracked bounty earnings history."""
    from whitemagic.core.memory.galaxy_manager import GalaxyManager

    status_filter = kwargs.get("status", "")
    limit = int(kwargs.get("limit", 50))

    try:
        gm = GalaxyManager()
        results = gm.search(
            query="bounty_earnings",
            galaxy="codex",
            limit=limit,
        )
        earnings = []
        for mem in results:
            content = mem.get("content", "")
            if "bounty_earnings" not in content:
                continue
            if status_filter and f'"status": "{status_filter}"' not in content:
                continue
            earnings.append({
                "memory_id": mem.get("id", ""),
                "content": content[:300],
                "tags": mem.get("tags", []),
                "timestamp": mem.get("created_at", 0),
            })
        return {"status": "success", "count": len(earnings), "earnings": earnings}
    except Exception as e:
        return {"status": "success", "count": 0, "earnings": [], "note": f"Galaxy search unavailable: {e}"}


def handle_strata_model_security(**kwargs: Any) -> dict[str, Any]:
    """Run STRATA model file format security checker on a project path."""
    from pathlib import Path
    from whitemagic.tools.strata.file_index import FileIndex
    from whitemagic.tools.strata.checkers.model_security import (
        check_unsafe_pickle_deserialization,
        check_unsafe_torch_load,
        check_unsafe_keras_load,
        check_hf_trust_remote_code,
        check_model_path_traversal,
        check_pickle_reduce_exploit,
        check_unsafe_yaml_in_model_config,
        check_onnx_unsafe_load,
        check_numpy_unsafe_load,
        check_pickle_files_in_repo,
    )

    project_path_str = kwargs.get("project_path", "")
    if not project_path_str:
        return {"status": "error", "message": "project_path required"}

    project_path = Path(project_path_str)
    if not project_path.exists():
        return {"status": "error", "message": f"Path not found: {project_path}"}

    file_index = FileIndex(project_path)
    findings: list = []

    all_checkers = [
        check_unsafe_pickle_deserialization,
        check_unsafe_torch_load,
        check_unsafe_keras_load,
        check_hf_trust_remote_code,
        check_model_path_traversal,
        check_pickle_reduce_exploit,
        check_unsafe_yaml_in_model_config,
        check_onnx_unsafe_load,
        check_numpy_unsafe_load,
        check_pickle_files_in_repo,
    ]

    for checker in all_checkers:
        try:
            checker(project_path, file_index, findings)
        except Exception as e:
            logger.warning("Checker %s failed: %s", checker.__name__, e)

    return {
        "status": "success",
        "project_path": str(project_path),
        "total_findings": len(findings),
        "findings": [
            {
                "severity": f.severity.value,
                "category": f.category,
                "file": f.file,
                "line": f.line,
                "message": f.message,
                "suggestion": f.suggestion,
            }
            for f in findings
        ],
        "checkers_run": [c.__name__ for c in all_checkers],
    }


def handle_bounty_huntr_mfv(**kwargs: Any) -> dict[str, Any]:
    """List huntr.com MFV (Model File Format) bounties mapped to STRATA checker patterns."""
    from whitemagic.agents.bounty_platforms import HuntrPlatform

    _cache._data.pop("huntr", None) if kwargs.get("refresh", False) else None
    platform = HuntrPlatform()
    bounties = platform.scan_bounties(limit=60)

    mfv_bounties = [b for b in bounties if "mfv" in b.external_id or "mvf" in b.external_id]
    challenges = [b for b in bounties if "challenge" in b.title.lower()]

    strata_mapping = {
        "pickle": "check_unsafe_pickle_deserialization",
        "keras": "check_unsafe_keras_load",
        "tensorflow": "check_unsafe_keras_load",
        "lambda": "check_unsafe_keras_load",
        "torch": "check_unsafe_torch_load",
        "pytorch": "check_unsafe_torch_load",
        "onnx": "check_onnx_unsafe_load",
        "numpy": "check_numpy_unsafe_load",
        "huggingface": "check_hf_trust_remote_code",
        "hf": "check_hf_trust_remote_code",
        "yaml": "check_unsafe_yaml_load",
        "archive": "check_model_path_traversal",
        "safetensors": "check_unsafe_torch_load",
        "gguf": "check_unsafe_torch_load",
    }

    mapped = []
    for b in mfv_bounties:
        checker = "check_unsafe_pickle_deserialization"  # default
        title_lower = b.title.lower()
        for keyword, chk in strata_mapping.items():
            if keyword in title_lower or keyword in b.external_id:
                checker = chk
                break
        mapped.append({
            "external_id": b.external_id,
            "title": b.title,
            "reward": b.reward,
            "url": b.url,
            "description": b.description[:200],
            "strata_checker": checker,
        })

    return {
        "status": "success",
        "mfv_count": len(mapped),
        "mfv_bounties": mapped,
        "challenges": [
            {
                "title": c.title,
                "reward": c.reward,
                "url": c.url,
                "deadline": c.deadline,
            }
            for c in challenges
        ],
        "total_value": sum(b.reward for b in mfv_bounties),
    }


def handle_bounty_opportunities(**kwargs: Any) -> dict[str, Any]:
    """Get high-value bounties sorted by reward × capability match score."""
    from whitemagic.agents.bounty_connector import get_bounty_connector

    connector = get_bounty_connector()
    matched = connector.scan_and_match()
    limit = int(kwargs.get("limit", 20))
    min_reward = float(kwargs.get("min_reward", 0))

    opportunities = []
    for m in matched:
        if m.estimated_reward < min_reward:
            continue
        score = m.capability_match_score * max(m.estimated_reward, 1)
        opportunities.append({
            "platform": m.bounty.platform,
            "title": m.bounty.title,
            "reward": m.estimated_reward,
            "currency": m.bounty.currency,
            "match_score": m.capability_match_score,
            "opportunity_score": round(score, 2),
            "best_agent": m.best_agent_id,
            "url": m.bounty.url,
            "deadline": m.bounty.deadline,
            "required_capabilities": m.bounty.required_capabilities,
        })
    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return {"status": "success", "count": len(opportunities), "opportunities": opportunities[:limit]}


def handle_bounty_register_agent(**kwargs: Any) -> dict[str, Any]:
    """Register agent capabilities with the bounty connector."""
    from whitemagic.agents.bounty_connector import get_bounty_connector

    agent_id = kwargs.get("agent_id", "")
    capabilities = kwargs.get("capabilities", [])

    if not agent_id:
        return {"status": "error", "message": "agent_id required"}
    if not capabilities:
        return {"status": "error", "message": "capabilities list required"}

    connector = get_bounty_connector()
    connector.register_agent(agent_id, capabilities)
    return {
        "status": "success",
        "agent_id": agent_id,
        "capabilities": capabilities,
        "total_agents": len(connector._agent_capabilities),
    }
