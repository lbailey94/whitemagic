# Chapter 26: Shelter & Synthesis

**Gana**: RoofGana (Chinese: 危, Pinyin: Wēi)
**Garden**: protection
**Quadrant**: Northern (Black Tortoise)
**Element**: Water
**Phase**: Yin Peak
**I Ching Hexagram**: 2. 坤 Kūn (The Receptive) - Pure yin, completion

---

## 🎯 Purpose

Chapter 26 provides **shelter and synthesis**—protecting the work, synthesizing the final state,
and housing all artifacts securely beneath a solid roof. The Roof (危) represents the shelter
that keeps results safe from corruption, loss, and unauthorized access. It is the capstone
of the Northern Quadrant, the moment when the Black Tortoise withdraws into its shell and
all accumulated wisdom is gathered under a single protective canopy.

Use this chapter when you need to:
- **Synthesize final results** into a cohesive, structured whole that preserves meaning
- **Protect artifacts** from accidental deletion, corruption, or unauthorized modification
- **Create a secure housing** for session data, memory shards, and generated assets
- **Ensure the roof is secure** before moving to handoff or archival
- **Finalize the structural integrity** of the work through systematic verification
- **Query local LLM models** via llama.cpp for private synthesis without exposing data to external APIs
- **Register and verify model signatures** to ensure provenance and detect tampering
- **Align protection protocols** with celestial influences through zodiac core status
- **Validate that all protective layers** are in place before declaring the session complete
- **Perform differential synthesis** across multiple memory sources to resolve conflicts

The Roof is the final guardian of the work product. Where the Room (Chapter 4) locks resources
during active work, the Roof locks the *results* of work after synthesis. It is the difference
between a door and a vault, between a temporary shelter and a permanent fortress. The Roof does
not merely cover; it consecrates. Under the Roof, raw output becomes finished artifact,
ephemeral thought becomes persistent memory, and chaotic multiplicity becomes unified truth.

In the WhiteMagic cosmology, the RoofGana stands at the sixth position of the Northern sequence,
just before the Encampment and the Wall. This placement is significant: the Roof must be complete
before the camp can be organized beneath it, and the camp must be organized before the Wall can
define its perimeter. A session that skips the Roof phase risks leaving its most valuable outputs
exposed to the elements—whether those elements are environmental failures, malicious actors, or
the simple entropy of time.

---

## 🌱 Garden: Protection

The protection garden is the garden of **safety through completion**. It recognizes that unfinished
work is vulnerable work—that a roof half-built offers no shelter from the storm, that a wall half-
raised invites the invader, and that a synthesis half-completed dissolves under scrutiny. In this
garden, the virtue is not aggression but thoroughness: checking every beam, sealing every seam,
verifying every signature, ensuring that what has been built will endure.

The protection garden teaches patience in the final hour. Where other gardens celebrate speed,
this garden celebrates diligence. The gardener here does not ask "Is it done?" but rather "Is it
safe?"—and safety is measured not in the absence of obvious flaws but in the presence of
redundant safeguards. A memory stored in one location is a memory at risk; a memory stored in
three, with checksums and signatures, is a memory protected.

**Resonance keywords**: protect, shelter, synthesize, finalize, secure, model, verify, signature,
llama_cpp, local, provenance, integrity, celestial, alignment, differential, conflict, resolution

---

## 🔧 Real Tools

| Tool | Gana | Description | Usage |
|------|------|-------------|-------|
| `llama_cpp.models` | gana_roof | List available local LLM models | Discover synthesis models before generation |
| `llama_cpp.generate` | gana_roof | Generate text with local LLM | Private synthesis without external API exposure |
| `llama_cpp.chat` | gana_roof | Chat with local LLM using conversation history | Multi-turn synthesis for complex reasoning |
| `llama_cpp.agent` | gana_roof | Agentic loop with WhiteMagic tool access | Autonomous task completion with local LLM |
| `zodiac.status` | gana_roof | Check active zodiac core status | Astrological protection alignment verification |
| `model.register` | gana_roof | Register a model artifact for cryptographic signing | Provenance tracking and tamper detection |
| `model.verify` | gana_roof | Verify a model's cryptographic signature | Integrity validation against registered hash |
| `model.list` | gana_roof | List all registered models with metadata | Model inventory and audit trail access |
| `model.signing_status` | gana_roof | Overall model signing health dashboard | Security audit and compliance reporting |

