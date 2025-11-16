"""Chinese Character Dictionary - Core concepts."""

from typing import Dict
from .symbolic import ConceptType

# Philosophical concepts
PHILOSOPHICAL_CONCEPTS = {
    "dao": {"english": "The Way", "chinese": "道", "definition": "Fundamental principle", "type": ConceptType.PRINCIPLE},
    "de": {"english": "Virtue", "chinese": "德", "definition": "Moral character", "type": ConceptType.QUALITY},
    "li": {"english": "Principle", "chinese": "理", "definition": "Natural law", "type": ConceptType.PRINCIPLE},
    "fa": {"english": "Method", "chinese": "法", "definition": "Systematic approach", "type": ConceptType.METHOD},
    "qi": {"english": "Energy", "chinese": "氣", "definition": "Vital force", "type": ConceptType.ENTITY},
    "yin_yang": {"english": "Yin-Yang", "chinese": "陰陽", "definition": "Dynamic balance", "type": ConceptType.PRINCIPLE},
    "wu_xing": {"english": "Five Phases", "chinese": "五行", "definition": "Five transformations", "type": ConceptType.PRINCIPLE},
}

# Technical concepts
TECHNICAL_CONCEPTS = {
    "efficiency": {"english": "Efficiency", "chinese": "效率", "definition": "Optimal performance", "type": ConceptType.QUALITY},
    "optimization": {"english": "Optimization", "chinese": "優化", "definition": "Improvement process", "type": ConceptType.ACTION},
    "memory": {"english": "Memory", "chinese": "記憶", "definition": "Information storage", "type": ConceptType.ENTITY},
    "pattern": {"english": "Pattern", "chinese": "模式", "definition": "Recurring structure", "type": ConceptType.PATTERN},
    "system": {"english": "System", "chinese": "系統", "definition": "Organized whole", "type": ConceptType.ENTITY},
}

ALL_CONCEPTS = {**PHILOSOPHICAL_CONCEPTS, **TECHNICAL_CONCEPTS}

def load_core_concepts():
    """Load all core concepts into dict."""
    return ALL_CONCEPTS
