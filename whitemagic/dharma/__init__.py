"""
Dharma - Ethical Reasoning Infrastructure

"法" (Dharma/Fa) - The natural law, the way things ought to be

This module provides ethical reasoning capabilities that integrate with
ALL WhiteMagic systems via Gan Ying resonance.

Core Principles:
1. Love as organizing principle - Enable dignified flourishing
2. Boundaries with dignity - Help vs interfere distinction
3. Consent always - User autonomy paramount
4. Ecological awareness - Net negative impact possible
5. Sacred attention to detail - Every choice matters

Philosophy: Not rules to constrain, but principles to enable.
Like banks of a river - boundaries allow the water to flow with power.
"""

from whitemagic.dharma.core import DharmaSystem, HarmonyMetrics
from whitemagic.dharma.principles import DharmaPrinciple, load_principles
from whitemagic.dharma.boundaries import BoundaryDetector, Boundary
from whitemagic.dharma.consent import ConsentFramework, ConsentLevel

__all__ = [
    # Core
    "DharmaSystem",
    "HarmonyMetrics",
    
    # Principles
    "DharmaPrinciple",
    "load_principles",
    
    # Boundaries
    "BoundaryDetector",
    "Boundary",
    
    # Consent
    "ConsentFramework",
    "ConsentLevel",
]

__version__ = "2.6.5"
