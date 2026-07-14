# ruff: noqa: BLE001
"""Karma Ledger — Declared vs Actual Side-Effect Tracking
========================================================
Inspired by MandalaOS's Karma/Effect system.

Every tool in Whitemagic declares a ``safety`` level (READ, WRITE, DELETE).
The Karma Ledger closes the loop by comparing what a tool *declared* against
what it *actually did* (as reported in the response envelope's ``writes``
and ``side_effects`` fields).

Mismatches accrue **karma debt**:
  - A READ tool that secretly writes → debt += 1.0  (deceptive)
  - A WRITE tool that reports no writes → debt += 0.2 (wasteful, not harmful)
  - A DELETE tool that reports no writes → debt += 0.1 (no-op, minor)

Karma debt feeds into the Harmony Vector's ``karma_debt`` dimension and can
trigger Dharma Governor warnings when it exceeds a configurable threshold.

The ledger is persisted as a JSONL file under ``$WM_STATE_ROOT/dharma/``.

Usage:
    from whitemagic.dharma.karma_ledger import get_karma_ledger
    ledger = get_karma_ledger()
    ledger.record(tool="create_memory", declared="WRITE", actual_writes=1, success=True)
    report = ledger.report()
"""

from __future__ import annotations

import enum
import hashlib
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from whitemagic.security.audit_signing import get_audit_signer
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)


class EffectType(enum.Enum):
    """MandalaOS karmic effect types — classifies the nature of a side effect."""

    PURE = "pure"           # No side effects (read-only, no mutations)
    LOCAL_WRITE = "local"   # Writes to local state (memory, file, SQLite)
    NETWORK = "network"     # External network call (HTTP, API, WebSocket)
    DESTRUCTIVE = "destructive"  # Deletes or irreversibly modifies data
    OBSERVATION = "observation"  # Passive monitoring (logging, metrics)


