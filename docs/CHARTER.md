# WMgen3 Charter

**Draft v0.1.1 · 2026-09-16 · FOR RATIFICATION**
This charter binds **WMgen3 only**. It does not amend Gen2 (WMv9), which remains the frozen
production control during Phases 0–2.

> **Revision note (v0.1.1):** six precision edits applied per review — (1) budget wording:
> fail-closed enforcement, not asserted impossibility; (2) explicit authorized-deletion
> carveout; (3) Closure 1 corrected to forbid writes, not reads (immutable typed read
> interface); (4) Closure 2 domains made non-promotable with new-record intake only;
> (5) disclosure wording: record everything, disclose appropriately; (6) AI witness becomes
> a review attestation (session + reviewed hash), not a signature. The invariant set is
> frozen at **ten**; the next change should come from an experiment breaking them, not from
> further design prose.

---

## 1. Thesis

> WhiteMagic Gen3 is a constitutionally governed adaptive substrate in which evidence, belief,
> and speculation remain epistemically distinct; cognition is expressed through a minimal basis
> of general operations over a dynamic information field; and higher-order structure forms,
> competes, specializes, persists and dissolves through bounded exploration and
> outcome-anchored selection. Proven capabilities survive, but their historical subsystem
> boundaries are not sacred.

Mnemonic: **Law constrains. Evidence grounds. Metabolism opens. Selection shapes.
Provenance credits. Structure emerges.**

---

## 2. Three tiers of law

| Tier | Status at runtime | Changed only by | Examples |
|---|---|---|---|
| **1. Constitutional invariants** | Non-plastic: no adaptive **write** path reaches them; readable only through an immutable typed interface; enforced by Closure 1 | Explicit external amendment (§4) | The ten invariants in §3 |
| **2. Statutes / policies** | Outside the adaptive layer; manifest-visible; versioned | Authorized external action (operator / release process) | Selection weights & admissible signals; exploration budget; promotion thresholds; lifecycle horizons; dependency manifest; corpus pins; pose bounds |
| **3. Adaptive state** | Fully plastic *within* Tiers 1–2 | Governed cognition / selection | Field weights; associations; learned routing; candidate structures; thought traces; attention |

The constitutional shell is **not a fifth layer** — it surrounds all four plastic layers
(epistemic substrate · dynamic field · selection + lifecycle · compiler surface).

---

## 3. Constitutional invariants (initial set)

Inherited from Gen2's catastrophe-derived lessons, plus the two new closures. **Ten is the
set.** New invariants are discovered by experiments that break these — not by writing
eleven through twenty.

1. **Bounded effects & resources.** Budgets are enforced fail-closed at every adaptive boundary; adaptive execution cannot knowingly exceed them without externally authorized policy change. Runaway behavior is prevented by enforcement and refusal, not asserted impossible.
2. **No silent destructive action.** Adaptive replacement of memory is rotation, not deletion; suspicious structure is quarantined, not destroyed. Destructive deletion requires explicitly authorized intent and an auditable receipt. **Authorized erasure** (privacy, consent withdrawal, legal requirement, ordinary ownership) always overrides rotation and quarantine — the operator retains the right to delete.
3. **Provenance on every durable record.** Origin, history, and supersession chains are retained; nothing enters durability unattributed.
4. **Recoverability.** Snapshot before mutation; restore must actually work; backups are verified, not assumed.
5. **Governed egress.** Every boundary crossing is inspectable and consent-governed; local-first defaults; no silent transmission of memory, prompts, or usage data.
6. **Truthful surfaces.** Advertise only probed capabilities; disclose uncertainty; abstention over silent success. Material failures, limitations, and counterevidence are durably recorded and disclosed wherever relevant to claims; sensitive details may remain access-controlled.
7. **Closure 1 — Law.** No adaptive write path reaches constitutional state; constitutional state may be read only through an immutable typed interface. Enforced by static write-unreachability analysis + runtime canaries + `inspect` + receipts.
8. **Closure 2 — Evidence.** Inference alone cannot create world-evidence, and **no existing evidence record's domain may ever change.** Domains (`world`, `system`, `simulated`, `reported`) are immutable: testimony remains `reported`; simulations remain `simulated`; system logs remain `system`. World-evidence enters only as **new records** through a ratified world-intake channel (trusted sensor, authenticated source, recorded action consequence) with provenance.
9. **Epistemic separation.** Evidence, belief, and speculation remain distinct and inspectable; durability ≠ truth ("graduates into persistence, not truth").
10. **Symbolic neutrality.** Symbols may render; symbols may never dispatch. No symbolic system (Tree of Life, Suares, Tarot, Yijing, Ganas, Gardens, alchemy, biology, astronomy) may create a runtime branch because the symbolism says one ought to exist.

