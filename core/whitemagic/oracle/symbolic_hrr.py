"""Universal HRR Encoding for Symbolic Systems.

Replaces hardcoded resonance maps (_WUXING_TO_ALCHEMY, _MODALITY_TO_ICHING, etc.)
with HRR-derived resonance computation. Each symbolic concept (Wu Xing phase,
zodiac sign, tarot card, Ifá Odu) is encoded as an HRR vector, and resonance
between systems is computed via cosine similarity.

This enables cross-system resonance discovery that wasn't possible with
hardcoded maps — e.g., finding that "fire" in Wu Xing resonates with
"The Tower" in Tarot at 0.72 similarity, even if no human had mapped that
connection.
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# Try to use the Rust HRR engine for vector operations
_rust_available = False
try:
    import whitemagic_rs as _wmr
    _rust_available = True
except ImportError:
    _wmr = None  # type: ignore[assignment]

_HRR_DIM = 64


def _seeded_vector(seed: int, dim: int = _HRR_DIM) -> list[float]:
    """Generate a deterministic unit vector from a seed."""
    import random
    rng = random.Random(seed)
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1e-12
    return [v / norm for v in vec]


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na < 1e-15 or nb < 1e-15:
        return 0.0
    return dot / (na * nb)


def _hash_seed(symbol: str, namespace: str = "") -> int:
    """Generate a deterministic seed from a symbol string."""
    h = hashlib.sha256(f"{namespace}:{symbol}".encode()).hexdigest()
    return int(h[:8], 16)


# ── Symbol Encodings ─────────────────────────────────────────────────

class SymbolicHRR:
    """Universal HRR encoding for symbolic systems.

    Encodes symbols from different divination systems (Wu Xing, Zodiac,
    Tarot, Ifá, I Ching) as HRR vectors and computes cross-system resonance.

    The encoding is deterministic — the same symbol always produces the same
    vector — enabling reproducible resonance computation across systems.
    """

    # Symbol namespaces
    WUXING = "wuxing"
    ZODIAC = "zodiac"
    TAROT = "tarot"
    IFA = "ifa"
    ICHING = "iching"
    ALCHEMY = "alchemy"
    MODALITY = "modality"

    # Known symbols per namespace
    SYMBOLS: dict[str, list[str]] = {
        WUXING: ["wood", "fire", "earth", "metal", "water"],
        ZODIAC: ["aries", "taurus", "gemini", "cancer", "leo", "virgo",
                  "libra", "scorpio", "sagittarius", "capricorn",
                  "aquarius", "pisces"],
        TAROT: ["fool", "magician", "high_priestess", "empress", "emperor",
                 "hierophant", "lovers", "chariot", "strength", "hermit",
                 "wheel", "justice", "hanged_man", "death", "temperance",
                 "devil", "tower", "star", "moon", "sun", "judgement", "world"],
        IFA: ["ogbe", "oye", "iwori", "odi", "irosun", "owonrin",
               "obara", "okanran", "ogunda", "osa", "ika", "oturupon",
               "otura", "irete", "ose", "ofun"],
        MODALITY: ["cardinal", "fixed", "mutable"],
        ALCHEMY: ["nigredo", "albedo", "citrinitas", "rubedo", "cauda_pavonis"],
    }

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._build_vectors()

    def _build_vectors(self) -> None:
        """Build HRR vectors for all known symbols."""
        for namespace, symbols in self.SYMBOLS.items():
            for symbol in symbols:
                key = f"{namespace}:{symbol}"
                seed = _hash_seed(symbol, namespace)
                self._vectors[key] = _seeded_vector(seed)

        # I Ching hexagrams 1-64
        for kw in range(1, 65):
            key = f"{self.ICHING}:{kw}"
            seed = _hash_seed(str(kw), self.ICHING)
            self._vectors[key] = _seeded_vector(seed)

    def get_vector(self, namespace: str, symbol: str | int) -> list[float]:
        """Get the HRR vector for a symbol.

        Args:
            namespace: Symbol namespace (WUXING, ZODIAC, etc.).
            symbol: Symbol name or number (for I Ching).

        Returns:
            The HRR vector (list of floats).
        """
        key = f"{namespace}:{symbol}"
        if key not in self._vectors:
            # Dynamically encode unknown symbols
            seed = _hash_seed(str(symbol), namespace)
            self._vectors[key] = _seeded_vector(seed)
        return self._vectors[key]

    def resonance(
        self,
        ns1: str, sym1: str | int,
        ns2: str, sym2: str | int,
    ) -> float:
        """Compute resonance (cosine similarity) between two symbols.

        Args:
            ns1: Namespace of first symbol.
            sym1: First symbol.
            ns2: Namespace of second symbol.
            sym2: Second symbol.

        Returns:
            Cosine similarity in [-1, 1].
        """
        v1 = self.get_vector(ns1, sym1)
        v2 = self.get_vector(ns2, sym2)
        return _cosine_sim(v1, v2)

    def top_resonances(
        self,
        namespace: str,
        symbol: str | int,
        target_namespace: str | None = None,
        threshold: float = 0.0,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """Find symbols that resonate most with a given symbol.

        Args:
            namespace: Namespace of the query symbol.
            symbol: Query symbol.
            target_namespace: Namespace to search (None = all namespaces).
            threshold: Minimum resonance to include.
            k: Maximum number of results.

        Returns:
            List of {"namespace", "symbol", "resonance"} sorted by resonance descending.
        """
        query_vec = self.get_vector(namespace, symbol)
        results: list[dict[str, Any]] = []

        search_namespaces = [target_namespace] if target_namespace else list(self.SYMBOLS.keys()) + [self.ICHING]

        for ns in search_namespaces:
            symbols = self.SYMBOLS.get(ns, [])
            if ns == self.ICHING:
                symbols = list(range(1, 65))
            for sym in symbols:
                if ns == namespace and sym == symbol:
                    continue
                vec = self.get_vector(ns, sym)
                res = _cosine_sim(query_vec, vec)
                if res > threshold:
                    results.append({"namespace": ns, "symbol": sym, "resonance": round(res, 6)})

        results.sort(key=lambda x: x["resonance"], reverse=True)
        return results[:k]

    def alchemical_phase(self, wuxing: str) -> str:
        """Get alchemical phase for a Wu Xing element via HRR resonance.

        Replaces the hardcoded _WUXING_TO_ALCHEMY map with HRR-derived mapping.
        The alchemical phase with highest resonance to the Wu Xing element is selected.

        Args:
            wuxing: One of 'wood', 'fire', 'earth', 'metal', 'water'.

        Returns:
            Alchemical phase description string.
        """
        ALCHEMY_DESCRIPTIONS = {
            "nigredo": "Nigredo (germination — raw potential breaking through)",
            "albedo": "Albedo (purification — washing the stone white)",
            "citrinitas": "Citrinitas (illumination — the golden moment of clarity)",
            "rubedo": "Rubedo (completion — the red stone, the finished work)",
            "cauda_pavonis": "Cauda Pavonis (dissolution — all colors present, none fixed)",
        }

        resonances = self.top_resonances(
            self.WUXING, wuxing,
            target_namespace=self.ALCHEMY,
            k=1,
        )
        if resonances:
            best = resonances[0]["symbol"]
            return ALCHEMY_DESCRIPTIONS.get(best, f"{best} phase (resonance: {resonances[0]['resonance']:.2f})")

        # Fallback to known mapping
        FALLBACK = {
            "wood": "Nigredo (germination — raw potential breaking through)",
            "fire": "Citrinitas (illumination — the golden moment of clarity)",
            "earth": "Albedo (purification — washing the stone white)",
            "metal": "Rubedo (completion — the red stone, the finished work)",
            "water": "Cauda Pavonis (dissolution — all colors present, none fixed)",
        }
        return FALLBACK.get(wuxing, "Unknown phase")

    def modality_dynamic(self, modality: str) -> str:
        """Get I Ching dynamic for a zodiac modality via HRR resonance.

        Replaces the hardcoded _MODALITY_TO_ICHING map.

        Args:
            modality: One of 'cardinal', 'fixed', 'mutable'.

        Returns:
            Description string of the modality's I Ching dynamic.
        """
        MODALITY_DESCRIPTIONS = {
            "cardinal": "Initiating force — the hexagram's opening line, the spark",
            "fixed": "Sustaining power — the hexagram's central lines, the axis",
            "mutable": "Transforming flow — the hexagram's changing lines, the pivot",
        }

        # Find the I Ching hexagram that resonates most with this modality
        resonances = self.top_resonances(
            self.MODALITY, modality,
            target_namespace=self.ICHING,
            k=1,
        )
        if resonances:
            hex_num = resonances[0]["symbol"]
            res = resonances[0]["resonance"]
            base_desc = MODALITY_DESCRIPTIONS.get(modality, f"{modality} modality")
            return f"{base_desc} (resonates with hexagram #{hex_num}, similarity: {res:.2f})"

        return MODALITY_DESCRIPTIONS.get(modality, f"{modality} modality")

    def cross_system_resonance(
        self,
        oracle_output: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Find all cross-system resonances in an oracle reading.

        Examines the symbols present in the oracle output and finds
        unexpected resonances between systems (e.g., Tarot card ↔ Wu Xing).

        Args:
            oracle_output: Dict from oracle consultation.

        Returns:
            List of {"pair", "resonance", "description"} sorted by resonance.
        """
        resonances: list[dict[str, Any]] = []

        wuxing = oracle_output.get("wu_xing")
        sign = oracle_output.get("sign", "").lower()
        iching_num = oracle_output.get("iching_number") or oracle_output.get("primary_hexagram")
        ifa_odu = oracle_output.get("ifa_odu", "").lower()
        tarot_cards = oracle_output.get("tarot_cards", [])

        # Wu Xing ↔ I Ching
        if wuxing and iching_num:
            res = self.resonance(self.WUXING, wuxing, self.ICHING, iching_num)
            if abs(res) > 0.1:
                resonances.append({
                    "pair": f"{wuxing} ↔ hexagram #{iching_num}",
                    "resonance": round(res, 4),
                    "description": f"Wu Xing '{wuxing}' resonates with hexagram #{iching_num} at {res:.2f}",
                })

        # Zodiac ↔ I Ching
        if sign and iching_num:
            res = self.resonance(self.ZODIAC, sign, self.ICHING, iching_num)
            if abs(res) > 0.1:
                resonances.append({
                    "pair": f"{sign} ↔ hexagram #{iching_num}",
                    "resonance": round(res, 4),
                    "description": f"Zodiac '{sign}' resonates with hexagram #{iching_num} at {res:.2f}",
                })

        # Ifá ↔ I Ching
        if ifa_odu and iching_num:
            res = self.resonance(self.IFA, ifa_odu, self.ICHING, iching_num)
            if abs(res) > 0.1:
                resonances.append({
                    "pair": f"{ifa_odu} ↔ hexagram #{iching_num}",
                    "resonance": round(res, 4),
                    "description": f"Ifá Odu '{ifa_odu}' resonates with hexagram #{iching_num} at {res:.2f}",
                })

        # Tarot ↔ Wu Xing
        if wuxing and tarot_cards:
            for card in tarot_cards:
                card_name = card.get("name", "").lower().replace(" ", "_") if isinstance(card, dict) else str(card).lower()
                if card_name:
                    res = self.resonance(self.TAROT, card_name, self.WUXING, wuxing)
                    if abs(res) > 0.1:
                        resonances.append({
                            "pair": f"{card_name} ↔ {wuxing}",
                            "resonance": round(res, 4),
                            "description": f"Tarot '{card_name}' resonates with Wu Xing '{wuxing}' at {res:.2f}",
                        })

        resonances.sort(key=lambda x: abs(x["resonance"]), reverse=True)
        return resonances


_symbolic_hrr: SymbolicHRR | None = None


def get_symbolic_hrr() -> SymbolicHRR:
    """Get the singleton SymbolicHRR instance."""
    global _symbolic_hrr
    if _symbolic_hrr is None:
        _symbolic_hrr = SymbolicHRR()
    return _symbolic_hrr