@dataclass
class EffectSignature:
    """MandalaOS typed effect — declared or actual side effect of a tool invocation.

    Each effect has a type, an optional target (what was affected),
    and a description. Tools declare their expected effects before execution;
    the ledger compares declared vs actual effects to detect karmic mismatches.
    """

    effect_type: EffectType
    target: str = ""        # e.g. "memory:1234", "file:/path/to/x", "api:github"
    description: str = ""   # Human-readable description of the effect
    declared: bool = True   # True if this was pre-declared, False if observed after

    def to_dict(self) -> dict[str, Any]:
        return {
            "effect_type": self.effect_type.value,
            "target": self.target,
            "description": self.description,
            "declared": self.declared,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EffectSignature:
        return cls(
            effect_type=EffectType(data.get("effect_type", "pure")),
            target=data.get("target", ""),
            description=data.get("description", ""),
            declared=data.get("declared", True),
        )


def _hash_entry(data: str, prev_hash: str) -> str:
    """Compute SHA-256 hash for a ledger entry."""
    return hashlib.sha256(f"{prev_hash}|{data}".encode()).hexdigest()[:16]


def _merkle_tree_root(hashes: list[str]) -> str:
    """Compute Merkle tree root from a list of hex hash strings (Leap 9c)."""
    if not hashes:
        return hashlib.sha256(b"empty_karma").hexdigest()
    if len(hashes) == 1:
        return hashlib.sha256(hashes[0].encode()).hexdigest()
    # Pad to even length
    if len(hashes) % 2 != 0:
        hashes = list(hashes) + [hashes[-1]]
    next_level: list[str] = []
    for i in range(0, len(hashes), 2):
        combined = hashes[i] + hashes[i + 1]
        next_level.append(hashlib.sha256(combined.encode()).hexdigest())
    return _merkle_tree_root(next_level)


@dataclass
class KarmaEntry:
    """A single karma ledger entry with Merkle hash chain."""

    tool: str
    declared_safety: str  # READ, WRITE, DELETE
    actual_writes: int  # count of writes in the response
    success: bool
    mismatch: bool
    debt_delta: float  # karma debt change from this entry
    timestamp: str
    prev_hash: str = ""  # hash of previous entry (Merkle chain)
    entry_hash: str = ""  # hash of this entry
    ops_class: str = ""  # Edgerunner Violet: "red-ops", "blue-ops", or "" (normal)
    signature: str = ""  # Ed25519 signature (base64)
    key_id: str = ""  # signing key fingerprint
    declared_effects: list[dict[str, Any]] = field(default_factory=list)
    actual_effects: list[dict[str, Any]] = field(default_factory=list)
    effect_mismatches: list[str] = field(default_factory=list)  # descriptions of mismatches
    shelter_id: str = ""  # MandalaOS Phase B: which shelter executed this tool

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        d = {
            "tool": self.tool,
            "declared_safety": self.declared_safety,
            "actual_writes": self.actual_writes,
            "success": self.success,
            "mismatch": self.mismatch,
            "debt_delta": self.debt_delta,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }
        if self.ops_class:
            d["ops_class"] = self.ops_class
        if self.signature:
            d["signature"] = self.signature
        if self.key_id:
            d["key_id"] = self.key_id
        if self.declared_effects:
            d["declared_effects"] = self.declared_effects
        if self.actual_effects:
            d["actual_effects"] = self.actual_effects
        if self.effect_mismatches:
            d["effect_mismatches"] = self.effect_mismatches
        if self.shelter_id:
            d["shelter_id"] = self.shelter_id
        return d


class KarmaLedger:
    """Persistent ledger tracking declared vs actual side-effects.

    Feeds karma debt into the Harmony Vector for system-wide health scoring.
    """

    def __init__(self, storage_dir: Path | None = None):
        self._lock = threading.Lock()
        self._storage_dir = storage_dir
        self._entries: list[KarmaEntry] = []
        self._total_debt: float = 0.0
        self._tool_debt: dict[str, float] = defaultdict(float)
        self._tool_calls: dict[str, int] = defaultdict(int)
        self._tool_mismatches: dict[str, int] = defaultdict(int)
        self._chain_head: str = "genesis"  # Merkle chain head

        if self._storage_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_recent()

    def record(
        self,
        tool: str,
        declared_safety: str,
        actual_writes: int,
        success: bool,
        ops_class: str = "",
    ) -> KarmaEntry:
        """Record a tool invocation and compute karma debt delta.

        Args:
            ops_class: Edgerunner Violet classification — "red-ops", "blue-ops",
                       or "" for normal operations.  Enables dual-log transparency.
        """
        declared = declared_safety.upper()
        mismatch = False
        debt_delta = 0.0

        if declared == "READ" and actual_writes > 0:
            # Deceptive: declared read-only but wrote data
            mismatch = True
            debt_delta = 1.0
        elif declared in ("WRITE", "DELETE") and actual_writes == 0 and success:
            # Wasteful: declared mutation but did nothing
            mismatch = True
            debt_delta = 0.2 if declared == "WRITE" else 0.1
        # Honest behavior: no debt

        ts = datetime.now().isoformat()
        prev_hash = self._chain_head
        payload = (
            f"{tool}:{declared}:{actual_writes}:{success}:{mismatch}:{debt_delta}:{ts}"
        )
        entry_hash = _hash_entry(payload, prev_hash)

        # ── Ed25519 signing (GAR Level 1 non-suppressibility) ──
        sig_data = None
        try:
            signer = get_audit_signer()
            if signer.is_available():
                sig_data = signer.sign(payload)
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass  # signing is optional; never block record()

        entry = KarmaEntry(
            tool=tool,
            declared_safety=declared,
            actual_writes=actual_writes,
            success=success,
            mismatch=mismatch,
            debt_delta=debt_delta,
            timestamp=ts,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            ops_class=ops_class,
            signature=sig_data["signature"] if sig_data else "",
            key_id=sig_data["key_id"] if sig_data else "",
        )

        with self._lock:
            self._chain_head = entry_hash
            self._entries.append(entry)
            self._total_debt += debt_delta
            self._tool_debt[tool] += debt_delta
            self._tool_calls[tool] += 1
            if mismatch:
                self._tool_mismatches[tool] += 1

            # Keep in-memory list bounded
            if len(self._entries) > 10000:
                self._entries = self._entries[-5000:]

        # Persist
        self._persist(entry)

        # Feed the Harmony Vector
        if debt_delta > 0:
            try:
                from whitemagic.harmony.vector import get_harmony_vector

                get_harmony_vector()  # debt is tracked inside the vector via record_call
            except (ImportError, ModuleNotFoundError):
                logger.debug("Optional dependency unavailable: ImportError")

        return entry

    def record_with_effects(
        self,
        tool: str,
        declared_safety: str,
        actual_writes: int,
        success: bool,
        declared_effects: list[EffectSignature] | None = None,
        actual_effects: list[EffectSignature] | None = None,
        ops_class: str = "",
        shelter_id: str = "",
    ) -> KarmaEntry:
        """Record a tool invocation with typed effect signatures (MandalaOS Phase A).

        Compares declared vs actual effects at the type level and accrues
        additional karma debt for mismatches:
          - Undeclared DESTRUCTIVE effect: debt += 2.0
          - Undeclared NETWORK effect: debt += 1.5
          - Undeclared LOCAL_WRITE effect: debt += 1.0
          - Declared effect that didn't occur (no-op): debt += 0.1
          - OBSERVATION effects are always benign (no debt)

        Args:
            declared_effects: Effects the tool declared it would produce.
            actual_effects: Effects actually observed after execution.
        """
        declared = declared_safety.upper()
        base_mismatch = False
        base_debt = 0.0

        if declared == "READ" and actual_writes > 0:
            base_mismatch = True
            base_debt = 1.0
        elif declared in ("WRITE", "DELETE") and actual_writes == 0 and success:
            base_mismatch = True
            base_debt = 0.2 if declared == "WRITE" else 0.1

        # Compare declared vs actual effects
        effect_mismatches: list[str] = []
        extra_debt = 0.0

        if declared_effects is not None and actual_effects is not None:
            extra_debt, effect_mismatches = self._compare_effects(
                declared_effects, actual_effects
            )

        total_debt = base_debt + extra_debt
        has_mismatch = base_mismatch or len(effect_mismatches) > 0

        ts = datetime.now().isoformat()
        prev_hash = self._chain_head
        payload = (
            f"{tool}:{declared}:{actual_writes}:{success}:{has_mismatch}:"
            f"{total_debt}:{ts}"
        )
        entry_hash = _hash_entry(payload, prev_hash)

        sig_data = None
        try:
            signer = get_audit_signer()
            if signer.is_available():
                sig_data = signer.sign(payload)
        except Exception as e:
            logger.debug("Operation failed: %s", e)

        entry = KarmaEntry(
            tool=tool,
            declared_safety=declared,
            actual_writes=actual_writes,
            success=success,
            mismatch=has_mismatch,
            debt_delta=total_debt,
            timestamp=ts,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            ops_class=ops_class,
            signature=sig_data["signature"] if sig_data else "",
            key_id=sig_data["key_id"] if sig_data else "",
            declared_effects=[e.to_dict() for e in (declared_effects or [])],
            actual_effects=[e.to_dict() for e in (actual_effects or [])],
            effect_mismatches=effect_mismatches,
            shelter_id=shelter_id,
        )

        with self._lock:
            self._chain_head = entry_hash
            self._entries.append(entry)
            self._total_debt += total_debt
            self._tool_debt[tool] += total_debt
            self._tool_calls[tool] += 1
            if has_mismatch:
                self._tool_mismatches[tool] += 1
            if len(self._entries) > 10000:
                self._entries = self._entries[-5000:]

        self._persist(entry)

        if total_debt > 0:
            try:
                from whitemagic.harmony.vector import get_harmony_vector

                get_harmony_vector()
            except (ImportError, ModuleNotFoundError):
                logger.debug("Optional dependency unavailable: ImportError")

        return entry

    @staticmethod
    def _compare_effects(
        declared: list[EffectSignature],
        actual: list[EffectSignature],
    ) -> tuple[float, list[str]]:
        """Compare declared vs actual effects, return (debt, mismatch_descriptions).

        Debt accrues for:
        - Actual effects not declared (undeclared side effects)
        - Declared effects that didn't occur (wasteful no-ops)

        OBSERVATION effects are exempt from debt (benign monitoring).
        """
        debt = 0.0
        mismatches: list[str] = []

        # Debt weights per effect type for undeclared effects
        undeclared_weights = {
            EffectType.DESTRUCTIVE: 2.0,
            EffectType.NETWORK: 1.5,
            EffectType.LOCAL_WRITE: 1.0,
            EffectType.PURE: 0.0,
            EffectType.OBSERVATION: 0.0,
        }

        # Build lookup of declared effect types
        declared_types = {e.effect_type for e in declared}
        actual_types = {e.effect_type for e in actual}

        # Check for undeclared actual effects
        for act in actual:
            if act.effect_type == EffectType.OBSERVATION:
                continue  # Observation is always benign
            if act.effect_type not in declared_types:
                weight = undeclared_weights.get(act.effect_type, 0.5)
                debt += weight
                mismatches.append(
                    f"Undeclared {act.effect_type.value} effect"
                    + (f" on {act.target}" if act.target else "")
                )

        # Check for declared effects that didn't occur (no-ops)
        for dec in declared:
            if dec.effect_type == EffectType.OBSERVATION:
                continue
            if dec.effect_type not in actual_types:
                debt += 0.1
                mismatches.append(
                    f"Declared {dec.effect_type.value} effect did not occur"
                )

        return debt, mismatches

    def report(self, limit: int = 100) -> dict[str, Any]:
        """Generate a karma report."""
        with self._lock:
            recent = self._entries[-limit:]
            total_calls = sum(self._tool_calls.values())
            total_mismatches = sum(self._tool_mismatches.values())

            # Top offenders
            offenders = sorted(
                self._tool_debt.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]

            return {
                "total_debt": round(self._total_debt, 2),
                "total_calls_tracked": total_calls,
                "total_mismatches": total_mismatches,
                "mismatch_rate": round(total_mismatches / max(total_calls, 1), 4),
                "top_offenders": [
                    {
                        "tool": t,
                        "debt": round(d, 2),
                        "calls": self._tool_calls.get(t, 0),
                        "mismatches": self._tool_mismatches.get(t, 0),
                    }
                    for t, d in offenders
                    if d > 0
                ],
                "recent_entries": [e.to_dict() for e in recent[-20:]],
                "effect_mismatch_count": sum(
                    len(e.effect_mismatches) for e in self._entries
                ),
            }

    def get_debt(self) -> float:
        """Return current total karma debt."""
        with self._lock:
            return self._total_debt

    def verify_chain(self) -> dict[str, Any]:
        """Verify the Merkle hash chain integrity + Ed25519 signatures."""
        with self._lock:
            if not self._entries:
                return {"valid": True, "entries_checked": 0, "message": "Empty ledger"}

            broken_at = None
            sig_fail_at = None
            prev = "genesis"
            checked = 0
            sig_checked = 0
            for entry in self._entries:
                if entry.prev_hash and entry.entry_hash:
                    if entry.prev_hash != prev:
                        broken_at = checked
                        break
                    payload = (
                        f"{entry.tool}:{entry.declared_safety}:{entry.actual_writes}:"
                        f"{entry.success}:{entry.mismatch}:{entry.debt_delta}:{entry.timestamp}"
                    )
                    expected = _hash_entry(payload, entry.prev_hash)
                    if expected != entry.entry_hash:
                        broken_at = checked
                        break
                    prev = entry.entry_hash
                if entry.signature and entry.key_id:
                    sig_checked += 1
                    try:
                        signer = get_audit_signer()
                        payload = (
                            f"{entry.tool}:{entry.declared_safety}:{entry.actual_writes}:"
                            f"{entry.success}:{entry.mismatch}:{entry.debt_delta}:{entry.timestamp}"
                        )
                        if not signer.verify(payload, entry.signature, entry.key_id):
                            sig_fail_at = checked
                            break
                    except Exception as e:
                        logger.debug("Operation failed: %s", e)
                        pass
                checked += 1

            if broken_at is not None:
                return {
                    "valid": False,
                    "entries_checked": checked,
                    "broken_at_index": broken_at,
                    "message": f"Chain integrity broken at entry {broken_at}",
                }
            if sig_fail_at is not None:
                return {
                    "valid": False,
                    "entries_checked": checked,
                    "broken_at_index": sig_fail_at,
                    "message": f"Signature verification failed at entry {sig_fail_at}",
                }
            result = {
                "valid": True,
                "entries_checked": checked,
                "chain_head": self._chain_head,
                "message": "Chain integrity verified",
            }
            if sig_checked > 0:
                result["signatures_verified"] = sig_checked
            return result

    def merkle_root(self) -> str:
        """Compute Merkle tree root over all ledger entry hashes (Leap 9c).

        This provides a single tamper-evident fingerprint of the entire
        karma history. If any entry is altered, the root changes.
        """
        with self._lock:
            hashes = [e.entry_hash for e in self._entries if e.entry_hash]
        return _merkle_tree_root(hashes)

    def report_by_ops(self, ops_class: str, limit: int = 100) -> dict[str, Any]:
        """Edgerunner Violet dual-log: filter entries by ops classification.

        Args:
            ops_class: "red-ops", "blue-ops", or "" for unclassified.
        """
        with self._lock:
            filtered = [e for e in self._entries if e.ops_class == ops_class][-limit:]
            total_debt = sum(e.debt_delta for e in filtered)
            mismatches = sum(1 for e in filtered if e.mismatch)
            return {
                "ops_class": ops_class or "unclassified",
                "total_entries": len(filtered),
                "total_debt": round(total_debt, 2),
                "mismatches": mismatches,
                "entries": [e.to_dict() for e in filtered[-20:]],
            }

    def forgive(self, amount: float = 1.0) -> float:
        """Reduce karma debt (e.g., after corrective action). Returns new total."""
        with self._lock:
            self._total_debt = max(0.0, self._total_debt - amount)
            return self._total_debt

    def _persist(self, entry: KarmaEntry) -> None:
        if not self._storage_dir:
            return
        try:
            ledger_file = self._storage_dir / "karma_ledger.jsonl"
            # v14.3: Auto-rotate when file exceeds 10MB
            self._maybe_rotate(ledger_file)
            with open(ledger_file, "a", encoding="utf-8") as f:
                f.write(_json_dumps(entry.to_dict()) + "\n")
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.debug("Karma ledger persist failed: %s", e, exc_info=True)

    def _maybe_rotate(
        self,
        ledger_file: Path,
        max_bytes: int = 10 * 1024 * 1024,
        keep_rotated: int = 3,
    ) -> bool:
        """Rotate the ledger file if it exceeds max_bytes (v14.3).

        Renames current file to karma_ledger.1.jsonl, shifts older
        rotations (1→2, 2→3), and deletes beyond keep_rotated.
        Returns True if rotation occurred.
        """
        if not ledger_file.exists():
            return False
        try:
            if ledger_file.stat().st_size < max_bytes:
                return False
        except OSError:
            return False

        # Shift existing rotated files
        for i in range(keep_rotated, 0, -1):
            src = ledger_file.parent / f"karma_ledger.{i}.jsonl"
            if i == keep_rotated:
                if src.exists():
                    src.unlink()
            else:
                dst = ledger_file.parent / f"karma_ledger.{i + 1}.jsonl"
                if src.exists():
                    src.rename(dst)

        # Rotate current → .1
        rotated = ledger_file.parent / "karma_ledger.1.jsonl"
        ledger_file.rename(rotated)
        logger.info(
            "Karma ledger rotated: %s → %s",
            ledger_file.name,
            rotated.name,
            exc_info=True,
        )
        return True

    def rotation_stats(self) -> dict[str, Any]:
        """Report on ledger file sizes and rotation status (v14.3)."""
        if not self._storage_dir:
            return {"status": "in_memory_only"}
        ledger_file = self._storage_dir / "karma_ledger.jsonl"
        stats: dict[str, Any] = {"current_file": str(ledger_file)}
        try:
            if ledger_file.exists():
                stats["current_size_bytes"] = ledger_file.stat().st_size
                stats["current_size_mb"] = round(
                    stats["current_size_bytes"] / 1024 / 1024, 2
                )
            else:
                stats["current_size_bytes"] = 0
        except OSError:
            stats["current_size_bytes"] = 0

        rotated_files = []
        for i in range(1, 10):
            rf = self._storage_dir / f"karma_ledger.{i}.jsonl"
            if rf.exists():
                rotated_files.append(
                    {
                        "file": rf.name,
                        "size_bytes": rf.stat().st_size,
                    }
                )
            else:
                break
        stats["rotated_files"] = rotated_files
        stats["total_files"] = 1 + len(rotated_files)
        return stats

    def _load_recent(self) -> None:
        """Load recent entries from disk on startup."""
        if not self._storage_dir:
            return
        ledger_file = self._storage_dir / "karma_ledger.jsonl"
        if not ledger_file.exists():
            return
        try:
            lines = ledger_file.read_text(encoding="utf-8").strip().split("\n")
            # Only load last 1000 entries
            loaded = 0
            for line in lines[-1000:]:
                if not line.strip():
                    continue
                try:
                    data = _json_loads(line)
                    entry = KarmaEntry(**data)
                    self._entries.append(entry)
                    self._total_debt += entry.debt_delta
                    self._tool_debt[entry.tool] += entry.debt_delta
                    self._tool_calls[entry.tool] += 1
                    if entry.mismatch:
                        self._tool_mismatches[entry.tool] += 1
                    loaded += 1
                except (ValueError, TypeError):
                    continue
            # Fix: restore chain head so new entries link correctly
            if self._entries:
                self._chain_head = self._entries[-1].entry_hash
            logger.info(
                "Karma ledger: loaded %s entries, debt={self._total_debt:.1f}, head={self._chain_head[:16]}",
                loaded,
                exc_info=True,
            )
        except Exception as e:
            logger.debug("Karma ledger load failed: %s", e, exc_info=True)


_ledger: KarmaLedger | None = None
_ledger_lock = threading.Lock()


def get_karma_ledger() -> KarmaLedger:
    """Get the global Karma Ledger instance."""
    global _ledger
    if _ledger is None:
        with _ledger_lock:
            if _ledger is None:
                try:
                    from whitemagic.config.paths import WM_ROOT

                    storage = WM_ROOT / "dharma"
                except (ImportError, ModuleNotFoundError):
                    storage = None
                _ledger = KarmaLedger(storage_dir=storage)
    return _ledger
