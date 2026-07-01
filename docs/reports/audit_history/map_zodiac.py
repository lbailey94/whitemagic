
import sqlite3
import random
import math
import sys
import os
from pathlib import Path
from collections import Counter
from typing import List, Tuple

# Ensure path
import sys; import os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Auto-fixed path

try:
    from whitemagic.config.paths import DB_PATH as DEFAULT_DB_PATH
except ImportError:
    DEFAULT_DB_PATH = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"

DB_PATH = Path(os.getenv("WM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
OUTPUT_FILE = "zodiac_report.md"

# Noise to filter
STOP_WORDS = {
    'the', 'and', 'to', 'of', 'in', 'a', 'for', 'is', 'on', 'with', 'by', 'as', 
    'linux', 'readme', 'example', 'test', 'tests', 'go', 'py', 'rs', 'cpp', 'c', 'h',
    'src', 'main', 'lib', 'pkg', 'cmd', 'internal', 'file', 'dir', 'new', 'old',
    'mod', 'use', 'impl', 'pub', 'fn', 'struct', 'class', 'def', 'import', 'from',
    'package', 'func', 'const', 'var', 'type', 'string', 'int', 'bool', 'true', 'false',
    'return', 'err', 'nil', 'error', 'interface', 'map', 'slice', 'build', 'make',
    'data', 'code', 'project', 'node', 'modules', 'version', 'license', 'github', 'com'
}

# Zodiac Archetypes & Keyword Associations
ZODIAC_MAP = {
    "Rat": ["script", "utility", "tool", "helper", "common", "base", "util"], # Resourcefulness / Small tools
    "Ox": ["kernel", "driver", "system", "os", "platform", "arch", "core", "infrastructure"], # Endurance / Foundations
    "Tiger": ["security", "auth", "crypto", "policy", "guard", "protect", "secret", "key"], # Power / Authority
    "Rabbit": ["net", "network", "web", "socket", "http", "api", "connect", "proxy", "speed"], # Speed / Agility
    "Dragon": ["ai", "model", "learn", "train", "neural", "brain", "smart", "logic", "magic"], # Power / Mysticism
    "Snake": ["db", "sql", "storage", "data", "store", "cache", "persist", "hidden"], # Wisdom / Hidden things
    "Horse": ["ui", "view", "render", "display", "gui", "front", "react", "css", "style"], # Strength / Visuals
    "Goat": ["media", "image", "audio", "video", "asset", "art", "resource", "sound"], # Art / Creativity
    "Monkey": ["algo", "math", "calc", "compute", "logic", "puzzle", "sort", "tree"], # Intelligence / Tricks
    "Rooster": ["log", "record", "monitor", "time", "clock", "date", "schedule", "alert"], # Punctuality / Observation
    "Dog": ["test", "verify", "check", "assert", "mock", "valid", "integ", "guard"], # Loyalty / Protection
    "Pig": ["config", "json", "yaml", "xml", "tomas", "opt", "flag", "param", "env"], # Wealth / Resources
}

class ZodiacMapper:
    def __init__(self, k=12):
        self.k = k
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self.points = []
        self.centroids = []
        self.clusters = {} 

    def load_data(self):
        print("1. Loading Holographic Coordinates...")
        cur = self.conn.cursor()
        cur.execute("""
            SELECT h.memory_id, h.x, h.y, h.z, h.w, m.title, m.content 
            FROM holographic_coords h
            JOIN memories m ON h.memory_id = m.id
            LIMIT 60000 
        """)
        rows = cur.fetchall()
        for r in rows:
            self.points.append({
                "id": r["memory_id"],
                "curr": [r["x"], r["y"], r["z"], r["w"]],
                "title": r["title"].lower(),
                "content": r["content"][:500].lower()
            })
        print(f"   -> Loaded {len(self.points)} stars.")

    def _dist(self, p1, p2):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def run_kmeans(self, max_iter=15):
        print(f"2. Running Refined K-Means (k={self.k})...")
        if not self.points: return

        self.centroids = [random.choice(self.points)["curr"] for _ in range(self.k)]
        
        for i in range(max_iter):
            self.clusters = {j: [] for j in range(self.k)}
            for p in self.points:
                dists = [self._dist(p["curr"], c) for c in self.centroids]
                closest_idx = dists.index(min(dists))
                self.clusters[closest_idx].append(p)
                
            new_centroids = []
            diff = 0
            for j in range(self.k):
                pts = self.clusters[j]
                if not pts:
                    new_centroids.append(self.centroids[j])
                    continue
                dim_sums = [0]*4
                for p in pts:
                    for d in range(4): dim_sums[d] += p["curr"][d]
                new_c = [ds / len(pts) for ds in dim_sums]
                new_centroids.append(new_c)
                diff += self._dist(self.centroids[j], new_c)
            
            self.centroids = new_centroids
            print(f"   Iteration {i+1}: Shift = {diff:.2f}")
            if diff < 0.5: break

    def assign_zodiac(self, cluster_idx, pts) -> Tuple[str, List[str]]:
        # Count keywords
        all_text = " ".join([p["title"] + " " + p["title"] for p in pts]) # Weight title more
        words = [w for w in all_text.split() if w.isalpha() and len(w) > 3 and w not in STOP_WORDS]
        common = Counter(words).most_common(20)
        
        # Scoring
        scores = {animal: 0 for animal in ZODIAC_MAP}
        
        for word, count in common:
            for animal, keywords in ZODIAC_MAP.items():
                if any(k in word for k in keywords):
                    scores[animal] += count * 2
                
                if word in keywords:
                    scores[animal] += count * 5

        # Bonus for cluster index (to encourage spread if scores are low)
        # (Optional: force assignment if needed, but let's see natural emergence first)
        
        best_animal = max(scores, key=scores.get)
        top_keywords = [c[0] for c in common[:5]]
        
        # If score is 0, assign based on index to ensure coverage (fallback)
        if scores[best_animal] == 0:
            animals = list(ZODIAC_MAP.keys())
            best_animal = animals[cluster_idx % 12]
            
        return best_animal, top_keywords

    def generate_report(self):
        print("3. Generating Zodiac Report...")
        report = []
        report.append("# Zodiac Alignment Report: The 12 Houses of WhiteMagic")
        report.append("**Status**: ALIGNED")
        report.append(f"**Total Stars**: {len(self.points)}")
        report.append("")
        
        assigned_animals = []
        
        for idx in range(self.k):
            pts = self.clusters[idx]
            if not pts: continue
            
            animal, keywords = self.assign_zodiac(idx, pts)
            assigned_animals.append(animal)
            
            report.append(f"## House {idx+1}: {animal}")
            report.append(f"- **Density**: {len(pts)} stars")
            report.append(f"- **Keywords**: {', '.join(keywords)}")
            report.append(f"- **Archetype**: {self._get_archetype_desc(animal)}")
            report.append(f"- **Representative Files**:")
            for p in pts[:3]:
                report.append(f"  - `{p['title']}`")
            report.append("")
            
        counts = Counter(assigned_animals)
        report.append("## Distribution Analysis")
        for animal, count in counts.most_common():
            report.append(f"- **{animal}**: {count} Houses")

        with open(OUTPUT_FILE, "w") as f:
            f.write("\n".join(report))
        print(f"   -> Written to {OUTPUT_FILE}")

    def _get_archetype_desc(self, animal):
        descs = {
            "Rat": "Resourcefulness, Scripts, Micro-tools",
            "Ox": "Endurance, Infrastructure, Kernel",
            "Tiger": "Power, Security, Policy",
            "Rabbit": "Speed, Networking, Connectivity",
            "Dragon": "Mysticism, AI, Logic, Magic",
            "Snake": "Wisdom, Databases, Storage",
            "Horse": "Strength, UI/UX, Rendering",
            "Goat": "Creativity, Media, Assets",
            "Monkey": "Intelligence, Algorithms, Computation",
            "Rooster": "Observation, Logging, Time",
            "Dog": "Loyalty, Testing, Verification",
            "Pig": "Wealth, Configuration, Resources"
        }
        return descs.get(animal, "Unknown")

    def run(self):
        self.load_data()
        self.run_kmeans()
        self.generate_report()
        self.conn.close()

if __name__ == "__main__":
    mapper = ZodiacMapper(k=12)
    mapper.run()
