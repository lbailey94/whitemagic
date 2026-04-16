"""
Galactic Memory Market — Renting access to specialized galaxies.
=================================================================
Allows agents to grant or request temporary access to a galaxy
in exchange for a micro-payment.

Philosophy: "The monetization of curated knowledge."
"""

import logging
import time
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)

@dataclass
class GalaxyAccess:
    """Temporary access grant to a galaxy."""
    galaxy_name: str
    agent_id: str
    expires_at: float
    access_type: str = "read" # read, write
    tx_hash: str = ""

class MemoryMarket:
    """Manages memory galaxy rentals."""

    def __init__(self):
        from whitemagic.config.paths import ECONOMY_DIR
        self._path = ECONOMY_DIR / "memory_rentals.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._rentals: list[GalaxyAccess] = []
        self._load()

    def _load(self):
        """Load rentals from disk."""
        if not self._path.exists():
            return
        from whitemagic.utils.fast_json import loads as _json_loads
        try:
            with open(self._path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = _json_loads(line)
                        self._rentals.append(GalaxyAccess(**data))
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.warning(f"Failed to load memory market: {e}")

    def grant_access(self, galaxy_name: str, agent_id: str, duration_hours: int = 24, tx_hash: str = "") -> GalaxyAccess:
        """Grant access to an agent for a specified duration."""
        access = GalaxyAccess(
            galaxy_name=galaxy_name,
            agent_id=agent_id,
            expires_at=time.time() + (duration_hours * 3600),
            tx_hash=tx_hash
        )
        self._rentals.append(access)
        self._persist(access)
        return access

    def has_access(self, galaxy_name: str, agent_id: str) -> bool:
        """Check if an agent currently has valid access to a galaxy."""
        now = time.time()
        for rental in self._rentals:
            if rental.galaxy_name == galaxy_name and rental.agent_id == agent_id:
                if rental.expires_at > now:
                    return True
        return False

    def _persist(self, access: GalaxyAccess):
        """Append rental to the ledger."""
        from whitemagic.utils.fast_json import dumps_str as _json_dumps
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(_json_dumps(asdict(access)) + "\n")
        except (ImportError, ModuleNotFoundError) as e:
            logger.error(f"Failed to persist rental: {e}")

_market: MemoryMarket | None = None

def get_memory_market() -> MemoryMarket:
    global _market
    if _market is None:
        _market = MemoryMarket()
    return _market