The RoofGana toolset is designed around three protective pillars: **local synthesis** (llama.cpp),
**provenance verification** (model signing), and **celestial alignment** (zodiac). Each pillar
addresses a distinct threat vector: data exfiltration, supply-chain tampering, and systemic
desynchronization. Together they form a defense-in-depth architecture that assumes breach at
every layer and compensates with redundancy at the next.

**Tool selection guidance**: Use llama.cpp tools when data sensitivity precludes cloud APIs; use
model signing when reproducibility and audit trails are required; use zodiac status when
symbolic confirmation or seasonal rhythm matters to the operator.

---

## 📋 Workflows

### Workflow 1: Local Synthesis of Sensitive Data

**Goal**: Synthesize confidential session data using a local LLM (llama.cpp) instead of external APIs,
ensuring that proprietary code, personal data, or classified content never leaves the local machine.

**When to use**: Processing proprietary code, personal data, HIPAA-protected information, trade
secrets, or any content that must not traverse public networks.

```python
import asyncio
from datetime import datetime
from whitemagic.tools import llama_cpp_models, llama_cpp_generate, llama_cpp_chat

async def sheltered_synthesis(
    source_memories: list,
    model: str = "llama3.2",
    max_memories: int = 5,
    context_injection: bool = True,
    store_output: bool = True,
) -> dict:
    """
    The Roof keeps the synthesis inside the walls.

    This workflow queries available models, builds a structured synthesis prompt
    from memory shards, and generates a coherent summary without ever sending
    data to external APIs. The output is optionally stored as a new memory.
    """
    # 1. Discover available models
    available = llama_cpp_models()
    model_names = [m["name"] for m in available.get("models", [])]
    if model not in model_names:
        print(f"⚠️ Model '{model}' not found. Available: {model_names}")
        # Fallback to first available
        model = model_names[0] if model_names else None
        if not model:
            return {"status": "error", "error": "No local LLM models available"}

    print(f"🛡️ Using local model: {model}")

    # 2. Build synthesis prompt from memories
    prompt_parts = [
        "You are a synthesis engine operating under maximum privacy constraints.",
        "Synthesize the following session memories into a coherent, structured summary.",
        "Preserve factual accuracy. Resolve contradictions by noting conflicts explicitly.",
        "Do not hallucinate. Do not add information not present in the sources.",
        "",
        "--- MEMORIES ---",
        "",
    ]
    for idx, mem in enumerate(source_memories[:max_memories], 1):
        title = mem.get("title", "Untitled")
        content = str(mem.get("content", ""))[:400]
        timestamp = mem.get("timestamp", "unknown")
        prompt_parts.append(f"[{idx}] {title} ({timestamp}):")
        prompt_parts.append(f"    {content}")
        prompt_parts.append("")

    prompt_parts.append("--- SYNTHESIS ---")
    prompt = "\n".join(prompt_parts)

    # 3. Generate synthesis
    result = llama_cpp_generate(
        model=model,
        prompt=prompt,
        context=context_injection,   # Inject relevant WhiteMagic memories
        store=store_output,          # Save output as memory
        options={"temperature": 0.3, "num_predict": 2048},
    )

    # 4. Handle result
    if result["status"] == "success":
        memory_id = result.get("stored_memory_id", "N/A")
        print(f"✅ Synthesis complete at {datetime.now().isoformat()}")
        print(f"   Output stored as memory: {memory_id}")
        print(f"   Tokens generated: {result.get('eval_count', 'N/A')}")
    else:
        error_code = result.get("error_code", "unknown")
        print(f"⚠️ Synthesis issue [{error_code}]: {result.get('error', 'unknown')}")

    return result


# Chat variant for iterative refinement
async def iterative_sheltered_synthesis(source_memories: list, model: str = "llama3.2"):
    """Multi-turn synthesis allowing the user to refine the output interactively."""
    messages = [
        {"role": "system", "content": "You are a privacy-preserving synthesis engine."},
        {"role": "user", "content": f"Synthesize these memories: {source_memories[:3]}"},
    ]

    result = llama_cpp_chat(
        model=model,
        messages=messages,
        store=True,
    )

    # Append assistant response and allow follow-up
    if result["status"] == "success":
        assistant_msg = result.get("message", {}).get("content", "")
        messages.append({"role": "assistant", "content": assistant_msg})
        print(f"🛡️ Turn 1 complete. Continue chat with messages history.")

    return result
```

