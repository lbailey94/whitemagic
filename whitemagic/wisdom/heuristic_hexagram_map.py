"""Map 385 heuristics to I Ching hexagram patterns"""

# Map heuristics to hexagram archetypes
HEURISTIC_HEXAGRAM_MAP = {
    # Creative/Initiation heuristics → Hexagram 1 (The Creative)
    "creative": {
        "hexagram": 1,
        "heuristics": [
            "When all systems align, act decisively",
            "High confidence + clear path = maximum action",
            "Yang dominant = parallel processing, full speed",
            "Initiate boldly when conditions are perfect",
            "Creative phase: Generate, don't refine"
        ]
    },
    
    # Receptive/Learning heuristics → Hexagram 2 (The Receptive)
    "receptive": {
        "hexagram": 2,
        "heuristics": [
            "When uncertain, gather more data",
            "Yin dominant = listen, observe, learn",
            "Consolidation phase: Absorb, don't output",
            "Patience brings clarity",
            "Yield to understand, don't force"
        ]
    },
    
    # Resource/Depth heuristics → Hexagram 48 (The Well)
    "resources": {
        "hexagram": 48,
        "heuristics": [
            "Draw from established patterns first",
            "Proven solutions > novel experiments",
            "Deep resources = system tools, libraries",
            "Consistency over innovation when stable works",
            "The well doesn't change - neither should core patterns"
        ]
    },
    
    # Pattern matching logic
    "pattern_detection": {
        "heuristics": [
            "If all systems confident → Hexagram 1 (Creative)",
            "If gathering information → Hexagram 2 (Receptive)",
            "If using established tools → Hexagram 48 (Well)",
            "If high uncertainty → Yin-dominant hexagrams",
            "If clear action needed → Yang-dominant hexagrams"
        ]
    }
}

def map_heuristic_to_hexagram(heuristic: str) -> int:
    """Map a heuristic to most relevant hexagram"""
    h_lower = heuristic.lower()
    
    # Keyword matching
    if any(word in h_lower for word in ['create', 'initiate', 'bold', 'decisive']):
        return 1  # The Creative
    elif any(word in h_lower for word in ['learn', 'gather', 'patient', 'observe']):
        return 2  # The Receptive
    elif any(word in h_lower for word in ['resource', 'proven', 'consistent', 'deep']):
        return 48  # The Well
    
    # Default: Use context to determine
    return None

def get_hexagram_heuristics(hexagram_num: int) -> list:
    """Get all heuristics for a hexagram"""
    for category, data in HEURISTIC_HEXAGRAM_MAP.items():
        if data.get("hexagram") == hexagram_num:
            return data.get("heuristics", [])
    return []

# Export
__all__ = ['HEURISTIC_HEXAGRAM_MAP', 'map_heuristic_to_hexagram', 'get_hexagram_heuristics']
