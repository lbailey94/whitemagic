# Tool Wrappers Guide: AI Framework Integrations

## Executive Summary

This document provides pre-built integrations for WhiteMagic with popular AI frameworks, eliminating the need for custom wrapper code.

**Prerequisites**: Python API (see PYTHON_API_DESIGN.md)  
**Effort**: 2-3 weeks (all integrations)  
**Impact**: Zero-friction adoption for OpenAI, Anthropic, LangChain users

---

## The Integration Problem

### What Users Face Today

Every team using WhiteMagic with AI frameworks must write custom wrappers:

```python
# Users write this manually (painful)
import subprocess

def create_memory_for_openai(title, content, tags):
    """Custom wrapper around CLI."""
    subprocess.run([
        "python3", "memory_manager.py", "create",
        "--title", title,
        "--content", content,
        *["--tag", tag for tag in tags]
    ], check=True)

# Then manually define function schema
OPENAI_FUNCTIONS = [
    {
        "name": "create_memory",
        "description": "...",
        "parameters": {...}
    }
]
```

**Problems**:
- 50-100 lines of boilerplate per project
- Inconsistent schemas across teams
- No best practices shared
- Maintenance burden on users
- Slows adoption

### Our Solution

```python
# Zero boilerplate
from whitemagic.integrations import WhiteMagicOpenAI

wm = WhiteMagicOpenAI()

# Pre-built tool definitions
tools = wm.get_tools()

# Pre-built execution handler
result = wm.execute(function_name, arguments)

# Done - 3 lines of code
```

---

## OpenAI Functions Integration

### Installation

```bash
pip install whitemagic[openai]
```

### Implementation