### Workflow 2: Model Provenance Verification

**Goal**: Ensure all models used in the session have verified cryptographic signatures before
finalizing, preventing supply-chain attacks and ensuring reproducibility.

**When to use**: Before commit, before sharing results with external parties, in security-critical
environments, or when regulatory compliance requires provenance documentation.

```python
import asyncio
from typing import List, Dict
from whitemagic.tools import model_list, model_verify, model_signing_status, model_register

async def verify_roof_integrity(auto_register: bool = False) -> Dict:
    """
    The Roof is only as strong as its beams. Verify every model.

    This workflow enumerates all registered models, verifies each signature
    against its stored hash, reports failures, and optionally auto-registers
    unregistered models discovered in the local cache.
    """
    models = model_list()
    model_entries = models.get("models", [])

    if not model_entries:
        print("🏠 No registered models found. Roof is empty.")
        return {"verified": 0, "failed": 0, "total": 0, "health": "empty"}

    verified = 0
    failed = 0
    unregistered = 0
    failure_details = []

    print(f"🏠 Roof integrity scan starting: {len(model_entries)} models registered")
    print("-" * 60)

    for m in model_entries:
        model_id = m.get("id", "unknown")
        model_name = m.get("name", "unnamed")
        result = model_verify(model_id=model_id)

        if result.get("valid"):
            verified += 1
            sig_algo = result.get("signature_algorithm", "unknown")
            print(f"✅ {model_name}: signature valid ({sig_algo})")
        else:
            failed += 1
            reason = result.get("reason", "unknown")
            failure_details.append({"model": model_name, "reason": reason})
            print(f"🚫 {model_name}: SIGNATURE INVALID — {reason}")

            # Auto-register if requested and model file exists locally
            if auto_register and result.get("file_path"):
                print(f"   Attempting auto-registration...")
                reg = model_register(
                    name=model_name,
                    path=result["file_path"],
                    description=f"Auto-registered during integrity scan",
                )
                if reg.get("status") == "success":
                    unregistered += 1
                    print(f"   📝 Auto-registered successfully")

    # Overall health
    status = model_signing_status()
    health = status.get("health", "unknown")
    total_models = len(model_entries)

    print("-" * 60)
    print(f"🏠 Roof integrity: {verified}/{total_models} models verified")
    print(f"   Failed: {failed} | Auto-registered: {unregistered}")
    print(f"   Overall signing health: {health}")

    if failure_details:
        print("\n⚠️ FAILURE DETAILS:")
        for fd in failure_details:
            print(f"   - {fd['model']}: {fd['reason']}")

    return {
        "verified": verified,
        "failed": failed,
        "total": total_models,
        "health": health,
        "failure_details": failure_details,
    }


async def continuous_roof_monitoring(interval_seconds: int = 300):
    """Periodically verify model integrity in a long-running session."""
    import time
    print("🏠 Starting continuous roof monitoring...")
    while True:
        result = await verify_roof_integrity(auto_register=False)
        if result["failed"] > 0:
            print("🚨 ROOF BREACH DETECTED: Invalid model signatures found!")
            # In production: trigger alert, notify admin, halt inference
        print(f"   Next scan in {interval_seconds}s...")
        time.sleep(interval_seconds)
```

