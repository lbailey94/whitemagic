# WhiteMagic Gen3 — Sovereign Logoglyphic Sutras & Taoist Mudras Guide
## The Zero-Allocation Fast-Path Codex for Autonomous Agents (v10.4)

> **Document Class:** Agent Specification & Standard Operating Procedures  
> **Target Runtimes:** Antigravity · Claude Code · Opencode · P2P Swarm Nodes  
> **Substrate:** `wm-gen3-core` · `wm-gen3-harness` (`wm3`)  
> **Performance Guarantee:** Zero heap allocation in hot paths (`StackCodon`), sub-40 µs parse latency, 6.90 µs System 0 triage.

---

## 1. Overview & Architectural Motivation

Traditional agent-to-agent and tool-dispatch coordination relies on heavy natural language prompting, multi-kilobyte JSON-RPC envelopes, and multi-second LLM reasoning. This creates latency, burns context tokens, and introduces stochastic syntax errors.

WhiteMagic Gen3 replaces verbose coordination with **Vectorized Logoglyphic Sutras** and **Taoist Hand Seals (手印 / 印诀 / Mudras)**:
* A **Sutra Glyph** is an atomic, immutable metaphysical and operational operator (e.g. `證` for proof/verify, `行` for execute/dispatch).
* A **Sutra Codon / Compound Mudra** is a sequence of 2 to 4 glyphs (e.g. `⟪ 觀 · 察 · 芽 ⟫`) that compiles deterministically into:
  1. A **Dynamic Kekkai Sandbox** (read-only paths, read-write paths, network isolation).
  2. Precondition validation rules (zero heap allocations via bitflags).
  3. A bound **Action Skeleton** executed by the deterministic Rust kernel (`skel-*`).
* A **Hexagram Macro-Action** binds one of the 64 King Wen hexagrams (upper and lower Ba Gua trigrams) into high-level agent campaign state machines.
* The **Catuṣkoṭi K3 Dialectical Router** evaluates conflicting or competing agent desires across Buddhist four-corner logic rather than naive Boolean mutual exclusion.

```
┌─────────────────────────────────┐
│     Agent Intent / Inquiry      │
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Model2Vec Semantic Centroid    │  (745 µs local embedding projection)
│     (or Direct Codon Input)     │
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    StackCodon Zero-Alloc Parse  │  (< 35 µs parse latency, #![forbid(unsafe_code)])
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    Dynamic Kekkai Boundary      │  (Strict FS & Network sandbox union)
└─────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    Geneseed Vault Dispatch      │  (Deterministic Action Skeleton execution)
└─────────────────────────────────┘
```

---

## 2. The 24-Glyph Yin/Yang Phase-Doubled Canon

The canon is organized into 12 classical baseline glyphs (Yang/Formative) and 12 conjugate polar counterparts (Yin/Reflexive):

