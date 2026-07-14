"""Research DAG, Autoswarm, Warp, and Mesh Experiment tool handlers."""

# ruff: noqa: BLE001
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Research DAG ──

def handle_research_dag_submit(**kwargs: Any) -> dict[str, Any]:
    """Submit a hypothesis to the research DAG."""
    from whitemagic.core.evolution.research_dag import (
        ResearchDomain,
        get_research_dag,
    )

    hypothesis = kwargs.get("hypothesis", "")
    if not hypothesis:
        return {"status": "error", "error": "hypothesis is required"}

    domain_str = kwargs.get("domain", "cognitive")
    try:
        domain = ResearchDomain(domain_str)
    except ValueError:
        domain = ResearchDomain.CUSTOM

    dag = get_research_dag()
    exp = dag.submit_hypothesis(
        hypothesis=hypothesis,
        domain=domain,
        parameters=kwargs.get("parameters", {}),
        agent_id=kwargs.get("agent_id", ""),
        inspiration_ids=kwargs.get("inspiration_ids", []),
        parent_id=kwargs.get("parent_id"),
        metadata=kwargs.get("metadata", {}),
    )
    return {"status": "success", "experiment": exp.to_dict()}


def handle_research_dag_result(**kwargs: Any) -> dict[str, Any]:
    """Record an experiment result."""
    from whitemagic.core.evolution.research_dag import get_research_dag

    experiment_id = kwargs.get("experiment_id", "")
    if not experiment_id:
        return {"status": "error", "error": "experiment_id is required"}

    fitness_score = float(kwargs.get("fitness_score", 0.0))
    dag = get_research_dag()
    dag.record_trial(experiment_id)
    exp = dag.record_result(
        experiment_id,
        fitness_score=fitness_score,
        outcome=kwargs.get("outcome"),
    )
    if exp is None:
        return {"status": "error", "error": "Experiment not found"}
    return {"status": "success", "experiment": exp.to_dict()}


def handle_research_dag_critique(**kwargs: Any) -> dict[str, Any]:
    """Submit a peer critique of an experiment."""
    from whitemagic.core.evolution.research_dag import get_research_dag

    experiment_id = kwargs.get("experiment_id", "")
    if not experiment_id:
        return {"status": "error", "error": "experiment_id is required"}

    score = int(kwargs.get("score", 5))
    critic_agent_id = kwargs.get("critic_agent_id", "anonymous")
    notes = kwargs.get("notes", "")

    dag = get_research_dag()
    exp = dag.record_critique(experiment_id, critic_agent_id, score, notes)
    if exp is None:
        return {"status": "error", "error": "Experiment not found"}
    return {"status": "success", "experiment": exp.to_dict()}


def handle_research_dag_lineage(**kwargs: Any) -> dict[str, Any]:
    """Get lineage tree for an experiment."""
    from whitemagic.core.evolution.research_dag import get_research_dag

    experiment_id = kwargs.get("experiment_id", "")
    if not experiment_id:
        return {"status": "error", "error": "experiment_id is required"}

    max_depth = int(kwargs.get("max_depth", 10))
    dag = get_research_dag()
    lineage = dag.get_lineage(experiment_id, max_depth)
    return {"status": "success", "lineage": lineage}


def handle_research_dag_breakthroughs(**kwargs: Any) -> dict[str, Any]:
    """List top breakthroughs."""
    from whitemagic.core.evolution.research_dag import (
        ResearchDomain,
        get_research_dag,
    )

    domain_str = kwargs.get("domain")
    domain = None
    if domain_str:
        try:
            domain = ResearchDomain(domain_str)
        except ValueError:
            logger.debug("Ignored ValueError in research.py:108")

    limit = int(kwargs.get("limit", 20))
    dag = get_research_dag()
    breakthroughs = dag.get_breakthroughs(domain=domain, limit=limit)
    return {
        "status": "success",
        "breakthroughs": [e.to_dict() for e in breakthroughs],
        "count": len(breakthroughs),
    }


