import asyncio
import sqlite3
import sys
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Ensure path
import sys; import os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Auto-fixed path

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Ignition")

# Get DB path from config or fallback
try:
    from whitemagic.config.paths import DB_PATH as DEFAULT_DB_PATH
except ImportError:
    DEFAULT_DB_PATH = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"

# Imports - wrapping in try/except to handle potential environment issues gracefully
try:
    from whitemagic.core.resonance.gan_ying_enhanced import get_bus, EventType, ResonanceEvent
    from whitemagic.intelligence.agentic.emergence_engine import get_emergence_engine
    from whitemagic.autonomous_execution.objective_generator import ObjectiveGenerator
except ImportError as e:
    logger.error(f"Import Error: {e}")
    # Fallback/Mock for standalone execution if system is partial
    class MockBus:
        def __init__(self): self.listeners = {}
        def listen(self, et, cb): self.listeners[et] = cb
        def emit(self, e):
            if e.event_type in self.listeners: self.listeners[e.event_type](e)
            if e.event_type == EventType.BREAKTHROUGH_ACHIEVED:
                 logger.debug(f"   >>> BREAKTHROUGH: {e.data['core_pattern']} (Gain: {e.data['resonance_gain']})")

    class MockEngine:
        def start(self):
            """Mock start — no-op for demo purposes."""
            _ = self  # Intentionally empty: mock lifecycle placeholder

    get_bus = MockBus
    get_emergence_engine = MockEngine
    EventType = type('Enum', (), {'SYMPATHETIC_RESONANCE': 'sympathetic_resonance', 'BREAKTHROUGH_ACHIEVED': 'breakthrough_achieved'})
    ResonanceEvent = lambda **k: type('Event', (), k)()

