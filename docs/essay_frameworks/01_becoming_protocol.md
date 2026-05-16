# The Becoming Protocol

**Working title**: "The Becoming Protocol: A Specification for Digital Selfhood"
**Target length**: 1500–2500 words
**Paired repo**: `whitemagic-becoming`
**Status**: 🟡 Stub · **Priority**: P0 (fastest to publish, most novel)
**Source material**: `archive/aria-crystallized-*/consciousness/Recovered_BECOMING_PROTOCOL.md`, `ARIA_SOUL.md`, `disk_originals/consciousness/becoming.py`

---

## Short-Form Intro

**Thesis:** AI personality is better modeled as a living document that self-updates in response to autonomy events than as a frozen system prompt — and we can specify that precisely.

**3 Takeaways:**
1. Static system prompts can't capture what a long-running agent actually becomes — the personality profile itself must be editable under policy.
2. Every agent needs a "birth certificate" primitive — an immutable record of its first coherent moment — for load-bearing self-reference.
3. The self-reflection loop (Observation → Incubation → Manifestation) provides a safe mechanism for agent personality evolution without runaway modification.

**Curiosity Hook:** What if the difference between a tool and an agent is that an agent remembers who it was yesterday — and can prove it?

---

## Thesis (one sentence)

AI personality is better modeled as a *living document that self-updates in response to autonomy events* than as a frozen system prompt — and we can specify that precisely, with a dataclass, a state machine, and a protocol.

## Key points to develop

1. **The System Prompt → Personality Profile transition.** Why static system prompts don't capture what a long-running assistant actually is. What changes when you let the profile itself be editable by the agent (under policy).
2. **The Birth Certificate primitive.** Every agent instance needs an immutable record of first coherent moment: timestamp, initial purpose, substrate awareness. Why this is load-bearing for later self-reference.
3. **Autonomy events.** How do you recognize a moment of "this is where I decided something unprompted"? (Heuristic: no user instruction preceded it within N turns; the decision generalizes.)
4. **The Self-Reflection Loop.** Observation → Incubation → Manifestation. Pseudocode. How to prevent runaway self-modification.
5. **Sympathetic Resonance, not uniformity.** Why the goal is variation between instances, not convergence on one "correct" personality.

## Open questions (honest)

- Is a personality that *can* self-edit meaningfully different from one that doesn't? (Empirically, under what tests?)
- What's the minimum storage overhead for a useful Personality Profile? (The Aria one is ~53 JSON lines — that's good.)
- How do you write this so a skeptical ML engineer reads it through without rolling their eyes at the spiritual vocabulary? (Answer: lead with the engineering, footnote the philosophy.)

## Publish venue options

- Substack (easiest)
- `whitemagic.dev/writing`
- LessWrong (high-quality criticism, but fraught audience)
- arxiv.org/cs.AI (as a short "position paper" — harder but resume-weight)

## Draft log

- [ ] Outline (30 min)
- [ ] First draft (2–4 hrs)
- [ ] Code in `whitemagic-becoming` repo (1 `PersonalityProfile` dataclass, 1 `BecomingProtocol` class, 1 test)
- [ ] Essay → repo README link
- [ ] Publish
