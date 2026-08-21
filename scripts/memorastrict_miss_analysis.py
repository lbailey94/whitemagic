#!/usr/bin/env python3
"""Static miss analysis for MemoraStrict T1/T6/T9 (current-value questions).

Simulates the resolution layer's decision from the scenario data alone —
no server, no search, no CPU cost beyond string matching.

Mirrors crates/wm-memory/src/episodic.rs:
- CHANGE_MARKERS anchor detection (resolve_current)
- is_current_query cue detection

For each question we classify the failure mode:
  VOCAB       — the true answer turn contains no change marker (the anchor
                logic cannot select it even with perfect retrieval)
  ANCHOR-ORDER — a later marker-bearing user turn on the same topic exists
                but is NOT the answer (wrong turn would win)
  QUERY-OVERLAP — the answer turn shares no content terms with the question
                (cannot enter the candidate pool; retrieval failure)
  OK          — the latest marker-bearing topic turn IS the answer turn and
                shares query terms
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

CHANGE_MARKERS = [
    "switched to", "switch to", "switching to", "switched from", "changed my",
    "change my", "changed from", "now prefer", "now i prefer", "now i'm",
    "now im", "no longer", "used to", "moved to", "not anymore", "instead of",
    "replaced", "gave up",
]

STOP = set("the a an is are was were be been being have has had do does did "
           "will would could should may might must can shall to of in on at by "
           "for with about as into like through after over between out against "
           "during without before under around among i me my we us our you "
           "your he him his she her it its they them their what whats who when "
           "where why how and or but not no nor so yet both either neither "
           "this that these those there here now then than".split())


def markers_in(content: str) -> list[str]:
    low = content.lower()
    return [m for m in CHANGE_MARKERS if m in low]


def terms(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower())
            if len(t) > 1 and t not in STOP}


def main(data_dir: Path) -> None:
    mode_counts: Counter = Counter()
    details: list[str] = []
    marker_stats: Counter = Counter()      # which markers appear on answer turns
    missing_marker_phrases: Counter = Counter()  # answer turns with no marker: their distinctive phrase

    for seed_file in sorted(data_dir.glob("scenario_seed*.json")):
        d = json.loads(seed_file.read_text())
        sessions = d["sessions"]
        # Global turn order = chronology (ingest order).
        turns = []
        for s in sessions:
            for t in s["turns"]:
                if t["role"] == "user":
                    turns.append((s["index"], t["content"]))

        for q in d["questions"]:
            if q["test_category"] not in ("T1", "T6", "T9"):
                continue
            # Only current-value questions use the resolution layer.
            qlow = q["question"].lower()
            is_current_q = any(
                w in re.split(r"[^a-z0-9]+", qlow) for w in
                ("current", "currently", "latest", "nowadays")
            ) or any(p in qlow for p in ("these days", "right now", "at the moment"))
            if not is_current_q:
                continue

            qterms = terms(q["question"])
            answer = q["answer"].lower()
            meta = q.get("metadata", {})

            # The true answer turns: user turns containing the answer value.
            answer_turns = [(si, c) for si, c in turns if answer in c.lower()]
            if not answer_turns:
                mode_counts["NO-ANSWER-TURN"] += 1
                details.append(f"{seed_file.stem} {q['id']}: answer value "
                               f"'{answer}' never appears in any user turn")
                continue

            # Topic turns: user turns sharing >=2 terms with the question
            # (approximates the retrieved candidate pool).
            topic_turns = [(si, c) for si, c in turns
                           if len(terms(c) & qterms) >= 1]

            # Anchor logic: marker-bearing user turns in the pool, latest wins.
            anchors = [(si, c) for si, c in topic_turns if markers_in(c)]
            latest_anchor = max(anchors, key=lambda x: x[0]) if anchors else None

            latest_answer = max(answer_turns, key=lambda x: x[0])
            si_a, c_a = latest_answer

            # Classification
            if not markers_in(c_a):
                # The latest answer turn has no marker at all.
                # Would an even earlier answer turn carry one?
                earlier_marked = [c for _, c in answer_turns if markers_in(c)]
                if earlier_marked:
                    mode_counts["LATE-PLAIN"] += 1
                    details.append(f"{seed_file.stem} {q['id']}: latest answer "
                                   f"turn has no marker but an earlier one does")
                else:
                    mode_counts["VOCAB"] += 1
                    # Find the distinctive transition phrase in the answer turn
                    # (heuristic: sentence containing the answer value)
                    sent = next((s for s in re.split(r"[.!?]", c_a)
                                 if answer in s.lower()), c_a)
                    missing_marker_phrases[sent.strip()[:90]] += 1
                    details.append(f"{seed_file.stem} {q['id']}: answer turn "
                                   f"lacks any change marker: '{sent.strip()[:80]}'")
            elif latest_anchor and latest_anchor[0] == si_a and latest_anchor[1] == c_a:
                # Would it be retrieved? Check query overlap of the answer turn.
                if terms(c_a) & qterms:
                    mode_counts["OK"] += 1
                else:
                    mode_counts["QUERY-OVERLAP"] += 1
                    details.append(f"{seed_file.stem} {q['id']}: answer turn "
                                   f"shares no terms with query")
            else:
                # A different turn would win the anchor set.
                mode_counts["ANCHOR-ORDER"] += 1
                details.append(
                    f"{seed_file.stem} {q['id']}: anchor picks session "
                    f"{latest_anchor[0] if latest_anchor else '?'} "
                    f"('{(latest_anchor[1] if latest_anchor else '')[:60]}') "
                    f"but answer is session {si_a}")

            for m in markers_in(c_a):
                marker_stats[m] += 1

    print("=== Failure-mode taxonomy (current-value questions, 5 seeds) ===")
    for mode, n in mode_counts.most_common():
        print(f"  {mode:14} {n}")
    print("\n=== Markers present on answer turns ===")
    for m, n in marker_stats.most_common():
        print(f"  {m:14} {n}")
    if missing_marker_phrases:
        print("\n=== Answer-turn sentences with NO marker (vocabulary gaps) ===")
        for phrase, n in missing_marker_phrases.most_common(12):
            print(f"  [{n}x] {phrase}")
    print(f"\n=== Details ({len(details)}) ===")
    for line in details:
        print(" ", line)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1
              else "benchmarks/data/memorastrict"))