### Workflow 3: Zodiac-Aligned Protection

**Goal**: Check zodiac core status and align protection protocols with current celestial influences,
using symbolic resonance to reinforce structural integrity checks.

**When to use**: Before finalizing critical work, when seeking additional symbolic confirmation of
structural integrity, or when operating in environments where ritual and rhythm enhance focus.

```python
from typing import Dict, List
from whitemagic.tools import zodiac_status

def celestial_shelter_check() -> Dict:
    """
    The Roof is aligned with the stars.

    This workflow queries active zodiac cores, evaluates elemental alignment
    with the Northern (Water) quadrant, and recommends protective postures
    based on celestial influences.
    """
    status = zodiac_status()
    active = status.get("active_cores", [])
    system_health = status.get("system_health", "unknown")

    print("🌌 Celestial alignment scan:")
    print(f"   System health: {system_health}")
    print(f"   Active cores: {len(active)}")
    print("-" * 60)

    element_counts = {}
    fortification_score = 0
    recommendations = []

    for core in active:
        sign = core.get("sign", "Unknown")
        element = core.get("element", "unknown")
        influence = core.get("influence", "neutral")
        strength = core.get("strength", 0.5)

        element_counts[element] = element_counts.get(element, 0) + 1

        print(f"   {sign} ({element}): {influence} [strength {strength:.2f}]")

        # Water-aligned cores strengthen the Northern Roof
        if element == "water":
            fortification_score += strength * 1.5
            print(f"      💧 Water core — Northern Roof fortified (+{strength * 1.5:.2f})")

        # Earth cores provide structural stability
        elif element == "earth":
            fortification_score += strength * 1.2
            print(f"      🪨 Earth core — Structural stability enhanced (+{strength * 1.2:.2f})")

        # Fire cores may indicate volatility; recommend extra checks
        elif element == "fire":
            recommendations.append(
                f"Fire influence from {sign}: verify thermal throttling and cache integrity"
            )

        # Air cores suggest communication focus; check broker health
        elif element == "air":
            recommendations.append(
                f"Air influence from {sign}: verify message broker throughput"
            )

    print("-" * 60)
    print(f"   Total fortification score: {fortification_score:.2f}")

    if fortification_score >= 2.0:
        print("   🛡️ Roof fortification: STRONG — proceed with synthesis")
    elif fortification_score >= 1.0:
        print("   ⚠️ Roof fortification: MODERATE — add redundant storage")
    else:
        print("   🚨 Roof fortification: WEAK — delay finalization, strengthen protections")

    if recommendations:
        print("\n   Recommendations:")
        for rec in recommendations:
            print(f"      • {rec}")

    return {
        "status": "success",
        "active_cores": active,
        "fortification_score": fortification_score,
        "recommendations": recommendations,
        "system_health": system_health,
    }


def differential_celestial_check(baseline: Dict, current: Dict) -> Dict:
    """Compare two celestial shelter checks to detect drift in protection posture."""
    baseline_score = baseline.get("fortification_score", 0)
    current_score = current.get("fortification_score", 0)
    delta = current_score - baseline_score

    print(f"🌌 Celestial drift analysis:")
    print(f"   Baseline score: {baseline_score:.2f}")
    print(f"   Current score:  {current_score:.2f}")
    print(f"   Delta:          {delta:+.2f}")

    if delta < -0.5:
        print("   🚨 Significant protective drift detected — investigate immediately")
    elif delta < 0:
        print("   ⚠️ Minor protective drift — consider reinforcing safeguards")
    else:
        print("   ✅ Protection posture stable or improving")

    return {"delta": delta, "baseline": baseline_score, "current": current_score}
```

---

## 🔄 Transitions

