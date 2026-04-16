#!/usr/bin/env python3
"""
The Great Work Pipeline Orchestrator
====================================
Orchestrates the Nigredo -> Albedo -> Rubedo stages to create the Holocron.

Usage:
    python3 whitemagic/alchemy/transmutation_pipeline.py
"""

import logging
import sqlite3
import sys
import time
from pathlib import Path

# Add project root to path if running directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from whitemagic.alchemy.albedo import AlbedoPurifier  # noqa: E402
from whitemagic.alchemy.holocron import Holocron  # noqa: E402
from whitemagic.alchemy.nigredo import NigredoClassifier  # noqa: E402
from whitemagic.alchemy.rubedo import RubedoSynthesizer  # noqa: E402
from whitemagic.config.paths import DB_PATH  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TransmutationPipeline:
    def __init__(self):
        self.classifier = NigredoClassifier()
        self.purifier = AlbedoPurifier()
        self.synthesizer = RubedoSynthesizer()
        self.holocron = Holocron()

    def run(self, limit: int = 10000):
        logger.info("=== The Great Work: Transmutation Sequence Initiated ===")
        start_time = time.time()

        # 1. Nigredo: Load and Classify
        logger.info("--- Stage 1: Nigredo (Decomposition) ---")
        if not DB_PATH.exists():
            logger.error(f"Database not found: {DB_PATH}")
            return

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Load active memories (LONG_TERM)
        cursor.execute("SELECT id, title, content FROM memories WHERE memory_type != 'quarantined' ORDER BY importance DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        logger.info(f"Loaded {len(rows)} active memories for transmutation.")

        novelty_memories = []
        routine_count = 0
        noise_count = 0

        for row in rows:
            content = row["content"] or ""
            title = row["title"] or ""
            category, score = self.classifier.classify(content, title)

            if category == "Novelty":
                novelty_memories.append({
                    "id": row["id"],
                    "title": title,
                    "content": content,
                    "score": score
                })
            elif category == "Routine":
                routine_count += 1
            else:
                noise_count += 1

        logger.info("Nigredo Yield:")
        logger.info(f"  Novelty (Gold): {len(novelty_memories)}")
        logger.info(f"  Routine (Body): {routine_count}")
        logger.info(f"  Noise (Dross):  {noise_count}")

        if not novelty_memories:
            logger.warning("No novelty found. Transmutation halted.")
            return

        # 2. Albedo: Vectorize and Cluster
        logger.info("--- Stage 2: Albedo (Purification) ---")
        vectorized = self.purifier.vectorize(novelty_memories)

        # Determine clusters based on count (aim for ~50 items per cluster)
        n_clusters = max(5, min(len(vectorized) // 50, 50))
        clusters = self.purifier.cluster(vectorized, n_clusters=n_clusters)
        logger.info(f"Purified into {len(clusters)} pattern clusters.")

        # 3. Rubedo: Synthesize Golden Rules
        logger.info("--- Stage 3: Rubedo (Synthesis) ---")
        golden_rules = self.synthesizer.synthesize(clusters)
        logger.info(f"Synthesized {len(golden_rules)} Golden Rules.")

        # 4. Save Holocron
        self.holocron.save(golden_rules)

        elapsed = time.time() - start_time
        logger.info(f"=== Transmutation Complete in {elapsed:.2f}s ===")
        logger.info(f"Philosopher's Stone created at {self.holocron.path}")

if __name__ == "__main__":
    pipeline = TransmutationPipeline()
    pipeline.run(limit=50000) # Process up to 50k memories
