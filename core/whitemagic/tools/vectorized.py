"""PRAT Vectorized Dispatcher — Symbolic compression for internal tool calls."""
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_TOOL_CODEBOOK: dict[str, str] = {
    "create_memory": "M+", "update_memory": "M~", "delete_memory": "M-",
    "search_memories": "M?", "search_query": "Mq", "read_memory": "Mr",
    "batch_read_memories": "MR", "fast_read_memory": "Mf",
    "hybrid_recall": "Mh", "graph_walk": "Mg", "list_memories": "Ml",
    "import_memories": "Mi", "vector.search": "Mv", "vector.index": "Mx",
    "vector.status": "Ms", "session_bootstrap": "Sb", "create_session": "Sc",
    "resume_session": "Sr", "checkpoint_session": "Sk", "scratchpad": "Hs",
    "session.handoff": "Hh", "context.pack": "Hp",
    "context.status": "Hq", "working_memory.attend": "Ha",
    "working_memory.context": "Hc", "working_memory.status": "Ht",
    "get_session_context": "Hg", "gnosis": "Gg", "capabilities": "Gc",
    "manifest": "Gm", "get_telemetry_summary": "Gt", "repo.summary": "Gr",
    "explain_this": "Ge", "selfmodel.forecast": "Gf", "selfmodel.alerts": "Ga",
    "graph_topology": "GT", "surprise_stats": "GS", "health_report": "Rh",
    "rust_status": "Rr", "ship.check": "Rs", "state.paths": "Rp",
    "state.summary": "RS", "kg.extract": "Ke", "kg.query": "Kq",
    "kg.top": "Kt", "kg.status": "Ks", "kg2.extract": "KE",
    "kg2.batch": "KB", "kg2.entity": "KX", "kg2.stats": "KS",
    "archaeology": "Ka", "pattern_search": "Xp", "cluster_stats": "Xc",
    "tool.graph": "Xg", "learning.patterns": "Xl", "learning.suggest": "Xs",
    "learning.status": "Xt", "governor_validate": "Vv", "governor_set_goal": "Vg",
    "governor_check_drift": "Vd", "dharma.reload": "VD",
    "set_dharma_profile": "Vp", "prat_invoke": "Vi", "prat_status": "Vs",
    "dream": "Dd", "memory.lifecycle": "Dl", "memory.retention_sweep": "Dr",
    "serendipity_surface": "Ds", "pulse.status": "Dp", "entity_resolve": "De",
    "view_hologram": "Oh", "track_metric": "Ot", "get_yin_yang_balance": "Oy",
    "record_yin_yang_activity": "OY", "green.report": "Og",
    "cache.status": "Oc", "cache.flush": "Of", "evaluate_ethics": "Ee",
    "check_boundaries": "Eb", "verify_consent": "Ec", "get_ethical_score": "Es",
    "get_dharma_guidance": "Ed", "harmony_vector": "Eh",
    "simd.cosine": "Tc", "simd.batch": "Tb", "simd.status": "Ts",
    "execute_cascade": "Tx", "watcher_add": "W+", "watcher_remove": "W-",
    "watcher_start": "W>", "watcher_stop": "W#", "watcher_status": "W?",
    "watcher_recent_events": "Wr", "watcher_stats": "Ws", "watcher_list": "Wl",
    "galaxy_backup": "Yb", "galaxy_restore": "Yr", "galaxy_status": "Ys",
    "galaxy_list": "Yl", "galaxy_switch": "Yw", "galaxy_ingest": "Yi",
    "galaxy_delete": "Yd", "export_memories": "Ye", "audit.export": "Ya",
    "mesh.connect": "Ym", "mesh.broadcast": "YB", "mesh.status": "YS",
    "grimoire_suggest": "Zs", "grimoire_cast": "Zc",
    "grimoire_recommend": "Zr", "grimoire_auto_status": "Za",
    "grimoire_walkthrough": "Zw", "navigate_grimoire": "Zn",
    "rate_limiter.stats": "Zt", "cast_oracle": "Zo",
    "forge.status": "Fs", "forge.reload": "Fr", "forge.validate": "Fv",
    "prompt.list": "Fp", "prompt.render": "FR", "prompt.reload": "FL",
}

# Build reverse mapping preserving FIRST occurrence for each glyph
# (some tools have aliases like "memory_search" -> "M?" and "search_memories" -> "M?")
_REVERSE_TOOL: dict[str, str] = {}
for k, v in _TOOL_CODEBOOK.items():
    if v not in _REVERSE_TOOL:
        _REVERSE_TOOL[v] = k

_ARG_KEY_CODEBOOK: dict[str, str] = {
    # ── Core memory ──
    "query": "q", "limit": "n", "memory_type": "t", "tags": "g",
    "importance": "i", "threshold": "h", "sort_by": "s", "order": "o",
    "content": "c", "title": "T", "id": "I", "tool": "p",
    "operation": "O", "context": "x", "mode": "m", "compact": "C",
    "dry_run": "D", "ground_in_memory": "G",
    # ── Extended memory ──
    "auto_embed": "e", "ids": "k", "include_metadata": "M",
    "include_embeddings": "E", "include_diagnostics": "N",
    "min_confidence": "F", "min_novelty": "J",
    # ── Session / context ──
    "phase": "P", "duration_min": "u",
    "horizon_days": "H", "topic": "B",
    # ── Introspection ──
    "depth": "v", "goal": "l", "domain": "r", "intent": "j",
    "question": "Q", "scenario": "S", "source": "R", "target": "V",
    # ── Format / meta ──
    "format": "f", "garden": "d", "name": "K", "tag": "U",
    "value": "W", "vectors": "X", "condition": "y",
}