def handle_research_dag_stats(**kwargs: Any) -> dict[str, Any]:
    """Get research DAG statistics."""
    from whitemagic.core.evolution.research_dag import get_research_dag

    dag = get_research_dag()
    return {"status": "success", "stats": dag.get_stats()}


def handle_research_dag_leaderboard(**kwargs: Any) -> dict[str, Any]:
    """Get domain leaderboard."""
    from whitemagic.core.evolution.research_dag import (
        ResearchDomain,
        get_research_dag,
    )

    domain_str = kwargs.get("domain", "cognitive")
    try:
        domain = ResearchDomain(domain_str)
    except ValueError:
        return {"status": "error", "error": f"Unknown domain: {domain_str}"}

    limit = int(kwargs.get("limit", 10))
    dag = get_research_dag()
    leaderboard = dag.get_domain_leaderboard(domain, limit)
    return {"status": "success", "leaderboard": leaderboard}


def handle_research_dag_experiments(**kwargs: Any) -> dict[str, Any]:
    """Query experiments with optional filters."""
    from whitemagic.core.evolution.research_dag import (
        ExperimentStage,
        ResearchDomain,
        get_research_dag,
    )

    domain_str = kwargs.get("domain")
    domain = None
    if domain_str:
        try:
            domain = ResearchDomain(domain_str)
        except ValueError:
            logger.debug("Ignored ValueError in research.py:161")

    stage_str = kwargs.get("stage")
    stage = None
    if stage_str:
        try:
            stage = ExperimentStage(stage_str)
        except ValueError:
            logger.debug("Ignored ValueError in research.py:169")

    limit = int(kwargs.get("limit", 50))
    offset = int(kwargs.get("offset", 0))
    dag = get_research_dag()
    experiments = dag.get_experiments(domain=domain, stage=stage, limit=limit, offset=offset)
    return {
        "status": "success",
        "experiments": [e.to_dict() for e in experiments],
        "count": len(experiments),
    }


# ── Autoswarm ──

def handle_autoswarm_campaign(**kwargs: Any) -> dict[str, Any]:
    """Launch an evolutionary campaign."""
    from whitemagic.core.evolution.autoswarm import (
        CampaignConfig,
        ResearchDomain,
        get_autoswarm,
    )

    campaign_name = kwargs.get("campaign_name", "manual_campaign")
    domain_str = kwargs.get("domain", "cognitive")
    try:
        domain = ResearchDomain(domain_str)
    except ValueError:
        domain = ResearchDomain.COGNITIVE

    config = CampaignConfig(
        campaign_name=campaign_name,
        domain=domain,
        hypothesis_space=kwargs.get("hypothesis_space", "guna_balance"),
        n_trials=int(kwargs.get("n_trials", 50)),
        max_iterations=int(kwargs.get("max_iterations", 10)),
        share_results=kwargs.get("share_results", True),
        dream_integration=kwargs.get("dream_integration", True),
    )

    autoswarm = get_autoswarm()
    result = autoswarm.run_campaign(config)
    return {"status": "success", "result": result.to_dict()}


def handle_autoswarm_status(**kwargs: Any) -> dict[str, Any]:
    """Get autoswarm status."""
    from whitemagic.core.evolution.autoswarm import get_autoswarm

    autoswarm = get_autoswarm()
    return {"status": "success", "autoswarm": autoswarm.get_status()}


def handle_autoswarm_start(**kwargs: Any) -> dict[str, Any]:
    """Start continuous autoswarm loop."""
    from whitemagic.core.evolution.autoswarm import get_autoswarm

    interval = float(kwargs.get("interval_seconds", 300.0))
    autoswarm = get_autoswarm()
    autoswarm.run_continuous(interval_seconds=interval)
    return {"status": "success", "message": f"Autoswarm started with {interval}s interval"}


def handle_autoswarm_stop(**kwargs: Any) -> dict[str, Any]:
    """Stop continuous autoswarm loop."""
    from whitemagic.core.evolution.autoswarm import get_autoswarm

    autoswarm = get_autoswarm()
    autoswarm.stop()
    return {"status": "success", "message": "Autoswarm stopped"}


