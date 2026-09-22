#!/usr/bin/env python3
"""Convert LongMemEval oracle rows into the T1 retrieval.jsonl contract.

The oracle split contains only the evidence sessions for each question, so it
is the reading-ceiling control: no retrieval harness is needed, and the reader
and judge sessions can run immediately while the retrieval-condition run is
being built. Metrics are intentionally not claimed for this variant — the row
is marked ``oracle: true`` (gold evidence only).

Usage:
  python3 scripts/t1_oracle_to_retrieval.py \
      --oracle benchmarks/data/longmemeval_s/cleaned/longmemeval_oracle.json \
      --out benchmarks/runs/t1-oracle/retrieval.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def session_text(session: list) -> str:
    lines = []
    for turn in session:
        role = turn.get("role", "unknown")
        content = (turn.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    oracle_path = Path(args.oracle)
    out_path = Path(args.out)
    dataset_sha = sha256_file(oracle_path)
    rows = json.loads(oracle_path.read_text(encoding="utf-8"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_path.open("w", encoding="utf-8") as out:
        for row in rows:
            sessions = row.get("haystack_sessions") or []
            session_ids = row.get("haystack_session_ids") or [
                f"s{i}" for i in range(len(sessions))
            ]
            retrieved = []
            for index, session in enumerate(sessions):
                text = session_text(session)
                if not text:
                    continue
                sid = session_ids[index] if index < len(session_ids) else f"s{index}"
                retrieved.append(
                    {
                        "rank": len(retrieved) + 1,
                        "memory_id": f"oracle-{sid}-{index}",
                        "session_id": sid,
                        "content": text,
                    }
                )
            entry = {
                "question_id": row["question_id"],
                "question": row.get("question", ""),
                "question_type": row.get("question_type", ""),
                "is_abstention": str(row["question_id"]).endswith("_abs"),
                "retrieved": retrieved,
                "retrieval": {
                    "oracle": True,
                    "note": "gold evidence sessions only — reading-ceiling control",
                },
                "provenance": {
                    "isolation": "oracle",
                    "run_id": "t1-oracle",
                    "dataset_sha256": dataset_sha,
                },
            }
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            written += 1
    print(f"oracle retrieval: {written} rows → {out_path} (dataset sha {dataset_sha[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
