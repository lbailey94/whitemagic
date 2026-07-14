"""WhiteMagic Framework Adapters

Plug WhiteMagic into popular AI frameworks with 2-3 lines of code.

## LangChain

    from whitemagic.adapters.langchain import WhiteMagicMemory
    memory = WhiteMagicMemory(galaxy="universal")
    # Use with any LangChain agent

## CrewAI

    from whitemagic.adapters.crewai import WhiteMagicCrewMemory
    memory = WhiteMagicCrewMemory(galaxy="universal")

## AutoGen

    from whitemagic.adapters.autogen import register_whitemagic_tools
    register_whitemagic_tools(agent)

## PydanticAI

    from whitemagic.adapters.pydantic_ai import WhiteMagicToolset
    toolset = WhiteMagicToolset()

All adapters gracefully degrade if the framework is not installed.
"""

from __future__ import annotations


def _check_optional(name: str) -> bool:
    """Check if an optional framework is installed."""
    try:
        __import__(name)
        return True
    except ImportError:
        return False


__all__ = ["_check_optional"]