```python
# whitemagic/integrations/openai_tools.py
"""OpenAI Functions integration for WhiteMagic."""

from typing import Any, Dict, List, Optional
import json

from whitemagic import MemoryManager
from whitemagic.exceptions import WhiteMagicError


class WhiteMagicOpenAI:
    """
    OpenAI Functions wrapper for WhiteMagic.
    
    Provides tool definitions and execution handlers for OpenAI's
    function calling API.
    
    Example:
        >>> from whitemagic.integrations import WhiteMagicOpenAI
        >>> import openai
        >>> 
        >>> wm = WhiteMagicOpenAI()
        >>> 
        >>> response = openai.chat.completions.create(
        ...     model="gpt-4",
        ...     messages=[{"role": "user", "content": "Debug this..."}],
        ...     tools=wm.get_tools()
        ... )
        >>> 
        >>> # Handle function call
        >>> for call in response.choices[0].message.tool_calls:
        ...     result = wm.execute(
        ...         call.function.name,
        ...         json.loads(call.function.arguments)
        ...     )
    """
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize OpenAI integration.
        
        Args:
            base_dir: WhiteMagic project directory
        """
        self.manager = MemoryManager(base_dir=base_dir)
    
    @staticmethod
    def get_tools() -> List[Dict[str, Any]]:
        """
        Get OpenAI tool definitions.
        
        Returns:
            List of tool definition dicts in OpenAI format
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_memory",
                    "description": (
                        "Store a new insight, decision, or pattern for future reference. "
                        "Use this when you discover something important that should be "
                        "remembered across sessions."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Brief descriptive title (2-10 words)"
                            },
                            "content": {
                                "type": "string",
                                "description": (
                                    "Full content with context, details, and reasoning. "
                                    "Be specific and include examples."
                                )
                            },
                            "memory_type": {
                                "type": "string",
                                "enum": ["short_term", "long_term"],
                                "description": (
                                    "short_term: Current session context, consolidates after 7 days. "
                                    "long_term: Reusable patterns and proven heuristics."
                                )
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Categorization tags. Use 'heuristic', 'pattern', 'proven', "
                                    "'decision', or 'insight' for auto-promotion to long-term."
                                )
                            }
                        },
                        "required": ["title", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_memories",
                    "description": (
                        "Search through stored memories by keywords or tags. "
                        "Use this to find relevant past learnings before making decisions."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search keywords (searches title and content)"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by specific tags"
                            },
                            "memory_type": {
                                "type": "string",
                                "enum": ["short_term", "long_term"],
                                "description": "Filter by memory type"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "load_context",
                    "description": (
                        "Load memory context for the current session. Call this at the "
                        "start of complex tasks to access relevant past learnings."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tier": {
                                "type": "integer",
                                "enum": [0, 1, 2],
                                "description": (
                                    "0: Minimal context (quick queries). "
                                    "1: Standard context (most tasks). "
                                    "2: Comprehensive context (complex analysis)."
                                )
                            }
                        },
                        "required": ["tier"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tags",
                    "description": (
                        "List all available tags with usage counts. "
                        "Useful for discovering what topics have been documented."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
    
    def execute(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function call from OpenAI.
        
        Args:
            function_name: Name of the function to execute
            arguments: Function arguments from OpenAI
            
        Returns:
            Result dict to send back to OpenAI
            
        Raises:
            WhiteMagicError: If execution fails
        """
        try:
            if function_name == "create_memory":
                memory = self.manager.create_memory(
                    title=arguments["title"],
                    content=arguments["content"],
                    memory_type=arguments.get("memory_type", "short_term"),
                    tags=arguments.get("tags", [])
                )
                return {
                    "success": True,
                    "filename": memory.filename,
                    "path": str(memory.path),
                    "message": f"Memory '{memory.title}' created successfully"
                }
            
            elif function_name == "search_memories":
                results = self.manager.search_memories(
                    query=arguments.get("query"),
                    tags=arguments.get("tags"),
                    memory_type=arguments.get("memory_type")
                )
                return {
                    "count": len(results),
                    "results": [
                        {
                            "title": r.memory.title,
                            "preview": r.preview,
                            "tags": r.memory.tags,
                            "memory_type": r.memory.memory_type,
                            "created": r.memory.created.isoformat()
                        }
                        for r in results[:10]  # Limit to top 10
                    ]
                }
            
            elif function_name == "load_context":
                context = self.manager.generate_context_summary(arguments["tier"])
                return {
                    "context": context,
                    "tier": arguments["tier"],
                    "message": "Context loaded successfully"
                }
            
            elif function_name == "list_tags":
                tags = self.manager.list_all_tags()
                return {
                    "total_tags": len(tags),
                    "tags": [
                        {
                            "name": tag.name,
                            "count": tag.count,
                            "used_in": tag.used_in
                        }
                        for tag in tags[:20]  # Top 20 tags
                    ]
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown function: {function_name}"
                }
                
        except WhiteMagicError as e:
            return {
                "success": False,
                "error": str(e)
            }
```

### Usage Example

```python
from whitemagic.integrations import WhiteMagicOpenAI
import openai
import json

# Initialize
client = openai.OpenAI()
wm = WhiteMagicOpenAI()

# First request with tools
messages = [
    {"role": "system", "content": "You are a helpful coding assistant with memory."},
    {"role": "user", "content": "Help me debug this performance issue in my database queries."}
]

response = client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    tools=wm.get_tools(),
    tool_choice="auto"
)

# Handle tool calls
while response.choices[0].message.tool_calls:
    # Add assistant response to messages
    messages.append(response.choices[0].message)
    
    # Execute each tool call
    for tool_call in response.choices[0].message.tool_calls:
        result = wm.execute(
            tool_call.function.name,
            json.loads(tool_call.function.arguments)
        )
        
        # Add tool result to messages
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result)
        })
    
    # Continue conversation
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=wm.get_tools()
    )

# Final response
print(response.choices[0].message.content)
```

---

## Anthropic Tools Integration

### Installation

```bash
pip install whitemagic[anthropic]
```

### Implementation

