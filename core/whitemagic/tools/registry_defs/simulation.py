"""Registry definitions for simulation MCP tools (P5)."""

from __future__ import annotations

from whitemagic.tools.tool_types import (
    ToolCategory,
    ToolDefinition,
    ToolSafety,
)

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="simulation.create",
        description=(
            "Create a simulation world with personas, seed documents, and rules. "
            "Sets up a dedicated simulation galaxy and generates cognitive agents "
            "with distinct internal states."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "world_name": {"type": "string", "description": "Name for the simulation world"},
                "seed_documents": {"type": "array", "items": {"type": "string"}, "description": "Seed document contents"},
                "personas": {"type": "array", "items": {"type": "object"}, "description": "Persona specs [{name, archetype}]"},
                "archetypes": {"type": "array", "items": {"type": "string"}, "description": "Persona archetypes (analyst, creative, conservative, explorer, synthesizer)"},
                "rules": {"type": "array", "items": {"type": "object"}, "description": "Rule specs [{name, description, type}]"},
            },
            "required": ["world_name"],
        },
        gana="Three Stars",
        garden="judgment",
        quadrant="northern",
        element="fire",
    ),
    ToolDefinition(
        name="simulation.run",
        description=(
            "Run a Monte Carlo simulation scenario with varied initial conditions. "
            "Generates N trials with different persona configurations and analyzes "
            "outcome distribution, parameter sensitivity, and robustness."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "scenario_name": {"type": "string", "description": "Name for the scenario"},
                "seed_documents": {"type": "array", "items": {"type": "string"}},
                "archetypes": {"type": "array", "items": {"type": "string"}},
                "num_personas": {"type": "integer", "description": "Personas per trial (default: 3)"},
                "ticks_per_trial": {"type": "integer", "description": "Ticks per trial (default: 10)"},
                "num_trials": {"type": "integer", "description": "Number of MC trials (default: 10)"},
            },
            "required": ["scenario_name"],
        },
        gana="Three Stars",
        garden="judgment",
        quadrant="northern",
        element="fire",
    ),
    ToolDefinition(
        name="simulation.search",
        description=(
            "Run MCTS-guided trajectory tree search for creative exploration. "
            "Uses UCB1 with novelty bonus for selection. Returns best trajectory "
            "and tree statistics."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "iterations": {"type": "integer", "description": "MCTS iterations (default: 100)"},
                "max_depth": {"type": "integer", "description": "Max tree depth (default: 10)"},
                "branching_factor": {"type": "integer", "description": "Children per node (default: 3)"},
                "initial_state": {"type": "object", "description": "Initial state dict"},
            },
        },
        gana="Three Stars",
        garden="judgment",
        quadrant="northern",
        element="fire",
    ),
    ToolDefinition(
        name="simulation.inject",
        description=(
            "Inject variables into a running simulation scenario at specified ticks. "
            "Supports injecting multiple variables with different values."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "scenario_name": {"type": "string", "description": "Scenario to inject into"},
                "injection": {"type": "object", "description": "Injection spec {tick, variable, value}"},
            },
            "required": ["scenario_name"],
        },
        gana="Three Stars",
        garden="judgment",
        quadrant="northern",
        element="fire",
    ),
    ToolDefinition(
        name="simulation.analyze",
        description=(
            "Analyze simulation results and optionally run dream-cycle consolidation. "
            "Returns outcome distribution, coherence statistics, and consolidation "
            "reports with insights and recommendations."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "scenario_name": {"type": "string", "description": "Scenario to analyze"},
                "consolidate": {"type": "boolean", "description": "Run dream-cycle consolidation (default: true)"},
            },
            "required": ["scenario_name"],
        },
        gana="Three Stars",
        garden="judgment",
        quadrant="northern",
        element="fire",
    ),
    ToolDefinition(
        name="simulation.synthesize",
        description=(
            "Synthesize emergent insights from simulation trajectories. "
            "Extracts patterns, discovers cross-trajectory connections, detects "
            "anomalies, and generates strategic insights. Ranks by novelty, "
            "impact, coherence, and cross-domain potential."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "scenario_name": {"type": "string", "description": "Scenario to synthesize from"},
                "top_n": {"type": "integer", "description": "Top insights to return (default: 5)"},
            },
            "required": ["scenario_name"],
        },
        gana="Three Stars",
        garden="judgment",
        quadrant="northern",
        element="fire",
    ),
    ToolDefinition(
        name="simulation.calibrate",
        description=(
            "Record predictions, resolve them against reality, and get calibration "
            "scorecard with Brier scores. Supports three actions: record, resolve, "
            "scorecard. Feeds calibration gap back into future predictions."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["record", "resolve", "scorecard"], "description": "Action (default: scorecard)"},
                "statement": {"type": "string", "description": "Prediction statement (for record)"},
                "probability": {"type": "number", "description": "Predicted probability [0,1] (for record)"},
                "outcome": {"type": "boolean", "description": "Actual outcome (for resolve)"},
                "prediction_id": {"type": "string", "description": "Prediction ID (for resolve)"},
                "confidence": {"type": "number", "description": "Confidence [0,1] (for record)"},
            },
        },
        gana="Three Stars",
        garden="judgment",
        quadrant="northern",
        element="fire",
    ),
    ToolDefinition(
        name="simulation.pipeline",
        description=(
            "Run the full P5 simulation pipeline end-to-end: create world, run "
            "Monte Carlo scenario, analyze with dream consolidation, synthesize "
            "insights, and optionally record/resolve calibrated predictions. "
            "Chains all 8 P5 components in a single call."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "scenario_name": {"type": "string", "description": "Name for the scenario"},
                "seed_documents": {"type": "array", "items": {"type": "string"}},
                "archetypes": {"type": "array", "items": {"type": "string"}},
                "num_personas": {"type": "integer", "description": "Personas per trial (default: 3)"},
                "ticks_per_trial": {"type": "integer", "description": "Ticks per trial (default: 10)"},
                "num_trials": {"type": "integer", "description": "Number of MC trials (default: 10)"},
                "prediction_statement": {"type": "string", "description": "Optional prediction to record"},
                "prediction_probability": {"type": "number", "description": "Predicted probability [0,1]"},
                "consolidate": {"type": "boolean", "description": "Run dream consolidation (default: true)"},
                "top_n_insights": {"type": "integer", "description": "Top insights to return (default: 5)"},
            },
            "required": ["scenario_name"],
        },
        gana="Three Stars",
        garden="judgment",
        quadrant="northern",
        element="fire",
    ),
]
