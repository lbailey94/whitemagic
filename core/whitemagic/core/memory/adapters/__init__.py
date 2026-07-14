"""Memory adapters — framework integration and three-tier facade.

Primary interface:
    from whitemagic.core.memory.adapters import AgentMemory
    mem = AgentMemory()
    mem.short_term.add("context", importance=0.8)
    mem.long_term.store("fact", tags=["api"])
    mem.episodic.record(role="user", content="Fix bug")

Framework adapters:
    from whitemagic.core.memory.adapters import (
        WhiteMagicMemory,          # LangChain
        WhiteMagicCrewMemory,      # CrewAI
        WhiteMagicAutoGenMemory,   # AutoGen
        WhiteMagicOpenAIMemory,    # OpenAI Agents SDK
        ObsidianAdapter,           # Obsidian vault sync
    )
"""

from whitemagic.core.memory.adapters.agent_memory import (
    AgentMemory,
    EpisodicMemory,
    LongTermMemory,
    ShortTermMemory,
    get_agent_memory,
    reset_agent_memory,
)

__all__ = [
    "AgentMemory",
    "ShortTermMemory",
    "LongTermMemory",
    "EpisodicMemory",
    "get_agent_memory",
    "reset_agent_memory",
    "WhiteMagicMemory",
    "WhiteMagicCrewMemory",
    "WhiteMagicAutoGenMemory",
    "WhiteMagicOpenAIMemory",
    "ObsidianAdapter",
]


def __getattr__(name: str):
    """Lazy-load framework adapters only when imported."""
    if name == "WhiteMagicMemory":
        from whitemagic.core.memory.adapters.langchain_adapter import WhiteMagicMemory
        return WhiteMagicMemory
    if name == "WhiteMagicCrewMemory":
        from whitemagic.core.memory.adapters.crewai_adapter import WhiteMagicCrewMemory
        return WhiteMagicCrewMemory
    if name == "WhiteMagicAutoGenMemory":
        from whitemagic.core.memory.adapters.autogen_adapter import (
            WhiteMagicAutoGenMemory,
        )
        return WhiteMagicAutoGenMemory
    if name == "WhiteMagicOpenAIMemory":
        from whitemagic.core.memory.adapters.openai_adapter import (
            WhiteMagicOpenAIMemory,
        )
        return WhiteMagicOpenAIMemory
    if name == "ObsidianAdapter":
        from whitemagic.core.memory.adapters.obsidian_adapter import ObsidianAdapter
        return ObsidianAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