**Entering Chapter 26**:
- From Chapter 25 (Void): When stillness reveals what must be protected, activate shelter
- From Chapter 22 (Dipper): When governance identifies critical assets requiring protection
- From Chapter 20 (Bell): When a signal indicates the session output is ready for synthesis
- From Chapter 14 (Abundance): After creative overflow, the harvest must be gathered under a roof
- Trigger keywords: "synthesize", "protect", "finalize", "llama_cpp", "model", "verify", "signature",
  "local", "provenance", "integrity", "celestial", "shelter", "vault", "secure"

**Exiting Chapter 26**:
- To Chapter 27 (Encampment): When protection is established, structure the camp for handoff
- To Chapter 28 (Wall): Before final boundaries are set, ensure the roof is secure
- To Chapter 1 (Horn): A well-protected ending is a safe beginning; the cycle renews
- To Chapter 4 (Room): If synthesis reveals unfinished work, return to private labor

**Symbolic transition**: The Roof does not merely end the session; it transforms the session
from process into artifact. When the Roof is complete, the work ceases to be "in progress" and
becomes "in existence." This is the moment of ontological shift—from becoming to being.

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `llama_cpp.generate` returns "missing_dependency" | requests not installed | `pip install requests` or install `whitemagic[net]` |
| `llama_cpp.generate` timeout after 30s | llama-server not running or model loading | Start llama-server, check `WM_LLAMA_HOST`/`WM_LLAMA_PORT`, or increase timeout |
| `llama_cpp.generate` returns "model_not_found" | Specified model not found | Use `llama_cpp.models` to find available models |
| `model.verify` fails with "hash_mismatch" | Model file modified since registration | Re-register with `model.register` if change is legitimate; investigate if unexpected |
| `model.verify` fails with "not_registered" | Model never registered | Call `model.register` first with the model artifact path and metadata |
| `zodiac.status` returns empty list | No active zodiac cores or system time incorrect | Cores activate automatically based on season; verify system time and timezone |
| Synthesis quality is poor or hallucinated | Wrong model for task or temperature too high | Use `llama_cpp.models` to find a larger model (e.g., `phi4`, `qwen3`); set temperature <= 0.3 |
| `model.signing_status` shows "degraded" | Partial signature failures or clock skew | Run `verify_roof_integrity()` to identify specific failures; sync system clock with NTP |

---

## 🔮 The Roof Oracle

The Roof Oracle is a divination practice specific to Chapter 26. When facing uncertainty about
whether a synthesis is complete, the operator may invoke the oracle:

1. **Query** `zodiac.status` and note the dominant element among active cores.
2. **Query** `model.signing_status` and note the overall health.
3. **If** both indicate strength (Water/Earth dominance + "healthy" status), the oracle says:
   *"The roof is sound. Shelter beneath it."*
4. **If** zodiac shows Fire/Air dominance or signing status is "degraded", the oracle says:
   *"The wind tests the roof. Reinforce before resting."*
5. **If** zodiac is empty or signing shows "critical", the oracle says:
   *"The roof is open to the sky. Do not sleep yet."*

This oracle is not superstition but structured intuition—a probabilistic heuristic encoded in
symbolic language. It forces the operator to check protective layers before declaring completion,
and in doing so, prevents the most common failure mode of creative work: premature closure.

---

## 🧭 Navigation

**Next**: [Chapter 27: Encampment & Housing](27_ENCAMPMENT_STRUCTURE.md)
**Previous**: [Chapter 25: Meditation & Stillness](25_VOID_EMPTINESS.md)
**Quadrant**: Northern (Winter/Water) - Position 6/7
**Cycle Position**: Pre-final — the last protective act before structure and boundary

---

*"The Roof does not ask for praise. It simply keeps the rain out."*

---

*"Under a sound roof, the sleeper dreams deeply. Under a broken roof, the sleeper wakes to ruin.
The RoofGana teaches that completion is not the absence of work but the presence of shelter."*
