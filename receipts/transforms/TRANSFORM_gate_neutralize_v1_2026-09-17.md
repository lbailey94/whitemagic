# TRANSFORM — `gate-neutralize.v1.2026-09-17`

**Status: first-class transform record** (protocol §9). Conditioning transform for regressions
against recorded cells when the A1 exact-hash gate is active. Append-only.

| Field | Value |
|---|---|
| `transform_id` | `gate-neutralize.v1.2026-09-17` |
| `kind` | gate-neutralize (corpus conditioning for gate-aware regression) |
| `source_identity` | `experiments/semantic_projection/holdout` seeds 6–10 — `MANIFEST.json` (10 files, hash-verified 2026-09-17) |
| `operation` | deduplicate each haystack by the **A1 gate identity** `(session_id, role, has_answer, content)`, keeping the first occurrence; scripted in `receipts/impl_b1_acceptance_2026-09-17/driver_regression.py` (`dedupe_corpus()`), deterministic |
| `output_identity` | `corpus_dedup.sha256` (sha256 `be3046f7d09f72f90a3658e963e4897e360b534077bb7c833750bc5a8bf52cd3`): `bench_seed6` `99c9cf1a…` · `seed7` `21efc892…` · `seed8` `8470e600…` · `seed9` `6d16f318…` · `seed10` `f4eccb31…` |
| `lineage` | none (v1) |
| `scope` | regressions comparing candidate vs source-frozen reference and/or recorded cells on the holdout corpus while the A1 gate is active (B1 stage B template) |
| `disclosures` | later same-identity turns removed per session (e.g., seed 6: 776 ingested turns → 527 gate-admissible); answers retained at their first occurrence; output files are derived and **not committed** (regenerable from the MANIFEST-verified source + this record) |
| `used_by` | `IMPL_B1_ACCEPTANCE_2026-09-17` (stage B: candidate ≡ reference on the deduped corpus, both C00/C01 configs) |

**Rule:** any future regression citing recorded cells on a conditioned corpus cites this
`transform_id`; a new conditioning change is a **new transform version with its own record and
lineage** (e.g., `gate-neutralize.v2.<date>` superseding this one), never an in-place edit.
