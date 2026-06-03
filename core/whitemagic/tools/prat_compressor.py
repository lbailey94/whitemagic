"""PRAT Compressor — Symbolic token reduction for tool dispatch.
===============================================================
Implements a scoped Tool DSL that maps verbose tool/arg names to compact
codes.  Inspired by GlyphCompress's codebook pattern, but scoped to
WhiteMagic's 28-Gana PRAT layer only.

Toggle: ``WM_VECTORIZED=1`` enables compression on the wire.

Compression model:
  - Gana names → 1-character lunar-mansion glyphs (角亢氐房…)
  - Nested tool names → 2-letter camelCase codes
  - Common arg names → 1-letter codes
  - The codebook is a static Python dict (no ML, no inference)

Typical savings:
  - ``gana_winnowing_basket(tool="search_memories", args={"query":"x","limit":5})``
  - → ``{"箕":{"槍":"sm","a":{"q":"x","n":5}}}``  (saves ~40 tokens)

This is intentionally simple.  If compression < 60% or debug time > 2×,
fallback to raw JSON (the decision gate from the research doc).
"""

from __future__ import annotations

import json
import os
from typing import Any

# ── Codebook ────────────────────────────────────────────────────────────

# Gana → single lunar-mansion character (Unicode from run_mcp_lean.py icons)
_GANA_CODES: dict[str, str] = {
    "gana_horn": "角",
    "gana_neck": "亢",
    "gana_root": "氐",
    "gana_room": "房",
    "gana_heart": "心",
    "gana_tail": "尾",
    "gana_winnowing_basket": "箕",
    "gana_ghost": "鬼",
    "gana_willow": "柳",
    "gana_star": "星",
    "gana_extended_net": "张",
    "gana_wings": "翼",
    "gana_chariot": "轸",
    "gana_abundance": "豐",
    "gana_straddling_legs": "奎",
    "gana_mound": "娄",
    "gana_stomach": "胃",
    "gana_hairy_head": "昴",
    "gana_net": "毕",
    "gana_turtle_beak": "觜",
    "gana_three_stars": "参",
    "gana_dipper": "斗",
    "gana_ox": "牛",
    "gana_girl": "女",
    "gana_void": "虚",
    "gana_roof": "危",
    "gana_encampment": "室",
    "gana_wall": "壁",
}

# Reverse lookup
_GANA_CODES_REV: dict[str, str] = {v: k for k, v in _GANA_CODES.items()}

# Nested tool names → 2-letter codes (most frequent tools only; unknowns pass through)
_TOOL_CODES: dict[str, str] = {
    # Winnowing Basket (memory)
    "search_memories": "sm",
    "create_memory": "cm",
    "update_memory": "um",
    "delete_memory": "dm",
    "read_memory": "rm",
    "memory_read": "mr",
    "memory_search": "ms",
    "memory_update": "mu",
    "memory_delete": "md",
    "hybrid_recall": "hr",
    "list_memories": "lm",
    # Ghost (introspection)
    "gnosis": "gn",
    "capabilities": "cp",
    "manifest": "mf",
    "health_report": "hr",  # overlap ok, different gana
    "get_telemetry_summary": "ts",
    # Neck (memory presence)
    "remember": "re",
    "recall": "rc",
    # Star (PRAT)
    "grimoire_cast": "gc",
    "grimoire_list": "gl",
    # Straddling Legs (ethics)
    "evaluate_ethics": "ee",
    "harmony_vector": "hv",
    "check_boundaries": "cb",
    # Willow (resilience)
    "cast_oracle": "co",
    # Tail (performance)
    "simd_infer": "si",
    "simd_batch": "sb",
    # Three Stars (wisdom)
    "ensemble": "en",
    "kaizen_analyze": "ka",
    # Room (security)
    "hermit_status": "hs",
    # Heart (context)
    "scratchpad": "sp",
    "context_pack": "cx",
    # Wall (boundaries)
    "vote_create": "vc",
    # Ox (endurance)
    "swarm_decompose": "sd",
    # Root (health)
    "ship_check": "sh",
}

_TOOL_CODES_REV: dict[str, str] = {v: k for k, v in _TOOL_CODES.items()}

# Common arg names → 1-letter codes
_ARG_CODES: dict[str, str] = {
    "query": "q",
    "limit": "n",
    "tags": "t",
    "title": "T",
    "content": "c",
    "memory_type": "m",
    "importance": "i",
    "tool": "槍",  # "spear" — the tool-within-gana selector
    "args": "a",
    "operation": "o",
    "context": "x",
    "memory_id": "id",
    "threshold": "th",
    "min_importance": "mi",
    "semantic_weight": "sw",
    "lexical_weight": "lw",
    "spatial_weight": "pw",
    "include_cold": "ic",
    "hops": "h",
    "anchor_limit": "al",
    "final_limit": "fl",
    "compact": "k",
    "format": "f",
    "type": "tp",
    "status": "s",
}

