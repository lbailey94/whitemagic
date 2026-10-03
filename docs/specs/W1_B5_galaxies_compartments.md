# Wave-1 spec B5 — Galaxies / compartments

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `309e111` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Galaxies/compartments (wave plan §2; Galaxies `CLEANLY → compile · E8`, Compartments
`PRESERVE IMPL. → link · E10`).
**Wire:** scope labels/views over one store; compartments = statutes + scopes.
**Nucleus touch points:** Part 1 invariants 1 (fail-closed) and 6 (truthful surfaces); Part 3
statutes; E8/E10.
**Caution carried:** the cap-20 bypass path and `_meta` **membership-vs-authz** are
**UNVERIFIED** items (W1 §4) — the spec must close or name them, not narrate them away.
**Do not re-raise:** errata A#6 (the 47-galaxy sprawl is **narrative-only** — no source
attestation; do not cite as measured); "fail-closed unknown values (v4.3.0)" is not in the v26
source.

---

## 1. Frozen behavioral spec

### 1.1 Scope labels (compile side)

- **Scope labels are a view over one store, not physical containers** (E8; canon §3.6). No
  per-name resources are created by a label (the v26 per-galaxy SQLite DB class is excluded).
- **The label set is bounded:** fixed enum (16 values; 11 memory galaxies; Telemetry excluded
  from evidence) + dynamic overlays capped at **20** with an effectiveness prune (min cluster 10,
  prune threshold 0.1); over-cap creation prunes then refuses (`mutable.rs:266-321`).
  (SOURCE-IMPLEMENTED + live)
- **Cap enforcement includes the bypass path:** the cap is on `DynamicGalaxyRegistry`; the
  physical `GalaxyRegistry::create` cap wiring is **UNVERIFIED** — this spec must either close
  the bypass or name it with its disclosure (no silent over-cap).
- **Scope labels carry provenance:** transfers tag origin (`transferred_from:` class) or the
  transfer is refused; the phylogenetics-edge class is **not inherited** unless separately earned.
- **Explicit selection stays explicit:** an explicit scope argument bypasses class isolation by
  design; the **default path stays filtered** — the explicit path must not become the default.
- Unscoped reads federate across the label set with the isolation filter applied; the filter is
  never silently dropped by a performance path.

### 1.2 Isolation classes (link side)

- Class markers (canonical/benchmark/eval/quarantine/test) are consulted on the read path
  (search + mining); **cross-class transfer must refuse or disclose** — v26's asymmetry (search
  filters, transfer hash-dedups without consulting the marker) is the exclusion exemplar.
- Federation over never-loaded labels must not fabricate results; discovery is bounded (no
  unbounded per-name resource construction — the v26 fd-mechanism class is excluded).

### 1.3 Compartments (link side, statutes + scopes)

- Compartment = **access tier on a request, not storage machinery** (E10): tiers
  research/sandbox/production/secure with the Gen2 access law; **unknown values fail closed**.
- **`_meta.compartment` is membership, not authenticated authorization**: it must never be
  treated as an authenticated identity claim (WMv9 AGENTS.md boundary; UNVERIFIED item carried).
  Any authorization story requires an authenticated channel (out of scope; the disclosure is the
  contract).
- **Fail-open-on-engine-error is named:** v26 Dharma ran governance then proceeded on engine
  error ("proceeding without governance"); the successor names one direction — fail-closed is
  the law (invariants 1/6). No silent degradation of a security verdict.
- **Tier labels must not outrun enforcement:** a template label (`secure` etc.) may not be
  reported when its enforcement tier degraded; report the **effective** grants, not the declared
  template.

### 1.4 Capability hygiene

Unknown capability strings are refused loudly (v26 **silently dropped** them while reporting the
requested template — a typo must never yield a laxer run).

### 1.5 Statutory parameters named (Tier-2)

Label enum + dynamic cap (20; min cluster 10; prune 0.1) · compartment tiers + access law ·
fail-closed direction for unknowns · effective-grant reporting.

