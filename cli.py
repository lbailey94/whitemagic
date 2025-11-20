"""Backward-compatible shim for the CLI entry point."""

from whitemagic.cli_app import *  # noqa: F401,F403
from whitemagic.cli_zodiac import zodiac

if __name__ == "__main__":
    import sys

    sys.exit(main())