_REVERSE_ARG_KEY = {v: k for k, v in _ARG_KEY_CODEBOOK.items()}

_VALUE_CODEBOOK: dict[str, str] = {
    # ── Memory types / enum ──
    "SHORT_TERM": "ST", "LONG_TERM": "LT", "EPISODIC": "EP",
    "SEMANTIC": "SM",
    # ── Sort / operation ──
    "importance": "imp", "created": "cre", "accessed": "acc",
    "desc": "D", "asc": "A",
    # ── CRUD / modes ──
    "search": "sr", "analyze": "an", "transform": "tr",
    "consolidate": "cs", "create": "cr", "read": "rd",
    "update": "up", "delete": "dl",
    # ── Status / result ──
    "success": "ok", "error": "er",
    # ── Domains / formats ──
    "memory": "mem", "dream": "dr", "governance": "gov",
    "ethics": "eth", "tool": "tl", "system": "sys",
    "json": "js", "REM": "R", "sweep": "sw",
    "docs": "dc", "winnowing_basket": "wb",
    "compress": "zip", "tool_dsl": "td",
}

_REVERSE_VALUE = {v: k for k, v in _VALUE_CODEBOOK.items()}


class VectorizedDispatcher:
    """Encode/decode tool calls using a pre-shared glyph codebook."""

    def __init__(self) -> None:
        self.stats = {"encoded": 0, "decoded": 0, "bytes_saved": 0}

    def encode(self, tool_name: str, args: dict[str, Any] | None = None) -> str:
        glyph = _TOOL_CODEBOOK.get(tool_name, tool_name)
        if not args:
            return glyph
        parts = []
        for k, v in sorted(args.items()):
            key_g = _ARG_KEY_CODEBOOK.get(k, k)
            val_s = self._encode_value(v)
            parts.append(f"{key_g}:{val_s}")
        return f"{glyph}[{','.join(parts)}]"

    def _encode_value(self, v: Any) -> str:
        if isinstance(v, bool):
            return "!t" if v else "!f"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, str):
            return _VALUE_CODEBOOK.get(v, v)
        if isinstance(v, list):
            # Flatten simple scalar lists with | for compactness
            if v and all(isinstance(i, (str, int, float, bool)) for i in v):
                return "|".join(self._encode_value(i) for i in v)
            # Nested or mixed lists / dicts -> JSON fallback
            return "!j" + json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        if isinstance(v, dict):
            return "!j" + json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        return str(v)

    def decode(self, glyph_str: str) -> tuple[str, dict[str, Any]]:
        if "[" in glyph_str and glyph_str.endswith("]"):
            tool_g, rest = glyph_str.split("[", 1)
            arg_block = rest[:-1]
        else:
            tool_g = glyph_str
            arg_block = ""
        tool_name = _REVERSE_TOOL.get(tool_g, tool_g)
        if not arg_block:
            return tool_name, {}
        args: dict[str, Any] = {}
        raw_parts = arg_block.split(",")
        i = 0
        while i < len(raw_parts):
            part = raw_parts[i]
            if ":" not in part:
                i += 1
                continue
            key_g, val_g = part.split(":", 1)
            # JSON values may contain commas — re-join until valid if !j prefix
            if val_g.startswith("!j"):
                while True:
                    try:
                        json.loads(val_g[2:])
                        break
                    except json.JSONDecodeError:
                        if i + 1 >= len(raw_parts):
                            break
                        val_g += "," + raw_parts[i + 1]
                        i += 1
            key = _REVERSE_ARG_KEY.get(key_g, key_g)
            val = self._decode_value(val_g)
            args[key] = val
            i += 1
        return tool_name, args

    def _decode_value(self, v: str) -> Any:
        if v == "!t":
            return True
        if v == "!f":
            return False
        if v in _REVERSE_VALUE:
            return _REVERSE_VALUE[v]
        # JSON fallback for nested structures
        if v.startswith("!j"):
            return json.loads(v[2:])
        if "|" in v:
            return [self._decode_value(i) for i in v.split("|")]
        try:
            if "." in v:
                return float(v)
            return int(v)
        except ValueError:
            return v

    def measure(self, tool_name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        raw = json.dumps({"tool": tool_name, "args": args or {}}, separators=(",", ":"), sort_keys=True)
        encoded = self.encode(tool_name, args)
        raw_len = len(raw.encode())
        enc_len = len(encoded.encode())
        saved = max(0, raw_len - enc_len)
        ratio = saved / raw_len if raw_len > 0 else 0.0
        return {"raw_bytes": raw_len, "encoded_bytes": enc_len, "saved": saved, "ratio": round(ratio, 3), "encoded": encoded}


_vectorized: VectorizedDispatcher | None = None


def get_vectorized_dispatcher() -> VectorizedDispatcher:
    global _vectorized
    if _vectorized is None:
        _vectorized = VectorizedDispatcher()
    return _vectorized


def is_vectorized_mode() -> bool:
    return os.environ.get("WM_VECTORIZED", "").strip().lower() in ("1", "true", "yes")


def encode_call(tool_name: str, args: dict[str, Any] | None = None) -> str:
    return get_vectorized_dispatcher().encode(tool_name, args)


def decode_call(glyph_str: str) -> tuple[str, dict[str, Any]]:
    return get_vectorized_dispatcher().decode(glyph_str)