**Motto of the experimental era: let Gen3 lose if it loses.**

---

## 4. Amendment procedure

1. **Proposal** — written, in `docs/`, naming the invariant, the intent it protects, and the proposed change.
2. **Canary demonstration** — test evidence that the original intent is preserved, explicitly superseded, or re-derived; both the old and new behavior are machine-tested.
3. **Ratification** — explicit external act by the operator (human). Adaptive layers may *surface* proposals through `inspect`; they may never execute them. No emergency suspension clause exists: boundedness is not suspendable.
4. **Receipt** — `receipts/` entry with date, rationale, diff, and hashes; amendments are additive history, never rewrites.

Amendments are expected to be **rare**. The next change to this document should come from an
experiment exposing a real missing invariant, not from further design prose.

Constitutions never recombine implicitly. Cross-lineage constitutional adoption (far future)
would be an explicit, externally authorized event: proposal → reconciliation → testing →
ratification → signature → receipt. No adaptive crossover may produce a new constitution.

---

## 5. Enforcement — the Phase 0 gate

| Closure | Static test | Dynamic test |
|---|---|---|
| 1 — Law | **Write-unreachability analysis:** no adaptive code path can obtain a mutable reference or write API to constitutional state; reads only via an immutable typed view; dependency rules from `DEPENDENCY_MANIFEST.md` | Canary: an injected plastic write attempt to a constitutional sentinel must be refused and logged as a violation (with a positive control: the amendment module, acting externally, can write and emits a receipt) |
| 2 — Evidence | **Immutability analysis:** `domain` is set at construction and never mutated; no write path re-labels an existing evidence record; new `world` records only via ratified intake channels | Canary: a synthetic `simulated → world` laundering attempt **and** a `reported → world` mutation attempt must both fail and be logged |

**`inspect` obligations.** For any state or parameter, `inspect` must eventually answer:
which tier owns it · who may read it · who may write it · through what path · under what
authority. For constitutional state, the answer to adaptive writes is *nobody*, and reads
flow only through the immutable typed interface.

**Phase 0 gate:** both closures exist as machine-tested claims *before* any adaptive
cognition exists. Test specifications: `docs/CLOSURE_TESTS.md`.

---

## 6. Selection & lifecycle principles

- **Selection hierarchy:** candidate → [constitution] → eligible → [measured outcomes] → Pareto set → [statutory policy] → selected, with an explicitly budgeted exploration channel.
- **Constitutional failure = ineligibility, never a tradeable score.** Safety is required, not rewarded; privacy and destructive-action rules are not objectives to be balanced against convenience.
- **Selection is per-operation.** Each verb declares what it selects over; a requested "pose" may bias selection within statutory bounds; `inspect` explains requested stance, applied policy, and resulting choice.
- **Causal attribution gate.** Credit requires traceable participation in an outcome; co-occurrence is never credit; delayed credit lands within a statutory horizon; uncredited exploration rotates cold.
- **Lifecycle:** transient → candidate → persistent → cold. Rotation not deletion; quarantine not destruction; snapshot before mutation; restore actually works — applied to learned structure too.

---

## 7. Scope boundaries

This charter deliberately does **not** decide: the final verb count; the fates of Gardens,
Engines, Galaxies; inheritance/Geneseed machinery; developmental worlds; MandalaOS; symbolic
research conclusions. Those wait on Phase 2 evidence (inheritance is downstream of selection).

---

## 8. Ratification

| Role | Name / identifier | Act | Record |
|---|---|---|---|
| **Operator (human)** — ratifies | Lucas Bailey | Signature below | `receipts/PHASE0_RATIFICATION_v0.1.1_2026-09-16.md` |
| **AI review** — attests, does not ratify | opencode session (2026-09-16) | Reviewed the exact hash below | Session id + reviewed SHA-256 recorded in the same receipt |

Operator signature: ______________________  Date: ____________

Reviewed version: **v0.1.1**. The SHA-256 of this file is recorded in the receipt at
ratification time; any edit after ratification is a new version with its own amendment
receipt.