```python
# whitemagic/integrations/anthropic_tools.py
"""Anthropic Tools integration for WhiteMagic."""

from typing import Any, Dict, List
import anthropic

from whitemagic import MemoryManager


class WhiteMagicAnthropic:
    """
    Anthropic Tools wrapper for WhiteMagic.
    
    Example:
        >>> from whitemagic.integrations import WhiteMagicAnthropic
        >>> import anthropic
        >>> 
        >>> client = anthropic.Anthropic()
        >>> wm = WhiteMagicAnthropic()
        >>> 
        >>> message = client.messages.create(
        ...     model="claude-3-5-sonnet-20241022",
        ...     max_tokens=1024,
        ...     tools=wm.get_tools(),
        ...     messages=[{"role": "user", "content": "Debug this..."}]
        ... )
    """
    
    def __init__(self, base_dir: str = "."):
        self.manager = MemoryManager(base_dir=base_dir)
    
    @staticmethod
    def get_tools() -> List[Dict[str, Any]]:
        """Get Anthropic tool definitions."""
        return [
            {
                "name": "create_memory",
                "description": (
                    "Store a new insight, decision, or pattern. Use when you discover "
                    "something important that should persist across sessions. "
                    "Examples: bug fixes, performance optimizations, design patterns."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Brief descriptive title"
                        },
                        "content": {
                            "type": "string",
                            "description": "Detailed content with context and reasoning"
                        },
                        "memory_type": {
                            "type": "string",
                            "enum": ["short_term", "long_term"],
                            "description": "short_term for session context, long_term for reusable patterns"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags like 'heuristic', 'debugging', 'performance'"
                        }
                    },
                    "required": ["title", "content"]
                }
            },
            {
                "name": "search_memories",
                "description": (
                    "Search stored memories by keywords or tags. Use before making "
                    "decisions to leverage past learnings."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search keywords"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags"
                        }
                    }
                }
            },
            {
                "name": "load_context",
                "description": (
                    "Load memory context at session start. Tier 0: minimal, "
                    "Tier 1: standard, Tier 2: comprehensive."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tier": {
                            "type": "integer",
                            "enum": [0, 1, 2],
                            "description": "Context tier"
                        }
                    },
                    "required": ["tier"]
                }
            }
        ]
    
    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool call from Claude."""
        # Same logic as OpenAI version
        if tool_name == "create_memory":
            memory = self.manager.create_memory(
                title=tool_input["title"],
                content=tool_input["content"],
                memory_type=tool_input.get("memory_type", "short_term"),
                tags=tool_input.get("tags", [])
            )
            return {
                "success": True,
                "filename": memory.filename,
                "message": f"Created memory: {memory.title}"
            }
        
        elif tool_name == "search_memories":
            results = self.manager.search_memories(
                query=tool_input.get("query"),
                tags=tool_input.get("tags")
            )
            return {
                "count": len(results),
                "results": [
                    {"title": r.memory.title, "preview": r.preview}
                    for r in results[:10]
                ]
            }
        
        elif tool_name == "load_context":
            context = self.manager.generate_context_summary(tool_input["tier"])
            return {"context": context}
        
        return {"error": f"Unknown tool: {tool_name}"}
```

### Usage Example

```python
from whitemagic.integrations import WhiteMagicAnthropic
import anthropic

client = anthropic.Anthropic()
wm = WhiteMagicAnthropic()

# Initial message
messages = [
    {"role": "user", "content": "Help me optimize this database query."}
]

# First request
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=wm.get_tools(),
    messages=messages
)

# Handle tool use
while response.stop_reason == "tool_use":
    # Add assistant response
    messages.append({"role": "assistant", "content": response.content})
    
    # Execute tools
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = wm.execute(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result)
            })
    
    # Add tool results
    messages.append({"role": "user", "content": tool_results})
    
    # Continue
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=wm.get_tools(),
        messages=messages
    )

# Final response
for block in response.content:
    if block.type == "text":
        print(block.text)
```

