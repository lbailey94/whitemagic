"""Emergent Behavior Detection and Capture

Automatically detect when novel solutions emerge spontaneously,
document them, and integrate them into the system.

Philosophy: 自然 (zì rán) - Self-so, spontaneous emergence
"""

from .detector import EmergenceDetector, NovelBehavior
from .capture import EmergenceCapture

__all__ = ['EmergenceDetector', 'NovelBehavior', 'EmergenceCapture']
