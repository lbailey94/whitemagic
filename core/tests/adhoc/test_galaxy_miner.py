import logging

from whitemagic.core.evolution.galaxy_miner import (
    RUST_GALAXY_MINER_AVAILABLE,
    get_galaxy_miner,
)

logging.basicConfig(level=logging.DEBUG)
miner = get_galaxy_miner()
print("Miner initialized. Rust available:", RUST_GALAXY_MINER_AVAILABLE)
try:
    patterns = miner.mine_access_patterns(min_frequency=2)
    print("Mined access patterns:", len(patterns))
except Exception as e:
    print("Error:", e)