_ARG_CODES_REV: dict[str, str] = {v: k for k, v in _ARG_CODES.items()}


# ── Engine ────────────────────────────────────────────────────────────────

class PratCompressor:
    """Bi-directional PRAT tool-call compressor.

    Compression levels (future):
      - ``0`` = off (passthrough)
      - ``1`` = alias only (gana/tool/arg names)
      - ``2`` = alias + MessagePack binary
    """

    def __init__(self, level: int = 1) -> None:
        self.level = level
        self._gana = _GANA_CODES
        self._gana_rev = _GANA_CODES_REV
        self._tool = _TOOL_CODES
        self._tool_rev = _TOOL_CODES_REV
        self._arg = _ARG_CODES
        self._arg_rev = _ARG_CODES_REV

    # ── Public API ──────────────────────────────────────────────────────

    def compress(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Compress a PRAT tool-call or response dict.

        Returns a new dict with codes substituted.  Unknown keys pass
        through unchanged so the payload remains decodable.
        """
        if self.level == 0:
            return payload
        return self._compress_value(payload)

    def decompress(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Reverse ``compress()``."""
        if self.level == 0:
            return payload
        return self._decompress_value(payload)

    def stats(self, original: dict[str, Any], compressed: dict[str, Any]) -> dict[str, Any]:
        """Return token-savings estimate for the payload pair."""
        orig_json = json.dumps(original, ensure_ascii=False, default=str)
        comp_json = json.dumps(compressed, ensure_ascii=False, default=str)
        orig_len = len(orig_json)
        comp_len = len(comp_json)
        saved = max(0, orig_len - comp_len)
        ratio = orig_len / comp_len if comp_len > 0 else 1.0
        return {
            "original_chars": orig_len,
            "compressed_chars": comp_len,
            "chars_saved": saved,
            "ratio": round(ratio, 2),
            "estimated_tokens_saved": saved // 4,
        }

    # ── Internals ───────────────────────────────────────────────────────

    def _compress_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                ck = self._arg.get(k, k)
                # Special-case the "tool" field when it holds a nested tool name
                if k == "tool" and isinstance(v, str):
                    cv = self._tool.get(v, v)
                else:
                    cv = self._compress_value(v)
                out[ck] = cv
            return out
        if isinstance(value, list):
            return [self._compress_value(item) for item in value]
        return value

    def _decompress_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                dk = self._arg_rev.get(k, k)
                # Reverse the tool-name alias
                if k == "槍" and isinstance(v, str):
                    dv = self._tool_rev.get(v, v)
                else:
                    dv = self._decompress_value(v)
                out[dk] = dv
            return out
        if isinstance(value, list):
            return [self._decompress_value(item) for item in value]
        return value

    # Convenience for run_mcp_lean.py
    def compress_gana_call(
        self,
        gana: str,
        tool_name: str | None,
        tool_args: dict[str, Any],
        operation: str | None,
    ) -> tuple[str, str | None, dict[str, Any], str | None]:
        """Compress the 4-tuple used by ``_sync_dispatch``."""
        if self.level == 0:
            return gana, tool_name, tool_args, operation
        cg = self._gana.get(gana, gana)
        ct = self._tool.get(tool_name, tool_name) if tool_name else None
        ca = self._compress_value(tool_args)
        co = self._arg.get(operation, operation) if operation else None
        return cg, ct, ca, co

    def decompress_gana_call(
        self,
        gana_code: str,
        tool_code: str | None,
        args_compressed: dict[str, Any],
        operation_code: str | None,
    ) -> tuple[str, str | None, dict[str, Any], str | None]:
        """Reverse ``compress_gana_call``."""
        if self.level == 0:
            return gana_code, tool_code, args_compressed, operation_code
        dg = self._gana_rev.get(gana_code, gana_code)
        dt = self._tool_rev.get(tool_code, tool_code) if tool_code else None
        da = self._decompress_value(args_compressed)
        do = self._arg_rev.get(operation_code, operation_code) if operation_code else None
        return dg, dt, da, do


# ── Singleton / convenience ─────────────────────────────────────────────

_compressor: PratCompressor | None = None


def get_prat_compressor() -> PratCompressor:
    """Return the global compressor (lazy-init, reads WM_VECTORIZED env)."""
    global _compressor
    if _compressor is None:
        level = 1 if os.environ.get("WM_VECTORIZED", "") in ("1", "true", "yes") else 0
        _compressor = PratCompressor(level=level)
    return _compressor


def is_vectorized() -> bool:
    """Check whether PRAT compression is enabled."""
    return os.environ.get("WM_VECTORIZED", "") in ("1", "true", "yes")
