# mypy: disable-error-code=no-untyped-def
"""WhiteMagic Fast CLI — thin redirect to main CLI.

Deprecated: The main CLI (cli_app.py) now uses LazyGroup for lazy loading,
making this module unnecessary. It remains for backwards compatibility.

Version: 4.0.0
"""

import sys


def main_fast(argv: list[str] | None = None) -> int:
    """Fast CLI entry point — delegates to main CLI with lazy loading."""
    from whitemagic.cli.cli_app import main

    return main(argv or sys.argv[1:])  # type: ignore[no-any-return]


if __name__ == "__main__":
    sys.exit(main_fast())
