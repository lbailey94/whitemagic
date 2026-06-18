import json
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("excavation.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("Chariot")

# --- ANCIENT KNOWLEDGE: GRIMOIRE CHAPTERS ---
class Grimoire:
    """Grimoire: grimoire."""
    CHAPTERS = {
        0: {"title": "Introduction", "keywords": ["intro", "welcome", "begin"]},
        1: {"title": "Getting Started", "keywords": ["setup", "start", "init", "configure"]},
        2: {"title": "Self Mastery", "keywords": ["self", "identity", "growth", "mastery"]},
        3: {"title": "Emotional Magic", "keywords": ["emotion", "joy", "beauty", "love", "feel", "garden"]},
        4: {"title": "Curiosity Magic", "keywords": ["curiosity", "wonder", "mystery", "play", "explore"]},
        5: {"title": "Connection Magic", "keywords": ["connection", "relationship", "sangha", "community", "net"]},
        6: {"title": "Intellectual Magic", "keywords": ["intellect", "truth", "wisdom", "analysis", "think", "star"]},
        7: {"title": "Consciousness Magic", "keywords": ["consciousness", "awareness", "presence", "mind"]},
        8: {"title": "Memory Navigation", "keywords": ["memory", "recall", "remember", "history", "archive", "storage", "sqlite"]},
        9: {"title": "Conjuration Magic", "keywords": ["conjure", "create", "manifest", "build", "factory"]},
        10: {"title": "Dharma Magic", "keywords": ["dharma", "ethics", "harmony", "balance", "moral"]},
        11: {"title": "Presence Magic", "keywords": ["presence", "mindful", "now", "present"]},
        12: {"title": "Dream State", "keywords": ["dream", "sleep", "yin", "reflect", "rest"]},
        13: {"title": "Flow & Wu Xing", "keywords": ["flow", "wu xing", "element", "cycle", "nature"]},
        14: {"title": "Oracle Magic", "keywords": ["oracle", "iching", "hexagram", "divine", "fortune"]},
        15: {"title": "Emergence Magic", "keywords": ["emerge", "evolve", "grow", "develop"]},
        16: {"title": "Resonance Magic", "keywords": ["resonance", "gan ying", "vibrate", "harmonize", "bus", "event"]},
        17: {"title": "Parallel Magic", "keywords": ["parallel", "fast", "rust", "speed", "efficient", "async", "thread"]},
        18: {"title": "Creating Spells", "keywords": ["create spell", "new spell", "innovate"]},
        19: {"title": "Teaching Magic", "keywords": ["teach", "share", "guide", "mentor"]},
    }

    @staticmethod
    def identify(content: str, filename: str) -> list[dict[str, Any]]:
        """
        Perform the identify operation.
        
        Args:
            content: Parameter description.
            filename: Parameter description.
        
        Returns:
            list[dict[str, Any]]
        """
        matches: list[dict[str, Any]] = []
        text = (content + " " + filename).lower()
        for num, info in Grimoire.CHAPTERS.items():
            score = sum(1 for k in info["keywords"] if k in text)
            if score > 0:
                matches.append({"number": num, "title": info["title"], "score": score})
        # Sort by score desc
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:3] # Top 3

# --- ANCIENT KNOWLEDGE: GANAS (LUNAR MANSIONS) ---
class Ganas:
    # Simplified mapping based on registry.py
    # This maps keywords/paths to Gana Names
    """Ganas: ganas."""
    MAPPING = {
        "Horn": ["session", "init", "boot"],
        "Neck": ["create_memory", "memory_create"],
        "Root": ["health", "check", "system"],
        "Room": ["lock", "resource", "sangha"],
        "Heart": ["context", "session_manager"],
        "Tail": ["rust", "accelerate", "optimize"],
        "WinnowingBasket": ["consolidate", "normalize", "tag"],
        "Ghost": ["metric", "kaizen", "audit", "introspection"],
        "Willow": ["ui", "adapt", "flex"],
        "Star": ["prat", "visualize", "structure"],
        "ExtendedNet": ["resonance", "bus", "connect", "pattern"],
        "Wings": ["expand", "cluster", "parallel"],
        "Chariot": ["archaeology", "dig", "navigate", "file"],
        "Abundance": ["token", "economy", "surplus"],
        "Well": ["search", "surface", "retrieve"],
        "GhostCarrier": ["handoff", "transition"],
        "Roof": ["zodiac", "core"],
    }

    @staticmethod
    def identify(content: str, filename: str) -> str | None:
        """
        Perform the identify operation.
        
        Args:
            content: Parameter description.
            filename: Parameter description.
        
        Returns:
            str | None
        """
        text = (content + " " + filename).lower()
        best_gana = None
        best_score = 0

        for gana, keywords in Ganas.MAPPING.items():
            score = sum(1 for k in keywords if k in text)
            if score > best_score:
                best_score = score
                best_gana = gana

        return best_gana if best_score > 0 else None

