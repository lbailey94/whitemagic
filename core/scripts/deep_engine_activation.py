#!/usr/bin/env python3
"""
WhiteMagic Deep Engine Activation
Activates Kaizen and Emergence engines to discover new self-improvement paths.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Whitemagic imports
from whitemagic.core.intelligence.synthesis.kaizen_engine import get_kaizen_engine
from whitemagic.core.intelligence.agentic.emergence_engine import get_emergence_engine
from whitemagic.dharma.rules import get_rules_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeepEngineActivation")


def run_activation():
    logger.debug("\n" + "=" * 60)
    logger.debug("DEEP ENGINE ACTIVATION: RECURSIVE ANALYSIS")
    logger.debug("=" * 60)

    # Ensure Dharma is in creative mode
    get_rules_engine().set_profile("creative")
    logger.debug("Dharma Profile: CREATIVE (Relaxed Restrictions)")

    # 1. Kaizen Engine
    logger.debug("\n[1/2] Activating Kaizen Engine (Quality & Gaps)...")
    kaizen = get_kaizen_engine()
    report = kaizen.analyze()

    logger.debug(f"  Found {len(report.proposals)} improvement proposals.")
    for cat, props in report.by_category.items():
        logger.debug(f"    - {cat.upper()}: {len(props)} proposals")
        for p in props[:2]:
            logger.debug(f"      * {p.title} (Impact: {p.impact})")

    # 2. Emergence Engine
    logger.debug("\n[2/2] Activating Emergence Engine (Insight Synthesis)...")
    emergence = get_emergence_engine()
    # Emergence engine usually needs to listen to the bus,
    # but we can trigger a proactive scan (v14 feature).
    insights = emergence.scan_for_emergence()

    logger.debug(f"  Found {len(insights)} emergent insights.")
    for insight in insights:
        logger.debug(f"    * ✨ {insight.title} (Confidence: {insight.confidence:.2f})")
        logger.debug(f"      {insight.description[:100]}...")

    # 3. Generate Synthesis Report
    output_md = REPO_ROOT / "scripts/archaeology_results/EVOLUTION_REPORT_v2.md"
    with open(output_md, "w") as f:
        f.write("# 🌀 WhiteMagic Evolution Report v2\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 改善 (Kaizen) Proposals\n")
        for p in report.proposals:
            f.write(f"- **[{p.category.upper()}]** {p.title}\n")
            f.write(f"  - Impact: {p.impact} | Auto-fixable: {p.auto_fixable}\n")
            f.write(f"  - {p.description}\n\n")

        f.write("## ✨ Emergent Insights\n")
        for insight in insights:
            f.write(f"### {insight.title}\n")
            f.write(f"- Source: {insight.source}\n")
            f.write(f"- Confidence: {insight.confidence:.2f}\n")
            f.write(f"- {insight.description}\n\n")

    logger.debug(f"\n✅ Evolution report saved to: {output_md}")


if __name__ == "__main__":
    run_activation()
