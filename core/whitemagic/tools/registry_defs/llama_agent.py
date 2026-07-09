"""llama.cpp tool definitions — Local LLM inference via llama-server.
==========================================================
Provides generate, chat, model listing, and agent loop.
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="llama.models",
        description="List available models on the local llama-server.",
        category=ToolCategory.INFERENCE,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        gana="Roof",
        garden="protection",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="llama.generate",
        description=(
            "Generate text with a local llama.cpp model. "
            "Supports context injection from WhiteMagic memories and optional "
            "Memory-Augmented Generation (store output as a memory)."
        ),
        category=ToolCategory.INFERENCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "llama.cpp model name"},
                "prompt": {"type": "string", "description": "Prompt text"},
                "context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Inject relevant memories",
                },
                "store": {
                    "type": "boolean",
                    "default": False,
                    "description": "Store output as memory",
                },
                "system": {"type": "string", "description": "System prompt override"},
            },
            "required": ["model", "prompt"],
        },
        gana="Roof",
        garden="protection",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="llama.chat",
        description=(
            "Chat with a local llama.cpp model using message history. "
            "Supports context injection and optional memory storage."
        ),
        category=ToolCategory.INFERENCE,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "llama.cpp model name"},
                "messages": {
                    "type": "array",
                    "description": "List of {role, content} messages",
                },
                "context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Inject relevant memories",
                },
                "store": {
                    "type": "boolean",
                    "default": False,
                    "description": "Store output as memory",
                },
            },
            "required": ["model", "messages"],
        },
        gana="Roof",
        garden="protection",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="llama.agent",
        description=(
            "Run an agentic loop with a local llama.cpp model that can autonomously "
            "call WhiteMagic tools (search, create memories, analyze patterns) to "
            "complete a given task. Injects relevant memories as context and supports "
            "up to 10 tool-call iterations."
        ),
        category=ToolCategory.INFERENCE,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "llama.cpp model name (e.g., 'llama3.2', 'phi4', 'qwen2.5')",
                },
                "task": {
                    "type": "string",
                    "description": "The task or question for the agent",
                },
                "max_iterations": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum tool-call rounds",
                },
                "context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to inject relevant memories",
                },
                "store": {
                    "type": "boolean",
                    "default": False,
                    "description": "Store outputs as memories",
                },
            },
            "required": ["model", "task"],
        },
        gana="Roof",
        garden="protection",
        quadrant="northern",
        element="water",
    ),
]
