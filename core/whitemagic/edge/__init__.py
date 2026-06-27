# ruff: noqa: BLE001
"""Edge — Edge AI capabilities for local/offline operation."""

from __future__ import annotations

from .embeddings import LocalEmbeddings, get_local_embeddings
from .export import EdgeExporter, get_edge_exporter
from .federated import FederatedLearning, get_federated
from .self_improving import SelfImprovingCascade, get_self_improving

__all__ = [
    "LocalEmbeddings",
    "get_local_embeddings",
    "FederatedLearning",
    "get_federated",
    "SelfImprovingCascade",
    "get_self_improving",
    "EdgeExporter",
    "get_edge_exporter",
]
