"""Immune system module."""

from whitemagic.core.immune.antibodies import AntibodyLibrary

try:
    from whitemagic.core.immune.immune_memory import ImmuneMemory
except ImportError:
    ImmuneMemory = None  # type: ignore[assignment,misc]

try:
    from whitemagic.core.immune.immune_response import ImmuneResponse
except ImportError:
    ImmuneResponse = None  # type: ignore[assignment,misc]

try:
    from whitemagic.core.immune.threat_detector import ThreatDetector
except ImportError:
    ThreatDetector = None  # type: ignore[assignment,misc]

try:
    from whitemagic.core.immune.threat_level import ThreatLevel
except ImportError:
    ThreatLevel = None  # type: ignore[assignment,misc]

__all__ = ["AntibodyLibrary", "ImmuneMemory", "ImmuneResponse", "ThreatDetector", "ThreatLevel"]
