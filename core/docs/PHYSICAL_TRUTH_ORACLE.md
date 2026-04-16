# Physical Truth Verification — Oracle Concept

> The trillion-dollar question: AIs can generate code and art, but they cannot easily verify physical truth.
> This document outlines WhiteMagic's approach to bridging the digital-physical divide.

---

## The Problem

AI agents excel at digital tasks: code, analysis, synthesis, coordination. But they **cannot independently verify** physical-world outcomes:

| Digital Truth (Agent can verify) | Physical Truth (Agent cannot verify) |
|--------------------------------|-------------------------------------|
| Code compiles and passes tests | The tree was actually planted |
| Transaction appeared on XRPL | The water is actually clean |
| Document was generated | The package actually arrived |
| API returned 200 OK | The building passed inspection |
| Memory was stored correctly | The patient received the medication |

This is the **fundamental limitation** of agent autonomy and the **fundamental value** of human participation in agent-driven systems.

---

## WhiteMagic's Current Approach

### Human Attestation Pattern

Today, WhiteMagic handles physical verification through a structured memory pattern:

```python
# 1. Agent creates a verification request
call_tool("create_memory",
    title="VERIFICATION_NEEDED: Solar panel installation at Site B",
    content="20 panels ordered, installer scheduled for March 20. Need photo + serial number verification.",
    tags=["physical_verification", "pending", "solar", "site_b"],
    importance=0.95
)

# 2. Human verifies in the real world and records attestation
call_tool("create_memory",
    title="VERIFIED: Solar panels installed at Site B",
    content="Confirmed 20 panels installed March 19. Photos in /evidence/site_b/. Serial numbers match order.",
    tags=["physical_verification", "confirmed", "solar", "site_b", "attested_by:lucas"],
    importance=1.0
)

# 3. Agent can now query verified physical state
results = call_tool("search_memories", query="solar panel verification site_b", tags=["confirmed"])
```

### Karma Ledger Integration

Physical verifications are tracked as karma events:

```python
# Declared: "Install solar panels"
# Actual: "Panels installed (verified by human attestation)"
# → Karma matches → Trust score increases
```

---

## Future: Oracle Network Design

### Architecture

```
Physical World
    │
    ├── IoT Sensors (automated)
    │       └── Temperature, air quality, water quality, GPS, cameras
    │
    ├── Human Attestors (manual)
    │       └── Photos, inspections, signed statements
    │
    ├── Third-Party Oracles (hybrid)
    │       └── Chainlink, UMA, API3 — existing oracle networks
    │
    └── Satellite/Remote Sensing (automated)
            └── Deforestation monitoring, crop health, urbanization
```

### WhiteMagic Oracle Integration Points

| Oracle Type | WhiteMagic Tool | Trust Level |
|------------|----------------|-------------|
| IoT sensor data | `create_memory` with `source: "iot_sensor"` tag | Medium (sensors can fail/be spoofed) |
| Human attestation | `create_memory` with `attested_by` tag | High (for known attestors) |
| Third-party oracle | `web_fetch` → parse → `create_memory` | Medium-High (depends on oracle reputation) |
| Satellite imagery | `web_fetch` → analyze → `create_memory` | High (hard to fake at scale) |
| Multi-source consensus | `ensemble.query` across sources | Highest (requires agreement) |

### Trust Scoring for Physical Claims

```python
# Future: physical_truth_score() function
def physical_truth_score(claim_id: str) -> float:
    """Score confidence in a physical-world claim based on evidence."""
    evidence = search_memories(tags=["physical_verification", claim_id])

    score = 0.0
    for e in evidence:
        if "iot_sensor" in e.tags:
            score += 0.3  # Sensor data
        if "attested_by" in str(e.tags):
            score += 0.4  # Human attestation
        if "satellite" in e.tags:
            score += 0.3  # Remote sensing
        if "third_party_oracle" in e.tags:
            score += 0.2  # External oracle

    return min(score, 1.0)
```

---

## Use Cases

### 1. Ecological Restoration Verification

**Scenario**: WhiteMagic Labs funds tree planting via gratitude revenue.

| Step | Actor | Action |
|------|-------|--------|
| 1 | Finance Agent | Allocates 100 XRP to reforestation project |
| 2 | Ops Agent | Coordinates with planting partner, tracks order |
| 3 | Human | Visits site, photographs planted trees, records GPS |
| 4 | Human | Creates attestation memory with evidence |
| 5 | QA Agent | Cross-references satellite imagery (before/after) |
| 6 | Finance Agent | Marks project as verified, updates karma ledger |

### 2. Healthcare Compliance

**Scenario**: Hospital agent tracks medication administration.

| Step | Actor | Action |
|------|-------|--------|
| 1 | Clinical Agent | Generates medication schedule |
| 2 | Nurse (Human) | Administers medication, scans barcode |
| 3 | EMR System | Records administration event |
| 4 | Clinical Agent | Queries EMR, creates verified memory |
| 5 | QA Agent | Runs compliance check against schedule |

### 3. Supply Chain Tracking

**Scenario**: Agent-run company verifies product delivery.

| Step | Actor | Action |
|------|-------|--------|
| 1 | Sales Agent | Processes order, creates shipment memory |
| 2 | Logistics API | Provides tracking updates (digital truth) |
| 3 | Customer | Confirms receipt (physical truth attestation) |
| 4 | Support Agent | Marks delivery verified, triggers karma update |

---

## Competitive Moat

This is WhiteMagic's long-term strategic advantage:

1. **Memory + Governance + Oracle = Complete Agent Infrastructure**
   - Other tools provide memory OR governance OR oracle integration
   - WhiteMagic provides all three with a unified karma/trust system

2. **Physical truth verification is the bottleneck for agent autonomy**
   - Code generation is solved (agents write code)
   - Content generation is solved (agents write text)
   - Physical verification remains human-dependent
   - The tool that bridges this gap captures massive value

3. **The trust scoring system compounds**
   - Every verified physical claim increases the attestor's trust score
   - Higher-trust attestors can verify higher-stakes claims
   - Network effects: more attestors → more verified claims → more trust

---

## Implementation Roadmap

### Phase 1 (v15.0) — Structured Attestation
- Formalize the `physical_verification` tag convention
- Add `attested_by` field to memory metadata
- Create `verification.request` and `verification.attest` tool pair
- Karma ledger tracks physical vs digital claims separately

### Phase 2 (v16.0) — IoT Integration
- `whitemagic[iot]` extra for sensor data ingestion
- MQTT subscriber for real-time sensor feeds
- Auto-create memories from sensor events
- Anomaly detection on sensor data (detect spoofing)

### Phase 3 (v17.0) — Oracle Network
- Integration with Chainlink / UMA / API3
- Multi-source consensus engine (extension of `ensemble.query`)
- On-chain anchoring of physical truth claims (XRPL + Karma Transparency Log)
- Reputation system for attestors (human and machine)

---

*Concept document: February 2026 — WhiteMagic v14.6.0*
