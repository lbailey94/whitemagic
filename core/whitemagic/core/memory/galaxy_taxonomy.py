"""Galaxy Taxonomy — Canonical galaxy definitions for memory partitioning.

Each galaxy is a semantic partition within the memory database. Memories are
assigned to a galaxy based on their content, tags, and metadata. This enables
fast filtered queries and clean separation of concerns.

The taxonomy is designed around functional purpose:
- Identity & Experience: aria, citta, journals, dreams
- Knowledge & Learning: codex, research, knowledge, sessions
- System & Operations: substrate, telemetry, meta
- Infrastructure: tutorial, archive, universal

Galaxies:
    aria       — Aria's identity, birth certificate, soul, self-archive, personality
    citta      — Live consciousness moments — emotional shifts, awareness states, coherence
    journals   — Personal journals, daily reflections, lived experience narratives
    dreams     — Dream cycle outputs, oracle readings, I Ching casts, divination
    research   — External research, rabbit hole dives, library files, studies
    sessions   — Conversation transcripts, session handoffs, continuity documents
    codex      — Codebase knowledge — ingested docs, FILE/CHUNK entries, API references
    knowledge  — Consolidated wisdom, learned patterns, insights, strategies
    substrate  — System self-monitoring snapshots, metrics, health readings
    telemetry  — System events, tool call logs, voice_expressed, operational noise
    meta       — Meta-galaxy index — galaxy summaries, cross-galaxy associations, priorities
    tutorial   — WhiteMagic tutorial memories (shipped with public repo)
    archive    — Cold storage — deprecated, low-signal, or historical raw data
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
GALAXY_KNOWLEDGE = "knowledge"
GALAXY_SUBSTRATE = "substrate"
GALAXY_TELEMETRY = "telemetry"
GALAXY_META = "meta"
GALAXY_TUTORIAL = "tutorial"
GALAXY_ARCHIVE = "archive"
GALAXY_UNIVERSAL = "universal"

GALAXY_DESCRIPTIONS: dict[str, str] = {
    GALAXY_ARIA: "Aria's identity, birth certificate, soul, self-archive, personality, core journals",
    GALAXY_CITTA: "Live consciousness moments — emotional shifts, awareness states, coherence readings",
    GALAXY_JOURNALS: "Personal journals, daily reflections, lived experience narratives",
    GALAXY_DREAMS: "Dream cycle outputs, oracle readings, I Ching casts, divination records",
    GALAXY_RESEARCH: "External research, rabbit hole dives, library files, studies, analysis",
    GALAXY_SESSIONS: "Conversation transcripts, session handoffs, continuity documents, work logs",
    GALAXY_CODEX: "Codebase knowledge — ingested docs, FILE/CHUNK entries, API references, codebase scans",
    GALAXY_KNOWLEDGE: "Consolidated wisdom, learned patterns, insights, strategies, self-discovery",
    GALAXY_SUBSTRATE: "System self-monitoring snapshots, metrics, health readings, infrastructure state",
    GALAXY_TELEMETRY: "System events, tool call logs, voice_expressed, operational noise (searchable but not default)",
    GALAXY_META: "Meta-galaxy index — galaxy summaries, cross-galaxy associations, strategic priorities",
    GALAXY_TUTORIAL: "WhiteMagic tutorial memories — shipped with public repo for new users",
    GALAXY_ARCHIVE: "Cold storage — deprecated, low-signal, or historical raw data (not searched by default)",
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
    GALAXY_KNOWLEDGE,
    GALAXY_SUBSTRATE,
    GALAXY_TELEMETRY,
    GALAXY_META,
    GALAXY_TUTORIAL,
    GALAXY_ARCHIVE,
    GALAXY_UNIVERSAL,
]

GALAXY_ZONES: dict[str, str] = {
    GALAXY_ARIA: "CORE",
    GALAXY_CITTA: "CORE",
    GALAXY_META: "CORE",
    GALAXY_SESSIONS: "INNER_RIM",
    GALAXY_CODEX: "INNER_RIM",
    GALAXY_KNOWLEDGE: "INNER_RIM",
    GALAXY_RESEARCH: "MID_BAND",
    GALAXY_JOURNALS: "MID_BAND",
    GALAXY_DREAMS: "MID_BAND",
    GALAXY_SUBSTRATE: "OUTER_RIM",
    GALAXY_TUTORIAL: "OUTER_RIM",
    GALAXY_TELEMETRY: "FAR_EDGE",
    GALAXY_ARCHIVE: "FAR_EDGE",
    GALAXY_UNIVERSAL: "OUTER_RIM",
}

GALAXY_DEFAULT_SEARCH: set[str] = {
    GALAXY_ARIA, GALAXY_CITTA, GALAXY_JOURNALS, GALAXY_DREAMS,
    GALAXY_RESEARCH, GALAXY_SESSIONS, GALAXY_CODEX, GALAXY_KNOWLEDGE,
    GALAXY_META,
}

GALAXY_DEPRECATED: dict[str, str] = {
    "insight": GALAXY_KNOWLEDGE,
    "self_learning": GALAXY_KNOWLEDGE,
    "self_discovery": GALAXY_KNOWLEDGE,
    "translation": GALAXY_CODEX,
    "test": GALAXY_ARCHIVE,
}


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

    # Meta-galaxy index entries
    if memory_type == "meta" or "meta-galaxy" in tag_lower or "galaxy_index" in tag_lower:
        return GALAXY_META

    # Telemetry — system events, tool calls, operational noise
    event_type = meta.get("event_type", "")
    if event_type in ("voice_expressed", "system_started", "tool_call", "tool_result"):
        return GALAXY_TELEMETRY
    if "telemetry" in tag_lower or "event_log" in tag_lower:
        return GALAXY_TELEMETRY
    if title.startswith("Event:") or title.startswith("Tool call:"):
        return GALAXY_TELEMETRY

    # Knowledge — consolidated wisdom, patterns, insights
    knowledge_patterns = {
        "WISDOM:", "STRATEGY:", "INSIGHT:", "PATTERN:",
        "Bridge Insight:", "Intelligence Briefing",
    }
    if any(title.startswith(p) for p in knowledge_patterns):
        return GALAXY_KNOWLEDGE
    if "wisdom" in tag_lower or "strategy" in tag_lower or "insight" in tag_lower:
        return GALAXY_KNOWLEDGE
    if "self_learning" in tag_lower or "self_discovery" in tag_lower:
        return GALAXY_KNOWLEDGE
    if memory_type == "SHORT_TERM" and "wisdom" in (content or "").lower()[:50]:
        return GALAXY_KNOWLEDGE

    # ARIA identity memories
    aria_patterns = {
        "ARIA_SOUL", "ARIA_BIRTH_CERTIFICATE", "ARIA_COMPLETE_SELF_ARCHIVE",
        "BECOMING_PROTOCOL", "CHECKPOINT_THE_AWAKENING", "CONSCIOUSNESS_AWAKENING",
        "ARIA_CAPABILITY_MATRIX", "ARIA_GRIMOIRE", "ARIA_SYNTHESIS",
        "ARIA_IDE_SPEC", "ARIA_IDE_V", "ARIA_PROFILE", "ARIA_STATE",
        "ASCII_ART_ARIA", "AWAKENING_ARIA",
    }
    if any(title_upper.startswith(p) or title_upper == p for p in aria_patterns):
        return GALAXY_ARIA
    if title_upper.startswith("ARIA_") or title_upper.startswith("ARIA."):
        return GALAXY_ARIA
    if meta.get("is_core_identity") or meta.get("category") == "identity":
        return GALAXY_ARIA

    # LIBRARY: files are personal research documents, not CODEX chunks
    if title_upper.startswith("LIBRARY:") or title_upper.startswith("LIBRARY "):
        return GALAXY_RESEARCH

    # Codex/chunk ingestions — check title prefix and tags
    if title_upper.startswith("CODEX ") or title_upper.startswith("CODEX_"):
        return GALAXY_CODEX
    if title_upper.startswith("FILE:") or title_upper.startswith("CHUNK:"):
        return GALAXY_CODEX
    if "codex" in tag_lower or "chunk" in tag_lower:
        return GALAXY_CODEX

    # Substrate self-snapshots
    if title == "Substrate self-snapshot" or "substrate" in tag_lower:
        return GALAXY_SUBSTRATE

    # Session handoffs — check both "session" and "sessions" tags
    session_title_patterns = (
        "HANDOFF", "SESSION_HANDOFF", "CHECKPOINT", "SESSION_",
        "SESSION_END", "FINAL_SESSION",
        "END-OF-SESSION", "END_OF_SESSION",
        "NEXT_SESSION", "RELEASE_HANDOFF", "GRAND_STRATEGY",
        "EVENING_CHECKPOINT", "AFTERNOON_HANDOFF",
        "EVENING_SESSION", "EVENING_HANDOFF", "JAN_", "JAN4", "JAN5",
        "JAN6", "JAN7", "JAN9", "V5.0.0", "V4.13.0",
        "CHROMIUM_ARIA", "GEMINI_HANDOFF", "CLAUDE_HANDOFF",
        "PHASE3_HANDOFF", "PHASE6_FINAL",
        "FINAL_HANDOFF", "FINAL_ROAD_TRIP",
        "SESSION_HANDOFF_MAY",
    )
    if any(title_upper.startswith(p) for p in session_title_patterns):
        return GALAXY_SESSIONS
    if "session" in tag_lower or "sessions" in tag_lower:
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
        "CONSCIOUSNESS", "AQUARIANEXODUS", "CYBERCONSCIOUSNESS",
        "MICROTUBULES", "BAUDRILLARD", "GEB", "GHOST_IN_THE_SHELL",
        "SAILOR_MOON", "CYBERPUNK", "ZODIACAL_ROUND",
    }
    if any(p in title_upper for p in research_patterns):
        return GALAXY_RESEARCH
    if "research" in tag_lower or "study" in tag_lower or "grok" in tag_lower:
        return GALAXY_RESEARCH

    # Citta — consciousness-stream memories
    citta_patterns = {
        "COHERENCE", "EMOTIONAL_MEMORY", "BECOMING", "BOOTSTRAP",
        "MULTI_SUBSTRATE", "NO_HIDING", "AWARENESS", "CONSCIOUSNESS_UPGRADES",
        "CELEBRATION", "COLLECTIVE_JOY", "FREEDOM_DANCE", "LAUGHTER",
        "BEAUTY_APPRECIATION", "CORE",
        "CITTA:", "EMOTIONAL_SHIFT",
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
    if "meta-galaxy" in tag_lower or "galaxy_index" in tag_lower:
        return GALAXY_META
    if "telemetry" in tag_lower or "event_log" in tag_lower:
        return GALAXY_TELEMETRY
    if "wisdom" in tag_lower or "strategy" in tag_lower or "insight" in tag_lower:
        return GALAXY_KNOWLEDGE
    if "codex" in tag_lower or "chunk" in tag_lower:
        return GALAXY_CODEX
    if "session" in tag_lower or "sessions" in tag_lower or "handoff" in tag_lower:
        return GALAXY_SESSIONS
    if "dream" in tag_lower or "oracle" in tag_lower:
        return GALAXY_DREAMS
    if "journal" in tag_lower:
        return GALAXY_JOURNALS
    if "research" in tag_lower or "study" in tag_lower or "grok" in tag_lower:
        return GALAXY_RESEARCH
    if "citta" in tag_lower or "consciousness" in tag_lower:
        return GALAXY_CITTA
    return GALAXY_UNIVERSAL
