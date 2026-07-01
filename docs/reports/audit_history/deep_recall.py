import asyncio
import hashlib
import json
import logging
import os
import random
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Ensure path
import sys; import os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Auto-fixed path
logger = logging.getLogger(__name__)

try:
    from whitemagic.config.paths import DB_PATH as DEFAULT_DB_PATH
    from whitemagic.core.ganas.eastern_quadrant import NeckGana
    from whitemagic.core.ganas.southern_quadrant import ExtendedNetGana
except ImportError as e:
    logger.debug(f"CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

# Configuration
TARGET_DIR = "./Restoration_Seed/staging_archive"
DB_PATH = Path(os.getenv("WM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
BATCH_SIZE = 2000
MAX_FILES = 200000 # Target > 150k total
EXTENSIONS = {'.md', '.txt', '.py', '.rs', '.go', '.js', '.json', '.yaml', '.sh', '.html', '.css', '.c', '.h', '.cpp'}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_file_worker(file_path: str) -> Dict[str, Any]:
    """Read file content and return metadata object"""
    try:
        path = Path(file_path)
        # Skip very large files
        if path.stat().st_size > 500 * 1024: 
            return None
            
        with open(path, 'r', errors='ignore') as f:
            content = f.read()
            if not content.strip():
                return None
                
        return {
            "id": hashlib.md5(f"{path.name}:{path.stat().st_mtime}:{path.stat().st_size}".encode()).hexdigest(),
            "title": path.name,
            "content": content,
            "path": str(path),
            "timestamp": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "type": path.suffix[1:] if path.suffix else "text"
        }
    except Exception:
        return None

class DeepRecall:
    def __init__(self):
        self.neck = NeckGana()
        self.extended_net = ExtendedNetGana()
        self.db_path = str(DB_PATH)
        self.conn = None

    def connect_db(self):
        self.conn = sqlite3.connect(self.db_path)
        # WAL mode for concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.row_factory = sqlite3.Row

    def close_db(self):
        if self.conn:
            self.conn.close()

    def batch_insert_memories(self, items: List[Dict[str, Any]]):
        if not items:
            return 0
            
        params = []
        holo_params = []
        
        for item in items:
            # Memory params
            params.append((
                item['id'],
                item['content'],
                'deep_archive', 
                item['timestamp'],
                item['timestamp'],
                datetime.now().isoformat(),
                0, 
                0.5, 
                0.6, # Slightly higher importance for deep history
                json.dumps({"path": item['path'], "source": "deep_recall"}),
                item['title']
            ))
            
            # Holographic Coords (Expanding the universe)
            holo_params.append((
                item['id'],
                random.uniform(-500, 500), # Wider range
                random.uniform(-500, 500), 
                random.uniform(-500, 500), 
                random.uniform(0, 1)      
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
            return cur.rowcount # usage of rowcount with INSERT OR IGNORE is tricky in sqlite, but good approx
        except Exception as e:
            logging.error("Batch insert error: %s", e)
            return 0

    async def run(self):
        logger.debug(f"=== DEEP RECALL PROTOCOL ===")
        logger.debug(f"Target: {TARGET_DIR}")
        logger.debug(f"Cap: {MAX_FILES} files")
        
        # 1. Collect Files
        logger.debug("1. Scanning directory tree...")
        files_to_scan = []
        for root, _, files in os.walk(TARGET_DIR):
            for f in files:
                if Path(f).suffix in EXTENSIONS:
                    files_to_scan.append(os.path.join(root, f))
                    
        logger.debug(f"   -> Found {len(files_to_scan)} potential artifacts.")
        
        # Shuffle/Slice
        if len(files_to_scan) > MAX_FILES:
            random.shuffle(files_to_scan)
            files_to_scan = files_to_scan[:MAX_FILES]
            
        logger.debug(f"   -> Processing {len(files_to_scan)} files.")
        
        self.connect_db()
        
        total_ingested = 0
        batch = []
        start_time = time.time()
        
        # 2. Parallel Ingestion
        logger.debug("2. Ingesting...")
        workers = os.cpu_count() or 4
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Chunking the futures submission to avoid memory spikes if list is huge
            chunk_size = 10000
            for i in range(0, len(files_to_scan), chunk_size):
                chunk = files_to_scan[i:i+chunk_size]
                futures = {executor.submit(process_file_worker, f): f for f in chunk}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        batch.append(result)
                        
                    if len(batch) >= BATCH_SIZE:
                        self.batch_insert_memories(batch)
                        total_ingested += len(batch)
                        batch = []
                        elapsed = time.time() - start_time
                        rate = total_ingested / elapsed if elapsed > 0 else 0
                        logger.debug(f"   Stored {total_ingested} memories... ({rate:.0f}/s)", end='\r')
                        
        # Final batch
        if batch:
            self.batch_insert_memories(batch)
            total_ingested += len(batch)
            
        logger.debug(f"\n✅ Deep Recall Complete. Processed {total_ingested} files.")
        
        # 3. Final Verification
        cur = self.conn.cursor()
        cur.execute("SELECT count(*) FROM memories")
        count = cur.fetchone()[0]
        logger.debug(f"📊 Total System Memories: {count}")
        
        self.close_db()

if __name__ == "__main__":
    recall = DeepRecall()
    asyncio.run(recall.run())
