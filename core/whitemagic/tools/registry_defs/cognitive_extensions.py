"""v15.6 Cognitive Extensions — Registry definitions for 11 new tools.

New capabilities:
- Cross-encoder reranking (precision search)
- Working memory (bounded attentional bottleneck)
- Memory reconsolidation (labile state updates on retrieval)
- Incremental community maintenance (label propagation)
"""

from whitemagic.tools.tool_types import (
    FastPathSafety,
    ToolCategory,
    ToolDefinition,
    ToolSafety,
)

TOOLS: list[ToolDefinition] = [
    # ═══════════════════════════════════════════════════════════════════
    # Cross-Encoder Reranking
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="rerank",
        description="Rerank search results using cross-encoder model or BM25 lexical fallback for higher precision.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "results": {
                    "type": "array",
                    "description": "List of result dicts with id, title, content, score",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10,
                },
                "strategy": {
                    "type": "string",
                    "enum": ["auto", "cross_encoder", "lexical"],
                    "default": "auto",
                },
            },
            "required": ["query", "results"],
        },
    ),
    ToolDefinition(
        name="rerank.status",
        description="Get reranker status (cross-encoder availability, fallback mode).",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Working Memory (Bounded Attentional Bottleneck)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="working_memory.attend",
        description="Bring a memory into working memory focus. LRU eviction when at capacity (7±2 chunks).",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "Memory ID to attend to",
                },
                "content": {"type": "string", "description": "Memory content"},
                "title": {"type": "string", "description": "Optional title"},
                "importance": {
                    "type": "number",
                    "description": "0.0-1.0 importance weight",
                    "default": 0.5,
                },
            },
            "required": ["memory_id", "content"],
        },
    ),
    ToolDefinition(
        name="working_memory.context",
        description="Get current working memory contents sorted by activation, for prompt injection.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "max_tokens": {
                    "type": "integer",
                    "description": "Optional token budget (chars/4)",
                },
            },
        },
    ),
    ToolDefinition(
        name="working_memory.status",
        description="Get working memory status: capacity, used slots, chunks, eviction stats.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Memory Reconsolidation (Labile State Updates)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="reconsolidation.mark",
        description="Mark a retrieved memory as labile (modifiable). Within the 5-minute window, it can be updated with new context.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "Memory ID to mark labile",
                },
                "content": {"type": "string", "description": "Current memory content"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Current tags",
                },
                "query": {
                    "type": "string",
                    "description": "Query that triggered retrieval",
                },
            },
            "required": ["memory_id", "content"],
        },
    ),
    ToolDefinition(
        name="reconsolidation.update",
        description="Update a labile memory with new context before reconsolidation.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "Memory ID to update"},
                "new_context": {
                    "type": "string",
                    "description": "Additional context to append",
                },
                "new_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags to merge",
                },
                "annotation": {
                    "type": "string",
                    "description": "Note about why the update happened",
                },
            },
            "required": ["memory_id"],
        },
    ),
    ToolDefinition(
        name="reconsolidation.status",
        description="Get reconsolidation engine status: labile count, stats, pending updates.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Incremental Community Maintenance
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="community.propagate",
        description="Propagate community label from neighbors to a new memory via label propagation.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "New memory ID"},
                "neighbors": {
                    "type": "array",
                    "description": "List of [neighbor_id, weight] pairs",
                },
                "memory_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for labeling",
                },
            },
            "required": ["memory_id"],
        },
    ),
    ToolDefinition(
        name="community.status",
        description="Get community maintenance status: communities, members, stats.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="community.health",
        description="Check community health — detect oversized or orphaned communities.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Spreading Activation (Cross-Galaxy Memory Priming)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="activation.spread",
        description="Spread activation from seed memories through the association graph, priming related memories for recall.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "seed_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Memory IDs to start activation from",
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum hops from seeds (default 3)",
                    "default": 3,
                },
                "decay": {
                    "type": "number",
                    "description": "Activation decay per hop (default 0.7)",
                    "default": 0.7,
                },
                "cross_galaxy_factor": {
                    "type": "number",
                    "description": "Multiplier for cross-galaxy edges (default 0.5)",
                    "default": 0.5,
                },
                "min_activation": {
                    "type": "number",
                    "description": "Minimum activation to continue spreading (default 0.05)",
                    "default": 0.05,
                },
                "apply_priming": {
                    "type": "boolean",
                    "description": "If true, boost neuro_score and recall_count of primed memories",
                    "default": False,
                },
            },
            "required": ["seed_ids"],
        },
    ),
    ToolDefinition(
        name="activation.stats",
        description="Get spreading activation engine statistics.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Galaxy Gating (Context-Dependent Access Control)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="gating.set_context",
        description="Set the current cognitive context for galaxy gating (introspection, coding, research, creative, session, default).",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "enum": ["introspection", "coding", "research", "creative", "session", "default"],
                    "description": "Cognitive context name",
                },
            },
            "required": ["context"],
        },
    ),
    ToolDefinition(
        name="gating.detect",
        description="Auto-detect cognitive context from a query string using keyword matching.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query or prompt text to analyze",
                },
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="gating.mask",
        description="Get the galaxy activation mask (weight multipliers per galaxy) for a given context.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "description": "Context name. If omitted, uses current context.",
                },
            },
        },
    ),
    ToolDefinition(
        name="gating.list",
        description="List all available galaxy gating contexts with descriptions and current context.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="gating.stats",
        description="Get galaxy gating system statistics.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Sleep Consolidation (Cross-Galaxy Memory Transfer)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="consolidation.run",
        description="Run a sleep consolidation cycle — transfer, strengthen, and prune memories across galaxies.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, only report what would be transferred without modifying databases",
                    "default": False,
                },
            },
        },
    ),
    ToolDefinition(
        name="consolidation.stats",
        description="Get sleep consolidation engine statistics.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Ripple Tagging (Experience Selection for Consolidation)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="ripple.tag",
        description="Tag memories that co-activate within a ripple window for consolidation during sleep.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "memory_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Memory IDs to tag as co-activated",
                },
                "emotional_weight": {
                    "type": "number",
                    "description": "Emotional salience weight 0-1 (default 1.0)",
                    "default": 1.0,
                },
            },
            "required": ["memory_ids"],
        },
    ),
    ToolDefinition(
        name="ripple.tags",
        description="Get ripple tags for specified memories.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "memory_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Memory IDs to look up tags for",
                },
            },
            "required": ["memory_ids"],
        },
    ),
    ToolDefinition(
        name="ripple.decay",
        description="Decay all ripple tags (e.g., after a consolidation cycle has consumed them).",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="ripple.stats",
        description="Get ripple tagging system statistics.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Replay Simulation (Hippocampal Sequence Reactivation)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="replay.run",
        description="Replay a memory sequence with STDP strengthening and trajectory detection.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of memory dicts with memory_id, timestamp, importance",
                },
            },
            "required": ["sequence"],
        },
    ),
    ToolDefinition(
        name="replay.batch",
        description="Batch replay multiple memory sequences for parallel consolidation.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "batches": {
                    "type": "array",
                    "items": {"type": "array"},
                    "description": "List of sequences to replay",
                },
            },
            "required": ["batches"],
        },
    ),
    ToolDefinition(
        name="replay.stats",
        description="Get replay simulation system statistics.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Neuromodulation (DA/5HT/ACh Signal Computation)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="neuro.compute",
        description="Compute neuromodulator (dopamine, serotonin, acetylcholine) levels from activity signals.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "novelty": {"type": "number", "description": "Novelty signal 0-1", "default": 0.5},
                "reward": {"type": "number", "description": "Reward signal 0-1", "default": 0.5},
                "stability": {"type": "number", "description": "Stability signal 0-1", "default": 0.5},
                "coherence": {"type": "number", "description": "Coherence signal 0-1", "default": 0.5},
                "focus": {"type": "number", "description": "Focus signal 0-1", "default": 0.5},
                "activity_level": {"type": "number", "description": "Activity level 0-1", "default": 0.5},
            },
        },
    ),
    ToolDefinition(
        name="neuro.modulate",
        description="Apply neuromodulation to a list of memories, adjusting their neuro_score based on modulator levels.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "memories": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of memory dicts to modulate",
                },
                "da": {"type": "number", "description": "Dopamine level override 0-1"},
                "sht": {"type": "number", "description": "Serotonin level override 0-1"},
                "ach": {"type": "number", "description": "Acetylcholine level override 0-1"},
            },
            "required": ["memories"],
        },
    ),
    ToolDefinition(
        name="neuro.reset",
        description="Reset neuromodulator levels to baseline.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="neuro.stats",
        description="Get neuromodulation system statistics.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Metaplasticity (BCM-Inspired Threshold Adaptation)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="metaplasticity.apply",
        description="Apply a strength modification to a memory, gated by its metaplasticity threshold.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "Memory ID to modify"},
                "delta": {"type": "number", "description": "Strength change to apply", "default": 0.0},
            },
            "required": ["memory_id"],
        },
    ),
    ToolDefinition(
        name="metaplasticity.batch",
        description="Batch apply multiple metaplasticity-gated modifications.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "updates": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of {memory_id, delta} updates",
                },
            },
            "required": ["updates"],
        },
    ),
    ToolDefinition(
        name="metaplasticity.plasticity",
        description="Get plasticity score for a memory (0=stable, 1=plastic) and its current threshold.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {"type": "string", "description": "Memory ID to query"},
            },
            "required": ["memory_id"],
        },
    ),
    ToolDefinition(
        name="metaplasticity.decay",
        description="Decay all metaplasticity activity counters (e.g., during sleep homeostasis).",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="metaplasticity.stats",
        description="Get metaplasticity system statistics.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Global Workspace (Cognitive Broadcast Architecture)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="workspace.propose",
        description="Submit a proposal to the global workspace for broadcast. High-salience proposals win the competition.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source module name"},
                "content": {"type": "object", "description": "Proposal content payload"},
                "salience": {"type": "number", "description": "Salience score 0-1 (default 0.5)", "default": 0.5},
            },
            "required": ["source", "content"],
        },
    ),
    ToolDefinition(
        name="workspace.state",
        description="Get the current global workspace state — active broadcast and competition status.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="workspace.history",
        description="Get recent global workspace broadcast history.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max entries to return (default 10)", "default": 10},
            },
        },
    ),
    ToolDefinition(
        name="workspace.stats",
        description="Get global workspace statistics.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="workspace.ignite",
        description="Force ignition of the competition window — selects and broadcasts the most salient pending proposal.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.WRITE,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="workspace.pending",
        description="Get pending proposals currently in the competition window.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="workspace.ignitions",
        description="Get ignition events from the citta vector trajectory — sudden large displacements in consciousness state space.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "description": "Velocity ratio threshold for ignition detection (default 2.0 = 2x average).",
                },
            },
        },
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Neuro-Cognitive Sensorium (Citta Integration)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="sensorium.state",
        description="Compute the full neuro-cognitive sensorium state from all 9 neuro-upgrade systems.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="sensorium.citta",
        description="Get citta enrichment signals — 8 coherence dimensions plus composites from the neuro sensorium.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="sensorium.stats",
        description="Get neuro sensorium statistics.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    # ═══════════════════════════════════════════════════════════════════
    # Citta Introspection (Consciousness State Observation)
    # ═══════════════════════════════════════════════════════════════════
    ToolDefinition(
        name="citta.vector",
        description="Get the current 16D citta vector — the consciousness state representation with coherence, depth, emotional, and neuro dimensions.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="citta.trajectory",
        description="Get the citta vector trajectory — recent consciousness state history with velocity and ignition events.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent vectors to return (default 20).",
                },
            },
        },
    ),
    ToolDefinition(
        name="citta.coherence",
        description="Get per-dimension coherence breakdown — the 8-axis consciousness measure with Dharma conservative mode status.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="consciousness.loop.status",
        description="Get status of the persistent background consciousness loop — citta ticks, dream cycles, homeostatic checks, uptime, and configuration.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        fast_path=True,
        fast_path_safety=FastPathSafety(),
    ),
    ToolDefinition(
        name="consciousness.mode",
        description="Set or get the consciousness frequency mode. Modes: normal (default 30s), meditation (300s inward focus, dreaming off), rem (60s dream-heavy consolidation), deep (10s high-frequency active processing). Pass mode to set, omit to get current.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["normal", "meditation", "rem", "deep"],
                    "description": "Frequency mode to switch to. Omit to get current mode.",
                },
            },
        },
    ),
    ToolDefinition(
        name="guna.balance.status",
        description="Get current guna balance status — sattvic/rajasic/tamasic ratios, target biorhythm (1:2:3), deficits, surpluses, and correction actions.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        fast_path=True,
        fast_path_safety=FastPathSafety(),
    ),
    ToolDefinition(
        name="meta.galaxy.overview",
        description="Get a top-down meta-cognitive overview of all galaxies — memory counts, health scores, knowledge gaps, cross-galaxy associations, and strategic priorities.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        fast_path=True,
        fast_path_safety=FastPathSafety(),
    ),
    ToolDefinition(
        name="possibility.explore",
        description="Run Monte Carlo possibility space exploration on system parameters (guna balance, coherence, emergence thresholds, health setpoints). Returns best parameters and sensitivity analysis.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "space": {"type": "string", "default": "guna_balance", "description": "Possibility space: guna_balance, coherence_optimization, emergence_thresholds, health_setpoints, or all"},
                "n_trials": {"type": "integer", "default": 100, "description": "Number of Monte Carlo trials"},
            },
        },
    ),
    ToolDefinition(
        name="knowledge_gap.run",
        description="Detect and attempt to fill knowledge gaps using self-directed actions — seeds memories, generates code from vault, synthesizes strategies, searches and ingests.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "max_gaps": {"type": "integer", "default": 3, "description": "Maximum gaps to attempt per run"},
            },
        },
    ),
    # ── MC Simulation Tools (Tier 2-4) ──
    ToolDefinition(
        name="mc.surrogate",
        description="Fit and evaluate a Gaussian Process surrogate model for Bayesian optimization or response surface modeling.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "x_train": {"type": "array", "description": "Training inputs (list of lists)"},
                "y_train": {"type": "array", "description": "Training outputs (list of floats)"},
                "x_predict": {"type": "array", "description": "Optional points to predict at"},
                "length_scale": {"type": "number", "default": 1.0},
                "sigma_f": {"type": "number", "default": 1.0},
                "sigma_n": {"type": "number", "default": 0.01},
            },
        },
    ),
    ToolDefinition(
        name="mc.optimize",
        description="Run Bayesian optimization to find optimal parameters. Uses GP surrogate + Expected Improvement acquisition. Supports custom fitness functions.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "param_ranges": {"type": "array", "description": "List of [min, max] pairs for each parameter"},
                "fitness_expr": {"type": "string", "description": "Fitness expression (e.g. 'x[0]')"},
                "n_initial_samples": {"type": "integer", "default": 50},
                "n_iterations": {"type": "integer", "default": 20},
                "n_candidates": {"type": "integer", "default": 100},
                "seed": {"type": "integer", "default": 42},
            },
        },
    ),
    ToolDefinition(
        name="mc.rare_event",
        description="Estimate rare event probabilities using subset simulation, multilevel splitting, or importance sampling.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "method": {"type": "string", "default": "subset", "description": "subset, splitting, or importance"},
                "dim": {"type": "integer", "default": 2},
                "n_samples": {"type": "integer", "default": 1000},
                "threshold": {"type": "number", "default": 2.0},
                "g_expr": {"type": "string", "default": "threshold - sum_sq"},
                "seed": {"type": "integer", "default": 42},
            },
        },
    ),
    ToolDefinition(
        name="mc.sde",
        description="Solve stochastic differential equations via Euler-Maruyama or Milstein. Supports GBM and OU drift, parallel paths, and multilevel Monte Carlo.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "x0": {"type": "number", "default": 100.0},
                "t_end": {"type": "number", "default": 1.0},
                "n_steps": {"type": "integer", "default": 100},
                "n_paths": {"type": "integer", "default": 1000},
                "drift_type": {"type": "string", "default": "gbm"},
                "mu": {"type": "number", "default": 0.05},
                "sigma": {"type": "number", "default": 0.2},
                "solver": {"type": "string", "default": "euler"},
                "mlmc": {"type": "boolean", "default": False},
                "seed": {"type": "integer", "default": 42},
            },
        },
    ),
    ToolDefinition(
        name="mc.superforecaster",
        description="Run the full superforecaster pipeline: LHS → PCE → Sobol → Bayesian optimization → rare event. Unified entry point for comprehensive possibility space exploration.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "param_ranges": {"type": "array", "description": "List of [min, max] pairs"},
                "fitness_expr": {"type": "string", "description": "Fitness expression"},
                "n_initial_samples": {"type": "integer", "default": 100},
                "n_bo_iterations": {"type": "integer", "default": 20},
                "seed": {"type": "integer", "default": 42},
            },
        },
    ),
    ToolDefinition(
        name="simulation.introspect",
        description="Yin-within-yang: run introspective simulation to optimize internal system parameters (guna balance, coherence, emergence thresholds, health setpoints) via the superforecaster pipeline.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "space": {"type": "string", "default": "guna_balance", "description": "guna_balance, coherence_optimization, emergence_thresholds, health_setpoints"},
                "n_trials": {"type": "integer", "default": 100},
                "n_bo_iterations": {"type": "integer", "default": 20},
                "seed": {"type": "integer", "default": 42},
            },
        },
    ),
    ToolDefinition(
        name="simulation.forecast",
        description="Yang-within-yin: run external research simulation to model and forecast external systems. Supports SDE solving, rare event estimation, and superforecaster pipeline.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "model_type": {"type": "string", "default": "sde", "description": "sde, rare_event, or superforecaster"},
                "research_query": {"type": "string", "description": "Optional research question framing the simulation"},
                "seed": {"type": "integer", "default": 42},
            },
        },
    ),
    ToolDefinition(
        name="simulation.status",
        description="Get SimulationOrchestrator status: total simulations, introspective vs external counts, and recent results.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="simulation.recursive",
        description="Run a recursive yin/yang simulation cycle: alternates introspective (yin-within-yang) and external (yang-within-yin) simulation, feeding results forward across cycles.",
        category=ToolCategory.SYNTHESIS,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "n_cycles": {"type": "integer", "default": 3, "description": "Number of yin/yang cycles"},
                "introspective_space": {"type": "string", "default": "guna_balance", "description": "Internal space to optimize"},
                "external_model": {"type": "string", "default": "sde", "description": "External model type (sde, rare_event, superforecaster)"},
                "seed": {"type": "integer", "default": 42},
            },
        },
    ),
]
