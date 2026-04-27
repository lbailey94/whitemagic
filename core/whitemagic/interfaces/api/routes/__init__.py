"""WhiteMagic API Routes."""

try:
    from . import dashboard_api, tip
    __all__ = ["dashboard_api", "tip"]
except ImportError:
    __all__ = []
