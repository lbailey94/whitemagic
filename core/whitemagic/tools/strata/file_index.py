import ast
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set

__all__ = ["FileIndex"]


class FileIndex:
    """Centralized file discovery with caching, skip logic, and content hash tracking."""

    SKIP_NAMES: Set[str] = {
        ".venv", "venv", "node_modules", "target", "dist", "build", "build-modern",
        ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".tox", "release",
        "external", "_deps", "vendor", "third_party", "thirdparty", "deps",
        "lib", "libs", "site-packages", "packages",
        "out", "cmake-build", "oldFiles", "archive", "archives",
    }

    def __init__(self, project_path: Path, extra_skip: Optional[Set[str]] = None, cache_path: Optional[Path] = None):
        self.project_path = Path(project_path).resolve()
        self._python_files: List[Path] = []
        self._file_cache: dict = {}
        self._ast_cache: Dict[str, Optional[ast.AST]] = {}
        self._skip_names: Set[str] = self.SKIP_NAMES | (extra_skip or set())
        self._hashes: Dict[str, str] = {}
        self._new_hashes: Dict[str, str] = {}
        self._meta_cache: Dict[str, Dict] = {}
        self._ext_index: Optional[Dict[str, List[Path]]] = None
        self._cache_file = cache_path or (self.project_path / ".strata-cache.json")
        self.incremental: bool = False
        self._load_hash_cache()

    def _load_hash_cache(self):
        """Load previous content hashes and file metadata from cache file."""
        if self._cache_file.exists():
            try:
                with self._cache_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "_meta" in data:
                    self._hashes = data.get("hashes", {})
                    self._meta_cache = data.get("_meta", {})
                else:
                    self._hashes = data
            except (json.JSONDecodeError, OSError):
                self._hashes = {}

    def save_hash_cache(self):
        """Persist current content hashes and file metadata to cache file."""
        try:
            with self._cache_file.open("w", encoding="utf-8") as f:
                json.dump({"hashes": self._new_hashes, "_meta": self._meta_cache}, f, indent=2)
        except OSError:
            pass

    @staticmethod
    def _hash_content(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def is_modified(self, path: Path) -> bool:
        """Return True if file content has changed since last run (or is new).

        Uses mtime+size as a fast pre-filter to avoid reading+hashing
        unchanged files. Falls back to content hash for definitive check.
        """
        rel = str(path.relative_to(self.project_path))
        try:
            stat = path.stat()
        except OSError:
            return True

        mtime = stat.st_mtime
        size = stat.st_size
        prev_meta = self._meta_cache.get(rel)

        if prev_meta is not None:
            if prev_meta.get("mtime") == mtime and prev_meta.get("size") == size:
                self._new_hashes[rel] = self._hashes.get(rel, "")
                return False

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            return True

        current_hash = self._hash_content(text)
        self._new_hashes[rel] = current_hash
        self._meta_cache[rel] = {"mtime": mtime, "size": size}
        previous = self._hashes.get(rel)
        return previous is None or previous != current_hash

    def should_skip(self, path: Path) -> bool:
        return any(part in self._skip_names for part in path.parts)

    def _should_skip(self, path: Path) -> bool:
        return self.should_skip(path)

    def _build_extension_index(self) -> Dict[str, List[Path]]:
        """Walk the project tree once and group all files by extension.
        This is cached and reused across all files_by_extension calls.
        Uses Rust parallel walker when available (98x faster).
        """
        if self._ext_index is not None:
            return self._ext_index

        index: Dict[str, List[Path]] = {}

        # Try Rust parallel walker first
        try:
            import whitemagic_rs
            rust_index = whitemagic_rs.walk_directory(str(self.project_path))
            for ext, paths in rust_index.items():
                index[ext] = [Path(p) for p in paths]
            self._ext_index = index
            return index
        except (ImportError, AttributeError, Exception):
            pass

        # Fallback: Python rglob
        for p in self.project_path.rglob("*"):
            if p.is_dir():
                continue
            if self.should_skip(p):
                continue
            ext = p.suffix
            if ext:
                index.setdefault(ext, []).append(p)

        self._ext_index = index
        return index

    def files_by_extension(self, *extensions: str) -> Iterator[Path]:
        """Yield files matching any of the given extensions, skipping vendor/build dirs.
        If incremental mode is enabled, only yield files whose content has changed since last run.
        """
        cache_key = (extensions, self.incremental)
        cached = self._file_cache.get(cache_key)
        if cached is not None:
            yield from cached
            return
        ext_index = self._build_extension_index()
        results: List[Path] = []
        for ext in extensions:
            for p in ext_index.get(ext, []):
                if self.incremental and not self.is_modified(p):
                    continue
                results.append(p)
        self._file_cache[cache_key] = results
        yield from results

    def python_files(self) -> Iterator[Path]:
        if self.incremental:
            yield from self.files_by_extension(".py")
        else:
            if not self._python_files:
                self._python_files = list(self.files_by_extension(".py"))
            yield from self._python_files

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    def get_ast(self, path: Path) -> Optional[ast.AST]:
        """Return a cached parsed AST for a Python file, or None if parsing fails."""
        rel = str(path.relative_to(self.project_path))
        if rel in self._ast_cache:
            return self._ast_cache[rel]
        try:
            text = self.read_text(path)
            tree = ast.parse(text)
            self._ast_cache[rel] = tree
            return tree
        except (SyntaxError, OSError, UnicodeDecodeError):
            self._ast_cache[rel] = None
            return None

    @staticmethod
    def is_test_file(path: Path) -> bool:
        """Detect test files by path or naming convention."""
        parts = [p.lower() for p in path.parts]
        name = path.name.lower()
        return (
            "tests" in parts or
            "test" in parts or
            name.startswith("test_") or
            name.endswith("_test.py")
        )
