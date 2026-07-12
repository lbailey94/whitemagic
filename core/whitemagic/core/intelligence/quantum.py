# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Quantum-Inspired Intelligence — Backward-compat shim.

Fused into AccelerationEngine (slot 5, Tail 尾) as of v23.1.
All quantum-inspired algorithms now live in
whitemagic.core.acceleration.quantum_bridge.

This module re-exports the fused classes and functions for backward
compatibility with existing imports.
"""

from __future__ import annotations

from whitemagic.core.acceleration.quantum_bridge import (
    QuantumEngine,
    QuantumGraphAdapter,
    QuantumGraphEngine,
    QuantumNode,
    QuantumWalkConfig,
    auto_select_manifold,
    born_rule_distribution,
    born_rule_sample,
    born_rule_select,
    embed_manifold,
    get_quantum_engine,
    manifold_distance,
    quantum_interference,
)

__all__ = [
    "QuantumEngine",
    "QuantumGraphAdapter",
    "QuantumGraphEngine",
    "QuantumNode",
    "QuantumWalkConfig",
    "auto_select_manifold",
    "born_rule_distribution",
    "born_rule_sample",
    "born_rule_select",
    "embed_manifold",
    "get_quantum_engine",
    "manifold_distance",
    "quantum_interference",
]