| Index | Glyph | Alchemical | Pinyin | English Meaning | Polarity | Wu Xing | Taoist Seal (印诀) | Bound Action Skeleton | Kekkai Sandbox Profile |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0** | `證` | `🜅` | Zhèng | Verify / Proof | Yang | Metal | 两仪分形印 (Dual Aspect) | `skel-verify-commit` | RO: `["."]`, RW: `["target/"]`, Net: `false` |
| **1** | `行` | `🜂` | Xíng | Execute / Dispatch | Yang | Fire | 太上开天火印 (Fire Seal) | `skel-verify-commit-vanguard` | RO: `["."]`, RW: `[".git/", "receipts/"]`, Net: `false` |
| **2** | `觀` | `🜁` | Guān | Survey / Inspect | Yang | Wood | 灵宝通真印 (True Spirit) | `skel-fast-lookup` | RO: `["."]`, RW: `[]`, Net: `false` |
| **3** | `合` | `🜊` | Hé | Synthesize / Unify | Yang | Earth | 阴阳交泰印 (Yin-Yang Fusion) | `skel-dream-dream-6cfcfda755` | RO: `["."]`, RW: `["SharedWorkspace/"]`, Net: `true` |
| **4** | `遠` | `🜄` | Yuǎn | Horizon / Project | Yang | Water | 玄武幽冥印 (Deep Water) | `skel-deliberate-horizon` | RO: `["."]`, RW: `["scratch/"]`, Net: `true` |
| **5** | `鏡` | `🜅` | Jìng | Mirror / Analogy | Yang | Metal | 照胆明镜印 (Clear Mirror) | `skel-dream-dream-bd11ebbb83` | RO: `["."]`, RW: `["logs/"]`, Net: `false` |
| **6** | `息` | `🜍` | Xī | Quiesce / Sleep | Yang | Earth | 抱元守一印 (Great Stillness) | `skel-dream-dream-658170e0ff` | RO: `["."]`, RW: `["dream.jsonl"]`, Net: `false` |
| **7** | `清` | `🜏` | Qīng | Clean / Prune | Yang | Water | 九天降魔印 (Exorcism Seal) | `skel-edit-lint-check-opt` | RO: `["."]`, RW: `["."]`, Net: `false` |
| **8** | `應` | `🜎` | Yìng | Resonate / Wire | Yang | Fire | 风雷飞升印 (Wind-Thunder) | `skel-ganying-handshake` | RO: `["."]`, RW: `["/dev/shm"]`, Net: `true` |
| **9** | `界` | `🜔` | Jiè | Kekkai / Sandbox | Yang | Metal | 金刚护身印 (Diamond Shield) | `skel-landlock-jail` | RO: `["/", "."]`, RW: `["sandbox/"]`, Net: `false` |
| **10** | `根` | `🜃` | Gēn | Origin / Root | Yang | Earth | 厚土承天印 (Heavy Earth) | `skel-archaeology-tacit` | RO: `["."]`, RW: `[]`, Net: `false` |
| **11** | `生` | `🝓` | Shēng | Evolve / Speciate | Yang | Wood | 九转还丹印 (Rebirth Elixir) | `skel-edit-lint-check-vanguard` | RO: `["."]`, RW: `["vault.jsonl"]`, Net: `false` |
| **12** | `辨` | `🜛` | Biàn | Discriminate / Fuzz | Yin | Metal | 青龙辨幽印 (Azure Dragon) | `skel-adversarial-redteam` | RO: `["."]`, RW: `["target/"]`, Net: `false` |
| **13** | `擬` | `🜚` | Nǐ | Simulate / Shadow | Yin | Fire | 幻虚拟影印 (Phantom Shadow) | `skel-shadow-dryrun` | RO: `["."]`, RW: `[]`, Net: `false` |
| **14** | `察` | `🜑` | Chá | Probe / Telemetry | Yin | Wood | 神目洞察印 (Divine Eye) | `skel-telemetry-probe` | RO: `["."]`, RW: `[]`, Net: `false` |
| **15** | `分` | `🜖` | Fēn | Decompose / Decouple | Yin | Earth | 太极分形印 (Taiji Fractal) | `skel-modular-decouple` | RO: `["."]`, RW: `["SharedWorkspace/"]`, Net: `true` |
| **16** | `微` | `🝤` | Wēi | Micro / Precision | Yin | Water | 芥子入微印 (Mustard Seed) | `skel-micro-inspect` | RO: `["."]`, RW: `["scratch/"]`, Net: `true` |
| **17** | `照` | `🝞` | Zhào | Illuminate / Diff | Yin | Metal | 烛幽普照印 (Radiant Torch) | `skel-diff-reveal` | RO: `["."]`, RW: `["logs/"]`, Net: `false` |
| **18** | `醒` | `🝢` | Xǐng | Awaken / Alert | Yin | Earth | 震雷警醒印 (Thunder Shock) | `skel-alarm-rearm` | RO: `["."]`, RW: `["dream.jsonl"]`, Net: `false` |
| **19** | `澄` | `🝪` | Chéng | Clarify / Settle | Yin | Water | 渊泉澄清印 (Deep Spring) | `skel-filter-clarify` | RO: `["."]`, RW: `["."]`, Net: `false` |
| **20** | `受` | `🝯` | Shòu | Receive / Ingest | Yin | Fire | 太仓受气印 (Great Granary) | `skel-ingest-receive` | RO: `["."]`, RW: `["/dev/shm"]`, Net: `true` |
| **21** | `通` | `🝰` | Tōng | Permeate / Bridge | Yin | Metal | 八荒通达印 (Boundless Permeation) | `skel-shm-bridge` | RO: `["/", "."]`, RW: `["sandbox/"]`, Net: `false` |
| **22** | `芽` | `🝱` | Yá | Sprout / Fork | Yin | Wood | 灵芽抽秀印 (Sacred Sprout) | `skel-fork-branch` | RO: `["."]`, RW: `[]`, Net: `false` |
| **23** | `化` | `🝲` | Huà | Transmute / Dissolve | Yin | Earth | 大罗造化印 (Cosmic Transmutation) | `skel-transmute-entropy` | RO: `["."]`, RW: `["vault.jsonl"]`, Net: `false` |

---

## 3. The Wu Xing Elemental Cycles

