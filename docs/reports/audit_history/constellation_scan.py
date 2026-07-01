import sqlite3
import random
import math
import os
from pathlib import Path
from collections import Counter

# Ensure path

try:
    from whitemagic.config.paths import DB_PATH as DEFAULT_DB_PATH
except ImportError:
    DEFAULT_DB_PATH = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"

DB_PATH = Path(os.getenv("WM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
OUTPUT_FILE = "constellation_report.md"

class ConstellationScanner:
    def __init__(self, k=8):
        self.k = k
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self.points = [] # list of dicts {id, x, y, z, w}
        self.centroids = []
        self.clusters = {} # centroid_idx -> list of points

    def load_data(self):
        print("1. Loading Holographic Coordinates...")
        cur = self.conn.cursor()
        # Join with memories to get titles for later
        cur.execute("""
            SELECT h.memory_id, h.x, h.y, h.z, h.w, m.title, m.content 
            FROM holographic_coords h
            JOIN memories m ON h.memory_id = m.id
            LIMIT 50000 
        """)
        rows = cur.fetchall()
        for r in rows:
            self.points.append({
                "id": r["memory_id"],
                "curr": [r["x"], r["y"], r["z"], r["w"]],
                "title": r["title"],
                "content": r["content"][:200]
            })
        print(f"   -> Loaded {len(self.points)} stars.")

    def _dist(self, p1, p2):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def run_kmeans(self, max_iter=10):
        print(f"2. Running 4D K-Means (k={self.k})...")
        
        # Init centroids
        if not self.points:
            print("No data points.")
            return

        self.centroids = [random.choice(self.points)["curr"] for _ in range(self.k)]
        
        for i in range(max_iter):
            self.clusters = {j: [] for j in range(self.k)}
            
            # Assign
            for p in self.points:
                dists = [self._dist(p["curr"], c) for c in self.centroids]
                closest_idx = dists.index(min(dists))
                self.clusters[closest_idx].append(p)
                
            # Update
            new_centroids = []
            diff = 0
            for j in range(self.k):
                cluster_points = self.clusters[j]
                if not cluster_points:
                    new_centroids.append(self.centroids[j]) # Keep same if empty
                    continue
                
                # Mean of each dimension
                dim_sums = [0]*4
                for p in cluster_points:
                    for d in range(4):
                        dim_sums[d] += p["curr"][d]
                
                new_c = [ds / len(cluster_points) for ds in dim_sums]
                new_centroids.append(new_c)
                diff += self._dist(self.centroids[j], new_c)
            
            self.centroids = new_centroids
            print(f"   Iteration {i+1}: Shift = {diff:.2f}")
            if diff < 1.0:
                break

    def analyze_constellations(self):
        print("3. Naming Constellations (Theme Analysis)...")
        report = []
        
        report.append("# Constellation Report: The Geometry of WhiteMagic")
        report.append("**Status**: SYNTHESIZED")
        report.append(f"**Total Stars**: {len(self.points)}")
        report.append("")
        
        for idx, cluster_points in self.clusters.items():
            if not cluster_points:
                continue
                
            # Theme extraction via common words in titles
            words = []
            for p in cluster_points:
                # heuristic: grab significant words from title and path
                t_words = p["title"].replace("_", " ").replace(".", " ").split()
                words.extend([w.lower() for w in t_words if len(w) > 4])
                
            common = Counter(words).most_common(3)
            theme_name = " ".join([c[0].title() for c in common]) or f"Sector {idx}"
            
            # Generate "Star Gana" name
            star_name = f"The {theme_name} Nebula"
            
            report.append(f"## Constellation {idx+1}: {star_name}")
            report.append(f"- **Density**: {len(cluster_points)} memories")
            report.append(f"- **Core Themes**: {', '.join([c[0] for c in common])}")
            report.append(f"- **Sample Stars**:")
            for p in cluster_points[:3]:
                report.append(f"  - `{p['title']}`")
            report.append("")
            
        print("4. Generating Report...")
        with open(OUTPUT_FILE, "w") as f:
            f.write("\n".join(report))
        print(f"   -> Written to {OUTPUT_FILE}")

    def run(self):
        self.load_data()
        self.run_kmeans()
        self.analyze_constellations()
        self.conn.close()

if __name__ == "__main__":
    scanner = ConstellationScanner(k=12) # 12 Zodiacal Houses
    scanner.run()
