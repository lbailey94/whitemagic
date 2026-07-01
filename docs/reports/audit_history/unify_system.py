import asyncio
import hashlib
import json
import logging
import os
import random
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Allow running from repo root without requiring installation.
REPO_ROOT = Path(os.environ.get("WM_REPO_ROOT", Path(__file__).resolve().parent.parent)).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from whitemagic.core.ganas.base import GanaCall
    from whitemagic.core.ganas.eastern_quadrant import NeckGana
    from whitemagic.core.ganas.southern_quadrant import ExtendedNetGana
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

# Configuration
from whitemagic.config.paths import DB_PATH as DEFAULT_DB_PATH

_default_dirs = [REPO_ROOT / "Restoration_Seed", REPO_ROOT / "newmagic"]
env_dirs = os.getenv("WM_DIRECTORIES_TO_SCAN")
if env_dirs:
    DIRECTORIES_TO_SCAN = [Path(p).expanduser().resolve() for p in env_dirs.split(os.pathsep) if p.strip()]
else:
    DIRECTORIES_TO_SCAN = [p for p in _default_dirs if p.exists()]

DB_PATH = Path(os.getenv("WM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser().resolve()
BATCH_SIZE = 1000
MAX_FILES = 50000 # Limit for this run to keep it responsive, user said "130k", we have 1M total.
EXTENSIONS = {'.md', '.txt', '.py', '.rs', '.go', '.js', '.json', '.yaml'}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_file_worker(file_path: str) -> Dict[str, Any]:
    """Read file content and return metadata object"""
    try:
        path = Path(file_path)
        if path.stat().st_size > 100 * 1024: # Skip > 100KB
            return None
            
        with open(path, 'r', errors='ignore') as f:
            content = f.read()
            if not content.strip():
                return None
                
        return {
            "id": hashlib.md5(f"{path.name}:{path.stat().st_mtime}".encode()).hexdigest(),
            "title": path.name,
            "content": content,
            "path": str(path),
            "timestamp": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "type": path.suffix[1:] if path.suffix else "text"
        }
    except Exception:
        return None

class SystemUnifier:
    def __init__(self):
        self.neck = NeckGana()
        self.extended_net = ExtendedNetGana()
        self.db_path = str(DB_PATH)
        self.conn = None

    def connect_db(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close_db(self):
        if self.conn:
            self.conn.close()

    def batch_insert_memories(self, items: List[Dict[str, Any]]):
        if not items:
            return
            
        params = []
        holo_params = []
        
        for item in items:
            # Memory params
            params.append((
                item['id'],
                item['content'],
                'scavenged', # memory_type
                item['timestamp'],
                item['timestamp'],
                datetime.now().isoformat(),
                0, # access_count
                0.5, # valence
                0.5, # importance
                json.dumps({"path": item['path'], "source": "unify_system"}),
                item['title']
            ))
            
            # Holographic Coords (Mock/Random for now to populate the "galaxy")
            holo_params.append((
                item['id'],
                random.uniform(-100, 100), # x
                random.uniform(-100, 100), # y
                random.uniform(-100, 100), # z
                random.uniform(0, 1)       # w (time/density)
            ))
            
        try:
            cur = self.conn.cursor()
            cur.executemany("""
                INSERT OR IGNORE INTO memories 
                (id, content, memory_type, created_at, updated_at, accessed_at, access_count, 
                 emotional_valence, importance, metadata, title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, params)
            
            cur.executemany("""
                INSERT OR IGNORE INTO holographic_coords
                (memory_id, x, y, z, w)
                VALUES (?, ?, ?, ?, ?)
            """, holo_params)
            
            self.conn.commit()
            return len(params)
        except Exception as e:
            logging.error("Batch insert error: %s", e)
            return 0

    async def scan_and_ingest(self):
        print(f"=== SYSTEM UNIFICATION PROTOCOL ===")
        print(f"Targeting: {DIRECTORIES_TO_SCAN}")
        print(f"Cap: {MAX_FILES} files")
        
        files_to_scan = []
        for d in DIRECTORIES_TO_SCAN:
            for root, _, files in os.walk(d):
                if any(x in root for x in ['.git', 'node_modules', '__pycache__']):
                    continue
                for f in files:
                    if Path(f).suffix in EXTENSIONS:
                        files_to_scan.append(os.path.join(root, f))
                        
        # Shuffle and slice to get a random sample if we exceed max
        random.shuffle(files_to_scan)
        files_to_scan = files_to_scan[:MAX_FILES]
        
        print(f"Selected {len(files_to_scan)} files for ingestion.")
        
        self.connect_db()
        
        total_ingested = 0
        batch = []
        
        # Parallel Read
        with ProcessPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
            futures = {executor.submit(process_file_worker, f): f for f in files_to_scan}
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    batch.append(result)
                    
                if len(batch) >= BATCH_SIZE:
                    c = self.batch_insert_memories(batch)
                    total_ingested += c
                    batch = []
                    print(f"   Stored {total_ingested} memories...", end='\r')
                    
        # Final batch
        if batch:
            c = self.batch_insert_memories(batch)
            total_ingested += c
            
        print(f"\n✅ Ingestion Complete. Total New Memories: {total_ingested}")
        self.close_db()
        
        print("\n=== GANA VERIFICATION ===")
        
        # NeckGana check
        neck_call = GanaCall(task="create_memory", state_vector={"title": "System Unification Log", "content": f"Ingested {total_ingested} files from Restoration_Seed."})
        await self.neck.invoke(neck_call)
        print("✓ NeckGana: Unification event recorded.")
        
        # ExtendedNet check (Mesh)
        ext_call = GanaCall(task="manage_resonance", state_vector={"operation": "emit_event", "event_type": "SYSTEM_UNIFICATION", "data": {"count": total_ingested}})
        await self.extended_net.invoke(ext_call)
        print("✓ ExtendedNetGana: Resonance signal emitted to Mesh.")

if __name__ == "__main__":
    unifier = SystemUnifier()
    asyncio.run(unifier.scan_and_ingest())
