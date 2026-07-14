# WhiteMagic Framework Adapters

Plug WhiteMagic into popular AI frameworks with 2-3 lines of code.

## Installation

```bash
# Install with adapter dependencies
pip install whitemagic[adapters]

# Or install individual frameworks
pip install whitemagic[langchain]
pip install whitemagic[crewai]
```

## LangChain

```python
from whitemagic.adapters.langchain import WhiteMagicMemory, WhiteMagicToolkit

# Memory for any LangChain agent
memory = WhiteMagicMemory(galaxy="universal", user_id="alice")

# Tools
toolkit = WhiteMagicToolkit(galaxy="universal")
tools = toolkit.get_tools()

# Use with agent
from langchain.agents import create_react_agent
agent = create_react_agent(llm, tools, memory=memory)
```

## CrewAI

```python
from whitemagic.adapters.crewai import WhiteMagicCrewMemory

memory = WhiteMagicCrewMemory(galaxy="universal")

# Store and search
memory.store("Important finding about quantum entanglement")
results = memory.search("quantum physics")
```

## AutoGen

```python
from whitemagic.adapters.autogen import register_whitemagic_tools

# Register with any AutoGen agent
register_whitemagic_tools(agent, galaxy="universal")

# Or use the mixin
from whitemagic.adapters.autogen import WhiteMagicAgentMixin

class MyAgent(WhiteMagicAgentMixin, ConversableAgent):
    pass

agent = MyAgent(...)
agent.init_whitemagic(galaxy="universal")
agent.remember("Key insight from the conversation")
```

## PydanticAI

```python
from whitemagic.adapters.pydantic_ai import WhiteMagicToolset

toolset = WhiteMagicToolset(galaxy="universal")

# Get OpenAI-compatible tool definitions
defs = toolset.get_tool_definitions()

# Execute tools directly
results = toolset.search_memories("quantum physics")
mem_id = toolset.create_memory("New finding")
```

## Graceful Degradation

All adapters work without the framework installed — they only require `whitemagic` core.
Framework-specific imports happen lazily, so you can install adapters without the framework
and it won't break imports.
