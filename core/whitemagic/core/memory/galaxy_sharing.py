"""Cross-AI Galaxy Sharing Protocol (P4.4).

Enables galaxies to be shared between different AI instances (WhiteMagic
or compatible systems) via a portable package format.

Package format (galaxy_package_v1):
{
    "manifest": {
        "format": "galaxy_package_v1",
        "source_ai": "whitemagic",
        "source_instance": "local/default",
        "source_version": "24.3.0",
        "galaxy": "research",
        "created_at": "2026-07-12T...",
        "content_hash": "sha256:...",
        "memory_count": N,
        "association_count": N,
        "trust_level": "verified",  # verified | unverified | quarantined
        "capabilities": ["search", "recall", "snapshot"],
    },
    "snapshot": { ... },  # from galaxy_snapshot()
}

The protocol supports:
- Content hashing for integrity verification
- Trust levels (verified, unverified, quarantined)
- Capability declarations (what the receiving AI can do with the data)
- Quarantine mode (import to isolated galaxy for inspection)
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "galaxy_package_v1"


def create_galaxy_package(
    snapshot: dict[str, Any],
    source_instance: str = "local/default",
    source_version: str = "24.3.0",
    trust_level: str = "verified",
    capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """Create a portable galaxy package from a snapshot.

    Args:
        snapshot: Galaxy snapshot from galaxy_snapshot().
        source_instance: Identifier of the source AI instance.
        source_version: Version of the source AI.
        trust_level: Trust level (verified, unverified, quarantined).
        capabilities: What the receiver can do with this data.

    Returns:
        Galaxy package dict with manifest + snapshot.
    """
    if capabilities is None:
        capabilities = ["search", "recall", "snapshot", "restore"]

    # Compute content hash for integrity verification
    snapshot_json = json.dumps(snapshot, sort_keys=True, default=str)
    content_hash = hashlib.sha256(snapshot_json.encode()).hexdigest()

    manifest = {
        "format": PROTOCOL_VERSION,
        "source_ai": "whitemagic",
        "source_instance": source_instance,
        "source_version": source_version,
        "galaxy": snapshot.get("galaxy_meta", {}).get("galaxy", "unknown"),
        "created_at": datetime.now().isoformat(),
        "content_hash": f"sha256:{content_hash}",
        "memory_count": snapshot.get("galaxy_meta", {}).get("memory_count", 0),
        "association_count": snapshot.get("galaxy_meta", {}).get("association_count", 0),
        "trust_level": trust_level,
        "capabilities": capabilities,
    }

    return {
        "manifest": manifest,
        "snapshot": snapshot,
    }


def verify_galaxy_package(package: dict[str, Any]) -> dict[str, Any]:
    """Verify a galaxy package's integrity.

    Checks:
    - Package format version
    - Content hash matches snapshot
    - Required manifest fields present

    Returns:
        Dict with verification result.
    """
    manifest = package.get("manifest", {})
    snapshot = package.get("snapshot", {})

    if not manifest or not snapshot:
        return {"valid": False, "error": "Missing manifest or snapshot"}

    if manifest.get("format") != PROTOCOL_VERSION:
        return {"valid": False, "error": f"Unsupported format: {manifest.get('format')}"}

    required_fields = ["source_ai", "source_instance", "content_hash", "trust_level"]
    missing = [f for f in required_fields if f not in manifest]
    if missing:
        return {"valid": False, "error": f"Missing manifest fields: {missing}"}

    # Verify content hash
    expected_hash = manifest.get("content_hash", "")
    snapshot_json = json.dumps(snapshot, sort_keys=True, default=str)
    actual_hash = f"sha256:{hashlib.sha256(snapshot_json.encode()).hexdigest()}"

    if expected_hash != actual_hash:
        return {
            "valid": False,
            "error": "Content hash mismatch — package may be corrupted",
            "expected": expected_hash,
            "actual": actual_hash,
        }

    return {
        "valid": True,
        "manifest": manifest,
        "memory_count": manifest.get("memory_count", 0),
        "association_count": manifest.get("association_count", 0),
        "trust_level": manifest.get("trust_level", "unverified"),
        "source": manifest.get("source_instance", "unknown"),
    }


def receive_galaxy_package(
    package: dict[str, Any],
    target_galaxy: str | None = None,
    quarantine: bool = False,
) -> dict[str, Any]:
    """Receive and import a galaxy package.

    Args:
        package: Galaxy package from create_galaxy_package().
        target_galaxy: Galaxy to import into. If None, uses manifest's galaxy.
        quarantine: If True, import to a quarantined galaxy for inspection.

    Returns:
        Dict with import result.
    """
    # Verify package first
    verification = verify_galaxy_package(package)
    if not verification["valid"]:
        return {"status": "error", "error": f"Package verification failed: {verification['error']}"}

    manifest = package["manifest"]
    snapshot = package["snapshot"]

    # Determine target galaxy
    if quarantine:
        galaxy_name = f"quarantine/{manifest.get('galaxy', 'unknown')}"
    else:
        galaxy_name = target_galaxy or manifest.get("galaxy", "universal")

    # Import the snapshot
    from whitemagic.core.memory.unified import get_unified_memory
    um = get_unified_memory()
    result = um.galaxy_restore(snapshot, target_galaxy=galaxy_name, merge=True)

    return {
        "status": "success",
        "verification": verification,
        "import": result,
        "quarantined": quarantine,
    }
