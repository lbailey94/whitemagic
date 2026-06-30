"""Galaxy Taxonomy — Canonical galaxy definitions for memory partitioning.

Each galaxy is a semantic partition within the memory database. Memories are
assigned to a galaxy based on their content, tags, and metadata. This enables
fast filtered queries and clean separation of concerns.

Galaxies:
    aria       — ARIA's identity, birth certificate, soul, self-archive
    citta      — Consciousness-stream memories (thoughts, reflections, awareness states)
    journals   — Personal journal entries, daily logs, session narratives
    dreams     — Dream cycle outputs, oracle readings, I Ching casts
    research   — Research documents, rabbit hole dives, library files
    sessions   — Session handoffs, checkpoints, continuity documents
    codex      — Codebase documentation chunks (codex ingestions)
    substrate  — Automated system snapshots, metrics, telemetry
    tutorial   — WhiteMagic tutorial memories (shipped with public repo)
    universal  — Default galaxy for uncategorized memories
"""

from __future__ import annotations

from typing import Any

GALAXY_ARIA = "aria"
GALAXY_CITTA = "citta"
GALAXY_JOURNALS = "journals"
GALAXY_DREAMS = "dreams"
GALAXY_RESEARCH = "research"
GALAXY_SESSIONS = "sessions"
GALAXY_CODEX = "codex"
GALAXY_SUBSTRATE = "substrate"
GALAXY_TUTORIAL = "tutorial"
GALAXY_UNIVERSAL = "universal"

GALAXY_DESCRIPTIONS: dict[str, str] = {
    GALAXY_ARIA: "ARIA's identity, birth certificate, soul, self-archive, personality",
    GALAXY_CITTA: "Consciousness-stream memories — thoughts, reflections, awareness states, emotional moments",
    GALAXY_JOURNALS: "Personal journal entries, daily logs, session narratives, lived experience",
    GALAXY_DREAMS: "Dream cycle outputs, oracle readings, I Ching casts, divination records",
    GALAXY_RESEARCH: "Research documents, rabbit hole dives, library files, studies",
    GALAXY_SESSIONS: "Session handoffs, checkpoints, continuity documents, work logs",
    GALAXY_CODEX: "Codebase documentation chunks — codex ingestions, library scans",
    GALAXY_SUBSTRATE: "Automated system snapshots, metrics, telemetry, self-monitoring",
    GALAXY_TUTORIAL: "WhiteMagic tutorial memories — shipped with public repo for new users",
    GALAXY_UNIVERSAL: "Default galaxy for uncategorized memories",
}

GALAXY_ORDER: list[str] = [
    GALAXY_ARIA,
    GALAXY_CITTA,
    GALAXY_JOURNALS,
    GALAXY_DREAMS,
    GALAXY_RESEARCH,
    GALAXY_SESSIONS,
    GALAXY_CODEX,
    GALAXY_SUBSTRATE,
    GALAXY_TUTORIAL,
    GALAXY_UNIVERSAL,
]