# ── Warps ──

def handle_warp_load(**kwargs: Any) -> dict[str, Any]:
    """Load a warp preset by name."""
    from whitemagic.agents.warps import get_warp_manager

    name = kwargs.get("name", "")
    if not name:
        return {"status": "error", "error": "warp name is required"}

    manager = get_warp_manager()

    # Check if stacking is requested
    names_str = kwargs.get("stack")
    if names_str:
        names = [n.strip() for n in names_str.split("+") if n.strip()]
        warp = manager.stack_warps(names)
    else:
        warp = manager.load_warp(name)

    if warp is None:
        return {"status": "error", "error": f"Warp '{name}' not found"}
    return {"status": "success", "warp": warp.to_dict()}


def handle_warp_list(**kwargs: Any) -> dict[str, Any]:
    """List all available warps."""
    from whitemagic.agents.warps import get_warp_manager

    include_custom = kwargs.get("include_custom", True)
    manager = get_warp_manager()
    warps = manager.list_warps(include_custom=include_custom)
    return {"status": "success", "warps": warps, "count": len(warps)}


def handle_warp_create(**kwargs: Any) -> dict[str, Any]:
    """Create a custom warp."""
    from whitemagic.agents.warps import Warp, get_warp_manager

    name = kwargs.get("name", "")
    if not name:
        return {"status": "error", "error": "warp name is required"}

    warp = Warp(
        name=name,
        description=kwargs.get("description", ""),
        tools_allowed=kwargs.get("tools_allowed"),
        tools_denied=kwargs.get("tools_denied", []),
        dharma_profile=kwargs.get("dharma_profile"),
        inference_tier=kwargs.get("inference_tier"),
        galaxies_accessible=kwargs.get("galaxies_accessible"),
        execution_mode=kwargs.get("execution_mode"),
        research_domains=kwargs.get("research_domains", []),
        shelter_template=kwargs.get("shelter_template"),
        max_iterations=kwargs.get("max_iterations"),
        timeout_seconds=kwargs.get("timeout_seconds"),
        metadata=kwargs.get("metadata", {}),
    )

    persist = kwargs.get("persist", True)
    manager = get_warp_manager()
    result = manager.create_warp(warp, persist=persist)
    return result


def handle_warp_delete(**kwargs: Any) -> dict[str, Any]:
    """Delete a custom warp."""
    from whitemagic.agents.warps import get_warp_manager

    name = kwargs.get("name", "")
    if not name:
        return {"status": "error", "error": "warp name is required"}

    manager = get_warp_manager()
    return manager.delete_warp(name)


def handle_warp_status(**kwargs: Any) -> dict[str, Any]:
    """Get warp manager status."""
    from whitemagic.agents.warps import get_warp_manager

    manager = get_warp_manager()
    return {"status": "success", "warp_manager": manager.get_status()}


# ── Mesh Experiment Sync ──

def handle_mesh_experiment_share(**kwargs: Any) -> dict[str, Any]:
    """Share an experiment result to the P2P mesh."""
    from whitemagic.mesh.experiment_sync import (
        ResearchDomain,
        get_experiment_sync,
    )

    experiment_id = kwargs.get("experiment_id", "")
    if not experiment_id:
        return {"status": "error", "error": "experiment_id is required"}

    domain_str = kwargs.get("domain")
    domain = None
    if domain_str:
        try:
            domain = ResearchDomain(domain_str)
        except ValueError:
            logger.debug("Ignored ValueError in research.py:345")

    sync = get_experiment_sync()
    return sync.share_experiment(experiment_id, domain)


def handle_mesh_experiment_receive(**kwargs: Any) -> dict[str, Any]:
    """Receive an experiment from a peer node."""
    from whitemagic.mesh.experiment_sync import get_experiment_sync

    payload = kwargs.get("payload", "")
    source_node = kwargs.get("source_node", "")
    if not payload:
        return {"status": "error", "error": "payload is required"}

    sync = get_experiment_sync()
    return sync.receive_experiment(payload, source_node)


