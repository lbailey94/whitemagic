"""
Python bridge to Haskell I Ching logic functions.

Provides type-safe state transitions and hexagram calculations using
Haskell's compile-time correctness guarantees.

Philosophy: Best of both worlds - Python flexibility + Haskell correctness.
"""

import ctypes
from pathlib import Path
from typing import List, Optional
import glob
import warnings

# Try to find Haskell shared library
_base_dir = Path(__file__).parent.parent / "whitemagic-logic"
_lib_patterns = [
    ".stack-work/install/**/libHSwhitemagic-logic-*.so",
    ".stack-work/dist/**/libHSwhitemagic-logic-*.so",
]

_lib_matches = []
for pattern in _lib_patterns:
    _lib_matches.extend(_base_dir.glob(pattern))
    if _lib_matches:
        break

if _lib_matches:
    try:
        # Load with RTLD_GLOBAL to make symbols available for GHC runtime
        # This helps resolve GHC runtime symbols like stg_gc_unpt_r1
        import sys
        if sys.platform == 'linux':
            # Load GHC base libraries first
            ghc_libs = [
                '/home/lucas/.ghcup/ghc/9.10.3/lib/ghc-9.10.3/lib/x86_64-linux-ghc-9.10.3/libHSbase-4.20.0.0-ghc9.10.3.so',
                '/home/lucas/.ghcup/ghc/9.10.3/lib/ghc-9.10.3/lib/x86_64-linux-ghc-9.10.3/libHSghc-prim-0.12.0-ghc9.10.3.so',
            ]
            
            # Try to preload GHC runtime
            for lib_path in ghc_libs:
                if Path(lib_path).exists():
                    try:
                        ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
                    except Exception:
                        pass  # Continue even if preload fails
        
        # Now load our Haskell library with RTLD_GLOBAL
        haskell_lib = ctypes.CDLL(str(_lib_matches[0]), mode=ctypes.RTLD_GLOBAL)
        
        # Initialize Haskell runtime
        haskell_lib.hs_init(None, None)
        
        HASKELL_AVAILABLE = True
    except Exception as e:
        HASKELL_AVAILABLE = False
        warnings.warn(f"Haskell library found but failed to load: {e}\nNote: Haskell integration is optional. Core functionality uses Rust.")
else:
    HASKELL_AVAILABLE = False
    warnings.warn(
        "Haskell library not found. Build with: cd whitemagic-logic && stack build"
    )

if HASKELL_AVAILABLE:
    # Define C function signatures
    haskell_lib.initFFI.argtypes = []
    haskell_lib.initFFI.restype = None
    
    haskell_lib.c_create_hexagram.argtypes = [
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_int
    ]
    haskell_lib.c_create_hexagram.restype = ctypes.c_void_p
    
    haskell_lib.c_hexagram_to_number.argtypes = [ctypes.c_void_p]
    haskell_lib.c_hexagram_to_number.restype = ctypes.c_int
    
    haskell_lib.c_is_balanced_hexagram.argtypes = [ctypes.c_void_p]
    haskell_lib.c_is_balanced_hexagram.restype = ctypes.c_int
    
    haskell_lib.c_free_hexagram.argtypes = [ctypes.c_void_p]
    haskell_lib.c_free_hexagram.restype = None
    
    # Initialize FFI
    haskell_lib.initFFI()


def create_hexagram(lines: List[int]) -> Optional[int]:
    """
    Create I Ching hexagram from 6 lines and return hexagram number (1-64).
    
    Args:
        lines: List of 6 integers (0=Yin, 1=Yang)
        
    Returns:
        Hexagram number (1-64), or None if Haskell unavailable
        
    Example:
        >>> create_hexagram([1,1,1,1,1,1])  # All Yang
        1  # The Creative (乾 Qián)
        >>> create_hexagram([0,0,0,0,0,0])  # All Yin
        2  # The Receptive (坤 Kūn)
    """
    if not HASKELL_AVAILABLE:
        warnings.warn("Haskell not available, cannot create hexagram")
        return None
    
    if len(lines) != 6:
        raise ValueError("Need exactly 6 lines")
    
    # Create hexagram
    hex_ptr = haskell_lib.c_create_hexagram(*lines)
    
    # Get hexagram number
    number = haskell_lib.c_hexagram_to_number(hex_ptr)
    
    # Free memory
    haskell_lib.c_free_hexagram(hex_ptr)
    
    return number


