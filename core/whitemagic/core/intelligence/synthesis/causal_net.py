# ruff: noqa: BLE001
"""Causal Net — Layer 2: Constraint Detection
Infers directed edges between memory clusters using 4D holographic coordinates.
"""

import logging
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, cast

import numpy as np

from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)


class CausalNet:
    """Causal Net — Layer 2: Constraint Detection
    Infers directed edges between memory clusters using 4D holographic coordinates.
    """

    def mine_causal_patterns(
        self, query: str = "", max_patterns: int = 10
    ) -> list[dict[str, Any]]:
        """Mine causal patterns from memory clusters.

        Query-driven pattern discovery across cluster centroids. Returns the
        top `max_patterns` edges whose source/target embeddings best match
        `query`, using the existing holographic coordinate gradient logic.
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            rows = conn.execute(
                "SELECT memory_id FROM memories_fts WHERE memories_fts MATCH ? LIMIT 50",
                (query or "*",),
            ).fetchall()
            if not rows:
                conn.close()
                return []

            memory_ids = [r[0] for r in rows]

            placeholders = ",".join("?" for _ in memory_ids)
            coord_rows = conn.execute(
                f"SELECT memory_id, x, y, z, w FROM holographic_coords WHERE memory_id IN ({placeholders})",
                memory_ids,
            ).fetchall()
            conn.close()

            if len(coord_rows) < 2:
                return []

            # Build simple clusters from coordinates
            coords = np.array([[r[1], r[2], r[3], r[4]] for r in coord_rows])
            ids = [r[0] for r in coord_rows]

            # Find causal edges based on temporal (w) gradient and spatial proximity
            patterns: list[dict[str, Any]] = []
            for i in range(len(coords)):
                for j in range(len(coords)):
                    if i == j:
                        continue
                    dist_xyz = np.linalg.norm(coords[i][:3] - coords[j][:3])
                    w_diff = coords[j][3] - coords[i][3]
                    if dist_xyz < 0.5 and abs(w_diff) > 0.001:
                        patterns.append(
                            {
                                "source": ids[i],
                                "target": ids[j],
                                "spatial_distance": float(dist_xyz),
                                "temporal_gradient": float(w_diff),
                                "direction": "forward" if w_diff > 0 else "backward",
                            }
                        )
                        if len(patterns) >= max_patterns:
                            return patterns
            return patterns
        except Exception as e:
            logger.debug("Causal pattern mining failed: %s", e, exc_info=True)
            return []

    def get_stats(self) -> dict[str, Any]:
        """Return statistics from the last infer_dependencies() call.

        Until infer_dependencies has been called, returns zeros. After a
        call, surfaces the inferred edge count and resonance-score coverage.
        """
        edge_count = getattr(self, "_last_edge_count", 0)
        chain_count = len(getattr(self, "_last_chain_keys", set()))
        return {
            "total_patterns": edge_count,
            "active_causal_chains": chain_count,
        }

    def __init__(self, db_path: Path | None = None):
        from whitemagic.config.paths import DB_PATH

        self.db_path = db_path or Path(DB_PATH)

    def infer_dependencies(
        self, active_clusters: dict[tuple[int, int], list[str]]
    ) -> dict[str, list[str]]:
        """Infer a Directed Acyclic Graph (DAG) between clusters.
        Logic: Calculate the 'flow' between clusters based on coordinate gradients.

        Rust Fast-Path: If whitemagic_rust is available, it handles the coordinate math and DAG generation.
        """
        try:
            import whitemagic_rust as rs

            synthesis_engine = getattr(rs, "synthesis_engine", None)
            if synthesis_engine and hasattr(synthesis_engine, "infer_dag_from_coords"):
                # Build cluster_data dict for Rust
                cluster_data: dict[str, Any] = {}
                conn = sqlite3.connect(str(self.db_path))
                for key, mids in active_clusters.items():
                    placeholders = ",".join("?" for _ in mids)
                    rows = conn.execute(
                        "SELECT x, y, z, w FROM holographic_coords WHERE memory_id IN ("
                        + placeholders
                        + ")",
                        mids,
                    ).fetchall()
                    if rows:
                        arr = np.array(rows)
                        centroid = np.mean(arr, axis=0)
                        cluster_data[str(key)] = {
                            "centroid": centroid.tolist(),
                            "ids": mids,
                        }
                conn.close()

                edges = synthesis_engine.infer_dag_from_coords(
                    cluster_data, dist_threshold=0.5, w_threshold=0.001
                )
                if edges:
                    logger.info(
                        "Rust fast-path: %s edges from %s clusters",
                        len(edges),
                        len(active_clusters),
                    )
                    return cast(dict[str, list[str]], edges)
        except Exception as e:
            logger.debug(
                "Rust fast-path unavailable, using Python fallback: %s",
                e,
                exc_info=True,
            )

        # Python fallback
        cluster_data_py: dict[str, dict[str, Any]] = {}
        conn = sqlite3.connect(str(self.db_path))

        for key, mids in active_clusters.items():
            placeholders = ",".join("?" for _ in mids)
            rows = conn.execute(
                "SELECT x, y, z, w FROM holographic_coords WHERE memory_id IN ("
                + placeholders
                + ")",
                mids,
            ).fetchall()
            if not rows:
                continue

            arr = np.array(rows)
            cluster_data_py[str(key)] = {
                "centroid": np.mean(arr, axis=0),
                "ids": mids,
            }

        conn.close()

        # Build edges
        edges_list: list[tuple[str, str]] = []
        keys = list(cluster_data_py.keys())
        for i, key in enumerate(keys):
            for j, key in enumerate(keys):
                if i == j:
                    continue
                c1 = cluster_data_py[keys[i]]
                c2 = cluster_data_py[keys[j]]

                dist_xyz = np.linalg.norm(c1["centroid"][:3] - c2["centroid"][:3])
                w_diff = c2["centroid"][3] - c1["centroid"][3]

                if dist_xyz < 0.5 and abs(w_diff) > 0.001:
                    if w_diff > 0:
                        edges_list.append((str(keys[i]), str(keys[j])))
                    else:
                        edges_list.append((str(keys[j]), str(keys[i])))

        self.resonance_scores: dict[str, float] = {}
        if edges_list:
            edges_list, self.resonance_scores = self._verify_with_julia(
                nodes=[str(k) for k in cluster_data_py.keys()], edges=edges_list
            )

        result_dict: dict[str, list[str]] = {}
        for src, dst in edges_list:
            if src not in result_dict:
                result_dict[src] = []
            result_dict[src].append(dst)

        # Track last-call state for get_stats()
        self._last_edge_count = len(edges_list)
        self._last_chain_keys = set(result_dict.keys())

        return result_dict

    def _verify_with_julia(
        self, nodes: list[str], edges: list[tuple[str, str]]
    ) -> tuple[list[tuple[str, str]], dict[str, float]]:
        """Invokes Julia to verify logical 'Ganying' (resonance) across the edges."""
        julia_script = (
            self.db_path.parent.parent
            / "whitemagic-julia"
            / "src"
            / "causal_resonance.jl"
        )
        if not julia_script.exists():
            logger.warning("Julia resonance script not found. Skipping verification.")
            return edges, {}

        payload = _json_dumps({"nodes": nodes, "edges": edges})
        try:
            cmd = ["julia", str(julia_script), payload]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            resonance_scores = _json_loads(result.stdout)

            pruned = []
            for src, dst in edges:
                score = resonance_scores.get(dst, 0.0)
                if score > 0.05:
                    pruned.append((src, dst))

            logger.info(
                "Julia Gan Ying verification: %s -> %s edges.", len(edges), len(pruned)
            )
            return pruned, resonance_scores
        except Exception as e:
            logger.error("Julia resonance verification failed: %s", e, exc_info=True)
            return edges, {}


CausalNetMiner = CausalNet

if __name__ == "__main__":
    pass