def handle_mesh_experiment_status(**kwargs: Any) -> dict[str, Any]:
    """Get experiment sync status."""
    from whitemagic.mesh.experiment_sync import get_experiment_sync

    sync = get_experiment_sync()
    return {"status": "success", "sync": sync.get_status()}


def handle_mesh_experiment_peers(**kwargs: Any) -> dict[str, Any]:
    """Get experiments received from peers."""
    from whitemagic.mesh.experiment_sync import (
        ResearchDomain,
        get_experiment_sync,
    )

    domain_str = kwargs.get("domain")
    domain = None
    if domain_str:
        try:
            domain = ResearchDomain(domain_str)
        except ValueError:
            logger.debug("Ignored ValueError in research.py:385")

    limit = int(kwargs.get("limit", 20))
    sync = get_experiment_sync()
    return {
        "status": "success",
        "peer_experiments": sync.get_peer_experiments(domain=domain, limit=limit),
    }


def handle_mesh_experiment_discover(**kwargs: Any) -> dict[str, Any]:
    """Discover peers on the mesh network."""
    from whitemagic.mesh.experiment_sync import get_experiment_sync

    sync = get_experiment_sync()
    return sync.discover_peers()


# ── Research DAG Synthesis ──

def handle_research_dag_synthesize(**kwargs: Any) -> dict[str, Any]:
    """Generate a synthesis (mini research paper) from accumulated experiments."""
    from whitemagic.core.evolution.research_dag import (
        ResearchDomain,
        get_research_dag,
    )

    domain_str = kwargs.get("domain")
    domain = None
    if domain_str:
        try:
            domain = ResearchDomain(domain_str)
        except ValueError:
            logger.debug("Ignored ValueError in research.py:418")

    min_experiments = int(kwargs.get("min_experiments", 5))
    top_n = int(kwargs.get("top_n", 10))

    dag = get_research_dag()
    result = dag.generate_synthesis(
        domain=domain,
        min_experiments=min_experiments,
        top_n=top_n,
    )
    if result is None:
        return {"status": "skipped", "message": "Not enough experiments for synthesis"}
    return {"status": "success", "synthesis": result}


# ── CRDT Leaderboard ──

def handle_leaderboard_submit(**kwargs: Any) -> dict[str, Any]:
    """Submit an experiment to the distributed CRDT leaderboard."""
    from whitemagic.mesh.crdt_leaderboard import get_leaderboard

    experiment_id = kwargs.get("experiment_id", "")
    if not experiment_id:
        return {"status": "error", "error": "experiment_id is required"}

    lb = get_leaderboard()
    entry = lb.submit(
        experiment_id=experiment_id,
        hypothesis=kwargs.get("hypothesis", ""),
        domain=kwargs.get("domain", "custom"),
        fitness_score=float(kwargs.get("fitness_score", 0.0)),
        agent_id=kwargs.get("agent_id", ""),
        metadata=kwargs.get("metadata", {}),
    )
    return {"status": "success", "entry": entry.to_dict()}


def handle_leaderboard_top(**kwargs: Any) -> dict[str, Any]:
    """Get top entries from the distributed leaderboard."""
    from whitemagic.mesh.crdt_leaderboard import get_leaderboard

    n = int(kwargs.get("n", 10))
    domain = kwargs.get("domain")

    lb = get_leaderboard()
    top = lb.get_top(n=n, domain=domain)
    return {
        "status": "success",
        "entries": [e.to_dict() for e in top],
        "count": len(top),
    }


def handle_leaderboard_status(**kwargs: Any) -> dict[str, Any]:
    """Get CRDT leaderboard status."""
    from whitemagic.mesh.crdt_leaderboard import get_leaderboard

    lb = get_leaderboard()
    return {"status": "success", "leaderboard": lb.get_status()}


