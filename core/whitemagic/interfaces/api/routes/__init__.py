"""WhiteMagic API Routes."""

try:
    from . import dashboard_api, galaxy_api, tip
    __all__ = ["dashboard_api", "galaxy_api", "tip"]
except ImportError:
    __all__ = []