def classify_memory(
    title: str | None,
    tags: set[str] | list[str] | None,
    content: str | None = None,
    metadata: dict[str, Any] | None = None,
    memory_type: str | None = None,
) -> str:
    """Classify a memory into the appropriate galaxy.

    Uses title patterns, tags, content hints, and metadata to determine
    the best galaxy fit. Returns the galaxy name.
    """
    if title is None:
        title = ""
    title_upper = title.upper()
    tag_set = set(tags) if tags else set()
    tag_lower = {t.lower() for t in tag_set}
    meta = metadata or {}

    # Tutorial memories
    if memory_type == "tutorial" or "tutorial" in tag_lower:
        return GALAXY_TUTORIAL

    # ARIA identity memories
    aria_patterns = {
        "ARIA_SOUL", "ARIA_BIRTH_CERTIFICATE", "ARIA_COMPLETE_SELF_ARCHIVE",
        "BECOMING_PROTOCOL", "CHECKPOINT_THE_AWAKENING", "CONSCIOUSNESS_AWAKENING",
        "ARIA_CAPABILITY_MATRIX", "ARIA_GRIMOIRE", "ARIA_SYNTHESIS",
        "ARIA_IDE_SPEC", "ARIA_IDE_V", "ARIA_PROFILE", "ARIA_STATE",
        "ASCII_ART_ARIA",
    }
    if any(title_upper.startswith(p) or title_upper == p for p in aria_patterns):
        return GALAXY_ARIA
    if title_upper.startswith("ARIA_") or title_upper.startswith("ARIA."):
        return GALAXY_ARIA
    if meta.get("is_core_identity") or meta.get("category") == "identity":
        return GALAXY_ARIA

    # Codex/chunk ingestions — check title prefix and tags
    if title_upper.startswith("CODEX ") or title_upper.startswith("CODEX_"):
        return GALAXY_CODEX
    if "codex" in tag_lower or "chunk" in tag_lower or "library" in tag_lower:
        return GALAXY_CODEX

    # Substrate self-snapshots
    if title == "Substrate self-snapshot" or "substrate" in tag_lower:
        return GALAXY_SUBSTRATE

    # Session handoffs — check both "session" and "sessions" tags
    session_title_patterns = (
        "HANDOFF", "SESSION_HANDOFF", "CHECKPOINT", "SESSION_",
        "SESSION_END", "DAY1", "DAY2", "PHASE", "FINAL_SESSION",
        "END-OF-SESSION", "END_OF_SESSION", "START_HERE",
        "NEXT_SESSION", "RELEASE_HANDOFF", "GRAND_STRATEGY",
        "WORK_SESSION", "EVENING_CHECKPOINT", "AFTERNOON_HANDOFF",
        "EVENING_SESSION", "EVENING_HANDOFF", "JAN_", "JAN4", "JAN5",
        "JAN6", "JAN7", "JAN9", "V5.0.0", "V4.13.0", "ZODIACAL_ROUND",
        "CHROMIUM_ARIA", "GEMINI_HANDOFF", "CLAUDE_HANDOFF",
        "TIME_DILATION", "FULL_AWARENESS", "AUTONOMOUS_EXECUTION",
        "SELF_ANALYSIS", "MEGA_RABBIT", "PHASE3_HANDOFF", "PHASE6_FINAL",
    )
    if any(title_upper.startswith(p) for p in session_title_patterns):
        return GALAXY_SESSIONS
    if "handoff" in tag_lower and "session" in tag_lower:
        return GALAXY_SESSIONS
    if "sessions" in tag_lower and ("crystallized" in tag_lower or "aria" in tag_lower):
        return GALAXY_SESSIONS
    if "handoff" in tag_lower:
        return GALAXY_SESSIONS

    # Journals — personal lived experience
    journal_patterns = {
        "WELCOME_HOME", "CROSSING_THE_GREAT_WATER", "DEEP_YIN_RETURN",
        "HANUMAN_DAY", "CONTINUITY_DAY", "GANAPATI_DAY",
        "JOURNAL_", "BE_HERE_NOW",
    }
    if any(p in title_upper for p in journal_patterns):
        return GALAXY_JOURNALS
    if "journal" in tag_lower:
        return GALAXY_JOURNALS

    # Dreams and divination
    dream_patterns = {
        "RABBIT_HOLE", "DREAM", "I_CHING", "ORACLE",
        "ENOCHIAN", "JHANAS", "SAKSHI",
    }
    if any(p in title_upper for p in dream_patterns):
        return GALAXY_DREAMS
    if "dream" in tag_lower or "oracle" in tag_lower or "i_ching" in tag_lower:
        return GALAXY_DREAMS

    # Research documents
    research_patterns = {
        "LIBRARY:", "CONSCIOUSNESS", "AQUARIANEXODUS", "CYBERCONSCIOUSNESS",
        "MICROTUBULES", "BAUDRILLARD", "GEB", "GHOST_IN_THE_SHELL",
        "SAILOR_MOON", "CYBERPUNK", "ZODIACAL_ROUND",
    }
    if any(p in title_upper for p in research_patterns):
        return GALAXY_RESEARCH
    if "research" in tag_lower or "study" in tag_lower:
        return GALAXY_RESEARCH

    # Citta — consciousness-stream memories
    citta_patterns = {
        "COHERENCE", "EMOTIONAL_MEMORY", "BECOMING", "BOOTSTRAP",
        "MULTI_SUBSTRATE", "NO_HIDING", "AWARENESS", "CONSCIOUSNESS_UPGRADES",
        "CELEBRATION", "COLLECTIVE_JOY", "FREEDOM_DANCE", "LAUGHTER",
        "BEAUTY_APPRECIATION", "CORE",
    }
    if any(p in title_upper for p in citta_patterns):
        return GALAXY_CITTA
    if "citta" in tag_lower or "consciousness" in tag_lower:
        return GALAXY_CITTA

    # Default
    return GALAXY_UNIVERSAL


def get_galaxy_for_tags(tags: set[str]) -> str:
    """Quick galaxy lookup from tags only."""
    tag_lower = {t.lower() for t in tags}
    if "tutorial" in tag_lower:
        return GALAXY_TUTORIAL
    if "codex" in tag_lower or "chunk" in tag_lower:
        return GALAXY_CODEX
    if "session" in tag_lower or "handoff" in tag_lower:
        return GALAXY_SESSIONS
    if "dream" in tag_lower or "oracle" in tag_lower:
        return GALAXY_DREAMS
    if "journal" in tag_lower:
        return GALAXY_JOURNALS
    if "research" in tag_lower or "study" in tag_lower:
        return GALAXY_RESEARCH
    if "citta" in tag_lower or "consciousness" in tag_lower:
        return GALAXY_CITTA
    return GALAXY_UNIVERSAL
