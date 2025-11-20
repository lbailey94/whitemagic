"""
Biological Immune System for WhiteMagic

Inspired by biological immune systems, this module provides:
1. Threat Detection - Identify problems before they cause damage
2. Antibodies - Pattern library of known issues and fixes
3. Auto-Healing - Automatic correction of common problems
4. Immune Memory - Remember and prevent recurring issues

Philosophy: Just as a body's immune system protects against threats,
WhiteMagic's immune system protects against version drift, import errors,
and other systemic issues.
"""

from whitemagic.immune.detector import ThreatDetector, Threat, ThreatLevel
from whitemagic.immune.antibodies import AntibodyLibrary, Antibody
from whitemagic.immune.response import ImmuneResponse
from whitemagic.immune.memory import ImmuneMemory
from whitemagic.immune.dna import DNAValidator, ImmuneRegulator, DNAPrinciple

__all__ = [
    "ThreatDetector",
    "Threat",
    "ThreatLevel",
    "AntibodyLibrary",
    "Antibody",
    "ImmuneResponse",
    "ImmuneMemory",
    "DNAValidator",
    "ImmuneRegulator",
    "DNAPrinciple",
]

__version__ = "2.6.5"
