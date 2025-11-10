"""Version utilities for WhiteMagic API"""

from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def get_version() -> str:
    """
    Read version from VERSION file.
    
    Cached to avoid repeated file reads.
    """
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"


def get_version_dict() -> dict:
    """Get version information as dictionary"""
    return {
        "version": get_version(),
        "api_version": "v1",
        "revision": get_version()
    }
