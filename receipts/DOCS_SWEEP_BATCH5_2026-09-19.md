# RECEIPT — Docs sweep batch 5 (code-walk steps 3–4 · errata M) — 2026-09-19

**Status: landed.** Code-walk steps 3–4 read in full (`field.rs`, `projection.rs`, harness
`main.rs`, `journal.rs`) against the Phase-1 interface and dependency records. Operator
authorization (in-session): *"continue our walk, and continue updating our docs as we go."*
No verdict, claim, gate, or threshold movement; no code changed; no registered artifact edited.

---

## 1. Walk results

- **Checked consistent (no action):** tokenizer + candidacy rule vs NUCLEUS statutes (divisor 20 /
  floor 2 / strict temporal order / fixed `e=(w,s,c,t)`); journal append-only with per-event flush
  and hash-out linkage; read-only mode refuses exactly the three write routes; `inspect` stays
  `&self`; the append-journal seq pitfall is already declared in HANDOFF §5.
- **Findings (registered as errata M):**
  - **#56** — T10 route `memory.aggregate` is an undeclared empty stub (`main.rs:353-358`);
    harmless historically (T10 never in the frozen set), but a future T10-scored run would get a
    valid-but-empty `results` list — the "silent zero" class. Interface record is pinned in
    `PREREG_FREEZE_2026-09-16` (`9be4f1d8…`) → versioned note is a morning decision.
  - **#57** — projection "no network at run time" is environment-enforced, not code-enforced
    (fastembed would attempt download on a cache miss; no `HF_HUB_OFFLINE`). Fix candidate queued.
  - **#58** — `DEPENDENCY_MANIFEST.md` still lists embeddings as deferred (§2/§4) while the
    embedding exception governs; manifest is pinned in `PHASE0_VERIFICATION` (`f3be8449…`).

## 2. Changes

| Artifact | Change | sha256 (before → after) |
|---|---|---|
| `docs/PHASE4_ERRATA.md` | section M (#56–58) + checked-consistent note; title A–M | `e0cdac25…` → `d4d6deb5…` |

## 3. Disclosures / limits

- Registered artifacts were **not edited** (interface record pinned in the pre-reg freeze;
  dependency manifest pinned in Phase-0 verification); both landed as errata with versioned-note
  options on the morning checklist.
- No code changed; nothing re-run; no store touched.

## 4. Attestation

AI session `8996b333-5168-4eb2-9b2a-0e1724fbc749` (WMgen3 docs sweep) prepared this receipt;
operator present and authorizing in-session. Append-only; corrections create a new receipt.
