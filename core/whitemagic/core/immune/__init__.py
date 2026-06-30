"""Immune system module."""

from whitemagic.core.immune.antibodies import AntibodyLibrary

try:
    from whitemagic.core.immune.memory import ImmuneMemory
except ImportError:
    ImmuneMemory = None  # type: ignore[assignment,misc]

try:
    from whitemagic.core.immune.response import ImmuneResponse
except ImportError:
    ImmuneResponse = None  # type: ignore[assignment,misc]

try:
    from whitemagic.core.immune.detector import ThreatDetector, ThreatLevel, ThreatType
except ImportError:
    ThreatDetector = None  # type: ignore[assignment,misc]
    ThreatLevel = None  # type: ignore[assignment,misc]
    ThreatType = None  # type: ignore[assignment,misc]

__all__ = [
    "AntibodyLibrary",
    "ImmuneMemory",
    "ImmuneResponse",
    "ThreatDetector",
    "ThreatLevel",
    "ThreatType",
]
