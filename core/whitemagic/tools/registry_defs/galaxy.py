"""Galaxy Management Tools — Multi-Galaxy Memory System.
=====================================================
Project-scoped memory databases for organizing knowledge
across different projects, archives, and domains.
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="galaxy.create",
        description=(
            "Create a new galaxy (project-scoped memory database). Each galaxy gets "
            "its own SQLite database and holographic index for isolated memory storage."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Galaxy name (alphanumeric, hyphens, underscores)",
                    "default": "main",
                },
                "path": {
                    "type": "string",
                    "description": "Optional project directory this galaxy is associated with",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
            },
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.switch",
        description=(
            "Switch the active galaxy. All subsequent memory operations (search, create, "
            "recall) will target the new galaxy's database."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Galaxy name to switch to",
                    "default": "main",
                },
            },
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.list",
        description="List all known galaxies with metadata, memory counts, and active status.",
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.status",
        description="Get overall galaxy manager status — active galaxy, total count, registry path.",
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.ingest",
        description=(
            "Ingest files from a directory into a galaxy's memory store. Reads text files "
            "matching a glob pattern and stores each as a memory."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Galaxy name to ingest into",
                    "default": "main",
                },
                "source_path": {
                    "type": "string",
                    "description": "Directory path to ingest from",
                    "default": ".",
                },
                "pattern": {
                    "type": "string",
                    "default": "**/*.md",
                    "description": "Glob pattern for files",
                },
                "max_files": {
                    "type": "integer",
                    "default": 500,
                    "description": "Max files to ingest",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to apply to all ingested memories",
                },
            },
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.delete",
        description="Remove a galaxy from the registry. The database file is preserved on disk.",
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Galaxy name to remove",
                    "default": "",
                },
            },
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    # ── v23.1: 6D Holographic Galaxy Router ──────────────────────────
    ToolDefinition(
        name="galaxy.route",
        description=(
            "Determine which cognitive galaxy a memory belongs to based on the "
            "source subsystem. Returns the galaxy name for routing."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "subsystem": {
                    "type": "string",
                    "description": "Name of the cognitive subsystem (e.g. 'dream_cycle', 'emergence_engine')",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata with explicit galaxy override",
                },
            },
            "required": ["subsystem"],
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.stats",
        description=(
            "Get statistics for a specific cognitive galaxy — memory count, "
            "average importance, average galactic distance, zone distribution."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "galaxy": {
                    "type": "string",
                    "description": "Galaxy name (e.g. 'universal', 'self_learning', 'oracle')",
                    "default": "universal",
                },
            },
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.migrate",
        description=(
            "Migrate a memory from one cognitive galaxy to another. "
            "Useful when a memory's cognitive role shifts over time."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "ID of the memory to migrate",
                },
                "target_galaxy": {
                    "type": "string",
                    "description": "Destination galaxy name",
                },
            },
            "required": ["memory_id", "target_galaxy"],
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.list_types",
        description=(
            "List all registered cognitive galaxy types with descriptions, "
            "colors, and decay multipliers."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.export",
        description=(
            "Export memories from a galaxy as Arrow IPC bytes for cross-instance sharing. "
            "Uses zero-copy columnar format (32x faster than JSON). "
            "Filters by galaxy and optionally by memory type."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "galaxy": {
                    "type": "string",
                    "description": "Galaxy to export (default: universal)",
                },
                "memory_type": {
                    "type": "string",
                    "description": "Filter by memory type (optional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max memories to export (default: 10000)",
                },
            },
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.import",
        description=(
            "Import memories from Arrow IPC bytes into the local memory system. "
            "Memories are stored via the normal ingestion pipeline with dedup, "
            "surprise gate, and holographic indexing. Galaxy metadata is preserved."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "ipc_bytes_b64": {
                    "type": "string",
                    "description": "Base64-encoded Arrow IPC bytes",
                },
            },
            "required": ["ipc_bytes_b64"],
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.search_multi",
        description=(
            "Search across multiple galaxies in parallel. Executes FTS5 queries "
            "against each specified galaxy (or all galaxies if none specified) "
            "and merges results by importance. Enables cross-galaxy recall "
            "without switching the active galaxy."
        ),
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "FTS5 search query (optional, browses all if omitted)",
                },
                "galaxies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Galaxy names to search. If omitted, searches all galaxies.",
                },
                "galaxy": {
                    "type": "string",
                    "description": "Single galaxy name to search (shorthand for galaxies=[name]).",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tag filter (memories must have ALL listed tags)",
                },
                "min_importance": {
                    "type": "number",
                    "description": "Minimum importance threshold (0.0-1.0)",
                    "default": 0.0,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results per galaxy",
                    "default": 20,
                },
            },
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.share",
        description=(
            "Share a galaxy with another user by creating a registry entry "
            "that points to the same database file. The target user gets "
            "read/write access. This is a lightweight share — no data copy."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Galaxy name to share",
                },
                "target_user_id": {
                    "type": "string",
                    "description": "User ID to share the galaxy with",
                },
            },
            "required": ["name", "target_user_id"],
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
    ToolDefinition(
        name="galaxy.list_shared",
        description=(
            "List all galaxies shared with a user. Shared galaxies have a "
            "'shared' tag and point to a database owned by another user."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {},
        },
        gana="Void",
        garden="stillness",
        quadrant="northern",
        element="water",
    ),
]
