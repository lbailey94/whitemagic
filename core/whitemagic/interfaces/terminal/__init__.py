"""WhiteMagic Terminal Tool - Structured execution for agents.

This package is a planned v22.3+ feature (structured agent execution
with allowlists, audit logs, and MCP tool exposure). The
implementation files have not yet landed in the repo. The package
exists in skeleton form so that downstream code can import
`whitemagic.interfaces.terminal` without ImportError.

Per AGENTS.md §7 (The Stub Lesson), the right behavior when a
module is missing its implementation is to make the failure
explicit, not to silently swallow it. This __init__ therefore
sets __all__ to [] and raises ImportError if any submodule is
requested, so callers either:
  (a) get the real implementation when the files land, or
  (b) fail loudly at the import site, with the specific missing
      submodule named in the traceback.
"""

__version__ = "2.6.5"
__all__: list[str] = []


def __getattr__(name: str):  # PEP 562 lazy attribute access
    """Raise an explicit ImportError when any submodule is requested.

    The original implementation wrapped this in `try: from .X import Y`
    / `except ImportError: __all__ = []`, which silently masked the
    missing implementation. That hid real bugs (e.g. AGENTS.md §7
    notes that structural stubs are dangerous because they "look like
    they work but silently do nothing"). With this PEP 562 hook, the
    failure happens at the call site with a clear message.
    """
    raise ImportError(
        f"whitemagic.interfaces.terminal.{name} is not yet implemented. "
        f"This package is a planned v22.3+ feature. See "
        f"STRATEGIC_ROADMAP_V23.md for the current roadmap."
    )
