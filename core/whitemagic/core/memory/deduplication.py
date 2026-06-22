"""
Deduplication & Noise Filtering Logic
=====================================
Core logic for Campaign C001: Quarantine Rehabilitation.
Identifies duplicate memories and noise (logs, tracebacks, empty content)
for purging or rehabilitation.
"""

import hashlib
import logging
import re

logger = logging.getLogger(__name__)

# Noise patterns - if content matches substantially, it's noise
NOISE_PATTERNS = [
    r'Traceback \(most recent call last\):',
    r'File ".*", line \d+, in',
    r'Error: .*',
    r'Exception: .*',
    r'^{"json":.*}$', # Raw JSON dumps often noise if contextless
    r'^<function .* at 0x.*>$',
    r'^\s*$', # Empty or whitespace
]

def calculate_content_hash(content: str) -> str:
    """Calculate SHA-256 hash of content."""
    if not content:
        return ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def is_noise(content: str, title: str = "") -> bool:
    """
    Check if a memory is likely noise/junk.
    Returns True if it should be purged.
    """
    if not content or len(content.strip()) < 10:
        return True

    # Check specific noise titles
    if title and any(x in title.lower() for x in ["checkpoint", "backup", "dump"]):
        # These might be valuable, handled separately? No, scout said "Noise Filter" included these.
        # But wait, checkpoints might be useful history.
        # Let's stick to content-based noise for PURGE safety.
        pass

    # Check content patterns
    for pat in NOISE_PATTERNS:
        if re.search(pat, content):
            return True

    # Check for excessive non-alphanumeric (binary dumps, large hashes)
    alnum_ratio = sum(c.isalnum() for c in content) / len(content)
    if len(content) > 500 and alnum_ratio < 0.3:
        return True # Probably binary garbage or encoded data without context

    return False

def find_duplicates(cursor, batch_size: int = 1000) -> list[str]:
    """
    Find IDs of memories that are exact content duplicates of ACTIVE memories.
    Active memories are the source of truth. Any quarantined memory with same hash as active is a dupe.
    """
    # Get all active content hashes
    cursor.execute("SELECT content_hash FROM memories WHERE memory_type != 'quarantined' AND content_hash IS NOT NULL")
    active_hashes = set(row[0] for row in cursor.fetchall())

    # Find quarantined memories with these hashes
    # We can do this in SQL for speed
    ",".join("?" * len(active_hashes))
    # Too many for IN clause potentially. Better to iterate quarantined and check set in python?
    # Or temporary table.

    # Let's stream quarantined
    to_purge = []
    cursor.execute("SELECT id, content_hash FROM memories WHERE memory_type = 'quarantined'")
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        for mid, chash in rows:
            if chash in active_hashes:
                to_purge.append(mid)

    return to_purge
