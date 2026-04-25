# Karma Ledger & Dharma Rules

**Working title**: "Karma Ledger: Merkle-Chained Ethical-Audit Logs for Agent Systems"
**Target length**: 2500–4000 words (technical)
**Paired repo**: `whitemagic-governance`
**Status**: 🟡 Stub · **Priority**: P1 (highest commercial relevance)
**Source material**: `core/whitemagic/core/governance/`, `dharma_audit` schema, EU AI Act Art. 12

---

## Thesis (one sentence)

Every consequential action an agent takes should leave a tamper-evident, policy-queryable audit entry — this is not just good practice, it maps cleanly onto the EU AI Act's Article 12 record-keeping requirement, and it's implementable in ~1000 lines of Python + SQLite.

## Key points to develop

1. **The regulatory hook.** EU AI Act Art. 12 requires "automatic recording of events ('logs') over the lifetime of the system." HIPAA §164.312(b) requires audit controls. SOC 2 CC7.2 wants monitoring. These are not the same spec, but they share a primitive.
2. **Why Merkle chain.** Append-only + tamper-evidence + selective disclosure. Each entry's hash includes the previous entry's hash.
3. **The Dharma Rule DSL.** Declarative policy: `on(action="deploy") require(consent_level >= "explicit") unless(context.emergency)`. Small, auditable, reviewable by non-engineers.
4. **Scope of Engagement tokens.** Capability-based permissions expressed as capsules the agent holds temporarily. Like OAuth scopes but designed for LLM delegation chains.
5. **Consent levels.** Explicit → implicit → none. Every action tagged. Disclosure generation becomes trivial when the schema includes consent as a column.
6. **Live demo.** Show 50 audit entries, show one tamper attempt being detected, show one policy denial, show one disclosure report generation.

## Open questions (honest)

- Is anyone actually asking for this *yet*? Or is it 18 months early? (Probably 6–12 months early. Ship now and be the canonical reference when the demand hits.)
- Does this compete with PostHog / Datadog / OpenObservability? (No — those are ops logs; this is policy logs. Different semantics, different audience.)
- Can this support federated / multi-agent chains (one agent delegates to another)? (Yes, with careful capability-token design.)

## Publish venue options

- GitHub README + medium.com writeup
- LWN (technical audience, serious)
- A compliance-focused newsletter (e.g., the IAPP daily)
- Submit to a workshop at AAAI/NeurIPS 2026 on "Trustworthy Agents"

## Draft log

- [ ] Outline (30 min)
- [ ] Extract karma-ledger code from `core/` into standalone repo
- [ ] README with EU AI Act Art. 12 mapping table
- [ ] Essay draft (2 sessions)
- [ ] Publish
