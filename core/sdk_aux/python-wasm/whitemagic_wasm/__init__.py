# WhiteMagic WASM Python Package
# Lightweight Python wrapper for WhiteMagic WASM

from pathlib import Path

__version__ = "18.1.0"

# Get WASM package path
_WASM_DIR = Path(__file__).parent / "wasm"

def get_wasm_path() -> Path:
    """Get the path to the WASM binary."""
    return _WASM_DIR / "whitemagic_rust_bg.wasm"

def get_js_path() -> Path:
    """Get the path to the JavaScript bindings."""
    return _WASM_DIR / "whitemagic_rust.js"

def wasm_version() -> str:
    """Return the WASM package version."""
    return __version__

def is_wasm_available() -> bool:
    """Check if WASM files are available."""
    return get_wasm_path().exists() and get_js_path().exists()

class EdgeEngine:
    """Python wrapper for WhiteMagic EdgeEngine WASM."""
    
    def __init__(self):
        if not is_wasm_available():
            raise RuntimeError("WASM files not found. Install with: pip install whitemagic-wasm")
        self._wasm_path = get_wasm_path()
        self._js_path = get_js_path()
    
    def get_wasm_bytes(self) -> bytes:
        """Load WASM binary as bytes."""
        with open(self._wasm_path, "rb") as f:
            return f.read()
    
    def get_js_source(self) -> str:
        """Load JavaScript bindings as string."""
        with open(self._js_path, "r") as f:
            return f.read()
    
    def __repr__(self):
        return f"EdgeEngine(wasm={self._wasm_path})"

def get_wasm_info() -> dict:
    """Get information about the WASM package."""
    wasm_path = get_wasm_path()
    js_path = get_js_path()
    
    info = {
        "version": __version__,
        "wasm_available": is_wasm_available(),
        "wasm_path": str(wasm_path),
        "js_path": str(js_path),
    }
    
    if wasm_path.exists():
        info["wasm_size_bytes"] = wasm_path.stat().st_size
    
    if js_path.exists():
        info["js_size_bytes"] = js_path.stat().st_size
    
    return info

__all__ = [
    "__version__",
    "get_wasm_path",
    "get_js_path",
    "wasm_version",
    "is_wasm_available",
    "EdgeEngine",
    "get_wasm_info",
]