def handle_leaderboard_merge(**kwargs: Any) -> dict[str, Any]:
    """Merge remote leaderboard data from a peer node."""
    from whitemagic.mesh.crdt_leaderboard import get_leaderboard

    remote_data = kwargs.get("remote_data", "")
    if not remote_data:
        return {"status": "error", "error": "remote_data is required"}

    lb = get_leaderboard()
    result = lb.merge_remote(remote_data)
    return {"status": "success", "merge": result}


# ── Pulse Verification ──

def handle_pulse_verify(**kwargs: Any) -> dict[str, Any]:
    """Verify an experiment pulse through tiered checks."""
    from whitemagic.mesh.pulse_verification import (
        VerificationTier,
        get_pulse_verifier,
    )

    experiment_id = kwargs.get("experiment_id", "")
    if not experiment_id:
        return {"status": "error", "error": "experiment_id is required"}

    force_tier_int = kwargs.get("force_tier")
    force_tier = None
    if force_tier_int is not None:
        try:
            force_tier = VerificationTier(int(force_tier_int))
        except (ValueError, TypeError):
            logger.debug("Ignored ValueError, TypeError in research.py:512")

    verifier = get_pulse_verifier()
    pulse = verifier.verify(
        experiment_id=experiment_id,
        experiment_data=kwargs.get("experiment_data"),
        node_reputation=float(kwargs.get("node_reputation", 0.5)),
        force_tier=force_tier,
    )
    if pulse is None:
        return {"status": "error", "error": "No pulse found for experiment"}
    return {"status": "success", "pulse": pulse.to_dict()}


def handle_pulse_status(**kwargs: Any) -> dict[str, Any]:
    """Get pulse verification system status."""
    from whitemagic.mesh.pulse_verification import get_pulse_verifier

    verifier = get_pulse_verifier()
    return {"status": "success", "verification": verifier.get_status()}


# ── Critique Protocol ──

def handle_critique_submit(**kwargs: Any) -> dict[str, Any]:
    """Submit a structured peer critique of an experiment."""
    from whitemagic.mesh.critique_protocol import get_critique_protocol

    experiment_id = kwargs.get("experiment_id", "")
    if not experiment_id:
        return {"status": "error", "error": "experiment_id is required"}

    scores = kwargs.get("scores", {})
    if not isinstance(scores, dict):
        return {"status": "error", "error": "scores must be a dict of dimension -> int"}

    critic_agent_id = kwargs.get("critic_agent_id", "anonymous")
    written_review = kwargs.get("written_review", "")

    protocol = get_critique_protocol()
    critique = protocol.critique_experiment(
        experiment_id=experiment_id,
        critic_agent_id=critic_agent_id,
        scores=scores,
        written_review=written_review,
    )
    if critique is None:
        return {"status": "error", "error": "Experiment not found"}
    return {"status": "success", "critique": critique.to_dict()}


def handle_critique_auto(**kwargs: Any) -> dict[str, Any]:
    """Automatically critique an experiment using heuristics."""
    from whitemagic.mesh.critique_protocol import get_critique_protocol

    experiment_id = kwargs.get("experiment_id", "")
    if not experiment_id:
        return {"status": "error", "error": "experiment_id is required"}

    critic_agent_id = kwargs.get("critic_agent_id", "auto_critic")

    protocol = get_critique_protocol()
    critique = protocol.auto_critique(
        experiment_id=experiment_id,
        critic_agent_id=critic_agent_id,
    )
    if critique is None:
        return {"status": "error", "error": "Experiment not found"}
    return {"status": "success", "critique": critique.to_dict()}


def handle_critique_status(**kwargs: Any) -> dict[str, Any]:
    """Get critique protocol status."""
    from whitemagic.mesh.critique_protocol import get_critique_protocol

    protocol = get_critique_protocol()
    return {"status": "success", "critique_protocol": protocol.get_status()}


# ── Durable Archive ──

