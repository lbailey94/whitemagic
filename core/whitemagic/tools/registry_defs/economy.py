"""ToolDefinitions for the Sovereign Economy (Leap 5.6).

Tools:
  - pulse.status: Check background XRPL scanning status
  - bounty.create: Create an XRPL Escrow-backed task bounty
  - bounty.list: List active task bounties
  - memory.rent: Pay for temporary access to a specialized galaxy
"""

from whitemagic.tools.registry import ToolCategory, ToolDefinition, ToolSafety

TOOLS = [
    ToolDefinition(
        name="pulse.status",
        description="Check the status of the Gratitude Pulse background scanner. Shows running state and scan interval.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="bounty.create",
        description="Create a new task bounty. Locked funds in XRPL Escrow ensure trustless payment upon completion.",
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Detailed description of the task"},
                "amount": {"type": "number", "description": "Amount in XRP to lock in escrow"},
                "expires_in": {"type": "integer", "description": "Seconds until the bounty expires", "default": 86400},
            },
            "required": ["task", "amount"],
        },
    ),
    ToolDefinition(
        name="bounty.list",
        description="List available task bounties on the node.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status (open, active, completed)", "default": "open"},
            },
        },
    ),
    ToolDefinition(
        name="memory.rent",
        description="Pay for temporary access to a specialized knowledge galaxy.",
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "galaxy_name": {"type": "string", "description": "Name of the galaxy to rent"},
                "agent_id": {"type": "string", "description": "ID of the agent requesting access"},
                "tx_hash": {"type": "string", "description": "XRPL transaction hash of the rental payment"},
            },
            "required": ["galaxy_name", "tx_hash"],
        },
    ),
]
