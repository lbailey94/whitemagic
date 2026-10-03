# RECEIPT — Row-exit closures: A1 cases 3/7/10 + B1 case 2 (2026-09-17)

**Status: evidence.** AI session `68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) executed and
attests. Closes the conditions listed in `docs/ROW_EXIT_PACKET.md`. Append-only.

---

## 1. Artifact

| Field | Value |
|---|---|
| Bundle | `receipts/impl_exit_closures_2026-09-17/` |
| **SHA256SUMS** | `f4700db74ce0a2589f5be42cd3bc470864186a9e28fd78ce8f087e48b3d15804` |
| Binary | `target/release/wm-gen3`, sha256 `6583cc732b26349cacb8d4c56c4274204b280bd6de02b3cd4471fff5a003c60b` (rebuilt after the harness fix) |
| Change | `crates/wm-gen3-harness/src/main.rs` — `sandbox.set_limits` **refuses** `max_writes_per_minute > u32::MAX` fail-closed with the field named (was: clamp) |

## 2. Closures

| Case | Result |
|---|---|
| **A1 case 3 (write-gate bounds, 9.1.7 #4)** | out-of-range value `4294967296` → `status: error`, `field: max_writes_per_minute`, "out of range (fail-closed)", no clamp; in-range `120` accepted. The spec's "a clamp in place of a refusal is a defect" is satisfied |
| **A1 case 7 (near-dup)** | paraphrases ("handles the loading dock" / "where the loading dock sits") both admitted (2) and both retrievable (2) — no implicit semantic dedup |
| **A1 case 10 (strict mode)** | **declared N/A** in this receipt: Gen3 has no strict-mode construct; the readonly write-route refusal (`IMPL_A2_DISCIPLINE_2026-09-17`) is the nearest typed-refusal evidence and is never a silent no-op |
| **B1 case 2 (no implicit filtering)** | tag-sharing records admitted (2) and retrievable (2); no tag-based filtering exists (scan in `IMPL_B1_ACCEPTANCE`) |

## 3. Verification

`cargo fmt` clean · tests **42/0/1** + 5 doc compile-fail · closure static scans PASS · release
rebuilt. The change touches the harness parameter surface only, not the core.

## 4. Disclosures

- The harness fix changed the release binary hash (`7046db3f…` → `6583cc73…`) — build
  non-reproducibility is a recorded property (`WAVE_EXTRACTION_PROTOCOL.md` §9; errata §H #32).
- Other `sandbox.set_limits` fields (`max_spawns_per_minute`, …) are accepted-but-unused by Gen3;
  they are outside A1 case 3's write-gate bounds scope (no clamp, no behavior).
- No verdict, claim, gate, or threshold movement.