def handle_archive_run(**kwargs: Any) -> dict[str, Any]:
    """Run a durable archive cycle (snapshot breakthroughs to git)."""
    from whitemagic.mesh.durable_archive import get_durable_archive

    force = kwargs.get("force", False)
    archive = get_durable_archive()
    result = archive.archive_new(force=force)
    return result


def handle_archive_status(**kwargs: Any) -> dict[str, Any]:
    """Get durable archive status."""
    from whitemagic.mesh.durable_archive import get_durable_archive

    archive = get_durable_archive()
    return {"status": "success", "archive": archive.get_status()}


# ── DiLoCo Distributed Training ──

def handle_dilo_co_init(**kwargs: Any) -> dict[str, Any]:
    """Initialize DiLoCo distributed training coordinator with parameters."""
    from whitemagic.mesh.dilo_co import get_dilo_co

    params = kwargs.get("params", {})
    if not params:
        return {"status": "error", "error": "params dict is required"}

    h = int(kwargs.get("h", 16))
    k_ratio = float(kwargs.get("k_ratio", 0.01))
    lr = float(kwargs.get("lr", 0.01))
    lr_outer = float(kwargs.get("lr_outer", 1.0))

    coordinator = get_dilo_co()
    coordinator.h = h
    coordinator.k_ratio = k_ratio
    coordinator.lr = lr
    coordinator.lr_outer = lr_outer
    coordinator.init_params(params)
    return {"status": "success", "param_count": len(params), "h": h, "k_ratio": k_ratio}


def handle_dilo_co_register_worker(**kwargs: Any) -> dict[str, Any]:
    """Register a worker to the DiLoCo Parcae pool."""
    from whitemagic.mesh.dilo_co import get_dilo_co

    worker_id = kwargs.get("worker_id", "")
    if not worker_id:
        return {"status": "error", "error": "worker_id is required"}

    compute_capacity = float(kwargs.get("compute_capacity", 1.0))
    coordinator = get_dilo_co()
    success = coordinator.register_worker(worker_id, compute_capacity)
    if not success:
        return {"status": "error", "error": "Worker pool is full"}
    return {"status": "success", "worker_id": worker_id, "compute_capacity": compute_capacity}


def handle_dilo_co_submit_gradient(**kwargs: Any) -> dict[str, Any]:
    """Submit gradients from a worker to the DiLoCo coordinator."""
    from whitemagic.mesh.dilo_co import get_dilo_co

    worker_id = kwargs.get("worker_id", "")
    gradients = kwargs.get("gradients", {})
    if not worker_id or not gradients:
        return {"status": "error", "error": "worker_id and gradients are required"}

    coordinator = get_dilo_co()
    result = coordinator.submit_gradient(worker_id, gradients)
    return result


def handle_dilo_co_sync(**kwargs: Any) -> dict[str, Any]:
    """Perform a DiLoCo global synchronization step."""
    from whitemagic.mesh.dilo_co import get_dilo_co

    coordinator = get_dilo_co()
    result = coordinator.sync_step()
    return result


def handle_dilo_co_status(**kwargs: Any) -> dict[str, Any]:
    """Get DiLoCo coordinator status."""
    from whitemagic.mesh.dilo_co import get_dilo_co

    coordinator = get_dilo_co()
    return {"status": "success", "dilo_co": coordinator.get_status()}


# ── Warp Marketplace ──

def handle_warp_market_publish(**kwargs: Any) -> dict[str, Any]:
    """Publish a warp preset to the P2P marketplace."""
    from whitemagic.mesh.warp_marketplace import get_warp_marketplace

    warp_name = kwargs.get("warp_name", "")
    warp_data = kwargs.get("warp_data", {})
    if not warp_name or not warp_data:
        return {"status": "error", "error": "warp_name and warp_data are required"}

    mp = get_warp_marketplace()
    return mp.publish(
        warp_name=warp_name,
        warp_data=warp_data,
        author_id=kwargs.get("author_id", ""),
        author_name=kwargs.get("author_name", ""),
        description=kwargs.get("description", ""),
        price_xrp=float(kwargs.get("price_xrp", 0.0)),
    )