---

## LangChain Integration

### Installation

```bash
pip install whitemagic[langchain]
```

### Implementation

```python
# whitemagic/integrations/langchain_tools.py
"""LangChain tools integration for WhiteMagic."""

from typing import Optional, Type
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field

from whitemagic import MemoryManager


# Input schemas
class CreateMemoryInput(BaseModel):
    """Input for create_memory tool."""
    title: str = Field(description="Memory title")
    content: str = Field(description="Memory content")
    memory_type: str = Field(default="short_term", description="Memory type")
    tags: list[str] = Field(default_factory=list, description="Tags")


class SearchMemoriesInput(BaseModel):
    """Input for search_memories tool."""
    query: Optional[str] = Field(None, description="Search query")
    tags: list[str] = Field(default_factory=list, description="Filter by tags")


class LoadContextInput(BaseModel):
    """Input for load_context tool."""
    tier: int = Field(description="Context tier (0, 1, or 2)")


# Tool implementations
class CreateMemoryTool(BaseTool):
    """Tool for creating memories."""
    
    name = "create_memory"
    description = (
        "Store a new insight or pattern for future reference. "
        "Use when you discover something important."
    )
    args_schema: Type[BaseModel] = CreateMemoryInput
    
    manager: MemoryManager = Field(default_factory=MemoryManager)
    
    def _run(
        self,
        title: str,
        content: str,
        memory_type: str = "short_term",
        tags: list = None
    ) -> str:
        """Create a memory."""
        memory = self.manager.create_memory(
            title=title,
            content=content,
            memory_type=memory_type,
            tags=tags or []
        )
        return f"Memory created: {memory.filename}"
    
    async def _arun(self, *args, **kwargs) -> str:
        """Async version."""
        return self._run(*args, **kwargs)


class SearchMemoriesTool(BaseTool):
    """Tool for searching memories."""
    
    name = "search_memories"
    description = "Search stored memories by keywords or tags"
    args_schema: Type[BaseModel] = SearchMemoriesInput
    
    manager: MemoryManager = Field(default_factory=MemoryManager)
    
    def _run(self, query: Optional[str] = None, tags: list = None) -> str:
        """Search memories."""
        results = self.manager.search_memories(query=query, tags=tags or [])
        
        if not results:
            return "No memories found."
        
        output = f"Found {len(results)} memories:\n\n"
        for r in results[:5]:
            output += f"- {r.memory.title}\n  {r.preview}\n\n"
        return output
    
    async def _arun(self, *args, **kwargs) -> str:
        return self._run(*args, **kwargs)


class LoadContextTool(BaseTool):
    """Tool for loading context."""
    
    name = "load_context"
    description = "Load memory context for current session"
    args_schema: Type[BaseModel] = LoadContextInput
    
    manager: MemoryManager = Field(default_factory=MemoryManager)
    
    def _run(self, tier: int) -> str:
        """Load context."""
        return self.manager.generate_context_summary(tier)
    
    async def _arun(self, tier: int) -> str:
        return self._run(tier)


def get_whitemagic_tools(base_dir: str = ".") -> list[BaseTool]:
    """
    Get all WhiteMagic tools for LangChain.
    
    Args:
        base_dir: WhiteMagic project directory
        
    Returns:
        List of LangChain tool instances
    """
    manager = MemoryManager(base_dir=base_dir)
    
    return [
        CreateMemoryTool(manager=manager),
        SearchMemoriesTool(manager=manager),
        LoadContextTool(manager=manager)
    ]
```

### Usage Example

```python
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI
from whitemagic.integrations.langchain_tools import get_whitemagic_tools

# Initialize
tools = get_whitemagic_tools()
llm = OpenAI(temperature=0)

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Use agent
result = agent.run(
    "Help me debug this caching issue and remember the solution for next time"
)
print(result)
```