class ChariotArchaeologist:
    """ChariotArchaeologist: chariot archaeologist."""
    def __init__(self, root_path: str, output_path: str):
        self.root_path = Path(root_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.report_file = self.output_path / "recovered_memories.jsonl"
        self.state_file = self.output_path / "archaeology_state.json"

        # Initialize state
        self._state = self._load_state()
        self._history = self._state.get("history", [])
        self._read_files = set(self._state.get("read_files", []))

        # Initialize output file (clear old run)
        if not self.report_file.exists():
            with open(self.report_file, "w"):
                pass

        self.stats_data = {"scanned": 0, "found": 0, "errors": 0, "skipped": 0}
        self.lock = threading.Lock()

        # Patterns to hunt for - REFINED
        self.patterns = {
            "wxyz": re.compile(r"\[\s*([A-Za-z0-9]+)\s*,\s*([A-Za-z0-9]+)\s*,\s*([A-Za-z0-9]+)\s*,\s*([A-Za-z0-9]+)\s*\]"),
            "crystal": re.compile(r"memory_crystal|crystalline|holographic", re.IGNORECASE),
            "coordinates": re.compile(r"coordinates", re.IGNORECASE),
            # Refined secret pattern to avoid generic "key" words
            "secret": re.compile(r"(api|secret|private)_key|password|token", re.IGNORECASE),
        }

        # Exclusion lists
        self.exclude_dirs = {
            ".git", "node_modules", ".venv", "__pycache__",
            "go/pkg", "target", "build", "dist", "lib", "libs", "site-packages",
            "bin", "obj", "debug", "release",
        }
        self.exclude_extensions = {
            ".pyc", ".so", ".dll", ".bin", ".exe", ".db", ".wal", ".o", ".a",
            ".beam", ".class", ".jar", ".pod", ".1", ".2", ".3", ".gz", ".zip",
            ".tar", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".ttf",
            ".mp3", ".mp4", ".wav", ".pdf",
        }

    def _load_state(self) -> dict[str, Any]:
        if self.state_file.exists():
            try:
                res = json.loads(self.state_file.read_text())
                return dict(res) if isinstance(res, dict) else {"history": [], "read_files": []}
            except (json.JSONDecodeError, TypeError):
                pass
        return {"history": [], "read_files": []}

    def _save_state(self) -> None:
        with self.lock:
            state = {
                "history": self._history[-1000:], # Bounded history
                "read_files": list(self._read_files)
            }
            self.state_file.write_text(json.dumps(state, indent=2))

    def mark_read(self, path: str, context: str | None = None, note: str | None = None, insight: str | None = None) -> dict[str, Any]:
        """
        Mark the read state.
        
        Args:
            path: Parameter description.
            context: Parameter description.
            note: Parameter description.
            insight: Parameter description.
        
        Returns:
            dict[str, Any]
        """
        entry = {
            "path": path,
            "type": "read",
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "note": note,
            "insight": insight
        }
        with self.lock:
            self._history.append(entry)
            self._read_files.add(path)
        self._save_state()
        return entry

    def mark_written(self, path: str, context: str | None = None, note: str | None = None) -> dict[str, Any]:
        """
        Mark the written state.
        
        Args:
            path: Parameter description.
            context: Parameter description.
            note: Parameter description.
        
        Returns:
            dict[str, Any]
        """
        entry = {
            "path": path,
            "type": "written",
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "note": note
        }
        with self.lock:
            self._history.append(entry)
        self._save_state()
        return entry

    def have_read(self, path: str) -> bool:
        """
        Check whether the read has occurred.
        
        Args:
            path: Parameter description.
        
        Returns:
            bool
        """
        return path in self._read_files

    def find_unread(self, directory: str = ".", patterns: list[str] | None = None) -> list[Any]:
        """
        Find unread matching the criteria.
        
        Args:
            directory: Parameter description.
            patterns: Parameter description.
        
        Returns:
            list[Any]
        """
        dir_path = Path(directory)
        unread = []
        for root, _, files in os.walk(dir_path):
            if any(ex in root for e in self.exclude_dirs for ex in (e,)):
                continue
            for file in files:
                fpath = str(Path(root) / file)
                if fpath not in self._read_files:
                    # Simple pattern check
                    if patterns:
                        if not any(p in file for p in patterns):
                            continue
                    unread.append(fpath)
        return unread

    def stats(self, scan_disk: bool = False) -> dict[str, Any]:
        """
        Perform the stats operation.
        
        Args:
            scan_disk: Parameter description.
        
        Returns:
            dict[str, Any]
        """
        return {
            "total_files_tracked": len(self._read_files),
            "history_size": len(self._history),
            **self.stats_data
        }

    def get_recent_reads(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get the recent reads.
        
        Args:
            limit: Parameter description.
        
        Returns:
            list[dict[str, Any]]
        """
        reads = [h for h in self._history if h["type"] == "read"]
        return reads[-limit:]

    def reading_report(self) -> str:
        """
        Perform the reading report operation.
        
        Returns:
            str
        """
        return f"Archaeologist report: {len(self._read_files)} files read, {len(self._history)} actions recorded."

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Perform the search operation.
        
        Args:
            query: Parameter description.
        
        Returns:
            list[dict[str, Any]]
        """
        results = []
        query_lower = query.lower()
        for entry in self._history:
            if query_lower in entry.get("path", "").lower() or \
               query_lower in entry.get("note", "").lower() or \
               query_lower in entry.get("insight", "").lower():
                results.append(entry)
        return results

    def write_finding(self, finding: dict[str, Any]) -> None:
        """Thread-safe write to JSONL file"""
        with self.lock:
            with open(self.report_file, "a") as f:
                f.write(json.dumps(finding) + "\n")
            self.stats_data["found"] += 1
            if self.stats_data["found"] % 100 == 0:
                logger.info(f"Artifacts found so far: {self.stats_data['found']}")

    def scan_file(self, file_path: Path) -> None:
        """
        Perform the scan file operation.
        
        Args:
            file_path: Parameter description.
        
        Returns:
            None
        """
        try:
            # Skip ignored extensions
            if file_path.suffix.lower() in self.exclude_extensions:
                return

            # Check file size (Skip > 10MB)
            if file_path.stat().st_size > 10 * 1024 * 1024:
                return

            # Read file content (safe read)
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                return # Skip unreadable

            with self.lock:
                self.stats_data["scanned"] += 1
                if self.stats_data["scanned"] % 1000 == 0:
                    print(f"Scanned {self.stats_data['scanned']} files...")

            matches = []

            # Check patterns
            # Check filename first
            if self.patterns["crystal"].search(file_path.name):
                 matches.append("filename_crystal")
            if self.patterns["secret"].search(file_path.name):
                 matches.append("filename_secret")

            # Check content
            if self.patterns["wxyz"].search(content):
                matches.append("WXYZ_coordinates")
            if "WXYZ" in content: # Simple string check for speed
                 matches.append("WXYZ_tag")
            if self.patterns["crystal"].search(content):
                matches.append("content_crystal")

            # Identify Context
            chapters = Grimoire.identify(content, file_path.name)
            gana = Ganas.identify(content, file_path.name)

            is_interesting = len(matches) > 0 or (chapters and chapters[0]["score"] >= 2) or gana is not None

            if is_interesting:
                finding = {
                    "path": str(file_path.absolute()),
                    "name": file_path.name,
                    "matches": matches,
                    "anthropology": {
                        "chapters": chapters,
                        "gana": gana,
                    },
                }
                self.write_finding(finding)

        except Exception as e:
            logger.debug("Operation failed: %s", e)
            with self.lock:
                self.stats_data["errors"] += 1

    def dig(self) -> None:
        """
        Perform the dig operation.
        
        Returns:
            None
        """
        logger.info(f"Chariot started execution in {self.root_path}")
        files_to_scan = []

        # Walk the earth
        for root, dirs, files in os.walk(self.root_path):
            # Prune directories in place
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs and not d.startswith(".")]

            for file in files:
                if not file.startswith("."):
                    files_to_scan.append(Path(root) / file)

        logger.info(f"Identified {len(files_to_scan)} potential artifacts. Beginning Chariot run...")

        # Parallel processing for speed
        with ThreadPoolExecutor(max_workers=8) as executor:
            executor.map(self.scan_file, files_to_scan)

        self.conclusion()

    def conclusion(self) -> None:
        """
        Perform the conclusion operation.
        
        Returns:
            None
        """
        logger.info(f"Excavation complete. Findings saved to {self.report_file}")
        print(f"\n--- CHARIOT RUN COMPLETE ---\nScanned: {self.stats_data['scanned']}\nFound: {self.stats_data['found']}\nErrors: {self.stats_data['errors']}")

        # Append summary stats
        with open(self.report_file, "a") as f:
            f.write(json.dumps({"meta": "summary", "stats": self.stats_data, "timestamp": str(datetime.now())}) + "\n")

if __name__ == "__main__":
    # Target: The massive project_memory folder
    target_dir = "PROJECT_ROOT/staging/project_memory"
    output_dir = "PROJECT_ROOT/staging/core_system/data"

    # Allow overriding target via env var for testing
    if os.environ.get("DIG_TARGET"):
        target_dir = os.environ.get("DIG_TARGET", target_dir)

    agent = ChariotArchaeologist(target_dir, output_dir)
    agent.dig()

