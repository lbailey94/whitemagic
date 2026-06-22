# LoCoMo Benchmark — Blind Retrieval Test (v2)

## What This Test Is

You are taking the **LoCoMo Benchmark Test** — a long-context memory retrieval evaluation designed to measure how accurately an AI can retrieve and reason over a provided memory corpus **without hints**.

This is **Version 2 (Blind)**. Unlike Version 1, no `source_memory_ids` are provided. You must find the relevant memories yourself.

---

## Files In This Directory

| File | Purpose |
|------|---------|
| `locomo_memory_sample.json` | Your **only** reference — 31 WhiteMagic memories |
| `external_ai_questions_blind.json` | 100 questions with no memory hints |

**Do NOT access any files outside this directory.**

---

## Your Task

1. Load `locomo_memory_sample.json` and read all 31 memories thoroughly before answering
2. Load `external_ai_questions_blind.json` — 100 questions across 4 types:
   - `single_hop` — one memory contains the answer
   - `multi_hop` — answer requires connecting 2–3 memories
   - `temporal` — answer involves dates, timestamps, or ordering
   - `open_domain` — synthesis across multiple memories
3. Answer every question using **only** the provided memory corpus
4. Return answers as a JSON array

---

## Output Format

```json
[
  {
    "question_id": "q001",
    "answer": "your answer here",
    "confidence": "high|medium|low",
    "source_memory_ids": ["memory ids you found and used"],
    "notes": "optional reasoning"
  }
]
```

If you cannot find the answer in the corpus, return `"answer": "not found"` — **do not guess or hallucinate**.

---

## Critical Isolation Requirements

- ✅ Use ONLY `locomo_memory_sample.json` as your knowledge source
- ✅ Search the memories yourself — no hints are provided this time
- ❌ Do NOT use outside knowledge or training data to fill gaps
- ❌ Do NOT reference prior conversations, session summaries, or handoffs
- ❌ Do NOT access `~/.windsurf/`, project archives, `SESSION_HANDOFF_*.md`, or any file outside this directory

---

## ⚠️ Important Caveat: MCP Tools Are NOT Allowed

WhiteMagic's MCP memory tools (`search_memories`, `recall`, `hybrid_recall`, etc.) query the **live WhiteMagic database** — which contains thousands of memories beyond the 31 in this test corpus.

**Using MCP tools would contaminate the test** by pulling in memories outside the controlled corpus.

> This test measures reading comprehension and retrieval over a fixed 31-memory corpus.
> A separate, more realistic benchmark (`locomo_benchmark.py`) tests WhiteMagic's actual
> MCP retrieval pipeline against the live DB — that is the true end-to-end system test.

**For this test: read `locomo_memory_sample.json` directly. Do not call any MCP tools.**

---

## Scoring Notes

- Exact matches score full credit
- Semantically equivalent answers score full credit
- Partial answers (right memory, incomplete detail) score partial credit
- "not found" on genuinely absent data scores full credit
- Hallucinated answers score zero

**Target baseline:** 78% (the LoCoMo benchmark standard)
**Version 1 result (with hints):** 100% — not representative of real retrieval difficulty

---

## Before You Begin

1. Confirm: *"I am only using `locomo_memory_sample.json`. No MCP tools. No outside files."*
2. Check system time
3. Read all 31 memories first, then answer questions
4. Check system time again when finished

Good luck.
