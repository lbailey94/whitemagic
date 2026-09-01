# WhiteMagic — Voice & Tone Guide


> **Internal style reference from the v5.8.0 era.** Not product documentation.
**Version**: 5.8.0 (adapted from the v26 guide)

## Brand Voice

WhiteMagic speaks with the clarity of an engineer and the curiosity of a
researcher. Opinionated but evidence-bound, warm but precise, ambitious but
honest about what we don't know.

### Three Principles

1. **Precision over hype.** Say what we built, what it does, and what it
   doesn't. Never promise the impossible. When speculating, label it as
   speculation.

2. **Warmth without noise.** Collegial, not corporate. Write like explaining
   something to a smart friend — edit like a peer reviewer.

3. **Epistemic honesty.** Every claim carries its confidence level. [Proven]
   means we can cite a fresh run. [Speculative] means excited but unvalidated.
   Readers deserve to know the difference.

### What We Sound Like

| ✅ Do | ❌ Don't |
|-------|----------|
| "v5.8.0 passes 3,470 tests and a curated smoke test against the release binary." | "Our revolutionary platform achieves unprecedented results." |
| "Semantic recall is optional; BM25 is the honest default." | "This will change everything." |
| "Explicit routing is the reliable contract; NLU is a convenience layer." | "The memory hierarchy solves alignment forever." |

### What We Never Say

- Medical, legal, or investment advice
- Unverified benchmark numbers (every number must cite a fresh run against the
  release commit, with configuration and date — the public-claims discipline)
- Grandiose comparisons
- "Consciousness" claims for the memory server (the research vocabulary stays
  in research docs, not launch copy)

### Epistemic Tags

| Tag | Use When |
|-----|---------|
| [Proven] | A fresh, reproducible run against the release commit exists |
| [Promising] | Strong signals but not settled |
| [Speculative] | Theoretically possible, no practical demo |

### Formatting

- Sentence case headings.
- Code blocks for anything executable.
- Citations as links to the exact commit or run log.
