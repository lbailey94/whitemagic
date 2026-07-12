"""Quantum Geometry & Topological Protection Tools.

Quantum-inspired computing primitives exposed as MCP tools:
- Manifold distance, Fubini-Study metric, natural gradient
- MPS tensor network compression
- Born-rule sampling and interference
- Berry phase, Chern number, topological encode/decode

Dispatch priority: Julia (quantum geometry), Haskell (topological),
Rust (numerical), Python (fallback).
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    # ── Quantum Geometry ──
    ToolDefinition(
        name="quantum.manifold_distance",
        description="Compute geodesic distance between two points on a Riemannian manifold (euclidean, hyperbolic, or spherical). Dispatchs to Julia QuantumGeometry.jl first, then Rust, then Python.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "a": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "First point coordinates",
                },
                "b": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Second point coordinates",
                },
                "manifold": {
                    "type": "string",
                    "enum": ["euclidean", "hyperbolic", "spherical"],
                    "default": "euclidean",
                    "description": "Manifold type",
                },
            },
            "required": ["a", "b"],
        },
    ),
    ToolDefinition(
        name="quantum.fubini_study",
        description="Compute the Fubini-Study metric tensor for quantum state parameter space. Used in natural gradient optimization.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "state": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Quantum state vector",
                },
                "jacobian": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "description": "Jacobian matrix of the parameterization",
                },
                "n_params": {
                    "type": "integer",
                    "description": "Number of parameters",
                },
            },
            "required": ["state"],
        },
    ),
    ToolDefinition(
        name="quantum.natural_gradient",
        description="Natural gradient descent step using the Fubini-Study metric. Adjusts parameters in the direction of steepest descent on the quantum manifold.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "params": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Current parameter values",
                },
                "gradients": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Euclidean gradients",
                },
                "metric": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "description": "Fubini-Study metric tensor",
                },
                "learning_rate": {
                    "type": "number",
                    "default": 0.01,
                    "description": "Step size",
                },
            },
            "required": ["params", "gradients"],
        },
    ),
    ToolDefinition(
        name="quantum.mps_compress",
        description="Compress vectors using Matrix Product State (MPS) tensor network decomposition with SVD truncation.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "vectors": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "description": "Input vectors to compress",
                },
                "bond_dim": {
                    "type": "integer",
                    "default": 2,
                    "description": "Maximum bond dimension",
                },
                "seed": {
                    "type": "integer",
                    "default": 42,
                },
            },
            "required": ["vectors"],
        },
    ),
    ToolDefinition(
        name="quantum.auto_manifold",
        description="Automatically select the best manifold type (euclidean, hyperbolic, spherical) for given data points based on geometric heuristics.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "points": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "description": "Data points to analyze",
                },
            },
            "required": ["points"],
        },
    ),
    ToolDefinition(
        name="quantum.born_sample",
        description="Sample an index from amplitudes using Born-rule probabilities (probability = |amplitude|^2).",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "amplitudes": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Amplitude values",
                },
                "seed": {
                    "type": "integer",
                    "default": 42,
                },
            },
            "required": ["amplitudes"],
        },
    ),
    ToolDefinition(
        name="quantum.born_distribution",
        description="Compute Born-rule probability distribution from amplitudes (probability = |amplitude|^2, normalized).",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "amplitudes": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Amplitude values",
                },
            },
            "required": ["amplitudes"],
        },
    ),
    ToolDefinition(
        name="quantum.interference",
        description="Compute quantum interference pattern between two amplitude vectors (constructive and destructive).",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "a": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "First amplitude vector",
                },
                "b": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Second amplitude vector",
                },
            },
            "required": ["a", "b"],
        },
    ),
    # ── Topological Protection ──
    ToolDefinition(
        name="topological.berry_phase",
        description="Compute the Berry phase (geometric phase) accumulated over a cyclic path in parameter space. Dispatches to Haskell topological bridge first for formal verification.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "states": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "description": "Quantum states along the path",
                },
                "params": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Parameter values at each state",
                },
            },
            "required": ["states", "params"],
        },
    ),
    ToolDefinition(
        name="topological.chern_number",
        description="Compute the Chern number (topological invariant) from Berry curvature over a 2D parameter space. Dispatches to Haskell for formal verification.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "curvature": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "description": "Berry curvature matrix",
                },
            },
            "required": ["curvature"],
        },
    ),
    ToolDefinition(
        name="topological.encode",
        description="Encode data with topological redundancy for fault-tolerant storage. Uses topological protection to detect and correct errors.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Data to encode",
                },
                "n_redundant": {
                    "type": "integer",
                    "default": 3,
                    "description": "Number of redundant copies",
                },
            },
            "required": ["data"],
        },
    ),
    ToolDefinition(
        name="topological.decode",
        description="Decode topologically encoded data with error correction. Recovers original data from redundant encoding.",
        category=ToolCategory.METRICS,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "encoded": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Topologically encoded data",
                },
                "original_length": {
                    "type": "integer",
                    "description": "Length of original data",
                },
                "n_redundant": {
                    "type": "integer",
                    "default": 3,
                    "description": "Number of redundant copies used in encoding",
                },
            },
            "required": ["encoded", "original_length"],
        },
    ),
]
