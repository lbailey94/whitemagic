"""Codebase Self-Model Scanner v2.

Weaves together the codex galaxy, GalaxyManager, CoordinateEncoder,
EmbeddingEngine, UnifiedMemory, and Rust accelerators to create a
self-updating snapshot of the entire codebase in galactic/holographic
memory.  Enables semantic recall of project structure and file contents
without raw grep.

v2 upgrades:
  - Overlapping chunk splitting (no more truncation data loss)
  - Batch ingestion with ThreadPoolExecutor for file reads
  - Batch SQLite writes via executemany
  - Semantic embedding integration (EmbeddingEngine.search_similar)
  - Rust-powered recall (BM25 search, holographic_nearest_5d)
  - Progress callbacks for long-running scans
  - Configurable batch sizes to prevent laptop hangs

Architecture:
    CodebaseScanner
        ├── scan()          — walk project tree, chunk + ingest files + dirs
        ├── recall()        — semantic + FTS5 + Rust BM25 search of codex galaxy
        ├── structure()     — recall directory topology from memory
        └── status()        — scan metadata, file counts, last scan time

Storage layout:
    File memories (parent):
        title:   "FILE: relative/path/to/file.py"
        content: first chunk (for quick preview)
        tags:    ["codex", "file", "ext:py", "path:..."]
        metadata: {source_path, relative_path, file_size, mtime, content_hash,
                   chunk_count, chunk_size, chunk_overlap}

    Chunk memories (children):
        title:   "CHUNK: relative/path.py#0"
        content: chunk text (up to chunk_size chars)
        tags:    ["codex", "chunk", "ext:py", "path:...", "chunk:0"]
        metadata: {relative_path, chunk_index, chunk_count, content_hash}

    Directory memories:
        title:   "DIR: relative/path/to/dir"
        content: JSON listing of files + subdirs
        tags:    ["codex", "directory", "topology", "path:..."]

    Scan manifest memory:
        title:   "CODEX SCAN MANIFEST"
        content: JSON summary of last scan
        tags:    ["codex", "scan_manifest", "substrate"]
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────

MAX_FILE_SIZE = 100_000  # 100KB — larger files skipped
CHUNK_SIZE = 4000  # ~1K tokens per chunk (conservative for code)
CHUNK_OVERLAP = 400  # 10% overlap for context continuity
MAX_CONTENT_STORE = 50_000  # Fallback truncation for non-chunked mode
BATCH_READ_WORKERS = 8  # Parallel file readers
BATCH_DB_SIZE = 50  # SQLite executemany batch size
EMBED_BATCH_SIZE = 64  # Embedding model batch size

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "target", "dist", ".next", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".hypothesis", ".eggs", "build", ".tox",
    ".git-backup", ".git-backup-upstream", "site-packages",
    "elm-stuff", "deps", "_build", "cover",
}
SCAN_EXTENSIONS = {
    # Source code
    ".py", ".rs", ".go", ".zig", ".kk", ".hs", ".ex", ".exs", ".jl",
    ".c", ".h", ".cpp", ".hpp", ".cc",
    # Frontend
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".css", ".html", ".vue", ".svelte",
    # Docs
    ".md", ".mdx", ".txt", ".rst", ".org",
    # Config
    ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".conf",
    ".env.example", ".gitignore", ".dockerignore",
    # Scripts
    ".sh", ".bash", ".zsh", ".fish", ".ps1",
    # Data
    ".sql", ".csv", ".tsv",
    # Build
    ".mk", "Makefile", "justfile", "Dockerfile",
    # Other
    ".lock", ".mod", ".sum", ".exs", ".eex", ".heex",
    ".wxs", ".wxi", ".wxl",
}
NO_EXT_FILES = {
    "Makefile", "justfile", "Dockerfile", "LICENSE", "README",
    "CHANGELOG", "VERSION", "AUTHORS", "CONTRIBUTING",
    ".gitignore", ".dockerignore", ".env.example", ".editorconfig",
    "CITATION.cff",
}
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg",
    ".tiff", ".heic", ".heif", ".pdf", ".zip", ".tar", ".gz", ".bz2",
    ".7z", ".rar", ".deb", ".rpm", ".dmg", ".exe", ".dll", ".so",
    ".dylib", ".o", ".a", ".lib", ".pyc", ".pyo", ".class", ".jar",
    ".wasm", ".mp4", ".mp3", ".wav", ".flac", ".ogg", ".avi", ".mov",
    ".db", ".sqlite", ".sqlite3", ".db-journal", ".db-wal", ".db-shm",
    ".bin", ".dat", ".pak", ".npy", ".npz", ".pkl", ".pickle",
    ".pt", ".pth", ".onnx", ".gguf", ".ggml", ".safetensors",
    ".lock.lock", ".log",
}


@dataclass
class ScanResult:
    """Result of a codebase scan."""

    total_files: int = 0
    total_dirs: int = 0
    total_bytes: int = 0
    ingested: int = 0
    skipped: int = 0
    errors: int = 0
    unchanged: int = 0
    chunks_created: int = 0
    embedded: int = 0
    duration_s: float = 0.0
    by_extension: dict[str, int] = field(default_factory=dict)
    scan_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_dirs": self.total_dirs,
            "total_bytes": self.total_bytes,
            "ingested": self.ingested,
            "skipped": self.skipped,
            "errors": self.errors,
            "unchanged": self.unchanged,
            "chunks_created": self.chunks_created,
            "embedded": self.embedded,
            "duration_s": round(self.duration_s, 2),
            "by_extension": self.by_extension,
            "scan_time": self.scan_time,
        }


@dataclass
class FileEntry:
    """Metadata for a single file."""

    path: Path
    relative_path: str
    size: int
    mtime: float
    content_hash: str
    extension: str
    is_text: bool = True

    def to_metadata(self) -> dict[str, Any]:
        return {
            "source_path": str(self.path),
            "relative_path": self.relative_path,
            "file_size": self.size,
            "mtime": self.mtime,
            "content_hash": self.content_hash,
            "extension": self.extension,
        }


@dataclass
class Chunk:
    """A single chunk of a file."""

    relative_path: str
    chunk_index: int
    chunk_count: int
    content: str
    content_hash: str
    extension: str

    @property
    def title(self) -> str:
        return f"CHUNK: {self.relative_path}#{self.chunk_index}"

    def to_tags(self) -> set[str]:
        return {
            "codex",
            "chunk",
            f"ext:{self.extension.lstrip('.')}" if self.extension else "ext:none",
            f"path:{self.relative_path}",
            f"chunk:{self.chunk_index}",
        }

    def to_metadata(self, parent_hash: str) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "chunk_index": self.chunk_index,
            "chunk_count": self.chunk_count,
            "content_hash": self.content_hash,
            "parent_hash": parent_hash,
            "galaxy": "codex",
            "is_codebase_chunk": True,
        }


def split_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks.

    Splits on paragraph boundaries when possible for cleaner context.
    Falls back to character-based splitting for files without paragraphs.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            # Try to break at a paragraph boundary within the last 20% of the chunk
            search_start = end - int(chunk_size * 0.2)
            para_break = text.rfind("\n\n", search_start, end)
            if para_break > start:
                end = para_break + 2
            else:
                # Try line break
                line_break = text.rfind("\n", search_start, end)
                if line_break > start:
                    end = line_break + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward with overlap
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks


class CodebaseScanner:
    """Scans a codebase and ingests its structure + contents into the codex galaxy.

    v2: Uses chunking, batch ingestion, and semantic embedding integration.
    """

    def __init__(
        self,
        project_root: Path | str | None = None,
        galaxy_name: str = "codex",
        max_file_size: int = MAX_FILE_SIZE,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        batch_workers: int = BATCH_READ_WORKERS,
        embed_batch_size: int = EMBED_BATCH_SIZE,
    ) -> None:
        from whitemagic.config.paths import WM_ROOT

        self.project_root = Path(project_root) if project_root else WM_ROOT
        self.galaxy_name = galaxy_name
        self.max_file_size = max_file_size
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_workers = batch_workers
        self.embed_batch_size = embed_batch_size
        self._last_scan: ScanResult | None = None

    # ── Public API ────────────────────────────────────────────────────

    def scan(
        self,
        incremental: bool = True,
        extensions: set[str] | None = None,
        skip_dirs: set[str] | None = None,
        max_files: int = 10000,
        embed: bool = True,
        progress_cb: Callable[[str, int, int], None] | None = None,
    ) -> ScanResult:
        """Full codebase scan → chunk + ingest into codex galaxy.

        Args:
            incremental: If True, skip files whose content_hash hasn't changed.
            extensions: Override default file extensions to scan.
            skip_dirs: Override default directories to skip.
            max_files: Maximum number of files to ingest.
            embed: If True, trigger embedding indexing after ingestion.
            progress_cb: Optional callback(phase, current, total) for progress.

        Returns:
            ScanResult with statistics.
        """
        start = time.time()
        exts = extensions or SCAN_EXTENSIONS
        skips = skip_dirs or SKIP_DIRS

        result = ScanResult(scan_time=datetime.now().isoformat())

        # Phase 1: Walk and collect file metadata
        if progress_cb:
            progress_cb("walking", 0, 0)
        files = self._walk(self.project_root, exts, skips, max_files)
        result.total_files = len(files)

        dirs = self._collect_dirs(files)
        result.total_dirs = len(dirs)

        # Phase 2: Get existing hashes for incremental dedup
        existing_hashes: dict[str, str] = {}
        if incremental:
            existing_hashes = self._get_existing_hashes()

        # Phase 3: Batch read file contents in parallel
        if progress_cb:
            progress_cb("reading", 0, len(files))
        file_contents = self._batch_read_files(files, progress_cb)

        # Phase 4: Ingest directories (topology) — batch
        if progress_cb:
            progress_cb("ingesting_dirs", 0, len(dirs))
        dir_memories: list[tuple[str, str, set[str], float, dict]] = []
        # Precompute dir → files mapping for O(N) instead of O(N×M)
        dir_files_map: dict[Path, list[str]] = {}
        dir_subdirs_map: dict[Path, set[str]] = {}
        for f in files:
            parent = f.path.parent
            dir_files_map.setdefault(parent, []).append(f.relative_path)
            # Walk up to root, registering each ancestor as having a subdir
            p = parent
            while p != self.project_root and p.parent != p:
                ancestor = p.parent
                rel = str(p.relative_to(self.project_root))
                dir_subdirs_map.setdefault(ancestor, set()).add(rel)
                p = ancestor
        for i, dir_path in enumerate(dirs):
            try:
                dir_data = self._build_dir_memory(dir_path, files, dir_files_map, dir_subdirs_map)
                dir_memories.append(dir_data)
            except Exception as e:  # noqa: BLE001
                logger.debug("Failed to build dir memory %s: %s", dir_path, e)
                result.errors += 1
            if progress_cb and i % 10 == 0:
                progress_cb("ingesting_dirs", i, len(dirs))
        # Dir memories stored in Phase 6 with parents + chunks

        # Phase 5: Chunk + collect file parent memories
        if progress_cb:
            progress_cb("chunking", 0, len(files))
        all_chunks: list[Chunk] = []
        parent_memories: list[tuple[str, str, set[str], float, dict]] = []

        for i, entry in enumerate(files):
            result.total_bytes += entry.size
            ext = entry.extension or "(no ext)"
            result.by_extension[ext] = result.by_extension.get(ext, 0) + 1

            if incremental and entry.content_hash in existing_hashes:
                existing_id = existing_hashes[entry.content_hash]
                if existing_id:
                    result.unchanged += 1
                    continue

            content = file_contents.get(entry.relative_path)
            if content is None:
                result.skipped += 1
                continue

            try:
                chunks = split_into_chunks(content, self.chunk_size, self.chunk_overlap)

                # Collect parent file memory data
                preview = chunks[0][:2000] if chunks else content[:2000]
                parent_tags = {
                    "codex",
                    "file",
                    f"ext:{entry.extension.lstrip('.')}" if entry.extension else "ext:none",
                    f"path:{entry.relative_path}",
                }
                parent_importance = self._calculate_importance(entry)
                parent_metadata = {
                    **entry.to_metadata(),
                    "galaxy": self.galaxy_name,
                    "is_codebase_file": True,
                    "chunk_count": len(chunks),
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                }
                parent_memories.append((
                    preview,
                    f"FILE: {entry.relative_path}",
                    parent_tags,
                    parent_importance,
                    parent_metadata,
                ))

                # Create chunk objects
                for ci, chunk_text in enumerate(chunks):
                    chunk_hash = hashlib.sha256(chunk_text.encode()).hexdigest()[:16]
                    chunk = Chunk(
                        relative_path=entry.relative_path,
                        chunk_index=ci,
                        chunk_count=len(chunks),
                        content=chunk_text,
                        content_hash=chunk_hash,
                        extension=entry.extension,
                    )
                    all_chunks.append(chunk)

                result.ingested += 1
                result.chunks_created += len(chunks)
            except Exception as e:  # noqa: BLE001
                logger.debug("Failed to ingest %s: %s", entry.relative_path, e)
                result.errors += 1

            if progress_cb and i % 10 == 0:
                progress_cb("chunking", i, len(files))

        # Phase 6: Batch store ALL memories (parents + chunks + dirs) in one transaction
        if progress_cb:
            progress_cb("storing", 0, len(all_chunks) + len(parent_memories) + len(dir_memories))
        self._batch_store_all(parent_memories, all_chunks, dir_memories)

        # Phase 7: Trigger embedding indexing (batch)
        if embed and all_chunks:
            if progress_cb:
                progress_cb("embedding", 0, len(all_chunks))
            result.embedded = self._batch_embed_chunks(all_chunks, progress_cb)

        result.duration_s = time.time() - start
        self._last_scan = result

        # Store scan manifest
        self._store_manifest(result)

        logger.info(
            "Codebase scan complete: %d files (%d ingested, %d unchanged), "
            "%d chunks, %d embedded, %d dirs, %d errors, %.1fs",
            result.total_files,
            result.ingested,
            result.unchanged,
            result.chunks_created,
            result.embedded,
            result.total_dirs,
            result.errors,
            result.duration_s,
        )
        return result

    def recall(
        self,
        query: str,
        limit: int = 20,
        tags: list[str] | None = None,
        min_importance: float = 0.0,
        semantic: bool = True,
    ) -> list[dict[str, Any]]:
        """Semantic + FTS5 recall from the codex galaxy.

        Tries in order:
        1. Semantic embedding search (if embeddings available)
        2. Rust BM25 search (if Rust available)
        3. FTS5 fallback (always available)
        """
        if not query:
            return []

        # Try semantic search first
        if semantic:
            sem_results = self._semantic_recall(query, limit, tags, min_importance)
            if sem_results:
                return sem_results

        # Try Rust BM25
        rust_results = self._rust_bm25_recall(query, limit)
        if rust_results:
            return rust_results

        # FTS5 fallback
        return self._fts5_recall(query, limit, tags, min_importance)

    def structure(self, dir_path: str | None = None) -> dict[str, Any]:
        """Recall directory topology from memory."""
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()

        if dir_path:
            rel_dir = dir_path
        else:
            rel_dir = "."
        proj_hash = hashlib.sha256(str(self.project_root).encode()).hexdigest()[:8]
        title = f"DIR:{proj_hash}:{rel_dir}"

        results = um.search(
            query=title,
            tags=["codex", "directory", "topology"],
            limit=10,
            galaxy=self.galaxy_name,
        )

        # Filter by project_root to avoid cross-project pollution in shared galaxy
        for mem in results:
            content = mem.content
            if isinstance(content, dict):
                data = content
            elif isinstance(content, str):
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    continue
            else:
                continue
            # Check if this memory belongs to our project
            mem_meta = getattr(mem, "metadata", None) or {}
            mem_project = mem_meta.get("project_root") if isinstance(mem_meta, dict) else None
            if mem_project and mem_project != str(self.project_root):
                continue
            if not mem_project:
                # Old memory without project_root — skip to avoid cross-project pollution
                continue
            return {
                "directory": data.get("path", dir_path or "."),
                "files": data.get("files", []),
                "subdirs": data.get("subdirs", []),
            }

        return {"directory": dir_path or ".", "files": [], "subdirs": [], "note": "Not scanned yet"}

    def status(self) -> dict[str, Any]:
        """Get scan status — last scan time, file counts, extension breakdown."""
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()

        results = um.search(
            query="CODEX SCAN MANIFEST",
            tags=["codex", "scan_manifest"],
            limit=1,
        )

        if results:
            mem = results[0]
            content = mem.content
            if isinstance(content, dict):
                manifest = content
            elif isinstance(content, str):
                try:
                    manifest = json.loads(content)
                except json.JSONDecodeError:
                    manifest = {}
            else:
                manifest = {}
            if manifest:
                return {
                    "last_scan": manifest.get("scan_time", "unknown"),
                    "project_root": str(self.project_root),
                    "galaxy": self.galaxy_name,
                    **manifest,
                }

        return {
            "last_scan": "never",
            "project_root": str(self.project_root),
            "galaxy": self.galaxy_name,
            "note": "No scan has been run yet. Call codebase.scan to begin.",
        }

    # ── Internal: file walking ────────────────────────────────────────

    def _walk(
        self,
        root: Path,
        extensions: set[str],
        skip_dirs: set[str],
        max_files: int,
    ) -> list[FileEntry]:
        """Walk the project tree and collect file metadata.

        Uses Rust parallel walker (rayon) when available for ~10x faster walks.
        Falls back to Python os.walk otherwise.
        """
        files: list[FileEntry] = []

        # Try Rust parallel walker first
        try:
            import whitemagic_rs

            rust_files = whitemagic_rs.walk_directory(str(root))
            # rust_files: dict[ext, list[path_string]]
            all_paths: list[str] = []
            for ext, paths in rust_files.items():
                if ext in extensions or ext in SKIP_EXTENSIONS:
                    if ext not in extensions:
                        continue
                    all_paths.extend(paths)
                else:
                    # Unknown extension — check if it's a no-ext file
                    pass

            # Also check no-ext files
            for ext, paths in rust_files.items():
                if ext not in extensions and ext not in SKIP_EXTENSIONS:
                    for p in paths:
                        if Path(p).name in NO_EXT_FILES:
                            all_paths.append(p)

            for path_str in all_paths:
                if len(files) >= max_files:
                    logger.info("Max files (%d) reached, stopping scan", max_files)
                    return files

                filepath = Path(path_str)
                ext = filepath.suffix.lower()

                # Skip dirs
                parts = filepath.relative_to(root).parts
                if any(p in skip_dirs or p.startswith(".git") for p in parts[:-1]):
                    continue

                try:
                    stat = filepath.stat()
                except OSError:
                    continue

                if stat.st_size > self.max_file_size:
                    continue

                content_hash = self._hash_file(filepath)
                rel_path = str(filepath.relative_to(root))

                files.append(
                    FileEntry(
                        path=filepath,
                        relative_path=rel_path,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        content_hash=content_hash,
                        extension=ext,
                    )
                )

            return files

        except (ImportError, AttributeError, Exception) as e:
            logger.debug("Rust walk_directory unavailable, falling back to os.walk: %s", e)

        # Python fallback
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".git")]

            for filename in filenames:
                if len(files) >= max_files:
                    logger.info("Max files (%d) reached, stopping scan", max_files)
                    return files

                filepath = Path(dirpath) / filename
                ext = filepath.suffix.lower()

                if ext not in extensions and filename not in NO_EXT_FILES:
                    if ext in SKIP_EXTENSIONS:
                        continue
                    continue

                try:
                    stat = filepath.stat()
                except OSError:
                    continue

                if stat.st_size > self.max_file_size:
                    continue

                content_hash = self._hash_file(filepath)
                rel_path = str(filepath.relative_to(root))

                files.append(
                    FileEntry(
                        path=filepath,
                        relative_path=rel_path,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        content_hash=content_hash,
                        extension=ext,
                    )
                )

        return files

    def _collect_dirs(self, files: list[FileEntry]) -> list[Path]:
        """Collect unique directory paths from file list."""
        dirs: set[Path] = set()
        for f in files:
            dirs.add(f.path.parent)
            parent = f.path.parent
            while parent != self.project_root and parent.parent != parent:
                dirs.add(parent)
                parent = parent.parent
        dirs.add(self.project_root)
        return sorted(dirs)

    def _hash_file(self, path: Path) -> str:
        """Compute SHA-256 hash of file content (first 10KB for speed)."""
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                h.update(f.read(10240))
        except OSError:
            logger.debug("Ignored OSError in codebase_scanner.py:723")
        return h.hexdigest()[:16]

    # ── Internal: batch file reading ──────────────────────────────────

    def _batch_read_files(
        self,
        files: list[FileEntry],
        progress_cb: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, str | None]:
        """Read file contents in parallel using ThreadPoolExecutor.

        Returns dict of relative_path -> content (or None if read failed).
        """
        contents: dict[str, str | None] = {}

        def _read_one(entry: FileEntry) -> tuple[str, str | None]:
            try:
                text = entry.path.read_text(encoding="utf-8", errors="replace")
                return entry.relative_path, text
            except OSError:
                return entry.relative_path, None

        workers = min(self.batch_workers, len(files) or 1)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_read_one, f): f for f in files
            }
            done = 0
            for future in as_completed(futures):
                rel_path, content = future.result()
                contents[rel_path] = content
                done += 1
                if progress_cb and done % 20 == 0:
                    progress_cb("reading", done, len(files))

        return contents

    # ── Internal: direct SQLite store (bypasses um.store overhead) ────

    def _direct_store(
        self,
        content: str,
        title: str,
        tags: set[str],
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory directly to SQLite, bypassing the full um.store pipeline.

        Skips: surprise gate, holographic index, HRR vector, auto-embed.
        This is ~100x faster than um.store() for batch ingestion.
        """
        import sqlite3

        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()
        metadata = metadata or {}
        galaxy = metadata.get("galaxy", self.galaxy_name)

        content_str = str(content)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        memory_id = hashlib.sha256(f"{content_str[:1000]}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        now = datetime.now().isoformat()

        try:
            # Write to the galaxy backend so um.search() can find it
            backend = um._galaxy_backend._get_galaxy_backend(galaxy)
            with backend.pool.connection() as conn:
                with conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO memories
                           (id, content, memory_type, created_at, updated_at, accessed_at,
                            access_count, emotional_valence, importance, neuro_score,
                            novelty_score, recall_count, half_life_days, is_protected,
                            metadata, title, galactic_distance, retention_score,
                            last_retention_sweep, content_hash, event_time, ingestion_time,
                            is_private, model_exclude, galaxy, source_trust)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            memory_id, content_str, "LONG_TERM", now, now, now,
                            0, 0.0, importance, 0.0,
                            0.0, 0, 0.0, 0,
                            json.dumps(metadata), title, 0.5, 0.5,
                            now, content_hash, None, now,
                            0, 0, galaxy, "tool_output",
                        ),
                    )
                    if tags:
                        conn.execute("DELETE FROM tags WHERE memory_id = ?", (memory_id,))
                        conn.executemany(
                            "INSERT INTO tags (memory_id, tag) VALUES (?, ?)",
                            [(memory_id, t) for t in tags],
                        )
                    # FTS5 index insert
                    conn.execute("DELETE FROM memories_fts WHERE id = ?", (memory_id,))
                    tags_text = " ".join(tags) if tags else ""
                    conn.execute(
                        "INSERT INTO memories_fts (id, title, content, tags_text) VALUES (?, ?, ?, ?)",
                        (memory_id, title, content_str, tags_text),
                    )
        except sqlite3.Error as e:
            logger.debug("Direct store failed for %s: %s", title, e)
            return ""

        return memory_id

    # ── Internal: batch ingestion (single transaction for all memories) ──

    def _build_dir_memory(
        self,
        dir_path: Path,
        all_files: list[FileEntry],
        dir_files_map: dict[Path, list[str]] | None = None,
        dir_subdirs_map: dict[Path, set[str]] | None = None,
    ) -> tuple[str, str, set[str], float, dict]:
        """Build directory topology memory data without storing."""
        try:
            rel_dir = str(dir_path.relative_to(self.project_root))
        except ValueError:
            rel_dir = str(dir_path)

        if rel_dir == ".":
            rel_dir = "."

        # Use precomputed maps if available (O(1) lookup)
        if dir_files_map is not None:
            files_in_dir = sorted(dir_files_map.get(dir_path, []))
        else:
            files_in_dir = sorted(
                f.relative_path for f in all_files if f.path.parent == dir_path
            )

        if dir_subdirs_map is not None:
            subdirs = sorted(dir_subdirs_map.get(dir_path, set()))
        else:
            subdirs = sorted(
                {
                    str(p.relative_to(self.project_root))
                    for f in all_files
                    for p in [f.path.parent]
                    if p != dir_path and p.is_relative_to(dir_path)
                    and len(p.relative_to(dir_path).parts) == 1
                }
            )

        topology = {
            "path": rel_dir,
            "files": sorted(files_in_dir),
            "subdirs": subdirs,
            "file_count": len(files_in_dir),
            "subdir_count": len(subdirs),
        }

        tags = {
            "codex",
            "directory",
            "topology",
            f"path:{rel_dir}",
        }

        content = json.dumps(topology, indent=2)
        metadata = {
            "galaxy": self.galaxy_name,
            "is_directory": True,
            "file_count": len(files_in_dir),
            "subdir_count": len(subdirs),
            "project_root": str(self.project_root),
        }
        # Include project root hash in title for unique FTS5 matching
        proj_hash = hashlib.sha256(str(self.project_root).encode()).hexdigest()[:8]
        return (content, f"DIR:{proj_hash}:{rel_dir}", tags, 0.6, metadata)

    def _batch_store_dir_memories(
        self, dir_memories: list[tuple[str, str, set[str], float, dict]]
    ) -> None:
        """Batch store directory memories in a single transaction."""
        if not dir_memories:
            return
        self._batch_store_all(dir_memories, [], [])

    def _batch_store_all(
        self,
        parent_memories: list[tuple[str, str, set[str], float, dict]],
        chunks: list[Chunk],
        dir_memories: list[tuple[str, str, set[str], float, dict]],
    ) -> None:
        """Batch store all memories (parents + chunks + dirs) in one transaction.

        This is the core performance method — ~100x faster than per-item um.store().
        """
        import sqlite3

        from whitemagic.core.memory.unified import get_unified_memory

        if not parent_memories and not chunks and not dir_memories:
            return

        um = get_unified_memory()
        backend = um._galaxy_backend._get_galaxy_backend(self.galaxy_name)
        now = datetime.now().isoformat()

        mem_rows: list[tuple] = []
        tag_rows: list[tuple[str, str]] = []
        fts_rows: list[tuple[str, str, str, str]] = []

        # Inline row construction (avoids closure call overhead for 5000+ items)
        # Parent file memories
        for content, title, tags, importance, metadata in parent_memories:
            content_str = str(content)
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()
            memory_id = hashlib.sha256(f"{content_str[:1000]}{now}{title}".encode()).hexdigest()[:16]
            tags_text = " ".join(tags)
            mem_rows.append((
                memory_id, content_str, "LONG_TERM", now, now, now,
                0, 0.0, importance, 0.0,
                0.0, 0, 0.0, 0,
                json.dumps(metadata), title, 0.5, 0.5,
                now, content_hash, None, now,
                0, 0, self.galaxy_name, "tool_output",
            ))
            for t in tags:
                tag_rows.append((memory_id, t))
            fts_rows.append((memory_id, title, content_str, tags_text))

        # Chunk memories
        for chunk in chunks:
            content_str = chunk.content
            metadata = chunk.to_metadata(chunk.content_hash)
            tags = chunk.to_tags()
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()
            memory_id = hashlib.sha256(f"{content_str[:1000]}{now}{chunk.title}".encode()).hexdigest()[:16]
            tags_text = " ".join(tags)
            mem_rows.append((
                memory_id, content_str, "LONG_TERM", now, now, now,
                0, 0.0, 0.5, 0.0,
                0.0, 0, 0.0, 0,
                json.dumps(metadata), chunk.title, 0.5, 0.5,
                now, content_hash, None, now,
                0, 0, self.galaxy_name, "tool_output",
            ))
            for t in tags:
                tag_rows.append((memory_id, t))
            fts_rows.append((memory_id, chunk.title, content_str, tags_text))

        # Directory memories
        for content, title, tags, importance, metadata in dir_memories:
            content_str = str(content)
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()
            memory_id = hashlib.sha256(f"{content_str[:1000]}{now}{title}".encode()).hexdigest()[:16]
            tags_text = " ".join(tags)
            mem_rows.append((
                memory_id, content_str, "LONG_TERM", now, now, now,
                0, 0.0, importance, 0.0,
                0.0, 0, 0.0, 0,
                json.dumps(metadata), title, 0.5, 0.5,
                now, content_hash, None, now,
                0, 0, self.galaxy_name, "tool_output",
            ))
            for t in tags:
                tag_rows.append((memory_id, t))
            fts_rows.append((memory_id, title, content_str, tags_text))

        # Store the timestamp so _batch_embed_chunks can use the same IDs
        self._last_batch_timestamp = now
        self._last_batch_chunk_ids = [row[0] for row in mem_rows if "CHUNK:" in (row[15] or "")]

        try:
            with backend.pool.connection() as conn:
                with conn:
                    conn.executemany(
                        """INSERT OR REPLACE INTO memories
                           (id, content, memory_type, created_at, updated_at, accessed_at,
                            access_count, emotional_valence, importance, neuro_score,
                            novelty_score, recall_count, half_life_days, is_protected,
                            metadata, title, galactic_distance, retention_score,
                            last_retention_sweep, content_hash, event_time, ingestion_time,
                            is_private, model_exclude, galaxy, source_trust)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        mem_rows,
                    )
                    if tag_rows:
                        conn.executemany(
                            "INSERT OR IGNORE INTO tags (memory_id, tag) VALUES (?, ?)",
                            tag_rows,
                        )
                    conn.executemany(
                        "INSERT INTO memories_fts (id, title, content, tags_text) VALUES (?, ?, ?, ?)",
                        fts_rows,
                    )
        except sqlite3.Error as e:
            logger.debug("Batch store all failed: %s", e)
            self._last_batch_chunk_ids = []
            # Fallback to per-item direct store
            for content, title, tags, importance, metadata in parent_memories + dir_memories:
                try:
                    self._direct_store(content=content, title=title, tags=tags, importance=importance, metadata=metadata)
                except Exception:
                    logger.debug("Ignored error in codebase_scanner.py:1022")
            for chunk in chunks:
                try:
                    self._direct_store(content=chunk.content, title=chunk.title, tags=chunk.to_tags(), importance=0.5, metadata=chunk.to_metadata(chunk.content_hash))
                except Exception:
                    logger.debug("Ignored error in codebase_scanner.py:1027")

    def _store_manifest(self, result: ScanResult) -> None:
        """Store scan manifest as a substrate galaxy memory."""
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()

        manifest = result.to_dict()
        manifest["project_root"] = str(self.project_root)
        manifest["galaxy"] = self.galaxy_name
        manifest["scanner_version"] = "v2"

        um.store(
            content=json.dumps(manifest, indent=2),
            title="CODEX SCAN MANIFEST",
            tags={"codex", "scan_manifest", "substrate"},
            importance=0.8,
            metadata={
                "galaxy": "substrate",
                "is_scan_manifest": True,
                "scan_time": result.scan_time,
            },
        )

    def _calculate_importance(self, entry: FileEntry) -> float:
        """Calculate importance score for a file based on type and location."""
        importance = 0.4

        if entry.extension in {".py", ".rs", ".ts", ".tsx"}:
            importance += 0.2
        elif entry.extension in {".md", ".mdx"}:
            importance += 0.1
        elif entry.extension in {".toml", ".yaml", ".yml", ".json"}:
            importance += 0.15

        if "core/" in entry.relative_path or "whitemagic/" in entry.relative_path:
            importance += 0.1
        if "tools/" in entry.relative_path or "handlers/" in entry.relative_path:
            importance += 0.05

        filename = entry.path.name.upper()
        if filename in {"README.MD", "AGENTS.MD", "CHANGELOG.MD", "INDEX.MD"}:
            importance += 0.2

        return min(1.0, importance)

    def _get_existing_hashes(self) -> dict[str, str]:
        """Get content hashes of existing codex file memories for dedup."""
        import sqlite3

        from whitemagic.core.memory.unified import get_unified_memory

        hashes: dict[str, str] = {}
        try:
            um = get_unified_memory()
            backend = um._galaxy_backend._get_galaxy_backend(self.galaxy_name)
            with backend.pool.connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT m.id, m.metadata FROM memories m "
                    "WHERE m.id IN (SELECT memory_id FROM tags WHERE tag = 'codex') "
                    "AND m.id IN (SELECT memory_id FROM tags WHERE tag = 'file') "
                    "AND m.metadata LIKE '%content_hash%'"
                ).fetchall()
                for row in rows:
                    try:
                        raw = row["metadata"]
                        if not raw:
                            continue
                        meta = json.loads(raw) if isinstance(raw, str) else raw
                        if isinstance(meta, dict):
                            ch = meta.get("content_hash")
                            if ch:
                                hashes[ch] = row["id"]
                    except (json.JSONDecodeError, TypeError):
                        continue
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to get existing hashes: %s", e)

        return hashes

    # ── Internal: embedding integration ───────────────────────────────

    def _batch_embed_chunks(
        self,
        chunks: list[Chunk],
        progress_cb: Callable[[str, int, int], None] | None = None,
    ) -> int:
        """Batch embed chunks using EmbeddingEngine.

        Processes in batches of embed_batch_size to avoid memory spikes.
        Returns number of chunks successfully embedded.
        """
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine

            engine = get_embedding_engine()
            if not engine.available():
                logger.info("Embedding engine not available — skipping embedding phase")
                return 0

            embedded = 0
            total = len(chunks)
            # Use IDs from _batch_store_all if available (ensures same IDs)
            chunk_ids = getattr(self, '_last_batch_chunk_ids', [])
            self._last_batch_chunk_ids = []  # Clear after use

            for i in range(0, total, self.embed_batch_size):
                batch = chunks[i : i + self.embed_batch_size]
                # Truncate to 500 chars — FastEmbed tokenizer is slow for long code
                # texts, and 500 chars captures enough semantic signal for similarity
                texts = [c.content[:500] for c in batch]

                try:
                    vecs = engine.encode_batch(texts, batch_size=self.embed_batch_size)
                    if vecs is None:
                        logger.debug("Batch encoding returned None at batch %d", i)
                        continue

                    # Build (memory_id, vec) pairs for batch caching
                    cache_items: list[tuple[str, list[float]]] = []
                    for j, vec in enumerate(vecs):
                        idx = i + j
                        if idx < len(chunk_ids):
                            memory_id = chunk_ids[idx]
                        else:
                            # Fallback: generate ID same way as _batch_store_all
                            now = getattr(self, '_last_batch_timestamp', datetime.now().isoformat())
                            chunk = batch[j]
                            memory_id = hashlib.sha256(
                                f"{chunk.content[:1000]}{now}{chunk.title}".encode()
                            ).hexdigest()[:16]
                        cache_items.append((memory_id, list(vec) if not isinstance(vec, list) else vec))

                    # Batch cache all embeddings in one transaction (single cache invalidation)
                    cached = engine.cache_embeddings_batch(cache_items)
                    embedded += cached

                except Exception as e:  # noqa: BLE001
                    logger.debug("Batch embedding failed at batch %d: %s", i, e)

                if progress_cb:
                    progress_cb("embedding", min(i + self.embed_batch_size, total), total)

            # Note: HNSW index rebuild is skipped here — it builds lazily on
            # first search_similar call. Building it synchronously after scan
            # can hang on large datasets. The embeddings are cached and will
            # be picked up by search_similar when it builds the index on demand.

            return embedded

        except ImportError:
            logger.debug("EmbeddingEngine not available")
            return 0

    # ── Internal: recall paths ────────────────────────────────────────

    def _semantic_recall(
        self,
        query: str,
        limit: int,
        tags: list[str] | None,
        min_importance: float,
    ) -> list[dict[str, Any]]:
        """Semantic embedding search via EmbeddingEngine."""
        try:
            from whitemagic.core.memory.embeddings import get_embedding_engine

            engine = get_embedding_engine()
            if not engine.available(include_cache=True):
                return []

            results = engine.search_similar(
                query=query,
                limit=limit * 3,  # Over-fetch, we'll filter by tags
                min_similarity=0.15,
                # Don't pass galaxy — our memories are in the galaxy DB,
                # but _filter_by_galaxy checks the monolithic DB.
                # We filter by tags after fetching instead.
            )

            if not results:
                return []

            # Fetch full memories and filter by tags
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()
            search_tags = {"codex", "chunk"}
            if tags:
                search_tags.update(tags)

            filtered: list[dict[str, Any]] = []
            for r in results:
                mem_id = r.get("memory_id")
                if not mem_id:
                    continue
                mem = um._galaxy_backend._get_galaxy_backend(self.galaxy_name).recall(mem_id)
                if mem is None:
                    continue

                # Check tag intersection
                if not search_tags.issubset(mem.tags):
                    # Also try file tag
                    if "codex" not in mem.tags:
                        continue

                if mem.importance < min_importance:
                    continue

                content = mem.content
                if not isinstance(content, str):
                    content = str(content) if content else ""
                filtered.append({
                    "id": mem.id,
                    "title": mem.title or "",
                    "content_preview": content[:500],
                    "tags": list(mem.tags) if mem.tags else [],
                    "metadata": mem.metadata if mem.metadata else {},
                    "importance": mem.importance,
                    "score": r.get("similarity", 0.0),
                    "recall_type": "semantic",
                })

                if len(filtered) >= limit:
                    break

            return filtered

        except Exception as e:  # noqa: BLE001
            logger.debug("Semantic recall failed: %s", e)
            return []

    def _rust_bm25_recall(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Rust BM25 search via rust_search module."""
        try:
            from whitemagic.optimization.rust_search import (
                rust_search_available,
                search_query,
            )

            if not rust_search_available():
                return []

            results = search_query(query, limit=limit)
            if not results:
                return []

            # Fetch full memories
            from whitemagic.core.memory.unified import get_unified_memory

            um = get_unified_memory()
            filtered: list[dict[str, Any]] = []

            for r in results:
                mem_id = r.get("id")
                if not mem_id:
                    continue
                mem = um._galaxy_backend._get_galaxy_backend(self.galaxy_name).recall(mem_id)
                if mem is None:
                    continue

                # Only return codex memories
                if "codex" not in (mem.tags or set()):
                    continue

                content = mem.content
                if not isinstance(content, str):
                    content = str(content) if content else ""
                filtered.append({
                    "id": mem.id,
                    "title": mem.title or "",
                    "content_preview": content[:500],
                    "tags": list(mem.tags) if mem.tags else [],
                    "metadata": mem.metadata if mem.metadata else {},
                    "importance": mem.importance,
                    "score": r.get("score", 0.0),
                    "recall_type": "rust_bm25",
                })

                if len(filtered) >= limit:
                    break

            return filtered

        except Exception as e:  # noqa: BLE001
            logger.debug("Rust BM25 recall failed: %s", e)
            return []

    def _fts5_recall(
        self,
        query: str,
        limit: int,
        tags: list[str] | None,
        min_importance: float,
    ) -> list[dict[str, Any]]:
        """FTS5 fallback recall via UnifiedMemory.search."""
        from whitemagic.core.memory.unified import get_unified_memory

        um = get_unified_memory()
        search_tags = ["codex"]
        if tags:
            search_tags.extend(tags)

        results = um.search(
            query=query,
            tags=search_tags,
            limit=limit,
            min_importance=min_importance,
        )

        out = []
        for m in results:
            content = m.content
            if not isinstance(content, str):
                content = str(content) if content else ""
            out.append({
                "id": m.id,
                "title": m.title or "",
                "content_preview": content[:500],
                "tags": list(m.tags) if m.tags else [],
                "metadata": m.metadata if m.metadata else {},
                "importance": m.importance,
                "score": getattr(m, "score", 0.0),
                "recall_type": "fts5",
            })
        return out


# ── Singleton ─────────────────────────────────────────────────────────

_scanner: CodebaseScanner | None = None


def get_scanner(project_root: Path | str | None = None) -> CodebaseScanner:
    """Get the singleton CodebaseScanner instance."""
    global _scanner
    if _scanner is None or project_root is not None:
        _scanner = CodebaseScanner(project_root=project_root)
    return _scanner