def is_balanced(lines: List[int]) -> Optional[bool]:
    """
    Check if hexagram is balanced (equal Yin and Yang).
    
    Args:
        lines: List of 6 integers (0=Yin, 1=Yang)
        
    Returns:
        True if balanced, False otherwise, None if Haskell unavailable
    """
    if not HASKELL_AVAILABLE:
        return None
    
    if len(lines) != 6:
        raise ValueError("Need exactly 6 lines")
    
    hex_ptr = haskell_lib.c_create_hexagram(*lines)
    balanced = haskell_lib.c_is_balanced_hexagram(hex_ptr)
    haskell_lib.c_free_hexagram(hex_ptr)
    
    return bool(balanced)


def recommend_threading_tier(task_count: int) -> int:
    """
    Use I Ching wisdom to recommend optimal threading tier.
    
    Maps workload intensity to hexagram, uses ancient wisdom to suggest
    threading tier (8, 16, 32, 64, 128, 256 threads).
    
    Args:
        task_count: Number of tasks to process
        
    Returns:
        Recommended thread count
        
    Philosophy:
        Light load (Yin-dominant) → Fewer threads (8-16)
        Heavy load (Yang-dominant) → More threads (64-256)
        Balanced load → Sweet spot (32-64)
    """
    if not HASKELL_AVAILABLE:
        # Fallback: simple linear mapping
        if task_count < 10:
            return 8
        elif task_count < 50:
            return 16
        elif task_count < 100:
            return 32
        elif task_count < 200:
            return 64
        elif task_count < 400:
            return 128
        else:
            return 256
    
    # Map task count to hexagram (Yin/Yang ratio)
    # Higher task count = more Yang (activity, movement)
    yang_ratio = min(task_count / 200, 1.0)
    
    # Create hexagram based on load intensity
    lines = [1 if i/6 < yang_ratio else 0 for i in range(6)]
    
    hexagram_num = create_hexagram(lines)
    
    if hexagram_num is None:
        return 64  # Default to I Ching sweet spot
    
    # Map hexagram number (1-64) to threading tier
    # Lower hexagrams (more Yin) → Fewer threads
    # Higher hexagrams (more Yang) → More threads
    if hexagram_num <= 10:
        return 8    # TIER_0
    elif hexagram_num <= 20:
        return 16   # TIER_1
    elif hexagram_num <= 32:
        return 32   # TIER_2
    elif hexagram_num <= 48:
        return 64   # TIER_3 (I Ching sweet spot!)
    elif hexagram_num <= 56:
        return 128  # TIER_4
    else:
        return 256  # TIER_5


def hexagram_name(number: int) -> str:
    """
    Get traditional I Ching hexagram name.
    
    Args:
        number: Hexagram number (1-64)
        
    Returns:
        Hexagram name in English and Chinese
    """
    names = {
        1: "The Creative (乾 Qián)",
        2: "The Receptive (坤 Kūn)",
        3: "Difficulty at the Beginning (屯 Zhūn)",
        4: "Youthful Folly (蒙 Méng)",
        # ... Full names can be added as needed
        63: "After Completion (既濟 Jì Jì)",
        64: "Before Completion (未濟 Wèi Jì)",
    }
    return names.get(number, f"Hexagram {number}")


def is_haskell_available() -> bool:
    """Check if Haskell library is available."""
    return HASKELL_AVAILABLE


def get_haskell_info() -> dict:
    """Get information about Haskell integration."""
    return {
        'available': HASKELL_AVAILABLE,
        'functions': [
            'create_hexagram',
            'is_balanced',
            'recommend_threading_tier'
        ] if HASKELL_AVAILABLE else [],
        'benefits': 'Type-safe state transitions, compile-time correctness',
        'installation': 'cd whitemagic-logic && stack build',
        'philosophy': 'Ancient wisdom meets modern type theory'
    }


# Cleanup on exit
if HASKELL_AVAILABLE:
    import atexit
    atexit.register(lambda: haskell_lib.hs_exit())
