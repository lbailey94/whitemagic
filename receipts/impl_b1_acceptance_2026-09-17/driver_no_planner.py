#!/usr/bin/env python3
"""B1 acceptance — no-planner check (spec W1_B1 §5.5 syntax level + §4 planner negative control).

Syntax level: forbidden planner/rerank organs are absent from the core + harness source; the
rank-key computation contains exactly the declared multiplicative factors (recency term and
supersede penalty) and nothing else; statutory constants are the declared values; the
dependency rule holds (cargo tree + closure scans). Behavioral half: driver_regression.py
(0-diff vs frozen cell C11 catches any unregistered ordering term).

Usage: python3 driver_no_planner.py <bundle-dir>
"""
import os
import re
import subprocess
import sys

BASE = sys.argv[1]
ROOT = "/home/lucas/Desktop/WMgen3"
CORE = os.path.join(ROOT, "crates/wm-gen3-core/src")
HARNESS = os.path.join(ROOT, "crates/wm-gen3-harness/src")
FORBIDDEN = ["rrf", "reciprocal_rank", "cross_encoder", "cross-encoder", "jaccard", "qfhrr",
             "planner", "rerank", "entity_boost", "importance_boost", "conversation_bonus",
             "wrrf", "multi_channel", "fusion_weight", "blend_weight"]


def main() -> int:
    hits = []
    for d in (CORE, HARNESS):
        for name in sorted(os.listdir(d)):
            if not name.endswith(".rs"):
                continue
            text = open(os.path.join(d, name)).read().lower()
            for term in FORBIDDEN:
                if term in text:
                    hits.append((name, term))
    assert hits == [], hits

    ops = open(os.path.join(CORE, "ops.rs")).read()
    norm = re.sub(r"\s+", " ", ops)
    assert "let mut key = support * (1.0 + self.policy.recency_weight * recency);" in norm
    assert "key *= 1.0 - self.policy.supersede_penalty;" in norm
    assert norm.count("let mut key = ") == 1, "exactly one rank-key assignment"
    assert norm.count("key *= ") == 1, "exactly one rank-key multiplicative step"
    assert "supersede_penalty: 0.6" in norm and "recency_weight: 0.05" in norm

    tree = subprocess.run(["cargo", "tree", "-p", "wm-gen3-core", "-p", "wm-gen3-harness"],
                          cwd=ROOT, capture_output=True, text=True, timeout=120)
    deps = [l for l in tree.stdout.splitlines()
            if not re.match(r"^wm-gen3-(core|harness) v", l)]  # skip workspace roots
    offenders = [l for l in deps if re.match(r"^[│├└ `\\-]*wm-", l)]
    assert offenders == [], offenders
    closures = subprocess.run(["bash", "scripts/check_closures.sh"], cwd=ROOT,
                              capture_output=True, text=True, timeout=120)
    assert "closure static scans: PASS" in closures.stdout, closures.stdout[-300:]

    print("B1 NO-PLANNER CHECK PASS")
    print("source scan    : forbidden organs absent (", ", ".join(FORBIDDEN[:6]), "... )")
    print("rank key       : exactly one assignment, one multiplicative step "
          "(recency 0.05, supersede 0.60) — any addition fails this check")
    print("dependencies   : cargo tree has no wm-* crate; closure static scans PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
