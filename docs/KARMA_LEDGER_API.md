# Karma Ledger API v1.0.0

**Version:** karma-ledger-v1.0.0
**Module:** `whitemagic.dharma.karma_ledger`
**Storage:** `$WM_STATE_ROOT/dharma/karma_ledger.jsonl`
**Scope:** Persistent, append-only ethical governance ledger with Merkle hash chain integrity.

---

## Overview

The Karma Ledger tracks **declared vs. actual side-effects** of every tool invocation in the WhiteMagic dispatch pipeline. It provides:

- **Persistent append-only log** with Merkle hash chain (tamper-evident)
- **Voice Audit integration** — detects hallucinated tool claims
- **Auto-rotation** at 10MB with up to 3 rotated files kept
- **Edgerunner dual-log** — red-ops / blue-ops classification
- **XRPL anchoring** — optional Merkle root submission to XRP Ledger (via `karma_anchor.py`)

---

## API Reference

### `KarmaEntry`

```python
@dataclass
class KarmaEntry:
    timestamp: str          # ISO-8601
    ops_class: str          # "red-ops" or "blue-ops"
    tool: str               # Tool name
    declared: dict          # What the caller claimed
    actual: dict            # What actually happened
    entry_hash: str         # SHA-256 of this entry
    prev_hash: str          # Hash of previous entry (chain link)
```

### `KarmaLedger`

#### `record(ops_class, tool, declared, actual) -> KarmaEntry`
Record a tool invocation and its outcome.

```python
ledger.record(
    ops_class="blue-ops",
    tool="memory_write",
    declared={"key": "x", "value": "y"},
    actual={"key": "x", "value": "y", "bytes_written": 1024}
)
```

#### `report() -> dict`
Generate a summary report of all karma debt.

```python
report = ledger.report()
# → {"total_entries": 1432, "debt_total": 0.0, "red_ops_count": 12, ...}
```

#### `get_debt() -> float`
Get current karma debt balance. Positive = more declared than actual (overclaiming).

```python
debt = ledger.get_debt()
```

#### `verify_chain() -> bool`
Verify the integrity of the full Merkle hash chain. Returns `True` if no tampering detected.

```python
assert ledger.verify_chain()  # Raises AssertionError if chain broken
```

#### `merkle_root() -> str`
Return the Merkle root hash of the entire ledger. Used for XRPL anchoring.

```python
root = ledger.merkle_root()
# → "a1b2c3d4..."
```

#### `forgive(amount: float) -> float`
Reduce karma debt by a specified amount. Returns remaining debt.

```python
remaining = ledger.forgive(10.0)
```

#### `report_by_ops() -> dict`
Breakdown of entries by ops_class.

```python
breakdown = ledger.report_by_ops()
# → {"red-ops": {"count": 12, "debt": 5.0}, "blue-ops": {"count": 1420, "debt": 0.0}}
```

#### `rotation_stats() -> dict`
Get statistics about log file rotation.

```python
stats = ledger.rotation_stats()
# → {"active_file": "...", "rotated_files": 2, "total_size_mb": 24.5}
```

---

## Factory

```python
from whitemagic.dharma.karma_ledger import get_karma_ledger

ledger = get_karma_ledger()  # Singleton, stored at WM_STATE_ROOT/dharma/
```

---

## Integration Points

| Consumer | What It Records |
|----------|----------------|
| `unified_api.call_tool()` | Every tool dispatch |
| `voice_audit.py` | ClaimLog cross-check against ledger |
| `corpus_callosum.py` | Interhemispheric debate events |
| `dream_cycle.py` | Dream generation events |
| `shelter/manager.py` | Shelter operations |
| `tools/handlers/dharma.py` | `karma.report`, `karma.forgive` tools |
| `gratitude/pulse.py` | Forgives 10% of tip value as debt |

---

## XRPL Anchoring (Optional)

```python
from whitemagic.dharma.karma_anchor import compute_anchor, submit_anchor, verify_anchor

# Compute anchor data
anchor = compute_anchor()

# Submit Merkle root to XRP Ledger
tx = submit_anchor()  # Requires xrpl-py installed

# Verify an existing anchor
assert verify_anchor(tx_hash)
```

Graceful degradation: if `xrpl-py` is not installed, anchoring returns `missing_dependency` status.

---

## Data Integrity

- Every entry is SHA-256 hashed.
- Each entry links to the previous via `prev_hash`.
- `verify_chain()` validates the full chain.
- XRPL anchoring provides external timestamp proof.
- Storage format: JSONL (one JSON object per line).

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2026-05-15 | Initial release — Merkle chain, rotation, dual-log, XRPL anchor |
