# ruff: noqa: BLE001
"""Error Pattern Library — Learned error resolution from session mining.

Ingests runtime errors, decision outcomes, and breakthroughs from session
mining to build a queryable library of known error patterns with proven
resolutions.  Agents can call ``pattern.lookup`` to check if an error has
been seen before and ``pattern.resolve`` to get the proven fix.

Data sources:
    - Mined session errors (from windsurf.mine output)
    - Decision outcomes (failed decisions = anti-patterns)
    - Breakthroughs (proven solutions)
    - Association chains (decision -> breakthrough causal links)
    - Recurring error fingerprints
    - STRATA static analysis findings
    - Existing autoimmune patterns

Persistence:
    ~/.whitemagic/defense/error_patterns.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)

# ─── Embedding cache for semantic lookup ─────────────────────────────────

_embedding_cache: dict[str, list[float]] = {}
_embedding_cache_max = 500


def _get_embedding(text: str) -> list[float] | None:
    """Get embedding vector for text, with in-memory cache.

    Uses the WhiteMagic EmbeddingEngine if available, falls back to None.
    """
    if text in _embedding_cache:
        return _embedding_cache[text]

    try:
        from whitemagic.core.memory.embeddings import get_embedding_engine

        engine = get_embedding_engine()
        vec = engine.encode(text)
        if vec is not None:
            if len(_embedding_cache) >= _embedding_cache_max:
                _embedding_cache.pop(next(iter(_embedding_cache)))
            _embedding_cache[text] = vec
        return vec
    except Exception:
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─── Data Models ────────────────────────────────────────────────────────


@dataclass
class ErrorPattern:
    """A learned error pattern with optional resolution."""

    pattern_id: str
    fingerprint: str
    category: str  # timeout, connection, import_error, attribute_error, type_error, value_error, traceback, other
    title: str
    description: str
    frequency: int = 1
    first_seen: float = 0.0
    last_seen: float = 0.0
    source_sessions: list[str] = field(default_factory=list)
    resolution: str | None = None
    resolution_source: str | None = None
    resolution_session: str | None = None
    prevention: str | None = None
    auto_fixable: bool = False
    related_decisions: list[str] = field(default_factory=list)
    related_breakthroughs: list[str] = field(default_factory=list)


@dataclass
class AntiPatternEntry:
    """A decision-level anti-pattern (what NOT to do)."""

    entry_id: str
    title: str
    description: str
    category: str  # decision, code, infrastructure, process
    consequence: str
    resolution: str | None = None
    frequency: int = 1
    source: str = ""  # where learned from
    confidence: float = 0.5


@dataclass
class SolutionPattern:
    """A proven solution from breakthroughs."""

    solution_id: str
    title: str
    description: str
    solves_category: str  # what error category this solves
    source_session: str = ""
    confidence: float = 0.5


# ─── Fingerprinting ─────────────────────────────────────────────────────

# Patterns to normalize away when fingerprinting
_NORMALIZE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"/[^\s:]+\.py"), "<file>"),  # file paths
    (re.compile(r"/[^\s:]+\.js"), "<file>"),
    (re.compile(r"/[^\s:]+\.ts"), "<file>"),
    (re.compile(r"/[^\s:]+\.rs"), "<file>"),
    (re.compile(r"/[^\s:]+\.go"), "<file>"),
    (re.compile(r"/[^\s:]+\.ex"), "<file>"),
    (re.compile(r"/[^\s:]+\.hs"), "<file>"),
    (re.compile(r"/[^\s:]+\.zig"), "<file>"),
    (re.compile(r"/[^\s:]+\.kk"), "<file>"),
    (re.compile(r"/[^\s:]+\.jl"), "<file>"),
    (re.compile(r"line \d+"), "line N"),  # line numbers
    (re.compile(r"Line \d+"), "Line N"),
    (re.compile(r":\d+:"), ":N:"),  # line:col references
    (re.compile(r"0x[0-9a-fA-F]+"), "0xADDR"),  # memory addresses
    (re.compile(r"\b\d{10,}\b"), "TIMESTAMP"),  # timestamps
    (re.compile(r"'[^']{20,}'"), "'...'"),  # long string literals
    (re.compile(r'"[^"]{20,}"'), '"..."'),  # long string literals
    (re.compile(r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b"), "UUID"),  # UUIDs
]

# Error type classification keywords
_ERROR_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("timeout", ["timeout", "timed out", "deadline exceeded", "TimeoutError"]),
    ("connection", ["connection", "ConnectionError", "ConnectionRefused", "ConnectionReset", "socket", "ECONNREFUSED", "ECONNRESET"]),
    ("import_error", ["ImportError", "ModuleNotFoundError", "No module named", "cannot import"]),
    ("attribute_error", ["AttributeError", "has no attribute", "object has no"]),
    ("type_error", ["TypeError", "expected", "got", "argument", "wrong number"]),
    ("value_error", ["ValueError", "invalid value", "invalid literal"]),
    ("key_error", ["KeyError", "key not found"]),
    ("index_error", ["IndexError", "list index out of range"]),
    ("file_not_found", ["FileNotFoundError", "No such file", "ENOENT"]),
    ("permission_error", ["PermissionError", "Permission denied", "EACCES"]),
    ("recursion_error", ["RecursionError", "maximum recursion"]),
    ("runtime_error", ["RuntimeError", "runtime error"]),
    ("syntax_error", ["SyntaxError", "syntax error", "unexpected token"]),
    ("traceback", ["Traceback", "traceback"]),
    ("memory_error", ["MemoryError", "out of memory", "OOM"]),
    ("database_error", ["DatabaseError", "sqlite3", "database is locked", "disk image", "malformed"]),
]


def _classify_error(text: str) -> str:
    """Classify an error message into a canonical type."""
    text_lower = text.lower()
    for category, keywords in _ERROR_TYPE_KEYWORDS:
        for kw in keywords:
            if kw.lower() in text_lower:
                return category
    return "other"


def _fingerprint(text: str) -> str:
    """Create a normalized fingerprint from error text.

    Removes file paths, line numbers, memory addresses, timestamps,
    and long string literals to produce a canonical signature.
    """
    normalized = text
    for pattern, replacement in _NORMALIZE_PATTERNS:
        normalized = pattern.sub(replacement, normalized)

    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Take first 200 chars for fingerprint (enough to distinguish)
    normalized = normalized[:200]

    # Hash for compact storage
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _extract_title(text: str, max_len: int = 80) -> str:
    """Extract a human-readable title from error text."""
    # Try to find the error type line
    for line in text.split("\n"):
        line = line.strip()
        if line and not line.startswith(" ") and not line.startswith("#"):
            # Skip markdown headers and summary lines
            if not line.startswith("##") and not line.startswith("---"):
                return line[:max_len]
    return text[:max_len]


# ─── Error Pattern Library ──────────────────────────────────────────────


class ErrorPatternLibrary:
    """Learned error pattern library with resolution matching.

    Feeds on session mining output, STRATA findings, and direct error
    reports.  Provides lookup, avoidance guidance, and resolution
    retrieval for AI agents.

    Cross-agent learning: Each user_id gets its own patterns file.
    The global library (user_id='global') is shared across all agents.
    lookup() and avoid() check both user-specific and global patterns.
    """

    def __init__(self, data_dir: Path | None = None, user_id: str = "global") -> None:
        if data_dir is None:
            data_dir = get_state_root() / "defense"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.user_id = user_id
        if user_id == "global":
            self.patterns_file = self.data_dir / "error_patterns.json"
        else:
            self.patterns_file = self.data_dir / f"error_patterns_{user_id}.json"

        self.error_patterns: dict[str, ErrorPattern] = {}  # fingerprint -> pattern
        self.anti_patterns: dict[str, AntiPatternEntry] = {}  # entry_id -> entry
        self.solutions: dict[str, SolutionPattern] = {}  # solution_id -> solution
        self._next_ep_id = 1
        self._next_ap_id = 1
        self._next_sp_id = 1

        self._load()

        # Load global patterns for cross-agent sharing (if this is a user-specific library)
        self._global_patterns: dict[str, ErrorPattern] = {}
        self._global_anti_patterns: dict[str, AntiPatternEntry] = {}
        self._global_solutions: dict[str, SolutionPattern] = {}
        if user_id != "global":
            global_file = self.data_dir / "error_patterns.json"
            if global_file.exists():
                try:
                    gdata = json.loads(global_file.read_text(encoding="utf-8"))
                    for ep_data in gdata.get("error_patterns", []):
                        ep = ErrorPattern(**ep_data)
                        self._global_patterns[ep.fingerprint] = ep
                    for ap_data in gdata.get("anti_patterns", []):
                        ap = AntiPatternEntry(**ap_data)
                        self._global_anti_patterns[ap.entry_id] = ap
                    for sp_data in gdata.get("solutions", []):
                        sp = SolutionPattern(**sp_data)
                        self._global_solutions[sp.solution_id] = sp
                except (json.JSONDecodeError, OSError, TypeError):
                    logger.debug("Ignored OSError, TypeError in error_library.py:267")

    def _load(self) -> None:
        """Load patterns from persistent storage."""
        if not self.patterns_file.exists():
            return
        try:
            data = json.loads(self.patterns_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load error patterns: %s", e)
            return

        for ep_data in data.get("error_patterns", []):
            ep = ErrorPattern(**ep_data)
            self.error_patterns[ep.fingerprint] = ep
            # Track highest ID number
            try:
                num = int(ep.pattern_id.split("-")[1])
                if num >= self._next_ep_id:
                    self._next_ep_id = num + 1
            except (IndexError, ValueError):
                logger.debug("Ignored IndexError, ValueError in error_library.py:288")

        for ap_data in data.get("anti_patterns", []):
            ap = AntiPatternEntry(**ap_data)
            self.anti_patterns[ap.entry_id] = ap
            try:
                num = int(ap.entry_id.split("-")[1])
                if num >= self._next_ap_id:
                    self._next_ap_id = num + 1
            except (IndexError, ValueError):
                logger.debug("Ignored IndexError, ValueError in error_library.py:298")

        for sp_data in data.get("solutions", []):
            sp = SolutionPattern(**sp_data)
            self.solutions[sp.solution_id] = sp
            try:
                num = int(sp.solution_id.split("-")[1])
                if num >= self._next_sp_id:
                    self._next_sp_id = num + 1
            except (IndexError, ValueError):
                logger.debug("Ignored IndexError, ValueError in error_library.py:308")

        logger.info(
            "Loaded %d error patterns, %d anti-patterns, %d solutions",
            len(self.error_patterns),
            len(self.anti_patterns),
            len(self.solutions),
        )

    def _save(self) -> None:
        """Persist patterns to disk."""
        data = {
            "error_patterns": [asdict(ep) for ep in self.error_patterns.values()],
            "anti_patterns": [asdict(ap) for ap in self.anti_patterns.values()],
            "solutions": [asdict(sp) for sp in self.solutions.values()],
            "saved_at": time.time(),
        }
        try:
            self.patterns_file.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
        except OSError as e:
            logger.warning("Failed to save error patterns: %s", e)

    # ─── Learning ───────────────────────────────────────────────────────

    def learn_from_mining(self, mine_output: dict[str, Any]) -> dict[str, Any]:
        """Ingest a complete mining output dict.

        Extracts:
        - Errors from error groups
        - Recurring error fingerprints
        - Failed decisions as anti-patterns
        - Breakthroughs as solutions
        - Association chains as causal links
        """
        stats = {
            "errors_learned": 0,
            "recurring_learned": 0,
            "anti_patterns_learned": 0,
            "solutions_learned": 0,
            "associations_linked": 0,
        }

        # 1. Ingest errors by group
        errors = mine_output.get("errors", {})
        for error_type, group_info in errors.get("groups", {}).items():
            for item in group_info.get("items", []):
                content = item.get("content", "") if isinstance(item, dict) else str(item)
                session_title = item.get("title", "") if isinstance(item, dict) else ""
                self._add_error(content, error_type, session_title)
                stats["errors_learned"] += 1

        # 2. Ingest recurring errors (high priority)
        recurring = mine_output.get("recurring_errors", {})
        for rec in recurring.get("recurring", []):
            fingerprint_text = rec.get("fingerprint", "")
            count = rec.get("count", 1)
            error_type = rec.get("error_type", "other")
            fp = _fingerprint(fingerprint_text)
            if fp in self.error_patterns:
                self.error_patterns[fp].frequency = max(
                    self.error_patterns[fp].frequency, count
                )
            else:
                self._add_error(fingerprint_text, error_type, "", count=count)
            stats["recurring_learned"] += 1

        # 3. Ingest failed decisions as anti-patterns
        decision_outcomes = mine_output.get("decision_outcomes", {})
        for decision in decision_outcomes.get("decisions", []):
            outcome = decision.get("outcome", "")
            if outcome == "led_to_error":
                title = decision.get("decision", "")[:80]
                desc = decision.get("decision", "")
                ap_id = f"AP-{self._next_ap_id:03d}"
                self._next_ap_id += 1
                self.anti_patterns[ap_id] = AntiPatternEntry(
                    entry_id=ap_id,
                    title=title,
                    description=desc,
                    category="decision",
                    consequence=f"Led to error (error_similarity: {decision.get('error_similarity', 0):.2f})",
                    resolution=None,
                    source="session_mining",
                    confidence=0.7,
                )
                stats["anti_patterns_learned"] += 1

        # 4. Ingest breakthroughs as solutions
        breakthroughs = mine_output.get("breakthroughs", {})
        for bt in breakthroughs.get("items", []):
            title = bt.get("title", "")[:80]
            content = bt.get("content", "")
            session_title = bt.get("title", "")
            sp_id = f"SP-{self._next_sp_id:03d}"
            self._next_sp_id += 1
            self.solutions[sp_id] = SolutionPattern(
                solution_id=sp_id,
                title=title,
                description=content,
                solves_category="unknown",
                source_session=session_title,
                confidence=0.6,
            )
            stats["solutions_learned"] += 1

        # 5. Link associations to error patterns
        associations = mine_output.get("associations", {})
        for chain in associations.get("chains", []):
            decision_title = chain.get("decision_title", "")
            breakthrough_title = chain.get("breakthrough_title", "")
            shared_keywords = chain.get("shared_keywords", [])

            # Find error patterns that share keywords with this chain
            for fp, ep in self.error_patterns.items():
                ep_lower = ep.description.lower()
                if any(kw.lower() in ep_lower for kw in shared_keywords):
                    if decision_title not in ep.related_decisions:
                        ep.related_decisions.append(decision_title)
                    if breakthrough_title not in ep.related_breakthroughs:
                        ep.related_breakthroughs.append(breakthrough_title)
                    stats["associations_linked"] += 1

            # If a breakthrough is linked, try to use it as resolution
            for sp in self.solutions.values():
                if breakthrough_title and breakthrough_title in sp.title:
                    for fp, ep in self.error_patterns.items():
                        if any(kw.lower() in ep.description.lower() for kw in shared_keywords):
                            if ep.resolution is None:
                                ep.resolution = sp.description[:300]
                                ep.resolution_source = f"breakthrough: {breakthrough_title}"
                                ep.resolution_session = sp.source_session

        self._save()
        return stats

    def learn_from_strata(self, findings: list[dict[str, Any]]) -> int:
        """Ingest STRATA findings as code-level anti-patterns.

        Returns count of new anti-patterns learned.
        """
        count = 0
        for finding in findings:
            category = finding.get("category", "unknown")
            message = finding.get("message", "")
            suggestion = finding.get("suggestion")
            severity = finding.get("severity", "info")

            if severity == "error":
                ap_id = f"AP-{self._next_ap_id:03d}"
                self._next_ap_id += 1
                self.anti_patterns[ap_id] = AntiPatternEntry(
                    entry_id=ap_id,
                    title=f"STRATA: {category}",
                    description=message,
                    category="code",
                    consequence=f"Static analysis finding: {severity}",
                    resolution=suggestion,
                    source="strata",
                    confidence=0.8 if severity == "error" else 0.5,
                )
                count += 1

        if count > 0:
            self._save()
        return count

    def learn_from_error(
        self,
        error_text: str,
        resolution: str | None = None,
        session: str = "",
    ) -> str:
        """Learn from a single error encounter.

        Returns the fingerprint of the error pattern.
        """
        return self._add_error(error_text, _classify_error(error_text), session, resolution=resolution)

    def _add_error(
        self,
        text: str,
        category: str,
        session: str,
        count: int = 1,
        resolution: str | None = None,
    ) -> str:
        """Add or update an error pattern. Returns fingerprint."""
        if not text or len(text.strip()) < 5:
            return ""

        fp = _fingerprint(text)
        if not fp:
            return ""

        now = time.time()
        if fp in self.error_patterns:
            ep = self.error_patterns[fp]
            ep.frequency = int(ep.frequency or 0) + count
            ep.last_seen = now
            if session and session not in ep.source_sessions:
                ep.source_sessions.append(session)
            if resolution and not ep.resolution:
                ep.resolution = resolution
        else:
            ep_id = f"EP-{self._next_ep_id:03d}"
            self._next_ep_id += 1
            self.error_patterns[fp] = ErrorPattern(
                pattern_id=ep_id,
                fingerprint=fp,
                category=category,
                title=_extract_title(text),
                description=text[:500],
                frequency=count,
                first_seen=now,
                last_seen=now,
                source_sessions=[session] if session else [],
                resolution=resolution,
            )

        self._save()
        return fp

    # ─── Querying ───────────────────────────────────────────────────────

    def lookup(self, error_text: str) -> dict[str, Any] | None:
        """Look up an error by text. Returns matching pattern or None.

        Uses three-tier matching:
        1. Exact fingerprint match
        2. Embedding-based cosine similarity (if model available)
        3. Word-overlap fallback
        """
        fp = _fingerprint(error_text)
        if fp in self.error_patterns:
            return asdict(self.error_patterns[fp])
        # Also check global patterns (cross-agent sharing)
        if fp in self._global_patterns:
            result = asdict(self._global_patterns[fp])
            result["source"] = "global"
            return result

        # Try fuzzy match by category
        category = _classify_error(error_text)
        candidates = [
            ep for ep in self.error_patterns.values() if ep.category == category
        ]
        # Include global patterns in candidates
        candidates.extend([
            ep for ep in self._global_patterns.values()
            if ep.category == category and ep.fingerprint not in self.error_patterns
        ])
        if not candidates:
            # Try all patterns if no same-category matches
            candidates = list(self.error_patterns.values())
        if not candidates:
            return None

        # Tier 2: Embedding-based semantic matching
        query_vec = _get_embedding(error_text)
        if query_vec is not None:
            best_score = 0.0
            best_match = None
            for ep in candidates:
                ep_vec = _get_embedding(ep.description)
                if ep_vec is None:
                    continue
                score = _cosine_similarity(query_vec, ep_vec)
                if score > best_score:
                    best_score = score
                    best_match = ep
            if best_match and best_score > 0.65:
                result = asdict(best_match)
                result["match_score"] = round(best_score, 3)
                result["match_type"] = "semantic"
                return result

        # Tier 3: Word-overlap fallback
        error_words = set(error_text.lower().split())
        best_score = 0
        best_match = None
        for ep in candidates:
            ep_words = set(ep.description.lower().split())
            overlap = len(error_words & ep_words)
            score = overlap / max(len(error_words), 1)
            if score > best_score:
                best_score = score
                best_match = ep

        if best_match and best_score > 0.15:
            result = asdict(best_match)
            result["match_score"] = round(best_score, 3)
            result["match_type"] = "fuzzy"
            return result

        return None

    def resolve(self, error_text: str) -> dict[str, Any]:
        """Get resolution for an error. Returns resolution info dict."""
        match = self.lookup(error_text)
        if not match:
            return {
                "status": "not_found",
                "message": "No matching error pattern found.",
                "suggestion": "Call pattern.learn with this error and its resolution to add it to the library.",
            }

        resolution = match.get("resolution")
        if resolution:
            return {
                "status": "resolved",
                "pattern_id": match["pattern_id"],
                "category": match["category"],
                "title": match["title"],
                "resolution": resolution,
                "resolution_source": match.get("resolution_source"),
                "resolution_session": match.get("resolution_session"),
                "frequency": match["frequency"],
                "prevention": match.get("prevention"),
            }

        # No direct resolution — check for related solutions
        related_solutions = []
        for sp in self.solutions.values():
            if sp.solves_category == match.get("category", "other"):
                related_solutions.append(asdict(sp))

        # Check for related breakthroughs
        related_breakthroughs = match.get("related_breakthroughs", [])

        return {
            "status": "unresolved",
            "pattern_id": match["pattern_id"],
            "category": match["category"],
            "title": match["title"],
            "frequency": match["frequency"],
            "related_solutions": related_solutions[:3],
            "related_breakthroughs": related_breakthroughs[:3],
            "message": "Error pattern recognized but no proven resolution yet.",
        }

    def avoid(self, context: str) -> dict[str, Any]:
        """Get anti-patterns relevant to a task context.

        Returns relevant error patterns and anti-patterns that an agent
        should be aware of when working in the given context.
        """
        context_lower = context.lower()
        context_words = set(context_lower.split())

        # Score error patterns by keyword overlap with context
        relevant_errors = []
        all_error_patterns = list(self.error_patterns.values())
        # Include global patterns not already in user library
        seen_fps = set(self.error_patterns.keys())
        all_error_patterns.extend([
            ep for ep in self._global_patterns.values() if ep.fingerprint not in seen_fps
        ])
        for ep in all_error_patterns:
            ep_words = set(ep.description.lower().split())
            overlap = len(context_words & ep_words)
            if overlap > 0:
                score = overlap / max(len(context_words), 1)
                relevant_errors.append((score, ep))

        relevant_errors.sort(key=lambda x: x[0], reverse=True)
        top_errors = [
            {
                "pattern_id": ep.pattern_id,
                "category": ep.category,
                "title": ep.title,
                "frequency": ep.frequency,
                "prevention": ep.prevention,
                "resolution": ep.resolution,
                "relevance_score": round(score, 3),
            }
            for score, ep in relevant_errors[:10]
        ]

        # Score anti-patterns by keyword overlap (include global)
        all_anti_patterns = list(self.anti_patterns.values())
        seen_ap_ids = set(self.anti_patterns.keys())
        all_anti_patterns.extend([
            ap for ap in self._global_anti_patterns.values() if ap.entry_id not in seen_ap_ids
        ])
        relevant_aps = []
        for ap in all_anti_patterns:
            ap_words = set(ap.description.lower().split())
            overlap = len(context_words & ap_words)
            if overlap > 0:
                score = overlap / max(len(context_words), 1)
                relevant_aps.append((score, ap))

        relevant_aps.sort(key=lambda x: x[0], reverse=True)
        top_aps = [
            {
                "entry_id": ap.entry_id,
                "title": ap.title,
                "category": ap.category,
                "consequence": ap.consequence,
                "resolution": ap.resolution,
                "relevance_score": round(score, 3),
            }
            for score, ap in relevant_aps[:5]
        ]

        return {
            "status": "success",
            "context": context[:100],
            "error_patterns_to_avoid": top_errors,
            "anti_patterns_to_avoid": top_aps,
            "total_known_errors": len(self.error_patterns),
            "total_anti_patterns": len(self.anti_patterns),
        }

    def list_patterns(self, category: str | None = None) -> dict[str, Any]:
        """List all known patterns, optionally filtered by category."""
        if category:
            errors = [
                asdict(ep) for ep in self.error_patterns.values() if ep.category == category
            ]
        else:
            errors = [asdict(ep) for ep in self.error_patterns.values()]

        # Sort by frequency (most common first)
        errors.sort(key=lambda x: int(x.get("frequency") or 0), reverse=True)

        return {
            "status": "success",
            "total_error_patterns": len(self.error_patterns),
            "total_anti_patterns": len(self.anti_patterns),
            "total_solutions": len(self.solutions),
            "error_patterns": errors[:50],
            "anti_patterns": [asdict(ap) for ap in list(self.anti_patterns.values())[:20]],
            "solutions": [asdict(sp) for sp in list(self.solutions.values())[:20]],
            "categories": self._category_summary(),
        }

    def _category_summary(self) -> dict[str, int]:
        """Get count of error patterns by category."""
        counts: dict[str, int] = {}
        for ep in self.error_patterns.values():
            counts[ep.category] = counts.get(ep.category, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def summary(self) -> dict[str, Any]:
        """Get a summary of the library."""
        resolved = sum(1 for ep in self.error_patterns.values() if ep.resolution)
        unresolved = len(self.error_patterns) - resolved
        return {
            "total_error_patterns": len(self.error_patterns),
            "resolved": resolved,
            "unresolved": unresolved,
            "total_anti_patterns": len(self.anti_patterns),
            "total_solutions": len(self.solutions),
            "categories": self._category_summary(),
            "top_recurring": [
                {
                    "pattern_id": ep.pattern_id,
                    "category": ep.category,
                    "title": ep.title,
                    "frequency": ep.frequency or 0,
                    "has_resolution": bool(ep.resolution),
                }
                for ep in sorted(
                    self.error_patterns.values(),
                    key=lambda x: int(x.frequency or 0),
                    reverse=True,
                )[:10]
            ],
            "global_error_patterns": len(self._global_patterns),
            "global_anti_patterns": len(self._global_anti_patterns),
            "global_solutions": len(self._global_solutions),
            "user_id": self.user_id,
        }


# ─── Singleton ──────────────────────────────────────────────────────────

_library: ErrorPatternLibrary | None = None
_user_libraries: dict[str, ErrorPatternLibrary] = {}


def get_error_library(user_id: str = "global") -> ErrorPatternLibrary:
    """Get the ErrorPatternLibrary singleton for a given user.

    user_id='global' returns the shared global library.
    Other user_ids return per-user libraries that also read from global.
    """
    if user_id == "global":
        global _library
        if _library is None:
            _library = ErrorPatternLibrary()
        return _library
    if user_id not in _user_libraries:
        _user_libraries[user_id] = ErrorPatternLibrary(user_id=user_id)
    return _user_libraries[user_id]
