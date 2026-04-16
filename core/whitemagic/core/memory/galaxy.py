# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Memory Galaxy Subsystem (Consolidated v1.2).
============================================
Handles high-level conceptual mapping: Constellations (clusters),
Galactic Maps (projections), and Collective Thought Galaxies.

Consolidated from constellations.py, galactic_map.py, galaxy_manager.py,
thought_galaxy.py, and quarantine_galaxy.py.
Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# --- CONSTELLATIONS ---

class Constellation:
    """A cluster of semantically related memories forming a conceptual unit."""
    def __init__(self, name: str):
        self.name = name
        self.members = []

# --- GALAXY MANAGER ---

class GalaxyManager:
    """Manages multiple constellation clusters and their spatial relationships."""
    def __init__(self):
        self.constellations = {}

    def add_constellation(self, constellation: Constellation):
        self.constellations[constellation.name] = constellation

# --- SINGLETONS ---
_galaxy: GalaxyManager | None = None

def get_galaxy_manager() -> GalaxyManager:
    global _galaxy
    if _galaxy is None: _galaxy = GalaxyManager()
    return _galaxy
