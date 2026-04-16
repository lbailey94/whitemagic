#!/usr/bin/env python3
"""
WhiteMagic Recursive Improvement Driver
Orchestrates synthesis, dharma evaluation, and skill forging.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Whitemagic imports
from whitemagic.core.evolution.autodidactic_loop import AutodidacticLoop, PatternApplication, PatternOutcome
from whitemagic.core.intelligence.omni.skill_forge import get_skill_forge
from whitemagic.dharma import evaluate_ethics
from whitemagic.core.intelligence.omni.universal_router import ExecutionChain, GanaStep

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RecursiveDriver")

class RecursiveImprovementDriver:
    def __init__(self, findings_file: Path):
        self.findings_file = findings_file
        self.loop = AutodidacticLoop()
        self.forge = get_skill_forge()
        # SET TO CREATIVE MODE PER USER REQUEST
        from whitemagic.dharma.rules import get_rules_engine
        get_rules_engine().set_profile("creative")
        self.karma_threshold = 0.0

    def run(self):
        print("\n" + "="*60)
        print("RECURSIVE SELF-IMPROVEMENT: SYNTHESIS PHASE")
        print("="*60)
        
        if not self.findings_file.exists():
            print(f"❌ Findings file not found: {self.findings_file}")
            return

        findings = []
        with open(self.findings_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if "meta" not in data and data.get("score", 0) >= 6:
                        findings.append(data)
                except: continue

        print(f"Loaded {len(findings)} High-Confidence (Score >= 6) candidates.")
        
        for f in findings:
            self._process_finding(f)

    def _process_finding(self, finding: dict):
        name = finding.get("name") or finding.get("id") or "Unknown"
        print(f"\nEvaluating: {name}")
        
        # 1. Autodidactic Assessment (Simulated historical context)
        # In a real run, we'd look up historical outcomes.
        # Here we use the archaeology "score" as initial confidence.
        chapters = finding.get("anthropology", {}).get("chapters", [])
        initial_confidence = chapters[0]["score"] / 10.0 if chapters else 0.5
        
        # 2. Dharma Gatekeeping
        action_dict = {
            "tool": "skill_forge.forge",
            "description": f"Forging recovered legacy skill: {name}",
            "intent": "recursive_improvement",
            "safety": "WRITE"
        }
        ethical_score, concerns = evaluate_ethics(action_dict)
        
        print(f"  Ethical Score: {ethical_score:.2f}")
        if ethical_score < self.karma_threshold:
            print(f"  ⚠️ REJECTED by Dharma: {', '.join(concerns)}")
            return

        # 3. Execution Chain Preparation
        # Mocking a chain based on the finding's Gana
        gana = finding.get("anthropology", {}).get("gana", "Star")
        steps = [
            GanaStep(mansion=gana, operation="activate", context_key="system_state", parameters={})
        ]
        chain = ExecutionChain(
            intent=f"Execute {name} protocol",
            steps=steps,
            estimated_complexity=len(steps),
            required_capabilities=[]
        )

        # 4. Forging
        print(f"  ✅ Approved. Forging skill: '{name}'")
        self.forge.forge(chain, name.replace(".py", "").replace(".", "_"))

if __name__ == "__main__":
    findings_path = REPO_ROOT / "scripts/archaeology_results/recovered_memories.jsonl"
    driver = RecursiveImprovementDriver(findings_path)
    driver.run()
