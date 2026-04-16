"""WhiteMagic API Routes."""

try:
    from . import dashboard_api
    __all__ = ["dashboard_api"]
except ImportError:
    __all__ = []
