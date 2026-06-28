"""Polyglot Memory Tools — Route holographic memory queries to Julia/Elixir/Haskell/Rust backends.
"""

from whitemagic.tools.tool_types import (
    ToolCategory,
    ToolDefinition,
    ToolSafety,
    ToolStability,
)

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="polyglot.memory_query",
        description=(
            "Execute a holographic memory query through an available polyglot backend "
            "(Julia, Elixir, Haskell, or Rust). Supports encode, nearest_neighbors, "
            "constellation_detect, and coherence_score. Falls back through backends "
            "automatically if one is unavailable."
        ),
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["encode", "nearest_neighbors", "constellation_detect", "coherence_score"],
                    "description": "Holographic memory operation to execute",
                },
                "text": {
                    "type": "string",
                    "description": "Text to encode (for encode operation)",
                },
                "query": {
                    "type": "string",
                    "description": "Query text (for nearest_neighbors)",
                },
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of texts to search against (for nearest_neighbors)",
                },
                "coords": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                    "description": "List of 5D coordinates (for constellation_detect, coherence_score)",
                },
                "k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of nearest neighbors to return",
                },
                "backend": {
                    "type": "string",
                    "enum": ["auto", "julia", "elixir", "haskell", "rust", "koka"],
                    "default": "auto",
                    "description": "Backend to use (auto = first available)",
                },
            },
            "required": ["operation"],
        },
        gana="Mound",
        garden="metrics",
        quadrant="western",
        element="metal",
        stability=ToolStability.EXPERIMENTAL,
    ),
    ToolDefinition(
        name="polyglot.search",
        description=(
            "Convenience tool: encode a query text and find its nearest neighbors "
            "among a pool of texts in a single call. Routes through polyglot backend."
        ),
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query text to encode"},
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Pool of texts to search against",
                },
                "k": {"type": "integer", "default": 5, "description": "Number of results"},
                "backend": {
                    "type": "string",
                    "enum": ["auto", "julia", "elixir", "haskell", "rust", "koka"],
                    "default": "auto",
                    "description": "Backend to use",
                },
            },
            "required": ["query", "texts"],
        },
        gana="WinnowingBasket",
        garden="metrics",
        quadrant="western",
        element="metal",
        stability=ToolStability.EXPERIMENTAL,
    ),
    ToolDefinition(
        name="polyglot.status",
        description=(
            "Check availability and health of all polyglot holographic memory backends. "
            "Returns per-backend ping results and an overall health score."
        ),
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        gana="Ghost",
        garden="introspection",
        quadrant="southern",
        element="fire",
        stability=ToolStability.EXPERIMENTAL,
    ),
    ToolDefinition(
        name="polyglot.evolution",
        description=(
            "Execute evolution algorithms through the Rust evolution backend. "
            "Supports information theory (shannon_entropy, kl_divergence, information_gain), "
            "thermodynamic simulation (thermo_cool, thermo_reheat, thermo_adapt, boltzmann_select), "
            "HRR composition (hrr_encode, hrr_bind, hrr_unbind, hrr_superposition), "
            "Monte Carlo integration (mc_run_trials, mc_importance_sampling), "
            "and counterfactual estimation (cf_project_forward, cf_estimate_impact)."
        ),
        category=ToolCategory.INFERENCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "shannon_entropy", "kl_divergence", "information_gain",
                        "system_uncertainty", "adapt_weights", "exploration_score",
                        "thermo_cool", "thermo_reheat", "thermo_adapt",
                        "boltzmann_probabilities", "boltzmann_select",
                        "hrr_encode", "hrr_bind", "hrr_unbind",
                        "hrr_superposition", "hrr_synergy", "hrr_similarity",
                        "mc_run_trials", "mc_importance_sampling",
                        "mc_control_variates", "mc_antithetic_variates",
                        "cf_project_forward", "cf_bootstrap_ci", "cf_estimate_impact",
                    ],
                    "description": "Evolution operation to execute",
                },
            },
            "required": ["operation"],
        },
        gana="Abundance",
        garden="wisdom",
        quadrant="eastern",
        element="wood",
        stability=ToolStability.EXPERIMENTAL,
    ),
    ToolDefinition(
        name="polyglot.yield",
        description=(
            "Execute yield curve operations through the Julia yield backend. "
            "Models temporal value of improvements: decaying, compounding, appreciating, transient. "
            "Supports value_at, duration, fit_parameters, portfolio_duration, "
            "select_by_horizon, detect_regime_change."
        ),
        category=ToolCategory.INFERENCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "value_at", "duration", "fit_parameters",
                        "portfolio_duration", "select_by_horizon",
                        "detect_regime_change",
                    ],
                    "description": "Yield curve operation to execute",
                },
                "yield_type": {
                    "type": "string",
                    "enum": ["decaying", "compounding", "appreciating", "transient"],
                    "default": "decaying",
                },
                "t": {"type": "number", "description": "Time point"},
                "v0": {"type": "number", "default": 1.0},
                "lambda": {"type": "number", "default": 0.1},
                "r": {"type": "number", "default": 0.05},
                "tau": {"type": "number", "default": 10.0},
            },
            "required": ["operation"],
        },
        gana="Dipper",
        garden="wisdom",
        quadrant="eastern",
        element="wood",
        stability=ToolStability.EXPERIMENTAL,
    ),
    ToolDefinition(
        name="polyglot.actor",
        description=(
            "Execute actor-based hypothesis tracking through the Elixir actor backend. "
            "Manages Bayesian belief updating across concurrent hypothesis actors. "
            "Supports start_actor, send_outcome, broadcast_outcome, transfer_belief, "
            "get_posteriors, get_stats."
        ),
        category=ToolCategory.AGENT,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "start_actor", "send_outcome", "broadcast_outcome",
                        "transfer_belief", "get_posteriors", "get_stats",
                    ],
                    "description": "Actor operation to execute",
                },
                "hypothesis_id": {"type": "string"},
                "prior": {"type": "number", "default": 0.5},
                "success": {"type": "boolean"},
                "gain": {"type": "number"},
                "from_id": {"type": "string"},
                "to_id": {"type": "string"},
                "weight": {"type": "number", "default": 0.5},
            },
            "required": ["operation"],
        },
        gana="Ox",
        garden="courage",
        quadrant="northern",
        element="water",
        stability=ToolStability.EXPERIMENTAL,
    ),
]
