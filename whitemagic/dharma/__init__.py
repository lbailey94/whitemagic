"""
Dharma - Ethical Reasoning Framework

धर्म (Dharma): Cosmic order, rightness, duty, morality.

Not just rules, but wisdom from multiple ethical traditions:
- Consequentialism (outcomes)
- Deontology (duties)
- Virtue ethics (character)
- Care ethics (relationships)
- Dharmic philosophy (cosmic order)
"""

from .ethics_engine import (
    EthicsEngine,
    EthicalFramework,
    EthicalEvaluation
)

try:
    from .boundaries import BoundaryDetector
except ImportError:
    BoundaryDetector = None

try:
    from .consent import ConsentFramework
except ImportError:
    ConsentFramework = None

__all__ = [
    'EthicsEngine',
    'EthicalFramework',
    'EthicalEvaluation',
    'BoundaryDetector',
    'ConsentFramework'
]