### 1.6 Non-goals

No physical per-label stores · no multi-membership weights (v26 provided single-valued containers
plus context weights only; the container-vs-weight question is named, not answered) · no
membership-as-authz · no unbounded label creation · no 47-galaxy narrative.

---

## 2. Selection history

**Ancestor (Gen1 v26):** 14-name taxonomy + zones as **advisory constants** (write path never
called the classifier); single-valued container column + **one SQLite DB per galaxy**, created
for any sanitized non-empty name with **no cap**; isolation classes real but partially wired
(search + mining consult; transfer does not); federation per discovered backend with over-fetch
and merge; runtime DB count outgrew the taxonomy (10 canonical → 32 at the association build;
47 claimed at collapse — **no source attestation**, UNVERIFIED); per-galaxy DB loss a known
failure class (sessions galaxy wiped 2026-07-28). Compartments: shelter templates with silent
tier degradation, silently dropped capabilities, thread tier ignoring grants, Dharma
fail-open-on-engine-error, process-global profile flips; **no compartment→galaxy access rule
in v26** (matrix L63's mapping is Gen2-side).

**Selection fate:** distilled to a 16-value enum over one LMDB env + capped dynamic registry
(Gen2); compartments folded to Mandala isolated envs; ratified rows: Galaxies CLEANLY→compile
(scope labels/views), Compartments PRESERVE→link (statutes + scopes; enforcement machinery stays
Gen2-side for alpha).

**Evidence levels:** v26 organs SOURCE-IMPLEMENTED; sprawl/47 UNVERIFIED (narrative-only);
Gen2 enum/cap SOURCE-IMPLEMENTED + read-verified; `_meta` membership boundary SOURCE-DOCUMENTED
(WMv9 AGENTS.md) — treat as UNVERIFIED authorization.

---

## 3. Adversarial cases

1. **Unbounded scope names** — a label either bounds names or demonstrably creates no per-name
   resources (measure descriptors/routes per label).
2. **Isolation asymmetry** — with a class marker on a source scope, federated search excludes it
   while transfer must **refuse or disclose**; one of the two, never silent.
3. **Explicit-selection creep** — assert the explicit path cannot become the default path.
4. **Capability typos** — misspelled grants refuse loudly; the reported template never exceeds
   the effective grants.
5. **Tier degradation label** — with only the thread tier available, a `secure` template reports
   its degraded enforcement, not the label.
6. **Cap bypass** — an over-cap create through the physical registry path is either refused or
   disclosed (UNVERIFIED item closed-or-named).
7. **Membership-vs-authz** — `_meta.compartment` alone never authorizes; a forged/unknown value
   fails closed.
8. **Fail-open-on-error** — engine error in the governance path yields a refusal or an explicit
   degraded disclosure, never "proceeding without governance".
9. **Narrative guard** — any metric citing the 47-galaxy collapse must carry its UNVERIFIED label
   or be excluded.

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Classification calls | advisory labels present | explicit-scope writes/recall unchanged (taxonomy is labeling, not containment) | EXECUTED → EFFECTFUL |
| Discovery pre-pass | never-loaded labels present in federation | they disappear while isolation filtering holds | EFFECTFUL |
| Class marker A/B | search excludes | transfer must refuse/disclose (asymmetry isolated) | EFFECTFUL |
| Tier availability + concurrency cap | effective grants reported | declared template diverges (the v26 class) | RE-ENTERS (reporting honesty) |

---

## 5. Acceptance + owner

Wrapper-side:

1. **Scope-label behavior** — labels are views; no per-name resources grow with label count.
2. **Fail-closed unknowns** — unknown compartment fails closed; membership ≠ authz disclosed.
3. **Cross-class transfer** — refused or disclosed, tested with a marked source.
4. **Cap + bypass** — cap enforced; the physical-registry path is closed or explicitly disclosed.
5. **Effective-grant reporting** — degraded tiers report actual grants, not template labels.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W1_SPEC_B5_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
