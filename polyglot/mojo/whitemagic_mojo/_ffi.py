"""MAX FFI Bridge for Python interop"""
import ctypes
from pathlib import Path

_lib_path = Path(__file__).parent / 'lib' / 'whitemagic_mojo.so'
if _lib_path.exists():
    _lib = ctypes.CDLL(str(_lib_path))
else:
    _lib = None

def mojo_available():
    return _lib is not None
