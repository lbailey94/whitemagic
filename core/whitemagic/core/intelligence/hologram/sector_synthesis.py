# ruff: noqa: BLE001, F401
"""
SectorSynthesizer - Hierarchical Knowledge Abstraction
======================================================

Synthesizes clusters of 4D memories into high-level "Sector Principles"
using the LLM Bridge and 4D spatial context.
"""

import json
import logging
import sqlite3
from whitemagic.core.memory.db_manager import safe_connect
from dataclasses import dataclass
from pathlib import Path

from whitemagic.config.paths import WM_ROOT

try:
    from ...llm_bridge import LLMBridge
except ImportError:
    LLMBridge = None
from .consolidation import MemoryCluster

logger = logging.getLogger(__name__)


@dataclass
class SectorPrinciple:
    """A high-level abstraction derived from a memory cluster."""

    title: str
    summary: str
    principles: list[str]
    quadrant: str
    centroid: tuple[float, float, float, float]
    source_ids: list[str]


class SectorSynthesizer:
    """Bridges 4D clusters with LLM synthesis for hierarchical intelligence."""

    def __init__(self, llm_bridge=None, db_path: Path | None = None):
        self.bridge = llm_bridge
        self.db_path = db_path or WM_ROOT / "memory" / "whitemagic.db"

    def _determine_style(self, center: tuple[float, float, float, float]) -> str:
        """Determine synthesis style based on 4D coordinates."""
        x, y, z, w = center
        style = []

        # X-Axis: Logic vs Emotion
        if x < -0.3:
            style.append("strictly logical and algorithmic")
        elif x > 0.3:
            style.append("intuitive and emotionally resonant")
        else:
            style.append("balanced and objective")

        # Y-Axis: Micro vs Macro
        if y < -0.3:
            style.append("highly detailed and technical")
        elif y > 0.3:
            style.append("abstract and strategic")
        else:
            style.append("mid-level and operational")

        return " and ".join(style)

    def _get_quadrant_name(self, center: tuple[float, float, float, float]) -> str:
        x, y, _, _ = center
        x_name = "logical" if x < 0 else "emotional"
        y_name = "detail" if y < 0 else "strategic"
        return f"{y_name}_{x_name}"

    def _fetch_contents(self, memory_ids: list[str]) -> str:
        """Fetch full content for cluster members from SQLite."""
        if not memory_ids:
            return ""

        try:
            conn = safe_connect(self.db_path)
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" * len(memory_ids))
            rows = conn.execute(
                f"SELECT title, content FROM memories WHERE id IN ({placeholders})",
                memory_ids,
            ).fetchall()

            parts = []
            for row in rows:
                parts.append(f"Title: {row['title']}\nContent: {row['content']}")

            conn.close()
            return "\n---\n".join(parts)
        except Exception as e:
            logger.error("Content fetch failed: %s", e)
            return ""

    def _cpu_fallback(self, cluster: MemoryCluster) -> SectorPrinciple:
        """Rule-based fallback if no LLM is available."""
        return SectorPrinciple(
            title=f"Macro-Cluster: {cluster.titles[0]}",
            summary=f"Aggregation of {len(cluster.memory_ids)} nodes in the {self._get_quadrant_name(cluster.center)} sector.",
            principles=[
                f"Consolidate {len(cluster.memory_ids)} related items",
                "Monitor density flux",
            ],
            quadrant=self._get_quadrant_name(cluster.center),
            centroid=cluster.center,
            source_ids=cluster.memory_ids,
        )

    def _parse_response(self, response: str, cluster: MemoryCluster) -> SectorPrinciple:
        """Parse structured LLM response into SectorPrinciple."""
        try:
            # Extract JSON from potential markdown blocks
            clean_response = response
            if "```json" in response:
                clean_response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                clean_response = response.split("```")[1].split("```")[0]

            data = json.loads(clean_response)

            return SectorPrinciple(
                title=data.get("title", cluster.titles[0]),
                summary=data.get("summary", "Synthesized macro-view."),
                principles=data.get("principles", []),
                quadrant=self._get_quadrant_name(cluster.center),
                centroid=cluster.center,
                source_ids=cluster.memory_ids,
            )
        except Exception as e:
            logger.error("Response parsing failed: %s", e)
            return self._cpu_fallback(cluster)

    async def synthesize_cluster(self, cluster: MemoryCluster) -> SectorPrinciple:
        """Synthesize a cluster into a Sector Principle."""
        style = self._determine_style(cluster.center)
        quadrant = self._get_quadrant_name(cluster.center)

        contents = self._fetch_contents(cluster.memory_ids)

        prompt = f"""
        Analyze the following cluster of {len(cluster.memory_ids)} related memories in the '{quadrant}' sector.
        Synthesize them into a high-level "Sector Principle" using a {style} tone.

        ## Cluster Context
        4D Center: {cluster.center}
        Quadrant: {quadrant}
        Initial Themes: {", ".join(cluster.titles[:5])}

        ## Memory Contents
        {contents}

        ## Output Format (JSON)
        {{
            "title": "Clear, evocative title for this knowledge sector",
            "summary": "2-sentence macro-view of what this cluster represents",
            "principles": ["Core lesson 1", "Core lesson 2", "Core lesson 3"]
        }}
        """

        if not self.bridge:
            return self._cpu_fallback(cluster)

        try:
            # LLMBridge.chat is sync
            response = self.bridge.chat(prompt, context_k=0, remember=False)
            return self._parse_response(response, cluster)
        except Exception as e:
            logger.error("LLM synthesis failed: %s", e)
            return self._cpu_fallback(cluster)
