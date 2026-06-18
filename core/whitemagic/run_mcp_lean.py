#!/usr/bin/env python3
# ruff: noqa: BLE001
# mypy: disable-error-code=no-untyped-def
"""
WhiteMagic MCP Server — Lean Edition
==============================================
Uses the standard mcp SDK directly (no FastMCP overhead).
Registers 28 PRAT Gana meta-tools.  All heavy imports are
deferred to first tool invocation so the server handshakes
with clients in < 1 second.

Supports:
- stdio transport (default, for IDE integration)
- Streamable HTTP transport (--http flag, for remote/browser access)
- Server Instructions (auto-injected into AI client context)
- Per-Gana tool icons (lunar mansion symbols)
- Task execution modes (slow tools marked as task-optional)

**SHIP_SURFACE**: 🎯 Core Tier - Essential runtime component
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from pathlib import Path
from typing import Any, cast

# ── Ensure project root is on sys.path ──────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
CORE_SYSTEM_DIR = ROOT_DIR.parent
REPO_ROOT = CORE_SYSTEM_DIR.parent
if str(CORE_SYSTEM_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SYSTEM_DIR))



# ── Logging (stderr only — stdout is the MCP transport) ─────────────
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger("wm_mcp")

# ── Lazy MCP SDK wrappers (deferred until first use) ─────────────────
class _LazyMCPTypes:
    """Proxy that imports mcp.types on first attribute access."""

    _mod: Any = None

    def __getattr__(self, name: str) -> Any:
        if self._mod is None:
            import mcp.types as _real_types

            self._mod = _real_types
        return getattr(self._mod, name)


class _LazyServer:
    """Proxy that creates mcp.server.Server on first *runtime* use.

    Decorator calls (``@server.list_tools()`` etc.) are captured and
    replayed when the real server is materialised inside ``main()``.
    """

    _srv: Any = None
    _deferred: dict[str, list] = {}

    def _ensure(self) -> Any:
        if self._srv is None:
            from mcp.server import Server

            self._srv = Server("WhiteMagic Core")
            self._srv.instructions = _INSTRUCTIONS
            self._srv.version = _VERSION
            self._srv.website_url = "https://github.com/whitemagic-ai/whitemagic"
            for method_name, callbacks in self._deferred.items():
                decorator_factory = getattr(self._srv, method_name)
                for fn in callbacks:
                    decorator_factory()(fn)
        return self._srv

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ensure(), name)

    def _capture(self, name: str):
        """Return a decorator that records the callback for later replay."""

        def decorator(fn):
            """
            Perform the decorator operation.
            
            Args:
                fn: Parameter description.
            """
            self._deferred.setdefault(name, []).append(fn)
            return fn

        return decorator

    def list_tools(self):
        """
        List the tools.
        """
        return self._capture("list_tools")

    def call_tool(self):
        """
        Perform the call tool operation.
        """
        return self._capture("call_tool")

    def list_resources(self):
        """
        List the resources.
        """
        return self._capture("list_resources")

    def read_resource(self):
        """
        Perform the read resource operation.
        """
        return self._capture("read_resource")


types = _LazyMCPTypes()
server = _LazyServer()

# ── Version ──────────────────────────────────────────────────────────
_VERSION_FILE = CORE_SYSTEM_DIR / "VERSION"
if _VERSION_FILE.exists():
    _VERSION = _VERSION_FILE.read_text().strip()
else:
    try:
        from importlib.metadata import version as _pkg_version
        _VERSION = _pkg_version("whitemagic")
    except (ImportError, ModuleNotFoundError):
        _VERSION = "unknown"


# ══════════════════════════════════════════════════════════════════════
# Lazy subsystem initialiser — runs once on first tool call
# ══════════════════════════════════════════════════════════════════════

_INITIALISED = False
_INIT_LOCK = threading.Lock()


def _ensure_init() -> None:
    """One-shot heavy initialisation (DB, singletons, Rust bridge)."""
    global _INITIALISED
    if _INITIALISED:
        return
    with _INIT_LOCK:
        if _INITIALISED:
            return
        logger.info("Lazy-initialising WhiteMagic subsystems …")
        import os

        from whitemagic.utils.feature_flags import get_all_flags, is_enabled
        all_flags = get_all_flags()
        enabled_flags = [name for name, info in all_flags.items() if info["enabled"]]
        if enabled_flags:
            logger.info("Feature flags enabled: %s", ", ".join(enabled_flags))

        # --- RUST ACCELERATION (PSR-001) ---
        try:
            from whitemagic.utils.feature_flags import is_enabled as _ff_is_enabled
            _rust_enabled = _ff_is_enabled("RUST_STORE")
        except (ImportError, ModuleNotFoundError):
            _rust_enabled = os.environ.get("WM_FEATURE_RUST_STORE") == "1"

        try:
            if _rust_enabled:
                import whitemagic_rust as _rust
                RustBackend = getattr(_rust, "PySQLiteBackend", None)
                RUST_AVAILABLE = True if RustBackend is not None else False
                if RUST_AVAILABLE:
                    logger.info("WhiteMagic Rust Backend (PSR-001) linked successfully.")
            else:
                RustBackend = None
                RUST_AVAILABLE = False
        except ImportError:
            RustBackend = None
            RUST_AVAILABLE = False
            logger.debug("Rust backend not found. Falling back to Python sqlite3.")

        if is_enabled("OTEL"):
            os.environ["WM_OTEL_ENABLED"] = "1"
            try:
                from whitemagic.core.monitoring.otel_export import get_otel
                get_otel()
                logger.info("OTEL tracing initialised")
            except ImportError:
                logger.warning("OTEL requested (WM_FEATURE_OTEL=1) but opentelemetry-sdk not installed")

        if is_enabled("DREAM_AUTO"):
            try:
                from whitemagic.core.intelligence.dream_synthesis import (
                    get_dream_synthesizer,
                )
                get_dream_synthesizer().mount()
                logger.info("DreamSynthesizer mounted (DREAM_AUTO enabled)")
            except (ImportError, ModuleNotFoundError) as e:
                logger.debug("DreamSynthesizer auto-mount failed: %s", e)


        try:
            from importlib.util import find_spec
            if find_spec("whitemagic_rs") is not None:
                logger.info("Rust bridge available")
        except (ImportError, ModuleNotFoundError) as e:
            import logging
            logging.getLogger(__name__).debug("Exception silenced: %s", e)

        # Auto-load Gana Forge extensions (12.108.17 — declarative śāstra)
        try:
            from whitemagic.tools.gana_forge import load_extensions
            ext_result = load_extensions()
            if ext_result.get("loaded", 0) > 0:
                logger.info("Forge: loaded %d extension tool(s)", ext_result["loaded"])
        except (ImportError, ModuleNotFoundError) as e:
            import logging
            logging.getLogger(__name__).debug("Exception silenced: %s", e)
        _INITIALISED = True


# ══════════════════════════════════════════════════════════════════════
# PRAT Gana tool definitions (static — no heavy imports needed)
# ══════════════════════════════════════════════════════════════════════

# Gana name → (short description, nested tool names)
_GANA_CACHE: dict[str, tuple[str, list[str]]] | None = None


# Shared Gana metadata lives in whitemagic.tools.tool_surface so lean and
# classic MCP surfaces draw from the same canonical 28-Gana contract.
_GANA_TOOLS: dict[str, list[str]] = {}
try:
    from whitemagic.tools.tool_surface import (
        get_gana_nested_tools as _get_gana_nested_tools,
    )

    _GANA_TOOLS = _get_gana_nested_tools()
except ImportError:
    pass


def _load_gana_metadata() -> dict[str, tuple[str, list[str]]]:
    """Load Gana metadata from the shared tool-surface module."""
    global _GANA_CACHE, _GANA_TOOLS
    if _GANA_CACHE is not None:
        return _GANA_CACHE

    from whitemagic.tools.tool_surface import get_gana_metadata as _get_gana_metadata

    _GANA_CACHE = _get_gana_metadata()
    _GANA_TOOLS = {gana: list(tools) for gana, (_, tools) in _GANA_CACHE.items()}
    return _GANA_CACHE


def _schema_for_gana(name: str) -> dict:
    """Build the input schema for a Gana with its specific tool enum."""
    tools_list = _GANA_TOOLS.get(name, [])
    tool_prop: dict = {
        "type": "string",
        "description": "Which nested tool to invoke within this Gana.",
    }
    if tools_list:
        tool_prop["enum"] = tools_list
    return {
        "type": "object",
        "properties": {
            "tool": tool_prop,
            "args": {
                "type": "object",
                "description": "Arguments to pass to the selected tool.",
                "default": {},
            },
            "operation": {
                "type": "string",
                "enum": ["search", "analyze", "transform", "consolidate"],
                "description": "Polymorphic operation (when no specific tool is given).",
            },
        },
    }


# ══════════════════════════════════════════════════════════════════════
# Per-Gana icons (lunar mansion Chinese characters as data-URI SVGs)
# ══════════════════════════════════════════════════════════════════════

_GANA_ICONS: dict[str, str] = {
    "gana_horn":             "\u89D2",  # 角
    "gana_neck":             "\u4EA2",  # 亢
    "gana_root":             "\u6C10",  # 氐
    "gana_room":             "\u623F",  # 房
    "gana_heart":            "\u5FC3",  # 心
    "gana_tail":             "\u5C3E",  # 尾
    "gana_winnowing_basket": "\u7B95",  # 箕
    "gana_ghost":            "\u9B3C",  # 鬼
    "gana_willow":           "\u67F3",  # 柳
    "gana_star":             "\u661F",  # 星
    "gana_extended_net":     "\u5F20",  # 张
    "gana_wings":            "\u7FFC",  # 翼
    "gana_chariot":          "\u8F78",  # 轸
    "gana_abundance":        "\u8C50",  # 豐
    "gana_straddling_legs":  "\u594E",  # 奎
    "gana_mound":            "\u5A04",  # 娄
    "gana_stomach":          "\u80C3",  # 胃
    "gana_hairy_head":       "\u6634",  # 昴
    "gana_net":              "\u6BD5",  # 毕
    "gana_turtle_beak":      "\u89DC",  # 觜
    "gana_three_stars":      "\u53C2",  # 参
    "gana_dipper":           "\u6597",  # 斗
    "gana_ox":               "\u725B",  # 牛
    "gana_girl":             "\u5973",  # 女
    "gana_void":             "\u865A",  # 虚
    "gana_roof":             "\u5371",  # 危
    "gana_encampment":       "\u5BA4",  # 室
    "gana_wall":             "\u58C1",  # 壁
}


def _icon_for_gana(name: str) -> list[types.Icon] | None:
    """Generate a data-URI SVG icon for a Gana using its lunar mansion character."""
    char = _GANA_ICONS.get(name)
    if not char:
        return None
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
        f'<circle cx="20" cy="20" r="18" fill="%23334155"/>'
        f'<text x="20" y="27" text-anchor="middle" font-size="20" fill="white">{char}</text>'
        f'</svg>'
    )
    import urllib.parse
    data_uri = "data:image/svg+xml," + urllib.parse.quote(svg)
    return [types.Icon(src=data_uri, mimeType="image/svg+xml")]


# ══════════════════════════════════════════════════════════════════════
# Slow tools — these get execution={mode: "optional"} for async tasks
# ══════════════════════════════════════════════════════════════════════

_SLOW_GANAS: set[str] = {
    "gana_abundance",       # dream cycle, lifecycle (2-7s)
    "gana_three_stars",     # kaizen analysis (3-5s)
    "gana_extended_net",    # pattern detection (1-2s)
    "gana_chariot",         # archaeology, KG operations (1-3s)
    "gana_ghost",           # graph topology rebuild (1s)
}


# ══════════════════════════════════════════════════════════════════════
# Server Instructions (loaded from markdown file)
# ══════════════════════════════════════════════════════════════════════

_INSTRUCTIONS_PATH = ROOT_DIR / "mcp_instructions.md"
_INSTRUCTIONS = ""
try:
    _INSTRUCTIONS = _INSTRUCTIONS_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    _INSTRUCTIONS = "WhiteMagic cognitive OS. Use gana_winnowing_basket to search, gana_neck to create memories."


# ══════════════════════════════════════════════════════════════════════
# Register handlers on the lazy server proxy
# ══════════════════════════════════════════════════════════════════════

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return the 28 Gana meta-tools with per-Gana tool enums, icons, and execution modes."""
    from whitemagic.tools.tool_surface import (
        GANA_NAMES as _GANA_NAMES,
    )
    from whitemagic.tools.tool_surface import (
        GANA_SHORT_DESC as _GANA_SHORT_DESC,
    )

    tools: list[types.Tool] = []
    for name in _GANA_NAMES:
        desc = _GANA_SHORT_DESC.get(name, f"Gana {name}")
        kwargs: dict[str, Any] = {
            "name": name,
            "description": desc,
            "inputSchema": _schema_for_gana(name),
        }
        icons = _icon_for_gana(name)
        if icons:
            kwargs["icons"] = icons
        if name in _SLOW_GANAS:
            kwargs["execution"] = types.ToolExecution(taskSupport=types.TASK_OPTIONAL)
        tools.append(types.Tool(**kwargs))
    return tools


