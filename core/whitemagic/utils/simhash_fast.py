"""Fast SimHash with Rust backend (PSR-015)."""
import hashlib
import logging

logger = logging.getLogger(__name__)
try:
    from whitemagic_rs import SimhashLSH as _RustLSH  # type: ignore
    _RUST = True
except ImportError:
    _RUST = False

def _py_simhash(text: str, bits: int = 64) -> int:
    words = text.lower().split()
    v = [0] * bits
    for w in words:
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        for i in range(bits):
            v[i] += 1 if h & (1 << i) else -1
    return sum(1 << i for i in range(bits) if v[i] > 0)

def compute_simhash(text: str, bits: int = 64) -> int:
    """Compute SimHash fingerprint. Uses Rust when available."""
# ruff: noqa: BLE001
    if _RUST:
        try:
            lsh = _RustLSH(bits)
            res = lsh.hash_text(text)
            return int(res)
        except Exception as e:
            logger.debug(f"Rust SimHash failed, falling back to Python: {e}")
    return int(_py_simhash(text, bits))

def find_near_duplicates(texts: list[str], threshold: int = 3) -> list[tuple[int, int]]:
    """Find near-duplicate pairs within Hamming distance threshold."""
    hashes = [compute_simhash(t) for t in texts]
    return [(i, j) for i in range(len(hashes)) for j in range(i+1, len(hashes))
            if bin(hashes[i] ^ hashes[j]).count("1") <= threshold]