Autonomous workflows should move through the generative cycle of the Five Elements (五行相生):

```
       木 Wood (觀/察/芽)
             │
             ▼
       火 Fire (照/行/應)
             │
             ▼
       土 Earth (合/息/化)
             │
             ▼
       金 Metal (證/辨/界)
             │
             ▼
       水 Water (遠/微/澄)
             │
             └────────► (Re-enters Wood)
```

### Standard Compound Mudras by Elemental Phase
1. **Wood (木) — Scouting & Topological Onboarding:**
   `⟪ 觀 · 察 · 芽 ⟫` (Survey $\rightarrow$ Probe $\rightarrow$ Fork)  
   *Use when:* Arriving in a new workspace, inspecting git status, discovering dependencies.
2. **Fire (火) — Kinetic Action & Swarm Dispatch:**
   `⟪ 照 · 行 · 應 ⟫` (Illuminate $\rightarrow$ Execute $\rightarrow$ Wire)  
   *Use when:* Running tests, applying mutations, syncing across P2P mesh runners.
3. **Earth (土) — Architectural Synthesis & State Grounding:**
   `⟪ 合 · 息 · 化 ⟫` (Synthesize $\rightarrow$ Quiesce $\rightarrow$ Transmute)  
   *Use when:* Consolidating cross-module designs, resolving dialectical conflicts.
4. **Metal (金) — Formal Invariant Verification & Boundary Containment:**
   `⟪ 證 · 辨 · 界 ⟫` (Verify $\rightarrow$ Fuzz $\rightarrow$ Kekkai)  
   *Use when:* Running CI audits, adversarial red-team fuzzing, Landlock sandboxing.
5. **Water (水) — Long-Horizon Foresight & Deep Incubation:**
   `⟪ 遠 · 微 · 澄 ⟫` (Horizon $\rightarrow$ Precision $\rightarrow$ Settle)  
   *Use when:* Designing 2027 roadmaps, running sleep/dream cycles, committing continuity.

---

## 4. The 64-Hexagram Macro-Action Engine

WhiteMagic Gen3 maps the 64 King Wen Hexagrams directly to macro-actions:
* Each hexagram is composed of an **Upper Trigram** (Outer Environment) and a **Lower Trigram** (Inner Agent Posture).
* An agent can query, inspect, mutate, and cast hexagrams via CLI:
  ```bash
  # List all 64 hexagrams
  wm3 sutra hexagram list

  # Inspect a specific hexagram by number, Chinese name, or pinyin
  wm3 sutra hexagram 63
  wm3 sutra hexagram 既济
  wm3 sutra hexagram qian

  # Mutate changing line 1..6 and see the transformed hexagram
  wm3 sutra hexagram 1 --mutate-line 1
  ```
* Any hexagram name or ID passed to `wm3 sutra cast` or MCP `sutra_cast` is parsed automatically as a compound sutra.

---

## 5. Catuṣkoṭi K3 Dialectical Router

When an agent faces competing constraints (e.g. "Execute quickly" vs. "Run dry-run simulation", or "Verify strictly" vs. "Fuzz adversarially"), traditional systems freeze or flip-flop.

The **Tripartite Cognitive Router** applies Buddhist **Catuṣkoṭi** (tetralemma) logic:
* **$K_1$ Affirmed:** Pure Affirmation ($A \land \neg B$).
* **$K_2$ Denied:** Pure Negation ($\neg A \land B$).
* **$K_3$ Dialectical Contradiction:** Both Affirmed ($A \land B$). Dispatches paraconsistent dual-layer synthesis (e.g. running shadow simulation before execution, or vanguard execution inside an asynchronous verification envelope).
* **$K_4$ Neutral Agnosticism:** Neither Affirmed ($\neg A \land \neg B$). Escalate to deep horizon deliberation (`skel-deliberate-horizon`).

---

## 6. MCP & CLI Invocation Cheat Sheet

### Calling from IDEs via MCP (`whitemagic` MCP Server)
```json
// Direct Mudra Cast
{
  "name": "sutra_cast",
  "arguments": {
    "codon": "觀 察 芽",
    "execute": true
  }
}

// Compile Natural Language to Codon
{
  "name": "sutra_compile",
  "arguments": {
    "query": "verify code and isolate sandbox"
  }
}
```

### Calling from Terminal (`wm3`)
```bash
# Direct Cast
wm3 sutra cast "證 辨 界" --execute

# Natural Language Compilation
wm3 sutra compile "explore and inspect repository dependencies"

# Hexagram Macro-Action Inspection
wm3 sutra hexagram 63 --json
```