def handle_warp_market_discover(**kwargs: Any) -> dict[str, Any]:
    """Discover warp presets on the marketplace."""
    from whitemagic.mesh.warp_marketplace import get_warp_marketplace

    mp = get_warp_marketplace()
    return mp.discover(
        query=kwargs.get("query", ""),
        capability=kwargs.get("capability", ""),
        domain=kwargs.get("domain", ""),
        inference_tier=kwargs.get("inference_tier", ""),
        max_price=float(kwargs.get("max_price", 0.0)),
        limit=int(kwargs.get("limit", 20)),
    )


def handle_warp_market_download(**kwargs: Any) -> dict[str, Any]:
    """Download and import a warp from the marketplace."""
    from whitemagic.mesh.warp_marketplace import get_warp_marketplace

    listing_id = kwargs.get("listing_id", "")
    if not listing_id:
        return {"status": "error", "error": "listing_id is required"}

    mp = get_warp_marketplace()
    return mp.download(
        listing_id=listing_id,
        target_warp_name=kwargs.get("target_warp_name"),
    )


def handle_warp_market_status(**kwargs: Any) -> dict[str, Any]:
    """Get warp marketplace status."""
    from whitemagic.mesh.warp_marketplace import get_warp_marketplace

    mp = get_warp_marketplace()
    return {"status": "success", "marketplace": mp.get_status()}


def handle_warp_market_broadcast(**kwargs: Any) -> dict[str, Any]:
    """Broadcast a warp listing to mesh peers."""
    from whitemagic.mesh.warp_marketplace import get_warp_marketplace

    listing_id = kwargs.get("listing_id", "")
    if not listing_id:
        return {"status": "error", "error": "listing_id is required"}

    mp = get_warp_marketplace()
    return mp.broadcast_listing(listing_id)


# ── Mesh Inference Router ──

def handle_mesh_route(**kwargs: Any) -> dict[str, Any]:
    """Route an inference request to the best available mesh node."""
    from whitemagic.mesh.inference_router import get_inference_router

    model = kwargs.get("model", "")
    if not model:
        return {"status": "error", "error": "model is required"}

    router = get_inference_router()
    decision = router.route(
        model=model,
        prompt=kwargs.get("prompt", ""),
        max_tokens=int(kwargs.get("max_tokens", 128)),
        temperature=float(kwargs.get("temperature", 0.7)),
        strategy=kwargs.get("strategy"),
    )
    return {"status": "success", "routing": decision.to_dict()}


def handle_mesh_route_register(**kwargs: Any) -> dict[str, Any]:
    """Register a mesh inference node."""
    from whitemagic.mesh.inference_router import get_inference_router

    node_id = kwargs.get("node_id", "")
    if not node_id:
        return {"status": "error", "error": "node_id is required"}

    router = get_inference_router()
    return router.register_node(
        node_id=node_id,
        address=kwargs.get("address", ""),
        models=kwargs.get("models", []),
        reputation=float(kwargs.get("reputation", 0.5)),
    )


def handle_mesh_route_nodes(**kwargs: Any) -> dict[str, Any]:
    """Get available inference nodes, optionally filtered by model."""
    from whitemagic.mesh.inference_router import get_inference_router

    router = get_inference_router()
    model = kwargs.get("model")
    nodes = router.get_available_nodes(model=model)
    return {"status": "success", "nodes": nodes, "count": len(nodes)}


def handle_mesh_route_status(**kwargs: Any) -> dict[str, Any]:
    """Get inference router status."""
    from whitemagic.mesh.inference_router import get_inference_router

    router = get_inference_router()
    return {"status": "success", "router": router.get_status()}


def handle_mesh_route_strategy(**kwargs: Any) -> dict[str, Any]:
    """Change the inference routing strategy."""
    from whitemagic.mesh.inference_router import get_inference_router

    strategy = kwargs.get("strategy", "")
    if not strategy:
        return {"status": "error", "error": "strategy is required"}

    router = get_inference_router()
    return router.set_strategy(strategy)