# ── Result cache (LRU) for read-only Gana calls ──────────────────────
_result_cache: dict[str, Any] = {}
_CACHE_MAX_SIZE = 64


def _cache_key(gana: str, tool_name: str, tool_args: dict[str, Any], operation: str | None) -> str:
    """Deterministic cache key for a PRAT call."""
    import hashlib
    import json
    payload = json.dumps({"g": gana, "t": tool_name, "a": tool_args, "o": operation}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _sync_dispatch(gana: str, tool_name: str | None, tool_args: dict[str, Any], operation: str | None) -> dict[str, Any]:
    """Run the PRAT dispatch synchronously — called from a worker thread."""
    _ensure_init()

    # ── PRAT Vectorized Compression (PoC) ──
    # When WM_VECTORIZED=1, attempt to decompress short codes back to full
    # names before routing.  Results are optionally compressed for telemetry.
    _compressed_in = False
    _original_tool_name = tool_name
    _original_tool_args = tool_args
    try:
        from whitemagic.tools.prat_compressor import get_prat_compressor
        comp = get_prat_compressor()
        if comp.level > 0:
            dg, dt, da, do = comp.decompress_gana_call(gana, tool_name, tool_args, operation)
            if dg != gana or dt != tool_name or da != tool_args or do != operation:
                _compressed_in = True
                gana, tool_name, tool_args, operation = dg, dt, da, do
    except (ImportError, AttributeError):
        pass  # Compression is optional; never block dispatch

    # --- Input validation ---
    if not tool_name:
        return {
            "status": "error",
            "error_code": "MISSING_TOOL_NAME",
            "error": "The 'tool' parameter is required.",
        }
    if not isinstance(tool_args, dict):
        return {
            "status": "error",
            "error_code": "INVALID_ARGS_TYPE",
            "error": f"Expected dict for 'args', got {type(tool_args).__name__}.",
        }

    # --- Security: input sanitization (defense-in-depth) ---
    try:
        from whitemagic.tools.input_sanitizer import sanitize_tool_args
        sanitized = sanitize_tool_args(tool_name, tool_args)
        if sanitized is not None:
            # Input was blocked by sanitizer
            logger.warning("Input sanitizer blocked %s/%s: %s", gana, tool_name, sanitized.get("error"))
            return sanitized
    except Exception as exc:
        logger.debug("Input sanitizer error (non-blocking): %s", exc)

    # --- Cache lookup (read-only Ganas only) ---
    _READ_ONLY_GANAS = {"gana_heart", "gana_star", "gana_ghost", "gana_willow"}
    use_cache = gana in _READ_ONLY_GANAS
    if use_cache:
        key = _cache_key(gana, tool_name, tool_args, operation)
        cached = _result_cache.get(key)
        if cached is not None:
            logger.debug("Cache hit for %s/%s", gana, tool_name)
            return cached

    try:
        from whitemagic.tools.prat_router import route_prat_call
        result = route_prat_call(
            gana,
            tool=tool_name,
            args=tool_args,
            operation=operation,
        )
        # Cache successful read-only results
        if use_cache and result.get("status") == "success":
            if len(_result_cache) >= _CACHE_MAX_SIZE:
                _result_cache.pop(next(iter(_result_cache)))
            _result_cache[key] = result

        # ── PRAT Vectorized telemetry (PoC) ──
        if _compressed_in:
            try:
                from whitemagic.tools.prat_compressor import get_prat_compressor
                comp = get_prat_compressor()
                _sample_payload = {"tool": _original_tool_name, "args": _original_tool_args}
                _sample_comp = comp.compress(_sample_payload)
                st = comp.stats(_sample_payload, _sample_comp)
                if st["estimated_tokens_saved"] > 0:
                    logger.debug("PRAT vectorized: saved ~%d tokens (ratio %.2fx)", st["estimated_tokens_saved"], st["ratio"])
            except (ImportError, AttributeError):
                pass
        return result
    except ImportError as exc:
        logger.error("PRAT router import failed: %s", exc)
        return {
            "status": "error",
            "error_code": "ROUTER_IMPORT_ERROR",
            "error": f"Failed to load PRAT router: {exc}",
        }
    except Exception as exc:
        logger.exception("Unhandled exception in _sync_dispatch")
        return {
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "error": str(exc),
        }


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """Dispatch a PRAT Gana call through the full WhiteMagic pipeline."""
    from whitemagic.utils.fast_json import dumps_str as _json_dumps

    args = arguments or {}
    tool_name = args.get("tool")
    tool_args = args.get("args") or {}
    operation = args.get("operation")

    # Keep dispatch synchronous here; some runtimes intermittently stall when
    # resolving executor-backed futures in this handler path.
    result = _sync_dispatch(name, tool_name, tool_args, operation)

    text = _json_dumps(result, indent=2, default=str)
    return [types.TextContent(type="text", text=text)]


# ── Workflow templates (v14.1.1) ─────────────────────────────────────
_WORKFLOW_DIR = ROOT_DIR / "workflows"
_WORKFLOW_META: dict[str, str] = {
    "new_session": "Start every conversation — bootstrap, health, introspect, serendipity",
    "deep_research": "Multi-step research — search, graph walk, KG extract, synthesise",
    "memory_maintenance": "Periodic Data Sea hygiene — sweep, constellations, patterns",
    "ethical_review": "Full ethical governance check — dharma, boundaries, karma, harmony",
    "galaxy_setup": "Create and populate a new galaxy (isolated memory namespace)",
    "local_ai_chat": "Privacy-first local AI reasoning via Ollama integration",
}


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """Expose orientation docs, workflow templates, and health status."""
    resources = [
        types.Resource(
            uri=cast(Any, "whitemagic://health"),
            name="Health",
            description="Server health and status check.",
            mimeType="application/json",
        ),
        types.Resource(
            uri=cast(Any, "whitemagic://orientation/prologue"),
            name="Prologue",
            description="Canonical introduction and documentation router for WhiteMagic.",
            mimeType="text/markdown",
        ),
        types.Resource(
            uri=cast(Any, "whitemagic://orientation/ai-primary"),
            name="AI Primary",
            description="Primary orientation document for AI runtimes.",
            mimeType="text/markdown",
        ),
        types.Resource(
            uri=cast(Any, "whitemagic://orientation/server-instructions"),
            name="Server Instructions",
            description="How to use WhiteMagic — tool guide for AI clients.",
            mimeType="text/markdown",
        ),
        types.Resource(
            uri=cast(Any, "whitemagic://orientation/system-map"),
            name="System Map",
            description="Architecture overview and subsystem map.",
            mimeType="text/markdown",
        ),
    ]
    # v14.1.1: Workflow templates
    for wf_name, wf_desc in _WORKFLOW_META.items():
        resources.append(types.Resource(
            uri=cast(Any, f"whitemagic://workflow/{wf_name}"),
            name=f"Workflow: {wf_name.replace('_', ' ').title()}",
            description=wf_desc,
            mimeType="text/markdown",
        ))
    # v22.2: Grimoire chapters as dynamic resources
    _GRIMOIRE_CHAPTERS = [
        ("01", "Horn — Session Initiation"),
        ("02", "Neck — Memory Presence"),
        ("03", "Root — System Foundation"),
        ("04", "Room — Resource Sanctuary"),
        ("05", "Heart — Context Connection"),
        ("06", "Tail — Performance Drive"),
        ("07", "Winnowing Basket — Consolidation"),
        ("08", "Ghost — Metrics Introspection"),
        ("09", "Willow — Adaptive Play"),
        ("10", "Star — PRAT Illumination"),
        ("11", "Extended Net — Resonance Network"),
        ("12", "Wings — Parallel Creation"),
        ("13", "Chariot — Codebase Navigation"),
        ("14", "Abundance — Resource Sharing"),
        ("15", "Straddling Legs — Ethical Balance"),
        ("16", "Mound — Strategic Patience"),
        ("17", "Stomach — Energy Management"),
        ("18", "Hairy Head — Detailed Attention"),
        ("19", "Net — Pattern Capture"),
        ("20", "Turtle Beak — Precise Validation"),
        ("21", "Three Stars — Wisdom Council"),
        ("22", "Dipper — Governance"),
        ("23", "Ox — Endurance"),
        ("24", "Girl — Nurture"),
        ("25", "Void — Emptiness"),
        ("26", "Roof — Shelter"),
        ("27", "Encampment — Structure"),
        ("28", "Wall — Boundaries"),
    ]
    for num, title in _GRIMOIRE_CHAPTERS:
        resources.append(types.Resource(
            uri=cast(Any, f"whitemagic://grimoire/chapter/{num}"),
            name=f"Grimoire Ch.{num}: {title}",
            description=f"WhiteMagic Grimoire Chapter {num} with live system state.",
            mimeType="text/markdown",
        ))
    # Quadrant summaries
    for quad, qtitle in (("eastern", "Eastern — Spring/Wood"),
                          ("southern", "Southern — Summer/Fire"),
                          ("western", "Western — Autumn/Metal"),
                          ("northern", "Northern — Winter/Water")):
        resources.append(types.Resource(
            uri=cast(Any, f"whitemagic://grimoire/quadrant/{quad}"),
            name=f"Grimoire Quadrant: {qtitle}",
            description=f"Summary of the {quad} quadrant with live resonance data.",
            mimeType="text/markdown",
        ))
    # Current most-resonant chapter
    resources.append(types.Resource(
        uri=cast(Any, "whitemagic://grimoire/current"),
        name="Grimoire: Current Chapter",
        description="The Grimoire chapter most resonant with current system state.",
        mimeType="text/markdown",
    ))
    return resources


@server.read_resource()
async def read_resource(uri) -> str:
    """Read a resource by URI."""
    uri_str = str(uri)
    if "health" in uri_str:
        import json
        status = {
            "status": "healthy",
            "version": _VERSION,
            "initialized": _INITIALISED,
            "server": "WhiteMagic Core",
        }
        return json.dumps(status, indent=2)
    if "prologue" in uri_str:
        path = ROOT_DIR / "grimoire" / "00_PROLOGUE.md"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"# Unavailable\n\nerror: {exc}"
    if "ai-primary" in uri_str:
        path = REPO_ROOT / "AI_PRIMARY.md"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"# Unavailable\n\nerror: {exc}"
    if "server-instructions" in uri_str:
        return _INSTRUCTIONS
    if "system-map" in uri_str:
        path = REPO_ROOT / "SYSTEM_MAP.md"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"# Unavailable\n\nerror: {exc}"
    # v14.1.1: Workflow templates
    if "workflow/" in uri_str:
        wf_name = uri_str.split("workflow/")[-1].strip("/")
        wf_path = _WORKFLOW_DIR / f"{wf_name}.md"
        try:
            return wf_path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"# Workflow not found: {wf_name}\n\nerror: {exc}"
    # v22.2: Grimoire resources with live state interpolation
    if "grimoire/" in uri_str:
        return _read_grimoire_resource(uri_str)
    return f"# Unknown resource: {uri}"


def _read_grimoire_resource(uri_str: str) -> str:
    """Read a Grimoire resource with live system state interpolated."""
    import json
    from datetime import datetime

    # Collect live state (best-effort)
    live_state = {"timestamp": datetime.now().isoformat()}
    try:
        from whitemagic.harmony.vector import get_harmony_vector
        hv = get_harmony_vector()
        snap = hv.snapshot()
        live_state["harmony_score"] = round(snap.harmony_score, 3)
        live_state["guna"] = {
            "sattvic": round(snap.guna_sattvic_pct, 2),
            "rajasic": round(snap.guna_rajasic_pct, 2),
            "tamasic": round(snap.guna_tamasic_pct, 2),
        }
    except Exception as e:
        logger.debug(f"Harmony vector snapshot failed: {e}")
    try:
        from whitemagic.core.monitoring.neurotransmitter_vector import (
            get_neurotransmitter_vector,
        )
        nt = get_neurotransmitter_vector()
        nt_snap = nt.snapshot()
        live_state["neurotransmitters"] = {
            "dominant": nt_snap.dominant,
            "cortisol": nt_snap.cortisol,
            "dopamine": nt_snap.dopamine,
        }
    except Exception as e:
        logger.debug(f"Neurotransmitter snapshot failed: {e}")
    try:
        from whitemagic.core.dreaming.dream_cycle import get_dream_cycle
        dc = get_dream_cycle()
        live_state["dream_phase"] = dc.status().get("phase", "unknown")
    except Exception as e:
        logger.debug(f"Dream cycle status failed: {e}")

    # Build frontmatter
    frontmatter = "---\n" + json.dumps(live_state, indent=2) + "\n---\n\n"

    if "grimoire/chapter/" in uri_str:
        chapter_num = uri_str.split("chapter/")[-1].strip("/")
        # Map chapter number to filename
        _CHAPTER_FILES = {
            "01": "01_HORN_SESSION_INITIATION.md",
            "02": "02_NECK_MEMORY_PRESENCE.md",
            "03": "03_ROOT_SYSTEM_FOUNDATION.md",
            "04": "04_ROOM_RESOURCE_SANCTUARY.md",
            "05": "05_HEART_CONTEXT_CONNECTION.md",
            "06": "06_TAIL_PERFORMANCE_DRIVE.md",
            "07": "07_WINNOWINGBASKET_CONSOLIDATION.md",
            "08": "08_GHOST_METRICS_INTROSPECTION.md",
            "09": "09_WILLOW_ADAPTIVE_PLAY.md",
            "10": "10_STAR_PRAT_ILLUMINATION.md",
            "11": "11_EXTENDEDNET_RESONANCE_NETWORK.md",
            "12": "12_WINGS_PARALLEL_CREATION.md",
            "13": "13_CHARIOT_CODEBASE_NAVIGATION.md",
            "14": "14_ABUNDANCE_RESOURCE_SHARING.md",
            "15": "15_STRADDLINGLEGS_ETHICAL_BALANCE.md",
            "16": "16_MOUND_STRATEGIC_PATIENCE.md",
            "17": "17_STOMACH_ENERGY_MANAGEMENT.md",
            "18": "18_HAIRYHEAD_DETAILED_ATTENTION.md",
            "19": "19_NET_PATTERN_CAPTURE.md",
            "20": "20_TURTLEBEAK_PRECISE_VALIDATION.md",
            "21": "21_THREESTARS_WISDOM_COUNCIL.md",
            "22": "22_DIPPER_GOVERNANCE.md",
            "23": "23_OX_ENDURANCE.md",
            "24": "24_GIRL_NURTURE.md",
            "25": "25_VOID_EMPTINESS.md",
            "26": "26_ROOF_SHELTER.md",
            "27": "27_ENCAMPMENT_STRUCTURE.md",
            "28": "28_WALL_BOUNDARIES.md",
        }
        fname = _CHAPTER_FILES.get(chapter_num)
        if fname:
            path = REPO_ROOT / "grimoire" / fname
            try:
                content = path.read_text(encoding="utf-8")
                return frontmatter + content
            except Exception as exc:
                return f"# Chapter unavailable\n\nerror: {exc}"
        return f"# Unknown chapter: {chapter_num}"

    if "grimoire/quadrant/" in uri_str:
        quadrant = uri_str.split("quadrant/")[-1].strip("/")
        _QUADRANT_DATA = {
            "eastern": {"chapters": "1-7", "element": "Wood", "season": "Spring", "theme": "Initiation, growth, foundation"},
            "southern": {"chapters": "8-14", "element": "Fire/Water/Earth", "season": "Summer", "theme": "Expansion, radiance, creation"},
            "western": {"chapters": "15-21", "element": "Metal/Earth/Fire", "season": "Autumn", "theme": "Refinement, judgment, precision"},
            "northern": {"chapters": "22-28", "element": "Fire/Earth/Water", "season": "Winter", "theme": "Depth, integration, completion"},
        }
        qdata = _QUADRANT_DATA.get(quadrant)
        if qdata:
            return frontmatter + f"""# {quadrant.title()} Quadrant

**Chapters**: {qdata['chapters']}
**Element**: {qdata['element']}
**Season**: {qdata['season']}
**Theme**: {qdata['theme']}

## Live Resonance
{json.dumps(live_state, indent=2)}
"""
        return f"# Unknown quadrant: {quadrant}"

    if "grimoire/current" in uri_str:
        # Pick chapter based on dominant guna
        try:
            from whitemagic.harmony.vector import get_harmony_vector
            hv = get_harmony_vector()
            snap = hv.snapshot()
            if snap.guna_rajasic_pct > 0.5:
                current_ch = "06_TAIL_PERFORMANCE_DRIVE.md"
            elif snap.guna_sattvic_pct > 0.5:
                current_ch = "08_GHOST_METRICS_INTROSPECTION.md"
            else:
                current_ch = "25_VOID_EMPTINESS.md"
            path = REPO_ROOT / "grimoire" / current_ch
            content = path.read_text(encoding="utf-8")
            return frontmatter + "# 🌟 Most Resonant Chapter Right Now\n\n" + content
        except Exception as exc:
            return f"# Current chapter unavailable\n\nerror: {exc}"

    return "# Unknown Grimoire resource"


# ══════════════════════════════════════════════════════════════════════
# Entry points — stdio (default) or HTTP
# ══════════════════════════════════════════════════════════════════════

async def main_stdio() -> None:
    """Run as stdio MCP server (default, for IDE integration)."""
    import anyio
    import signal
    from mcp.shared.message import SessionMessage

    from whitemagic.runtime_status import get_runtime_status

    runtime_status = get_runtime_status()
    if not runtime_status.get("silent_init"):
        suffix = " [DEGRADED]" if runtime_status.get("degraded_mode") else ""
        print(f"\n  WhiteMagic MCP Server v{_VERSION}{suffix}", file=sys.stderr)
        print(f"  Mode: {runtime_status.get('mode')} | 28 Gana tools", file=sys.stderr)
        if runtime_status.get("degraded_reasons"):
            reasons = ", ".join(runtime_status["degraded_reasons"])
            print(f"  Degraded reasons: {reasons}", file=sys.stderr)
        print("", file=sys.stderr)

    # Bridge 3 (Microkernel Mandala): register hot-loadable subsystems
    try:
        from whitemagic.core.plugin.grimoire_plugin import register_grimoire_plugin
        register_grimoire_plugin()
    except (ImportError, ModuleNotFoundError):
        pass  # Plugin system is optional; never block MCP startup

    read_stream_writer, read_stream = anyio.create_memory_object_stream[SessionMessage | Exception](0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream[SessionMessage](0)

    # Graceful shutdown mechanism
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        sig_name = signal.Signals(signum).name
        logger.warning(f"Received {sig_name}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    async def stdin_reader() -> None:
        """Read newline-delimited JSON-RPC from stdin and forward to MCP stream."""
        async with read_stream_writer:
            while not shutdown_event.is_set():
                try:
                    raw = await asyncio.to_thread(sys.stdin.buffer.readline)
                    if not raw:
                        logger.info("stdin closed, shutting down")
                        shutdown_event.set()
                        break
                    line = raw.decode("utf-8")
                    message = types.JSONRPCMessage.model_validate_json(line)
                    await read_stream_writer.send(SessionMessage(message))
                except Exception as exc:
                    if not shutdown_event.is_set():
                        logger.error(f"stdin_reader error: {exc}")
                        await read_stream_writer.send(exc)
                    continue

    async def stdout_writer() -> None:
        """Write MCP session messages as newline-delimited JSON-RPC to stdout."""
        async with write_stream_reader:
            async for session_message in write_stream_reader:
                if shutdown_event.is_set():
                    break
                try:
                    payload = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                    sys.stdout.write(payload + "\n")
                    sys.stdout.flush()
                except Exception as exc:
                    logger.error("stdout_writer error: %s", exc, exc_info=True)
                    if shutdown_event.is_set():
                        break

    async def shutdown_watcher() -> None:
        """Monitor shutdown event and cancel tasks when triggered."""
        await shutdown_event.wait()
        logger.info("Shutdown event triggered, closing streams...")
        # Close streams to unblock any pending reads/writes
        try:
            await read_stream_writer.aclose()
        except Exception as e:
            logger.debug(f"Shutdown: read_stream_writer.aclose() raised: {e}")
        try:
            await write_stream.aclose()
        except Exception as e:
            logger.debug(f"Shutdown: write_stream.aclose() raised: {e}")
        # Cancel the main server task to force exit
        current_task = asyncio.current_task()
        for task in asyncio.all_tasks():
            if task != current_task and task not in (stdin_task, stdout_task, shutdown_task):
                task.cancel()

    stdin_task = asyncio.create_task(stdin_reader())
    stdout_task = asyncio.create_task(stdout_writer())
    shutdown_task = asyncio.create_task(shutdown_watcher())

    try:
        # Run server - it will exit when stdin closes or on error
        await server.run(read_stream, write_stream, server.create_initialization_options())
    except asyncio.CancelledError:
        logger.info("Server task cancelled during shutdown")
    except Exception as exc:
        logger.error("Server run error: %s", exc, exc_info=True)
        raise
    finally:
        logger.info("Cleaning up MCP server tasks...")
        shutdown_event.set()
        stdin_task.cancel()
        stdout_task.cancel()
        shutdown_task.cancel()
        # Give tasks a moment to clean up
        await asyncio.gather(
            stdin_task, stdout_task, shutdown_task,
            return_exceptions=True
        )
        logger.info("MCP server shutdown complete")


async def main_http(host: str = "127.0.0.1", port: int = 8770) -> None:
    """Run as Streamable HTTP MCP server (for remote/browser access)."""
    import uuid

    import uvicorn
    from mcp.server.streamable_http import StreamableHTTPServerTransport
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from starlette.routing import Mount

    transport = StreamableHTTPServerTransport(
        mcp_session_id=str(uuid.uuid4()),
        is_json_response_enabled=True,
    )

    import os

    # F-12: Restrict CORS to localhost by default (configurable via WM_MCP_CORS_ORIGINS)
    _cors_env = os.environ.get("WM_MCP_CORS_ORIGINS", "")
    if _cors_env.strip():
        _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
    else:
        _cors_origins = [
            f"http://localhost:{port}",
            f"http://127.0.0.1:{port}",
            "http://localhost",
            "http://127.0.0.1",
        ]

    app = Starlette(
        routes=[Mount("/mcp", app=transport.handle_request)],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=_cors_origins,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "Mcp-Session-Id", "Authorization"],
                allow_credentials=True,
            )
        ],
    )

    from whitemagic.runtime_status import get_runtime_status

    runtime_status = get_runtime_status()
    logger.warning(f"WhiteMagic MCP HTTP server starting on http://{host}:{port}/mcp")
    suffix = " [DEGRADED]" if runtime_status.get("degraded_mode") else ""
    print(f"\n  WhiteMagic MCP Server v{_VERSION}{suffix}", file=sys.stderr)
    print(f"  HTTP endpoint: http://{host}:{port}/mcp", file=sys.stderr)
    print(f"  Mode: {runtime_status.get('mode')} | 28 Gana tools", file=sys.stderr)
    if runtime_status.get("degraded_reasons"):
        reasons = ", ".join(runtime_status["degraded_reasons"])
        print(f"  Degraded reasons: {reasons}", file=sys.stderr)
    print("", file=sys.stderr)

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    uv_server = uvicorn.Server(config)

    async with transport.connect() as (read_stream, write_stream):
        await asyncio.gather(
            server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            ),
            uv_server.serve(),
        )


def main() -> None:
    """CLI entry point with --http flag support."""
    if "--http" in sys.argv:
        host = "127.0.0.1"
        port = 8770
        for i, arg in enumerate(sys.argv):
            if arg == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        asyncio.run(main_http(host, port))
    else:
        asyncio.run(main_stdio())


if __name__ == "__main__":
    main()
