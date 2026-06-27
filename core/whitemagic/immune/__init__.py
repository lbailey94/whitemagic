# ruff: noqa: BLE001
"""
Biological Immune System for WhiteMagic

Inspired by biological immune systems, this module provides:
1. Threat Detection - Identify problems before they cause damage
2. Antibodies - Pattern library of known issues and fixes
3. Auto-Healing - Automatic correction of common problems
4. Immune Memory - Remember and prevent recurring issues
"""

from __future__ import annotations

from .antibodies import Antibody, AntibodyLibrary, get_antibody_library
from .detector import Threat, ThreatDetector, ThreatLevel, ThreatType, get_detector
from .dna import DNALayer, get_dna_layer
from .memory import ImmuneMemory, get_immune_memory
from .response import ImmuneResponse, get_response

__all__ = [
    "ThreatDetector",
    "Threat",
    "ThreatType",
    "ThreatLevel",
    "get_detector",
    "AntibodyLibrary",
    "Antibody",
    "get_antibody_library",
    "ImmuneResponse",
    "get_response",
    "ImmuneMemory",
    "get_immune_memory",
    "DNALayer",
    "get_dna_layer",
]