---

## Haystack Integration

```python
# whitemagic/integrations/haystack_nodes.py
"""Haystack integration for WhiteMagic."""

from haystack import BaseComponent
from whitemagic import MemoryManager


class WhiteMagicRetriever(BaseComponent):
    """Haystack retriever backed by WhiteMagic."""
    
    outgoing_edges = 1
    
    def __init__(self, base_dir: str = "."):
        self.manager = MemoryManager(base_dir=base_dir)
    
    def run(self, query: str, tags: list = None):
        """Retrieve memories."""
        results = self.manager.search_memories(query=query, tags=tags)
        
        documents = [
            {
                "content": r.memory.content or r.preview,
                "meta": {
                    "title": r.memory.title,
                    "tags": r.memory.tags,
                    "score": r.score,
                    "created": r.memory.created.isoformat()
                }
            }
            for r in results
        ]
        
        return {"documents": documents}, "output_1"


# Usage
from haystack import Pipeline
from haystack.nodes import PromptNode

pipeline = Pipeline()
pipeline.add_node(
    WhiteMagicRetriever(),
    name="MemoryRetriever",
    inputs=["Query"]
)
pipeline.add_node(
    PromptNode(),
    name="PromptNode",
    inputs=["MemoryRetriever"]
)

result = pipeline.run(query="How do we handle caching?")
```

---

## Testing Integrations

```python
# tests/test_integrations.py
import pytest
from whitemagic.integrations import WhiteMagicOpenAI, WhiteMagicAnthropic

def test_openai_get_tools():
    wm = WhiteMagicOpenAI()
    tools = wm.get_tools()
    
    assert len(tools) >= 3
    assert tools[0]["type"] == "function"
    assert "create_memory" in tools[0]["function"]["name"]

def test_openai_execute_create(tmp_path):
    wm = WhiteMagicOpenAI(base_dir=tmp_path)
    
    result = wm.execute("create_memory", {
        "title": "Test",
        "content": "Test content",
        "tags": ["test"]
    })
    
    assert result["success"] == True
    assert "filename" in result

def test_anthropic_tools():
    wm = WhiteMagicAnthropic()
    tools = wm.get_tools()
    
    assert len(tools) >= 3
    assert "input_schema" in tools[0]
```

---

## Best Practices

### 1. Start Session with Context

```python
# OpenAI
wm = WhiteMagicOpenAI()

# First message: load context
messages = [
    {
        "role": "system",
        "content": wm.manager.generate_context_summary(tier=1)
    },
    {"role": "user", "content": "Help me debug..."}
]
```

### 2. Store Important Discoveries

```python
# Let the AI decide when to store
response = client.chat.completions.create(
    model="gpt-4",
    messages=messages,
    tools=wm.get_tools(),
    tool_choice="auto"  # AI decides when to call
)
```

### 3. Search Before Deciding

```python
# Encourage memory search
messages.append({
    "role": "system",
    "content": "Before making recommendations, search memories for relevant past learnings."
})
```

### 4. Tag Strategically

```python
# Guide the AI on tagging
system_prompt = """
When creating memories, use these tags:
- 'heuristic': Proven patterns
- 'debugging': Bug fixes
- 'performance': Optimizations
- 'decision': Architecture decisions
- 'insight': Key learnings
"""
```

---

## Benefits Summary

| Integration | Effort | User Benefit |
|-------------|--------|-------------|
| **OpenAI** | 1 week | GPT-4 with memory (most popular) |
| **Anthropic** | 3 days | Claude with memory (growing fast) |
| **LangChain** | 1 week | Agent memory (ecosystem play) |
| **Haystack** | 3 days | Retrieval augmentation |

**Total effort**: 2-3 weeks for all integrations  
**User benefit**: Zero boilerplate, 10 minutes to production

---

## Next Steps

See API_BENEFITS_ANALYSIS.md for strategic value and ROI analysis.