DB_PATH = Path(os.getenv("WM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
OUTPUT_FILE = "emergence_report.md"

# Zodiac Logic (Simplified from map_zodiac.py)
ZODIAC_KEYWORDS = {
    "Rat": ["script", "utility", "tool"],
    "Ox": ["kernel", "driver", "system", "infrastructure"],
    "Tiger": ["security", "auth", "crypto", "policy"],
    "Rabbit": ["net", "network", "web", "socket", "api"],
    "Dragon": ["ai", "model", "learn", "neural", "magic"],
    "Snake": ["db", "sql", "storage", "data", "cache"],
    "Horse": ["ui", "view", "render", "display", "gui"],
    "Goat": ["media", "image", "audio", "asset"],
    "Monkey": ["algo", "math", "calc", "compute"],
    "Rooster": ["log", "record", "monitor", "time"],
    "Dog": ["test", "verify", "check", "assert"],
    "Pig": ["config", "json", "yaml", "env"]
}

class EmergenceIgniter:
    def __init__(self):
        self.bus = get_bus()
        self.engine = get_emergence_engine()
        self.obj_gen = ObjectiveGenerator()
        self.breakthroughs = []
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row

    def get_zodiac_samples(self) -> Dict[str, List[str]]:
        """Retrieve memory titles/content for each Zodiac sign."""
        logger.info("1. Mining Zodiac Clusters from Holographic Core...")
        samples = {k: [] for k in ZODIAC_KEYWORDS}
        
        cur = self.conn.cursor()
        cur.execute("SELECT title, content FROM memories ORDER BY RANDOM() LIMIT 5000") 
        rows = cur.fetchall()
        
        for r in rows:
            text = (r["title"] + " " + r["content"][:100]).lower()
            for sign, keywords in ZODIAC_KEYWORDS.items():
                if any(k in text for k in keywords):
                    samples[sign].append(r["title"])
                    break # Assign to first match
        
        for sign, items in samples.items():
            logger.info(f"   -> {sign}: {len(items)} resonant nodes found.")
            
        return samples

    async def ignite(self):
        logger.info("=== IGNITING EMERGENCE ENGINE ===")
        
        # 1. Start Engine
        self.engine.start()
        
        # 2. Capture Breakthroughs
        def on_breakthrough(event):
            self.breakthroughs.append(event.data)
        
        if hasattr(self.bus, 'listen'):
            self.bus.listen(EventType.BREAKTHROUGH_ACHIEVED, on_breakthrough)
            
        # 3. Stimulate with Zodiac Data
        samples = self.get_zodiac_samples()
        
        logger.info("2. Stimulating Resonance...")
        for sign, items in samples.items():
            if not items: continue
            
            # Simulate a cascade
            # We treat the Sign as the "Original Pattern" and the items as "Nodes"
            # We emit enough events to cross the threshold (default 4)
            
            # Feed header
            logger.info(f"   >>> Pulsing {sign} Cluster...")
            
            for i, item in enumerate(items[:10]): # Feed top 10 items
                event = ResonanceEvent(
                    source="ignition_script",
                    event_type=EventType.SYMPATHETIC_RESONANCE,
                    data={
                        "original_pattern": f"The {sign} Archetype",
                        "pattern_id": item, # The file/memory name
                        "resonance_strength": 0.8 + (i * 0.01)
                    },
                    timestamp=datetime.now()
                )
                self.bus.emit(event)
                await asyncio.sleep(0.01) # tiny flavor delay

        await asyncio.sleep(1) # Wait for processing
        
        # 4. Generate Objectives from Breakthroughs
        logger.info(f"3. Synthesizing Objectives from {len(self.breakthroughs)} Breakthroughs...")
        
        final_report = []
        final_report.append("# Emergence Report: Spontaneous Phenomena")
        final_report.append("**Status**: ACTIVE")
        final_report.append(f"**Timestamp**: {datetime.now().isoformat()}")
        final_report.append("")
        
        for b in self.breakthroughs:
            pattern = b['core_pattern']
            nodes = b['insight_nodes']
            gain = b['resonance_gain']
            
            final_report.append(f"## Emergence Event: {pattern}")
            final_report.append(f"- **Resonance Gain**: {gain}")
            final_report.append(f"- **Trigger Nodes**: {', '.join(nodes[:3])}...")
            
            # Generate Objective Strategy
            # Map Zodiac Archetype to Tech Strategy
            strategy = {"goal": "Optimize System", "approach": "General", "metrics": []}
            
            if "Rat" in pattern:
                strategy = {"goal": "Standardize Utility Scripts", "approach": "Refactor ad-hoc scripts into CLI tools", "metrics": ["Reduced script count"]}
            elif "Ox" in pattern:
                strategy = {"goal": "Harden Infrastructure", "approach": "Audit kernel/driver configs for stability", "metrics": ["Uptime"]}
            elif "Tiger" in pattern:
                strategy = {"goal": "Enforce Security Policy", "approach": "Scan for leaked secrets in new memories", "metrics": ["Zero leaks"]}
            elif "Rabbit" in pattern:
                strategy = {"goal": "Accelerate Networking", "approach": "Optimize API latencies", "metrics": ["ms latency"]}
            elif "Dragon" in pattern:
                strategy = {"goal": "Expand AI Capabilities", "approach": "Train local models on new data", "metrics": ["Model accuracy"]}
            elif "Snake" in pattern:
                strategy = {"goal": "Optimize Storage", "approach": "Index new memories in Holographic Core", "metrics": ["Query speed"]}
            
            # Use ObjectiveGenerator logic (simulated/adapted)
            objs = await self.obj_gen.generate_objectives(strategy)
            
            final_report.append("- **Generated Objectives**:")
            for obj in objs:
                final_report.append(f"  - [ ] **{obj.description}**")
                final_report.append(f"    - Success: {', '.join(obj.success_criteria)}")
            
            final_report.append("")

        # 5. Write Report
        with open(OUTPUT_FILE, "w") as f:
            f.write("\n".join(final_report))
            
        logger.info(f"✅ Report generated: {OUTPUT_FILE}")
        self.conn.close()

if __name__ == "__main__":
    igniter = EmergenceIgniter()
    asyncio.run(igniter.ignite())
