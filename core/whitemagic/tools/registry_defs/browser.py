"""Registry definitions for browser and web research tools."""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

BROWSER_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="browser_navigate",
        description="Navigate the browser to a URL using Chrome DevTools Protocol.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
            },
            "required": ["url"],
        },
    ),
    ToolDefinition(
        name="browser_click",
        description="Click an element on the page by CSS selector.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for element to click",
                },
            },
            "required": ["selector"],
        },
    ),
    ToolDefinition(
        name="browser_type",
        description="Type text into an input element by CSS selector.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for input element",
                },
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["selector", "text"],
        },
    ),
    ToolDefinition(
        name="browser_extract_dom",
        description="Extract and distill the DOM of the current page for AI consumption.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="browser_screenshot",
        description="Capture a screenshot of the current page.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="browser_get_interactables",
        description="Get all interactive elements (buttons, links, inputs) from the current page.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="web_fetch",
        description="Fetch a URL and return clean text content. Fast httpx-based fetcher — no browser needed. "
        "Converts HTML to clean text optimized for AI token usage. Use this for reading articles, docs, and web pages.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return (default 30000)",
                    "default": 30000,
                },
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in seconds (default 15)",
                    "default": 15.0,
                },
            },
            "required": ["url"],
        },
    ),
    ToolDefinition(
        name="web_fetch_enhanced",
        description="Enhanced web fetch with outline extraction, content chunking, and summarization. "
        "Fetches a URL, extracts heading hierarchy (outline), splits content into ~2K-char semantic chunks "
        "with overlap, and generates a summary via llama-server (extractive fallback). "
        "Supports progressive loading: use chunk_index to retrieve individual chunks. "
        "Inspired by Windsurf's chunking and outline-building approach.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "chunk_size": {
                    "type": "integer",
                    "description": "Target chars per chunk (default 2000)",
                    "default": 2000,
                },
                "overlap": {
                    "type": "integer",
                    "description": "Overlap chars between chunks (default 200)",
                    "default": 200,
                },
                "summarize": {
                    "type": "boolean",
                    "description": "Generate summary (default true)",
                    "default": True,
                },
                "focus": {
                    "type": "string",
                    "description": "Optional focus topic to guide summarization",
                },
                "llama_model": {
                    "type": "string",
                    "description": "lla.cpp model for summarization (optional — uses WM_LLAMA_MODEL by default)",
                    "default": "",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max chars to fetch (default 50000)",
                    "default": 50000,
                },
                "chunk_index": {
                    "type": "integer",
                    "description": "If specified, return only this chunk's full text (progressive loading)",
                },
            },
            "required": ["url"],
        },
    ),
    ToolDefinition(
        name="web_search",
        description="Search the web using DuckDuckGo. No API key needed. Returns titles, URLs, and snippets. "
        "Use this to find information, articles, documentation, code examples, or anything on the public web.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 8)",
                    "default": 8,
                },
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in seconds (default 10)",
                    "default": 10.0,
                },
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="web_search_and_read",
        description="Search the web AND fetch content from top results in one call. "
        "Combines web_search + web_fetch for the most common research pattern. "
        "Returns search results with full page content for top hits.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {
                    "type": "integer",
                    "description": "Number of search results (default 5)",
                    "default": 5,
                },
                "max_fetch": {
                    "type": "integer",
                    "description": "Max results to fetch content from (default 3)",
                    "default": 3,
                },
                "max_chars_per_page": {
                    "type": "integer",
                    "description": "Max chars per page (default 15000)",
                    "default": 15000,
                },
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="research_topic",
        description="Deep research on a topic: search → fetch top results → extract key points → synthesize. "
        "Single-call replacement for multi-step search workflows. "
        "Returns findings with full content, synthesis, and related topics for further exploration.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Research topic or question",
                },
                "num_search_results": {
                    "type": "integer",
                    "description": "How many search results to get (default 6)",
                    "default": 6,
                },
                "max_sources": {
                    "type": "integer",
                    "description": "How many top results to fetch (default 4)",
                    "default": 4,
                },
                "max_chars_per_source": {
                    "type": "integer",
                    "description": "Max chars per source (default 15000)",
                    "default": 15000,
                },
            },
            "required": ["topic"],
        },
    ),
    ToolDefinition(
        name="browser_session_status",
        description="Get the status of the persistent browser session (CDP connection).",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="web_search_category",
        description="Search the web with category filters. Categories: people, company, academic, code, docs, news. "
        "Modifies the query with site-specific filters for targeted results.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "category": {
                    "type": "string",
                    "enum": [
                        "general",
                        "people",
                        "company",
                        "academic",
                        "code",
                        "docs",
                        "news",
                    ],
                    "description": "Category filter (default 'general')",
                    "default": "general",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results (default 8)",
                    "default": 8,
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (default 10)",
                    "default": 10.0,
                },
            },
            "required": ["query", "category"],
        },
    ),
    ToolDefinition(
        name="deep_fetch",
        description="Fetch a URL with full-content retrieval (up to 200K chars). Unlike web_fetch (30K cap), "
        "deep_fetch gets the entire page. Follows pagination links when detectable. "
        "Use this when you need ALL information from a page, not just a summary.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum total characters (default 200000)",
                    "default": 200000,
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (default 30)",
                    "default": 30.0,
                },
            },
            "required": ["url"],
        },
    ),
    ToolDefinition(
        name="research_repo",
        description="Research a GitHub repository by fetching its README, docs, and wiki pages. "
        "Stores fetched content as WhiteMagic memories for later Q&A via hybrid_recall. "
        "Replaces DeepWiki's instant repo Q&A with a self-contained approach. "
        "Use owner/repo format (e.g. 'facebook/react').",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "GitHub repo in owner/repo format (e.g. 'facebook/react')",
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Max pages to fetch (default 5)",
                    "default": 5,
                },
                "max_chars_per_page": {
                    "type": "integer",
                    "description": "Max chars per page (default 50000)",
                    "default": 50000,
                },
                "store_memories": {
                    "type": "boolean",
                    "description": "Store as memories for Q&A (default true)",
                    "default": True,
                },
            },
            "required": ["repo"],
        },
    ),
    ToolDefinition(
        name="research_url",
        description="Fetch full content from any URL on the open net and store as a WhiteMagic memory. "
        "Uses deep_fetch for full-content retrieval (no chunk skimming). "
        "Enables Q&A on any web content via hybrid_recall after storing.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to research"},
                "max_chars": {
                    "type": "integer",
                    "description": "Max chars to retrieve (default 200000)",
                    "default": 200000,
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (default 30)",
                    "default": 30.0,
                },
                "store_memory": {
                    "type": "boolean",
                    "description": "Store as memory for Q&A (default true)",
                    "default": True,
                },
            },
            "required": ["url"],
        },
    ),
    ToolDefinition(
        name="web_search_batch",
        description="Search multiple queries in parallel. Dramatically speeds up multi-faceted research. "
        "Returns results grouped by query. Use with rabbit_hole_research for recursive spiral exploration.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of search queries to run in parallel",
                },
                "num_results_per_query": {
                    "type": "integer",
                    "description": "Results per query (default 5)",
                    "default": 5,
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout per search (default 10s)",
                    "default": 10.0,
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter for all queries",
                },
            },
            "required": ["queries"],
        },
    ),
    ToolDefinition(
        name="rabbit_hole_research",
        description="Deep recursive spiral research: searches topic, extracts unfamiliar terms, batch-searches them "
        "in parallel, deep-fetches results, recurses to max_depth levels. Cross-references sources, "
        "synthesizes findings, stores as memories for Q&A, caches content for re-reading. "
        "The ultimate research tool -- replaces multi-step external workflows.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to research"},
                "max_depth": {
                    "type": "integer",
                    "description": "Max recursion depth (default 3)",
                    "default": 3,
                },
                "max_parallel_terms": {
                    "type": "integer",
                    "description": "Max terms per level (default 12)",
                    "default": 12,
                },
                "num_search_results": {
                    "type": "integer",
                    "description": "Search results per term (default 5)",
                    "default": 5,
                },
                "fetch_top_results": {
                    "type": "integer",
                    "description": "Top results to fetch per term (default 3)",
                    "default": 3,
                },
                "max_chars_per_fetch": {
                    "type": "integer",
                    "description": "Max chars per fetch (default 50000)",
                    "default": 50000,
                },
                "store_memories": {
                    "type": "boolean",
                    "description": "Store as memories (default true)",
                    "default": True,
                },
                "cache_content": {
                    "type": "boolean",
                    "description": "Cache content for re-reading (default true)",
                    "default": True,
                },
                "initial_temperature": {
                    "type": "number",
                    "description": "Starting curiosity temp: 0.0=focused, 0.5=curious, 1.0=wild (default 0.0)",
                    "default": 0.0,
                },
                "temperature_rise": {
                    "type": "number",
                    "description": "Temp rise per depth level — simulates clicking tangential links (default 0.25)",
                    "default": 0.25,
                },
                "novelty_floor": {
                    "type": "number",
                    "description": "Stop if novelty below this for 2 levels — detects same-y echo chambers (default 0.15)",
                    "default": 0.15,
                },
            },
            "required": ["topic"],
        },
    ),
    ToolDefinition(
        name="web_cache_list",
        description="List all cached web content files with metadata (URL, title, cached time, size).",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name="web_cache_clear",
        description="Clear cached web content. Optionally only remove files older than N hours.",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "older_than_hours": {
                    "type": "integer",
                    "description": "Only remove files older than this many hours",
                },
            },
        },
    ),
    ToolDefinition(
        name="alchemical_cycle",
        description="Run the yin/yang zodiacal alchemical procession as a meta-loop orchestrator. "
        "Yang phase: creative outward action (research, reason, generate). "
        "Yin phase: receptive inward reflection (analyze, score, learn). "
        "Fixed hubs: stability checkpoints. "
        "Each cycle's output becomes the next cycle's input for iterative refinement.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task to process through the alchemical cycle",
                },
                "cycles": {
                    "type": "integer",
                    "description": "Number of yin-yang cycles (default 2)",
                    "default": 2,
                },
            },
            "required": ["task"],
        },
    ),
    ToolDefinition(
        name="codegenome_validate",
        description="Recursive self-improvement pipeline: ParallelReasoningTree explores approaches, "
        "CodeGenome generates code, STRATA analyzes it, Monte Carlo scores confidence, "
        "issues feed back as revision triggers for iterative improvement. "
        "Lessons auto-persisted to AutonomousLearner for future avoidance.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Natural language code generation prompt",
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Max improvement iterations (default 3)",
                    "default": 3,
                },
                "score_threshold": {
                    "type": "number",
                    "description": "Score at which to stop (default 0.8)",
                    "default": 0.8,
                },
                "repo_path": {
                    "type": "string",
                    "description": "Optional repo path for context",
                },
            },
            "required": ["prompt"],
        },
    ),
    ToolDefinition(
        name="image_analyze",
        description="Analyze an image file: extract metadata, structural layout (content regions, "
        "text bands, grid map, dominant colors), OCR text, and optional natural-language "
        "description via a local llama.cpp vision model (moondream). Uses tiered analysis: "
        "tesseract OCR → ocr.space API OCR → PIL structural analysis → llama.cpp vision "
        "description (if describe=True). Accepts a local file path or URL. "
        "Belongs to gana_chariot (perception/navigation).",
        category=ToolCategory.BROWSER,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to local image file",
                },
                "url": {
                    "type": "string",
                    "description": "URL of image to analyze (alternative to image_path)",
                },
                "extract_text": {
                    "type": "boolean",
                    "description": "Attempt OCR text extraction (default true)",
                    "default": True,
                },
                "max_text_length": {
                    "type": "integer",
                    "description": "Max OCR text length to return (default 5000)",
                    "default": 5000,
                },
                "describe": {
                    "type": "boolean",
                    "description": "Request a natural-language description from a local llama.cpp vision model (default false)",
                    "default": False,
                },
                "vision_prompt": {
                    "type": "string",
                    "description": "Prompt for the vision model (default asks for detailed description)",
                    "default": "Describe this image in detail. Include visible text, UI elements, layout, and the overall meaning or context.",
                },
                "vision_model": {
                    "type": "string",
                    "description": "Vision model name (default llama-server)",
                    "default": "llama-server",
                },
                "llama_url": {
                    "type": "string",
                    "description": "Base URL for llama-server (default http://localhost:8080)",
                    "default": "http://localhost:8080",
                },
            },
        },
    ),
    ToolDefinition(
        name="parallel_reason",
        description="Run parallel multi-branch reasoning with branching, backtracking, and revision. "
        "Explores multiple hypotheses simultaneously, cross-pollinates insights between branches, "
        "and converges on a synthesis. Closer to biological human thought patterns. "
        "Replaces sequential-thinking MCP with a far more capable cognitive engine.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question or problem to reason about",
                },
                "max_branches": {
                    "type": "integer",
                    "description": "Max concurrent branches (default 4)",
                    "default": 4,
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Max thoughts per branch (default 6)",
                    "default": 6,
                },
                "fork_threshold": {
                    "type": "number",
                    "description": "Confidence threshold for forking (default 0.5)",
                    "default": 0.5,
                },
            },
            "required": ["question"],
        },
    ),
]
