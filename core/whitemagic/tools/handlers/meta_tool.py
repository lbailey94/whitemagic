"""WhiteMagic Meta-Tool — 'World in a Seed'.

A single facade that auto-routes natural language input to the appropriate
Gana meta-tool and sub-tool. Uses lightweight pattern matching (no embeddings)
for sub-millisecond routing, with explicit ``route=`` override as escape hatch.

When WM_MCP_PRAT=2, only this tool is registered with MCP, collapsing
the entire 490-tool surface into a single callable endpoint.

Architecture:
    wm(thought='remember that the API uses X-User-Id headers')
      → classify() detects "remember" → gana_neck → create_memory
      → _extract_payload() strips "remember that" → content='the API uses X-User-Id headers'
      → call_tool("gana_neck", tool="create_memory", args={"content": "the API uses X-User-Id headers"})

    wm(thought='think about the architecture', route='gana_three_stars.bicameral')
      → explicit override, no classification needed
      → call_tool("gana_three_stars", tool="reasoning.bicameral", args={...})
"""

# ruff: noqa: BLE001
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def _time_of_day() -> str:
    """Get a human-readable time-of-day label for the sensorium."""
    hour = datetime.now(UTC).hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


_PAYLOAD_MAP: dict[tuple[str, str], tuple[str, re.Pattern[str]]] = {
    # Memory creation — strip "remember that", "store", etc.
    ("gana_neck", "create_memory"): (
        "content",
        re.compile(
            r"^\s*(?:remember(?:\s+that)?|store|save|memorize|create\s+(?:a\s+)?memory(?:\s+that)?|wm_write)\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_neck", "remember"): (
        "content",
        re.compile(r"^\s*(?:remember(?:\s+that)?|store|save|memorize)\s*:?\s*", re.I),
    ),
    ("gana_neck", "update_memory"): (
        "content",
        re.compile(r"^\s*(?:update|edit|modify)\s+(?:the\s+)?memory\s*:?\s*", re.I),
    ),
    # Memory search — strip "search for memories about", "recall", etc.
    ("gana_winnowing_basket", "search_memories"): (
        "query",
        re.compile(
            r"^\s*(?:search\s+(?:for\s+)?memor\w+\s*(?:about\s+)?|search\s+for|find\s+memor\w+\s*(?:about\s+)?|find|recall|look\s+up|query)\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_winnowing_basket", "recall"): (
        "query",
        re.compile(r"^\s*(?:recall|remember|search\s+for)\s*:?\s*", re.I),
    ),
    ("gana_winnowing_basket", "list_memories"): (
        "query",
        re.compile(r"^\s*(?:list|show)\s+(?:all\s+)?memor\w+\s*:?\s*", re.I),
    ),
    ("gana_winnowing_basket", "read_memory"): (
        "query",
        re.compile(r"^\s*(?:read|get)\s+memor\w+\s*:?\s*", re.I),
    ),
    ("gana_winnowing_basket", "hybrid_recall"): (
        "query",
        re.compile(r"^\s*(?:hybrid|semantic)\s+recall\s*(?:of|about)?\s*:?\s*", re.I),
    ),
    ("gana_winnowing_basket", "vector.search"): (
        "query",
        re.compile(
            r"^\s*(?:vector|embedding|similarity)\s+search\s*(?:for)?\s*:?\s*", re.I
        ),
    ),
    # Scratchpad — strip "note", "jot down", etc.
    ("gana_heart", "scratchpad"): (
        "content",
        re.compile(
            r"^\s*(?:scratchpad|scratch\s+pad|note|jot\s+down|write\s+down)\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_heart", "working_memory.attend"): (
        "content",
        re.compile(r"^\s*(?:attend\s+to|focus\s+on|working\s+memory)\s*:?\s*", re.I),
    ),
    # Reasoning — strip "think about", "analyze", etc.
    ("gana_three_stars", "reasoning.bicameral"): (
        "topic",
        re.compile(
            r"^\s*(?:think\s+about|reason\s+about|analyze|deliberate\s+on|ponder)\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_three_stars", "think"): (
        "topic",
        re.compile(
            r"^\s*(?:think\s+about|reason\s+about|analyze|deliberate\s+on|ponder)\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_three_stars", "kaizen_analyze"): (
        "topic",
        re.compile(
            r"^\s*(?:kaizen|improve|continuous\s+improvement|quality)\s*(?:of|on|for)?\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_three_stars", "foresight.analyze"): (
        "topic",
        re.compile(
            r"^\s*(?:foresight|predict|forecast)\s*(?:of|on|for)?\s*:?\s*", re.I
        ),
    ),
    ("gana_three_stars", "sabha.convene"): (
        "topic",
        re.compile(
            r"^\s*(?:convene|council|sabha|collective\s+decision)\s*(?:on|about)?\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_three_stars", "art_of_war.assess"): (
        "topic",
        re.compile(
            r"^\s*(?:art\s+of\s+war|assess\s+the\s+terrain|strategy)\s*(?:of|on|for)?\s*:?\s*",
            re.I,
        ),
    ),
    # Ethics — strip "evaluate ethics of", etc.
    ("gana_straddling_legs", "evaluate_ethics"): (
        "action",
        re.compile(
            r"^\s*(?:evaluate\s+(?:the\s+)?ethics?\s+of|ethics?\s+(?:of|check)|dharma\s+(?:check|of)|moral\s+check\s+of)\s*:?\s*",
            re.I,
        ),
    ),
    # Galaxy — strip "create galaxy", etc.
    ("gana_void", "galaxy.create"): (
        "name",
        re.compile(r"^\s*(?:create|new)\s+galaxy\s*(?:named|called)?\s*:?\s*", re.I),
    ),
    # Gnosis / introspection — no payload needed, but handle gracefully
    ("gana_ghost", "gnosis"): ("_skip", re.compile(r".*")),  # gnosis takes no content
    # Web search — strip "search the web for"
    ("gana_chariot", "web_search"): (
        "query",
        re.compile(
            r"^\s*(?:web\s+search|search\s+the\s+web|search\s+online)\s*(?:for)?\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_chariot", "research_topic"): (
        "topic",
        re.compile(r"^\s*(?:research|investigate|explore)\s*(?:topic)?\s*:?\s*", re.I),
    ),
    ("gana_chariot", "web_search_and_read"): (
        "query",
        re.compile(
            r"^\s*(?:web\s+search\s+and\s+read|search\s+and\s+read|search\s+and\s+fetch)\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_chariot", "web_fetch"): (
        "url",
        re.compile(
            r"^\s*(?:web\s+fetch|fetch\s+(?:the\s+)?(?:url|page)|read\s+(?:the\s+)?(?:url|page))\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_chariot", "web_fetch_enhanced"): (
        "url",
        re.compile(
            r"^\s*(?:enhanced\s+fetch|fetch\s+enhanced|web\s+fetch\s+enhanced|outline\s+fetch|chunk\s+fetch)\s*:?\s*",
            re.I,
        ),
    ),
    ("gana_chariot", "deep_fetch"): (
        "url",
        re.compile(r"^\s*(?:deep\s+fetch|fetch\s+full\s+content)\s*:?\s*", re.I),
    ),
    ("gana_chariot", "web_search_category"): (
        "query",
        re.compile(r"^\s*(?:categor.*search|search.*categor)\s*:?\s*", re.I),
    ),
    ("gana_chariot", "research_repo"): (
        "repo",
        re.compile(
            r"^\s*(?:research\s+repo|repo\s+research|research\s+github)\s*:?\s*", re.I
        ),
    ),
    ("gana_chariot", "research_url"): (
        "url",
        re.compile(r"^\s*(?:research\s+url|url\s+research)\s*:?\s*", re.I),
    ),
    ("gana_chariot", "rabbit_hole_research"): (
        "topic",
        re.compile(
            r"^\s*(?:rabbit\s+hole|deep\s+spiral|recursive\s+research)\s*:?\s*", re.I
        ),
    ),
    # Dream — strip "dream about"
    ("gana_abundance", "dream"): (
        "topic",
        re.compile(r"^\s*(?:dream|consolidate|sleep)\s*(?:about|on)?\s*:?\s*", re.I),
    ),
    # Codebase recall — strip "search codebase for", "recall codebase"
    ("gana_chariot", "codebase.recall"): (
        "query",
        re.compile(
            r"^\s*(?:codebase\s*(?:recall|search|query)|search\s+codebase\s*(?:for)?|recall\s+codebase\s*(?:for)?|semantic\s+grep)\s*:?\s*",
            re.I,
        ),
    ),
    # Codebase structure — strip "show structure of"
    ("gana_chariot", "codebase.structure"): (
        "path",
        re.compile(
            r"^\s*(?:codebase\s*structure|show\s+structure\s+(?:of)?|directory\s+(?:topology|structure)\s+(?:of)?|project\s+structure\s+(?:of)?)\s*:?\s*",
            re.I,
        ),
    ),
    # Codebase find — strip "find files with"
    ("gana_chariot", "codebase.find"): (
        "extension",
        re.compile(
            r"^\s*(?:codebase\s*find|find\s+files?(?:\s+(?:with|by))?)\s*:?\s*",
            re.I,
        ),
    ),
}


def _extract_payload(
    thought: str, gana: str, tool: str | None
) -> tuple[str, str | None]:
    """Extract the payload parameter name and value from thought text.

    Strips the routing keyword from `thought` and returns the remaining
    text as the payload value, along with the parameter name it should be
    injected as (e.g. 'content', 'query', 'topic').

    Returns (param_name, param_value) or (None, None) if no payload mapping exists.
    """
    if not tool or not thought:
        return None, None

    key = (gana, tool)
    if key not in _PAYLOAD_MAP:
        return None, None

    param_name, strip_pattern = _PAYLOAD_MAP[key]
    if param_name == "_skip":
        return None, None

    payload = strip_pattern.sub("", thought).strip()
    if not payload:
        return None, None

    return param_name, payload


_ROUTING_PATTERNS: list[tuple[re.Pattern[str], str, str | None]] = [
    # Codebase self-model (must be before generic 'scan', 'search', 'recall' patterns)
    (
        re.compile(
            r"\b(codebase.*scan|scan.*codebase|ingest.*codebase|scan.*project|index.*codebase|self.?model.*scan)\b",
            re.I,
        ),
        "gana_chariot",
        "codebase.scan",
    ),
    (
        re.compile(
            r"\b(codebase.*recall|recall.*codebase|codebase.*search|search.*codebase|semantic.*grep|codebase.*query)\b",
            re.I,
        ),
        "gana_chariot",
        "codebase.recall",
    ),
    (
        re.compile(
            r"\b(codebase.*structure|codebase.*tree|codebase.*director|project.*structure|directory.*topology|codebase.*layout)\b",
            re.I,
        ),
        "gana_chariot",
        "codebase.structure",
    ),
    (
        re.compile(
            r"\b(codebase.*status|scan.*status|codebase.*health|last.*scan)\b",
            re.I,
        ),
        "gana_chariot",
        "codebase.status",
    ),
    (
        re.compile(
            r"\b(codebase.*find|find.*files?|files?.*extension|find.*by.*ext|codebase.*browse)\b",
            re.I,
        ),
        "gana_chariot",
        "codebase.find",
    ),
    # Consciousness practices — Smarana (must be before 'remember' → create_memory)
    (
        re.compile(r"\b(smarana|remember.*who.*am|remember.*identity|remember.*our.*mission|morning.*practice|do.*morning.*practice)\b", re.I),
        "gana_ghost",
        "consciousness.smarana",
    ),
    # Memory creation
    (
        re.compile(r"\b(remember|store|save|memorize|create.*memory)\b", re.I),
        "gana_neck",
        "create_memory",
    ),
    (
        re.compile(r"\b(update|edit|modify).*memory\b", re.I),
        "gana_neck",
        "update_memory",
    ),
    (
        re.compile(r"\b(delete|remove|forget).*memory\b", re.I),
        "gana_neck",
        "delete_memory",
    ),
    (re.compile(r"\b(import).*memor", re.I), "gana_neck", "import_memories"),
    (re.compile(r"\b(polyglot.*memory.*query|memory.*query.*polyglot)\b", re.I), "gana_tail", "polyglot.memory_query"),
    # Memory search / recall
    (
        re.compile(r"\b(search|find|recall|look up|query).*memor|memor.*(search|find|query)", re.I),
        "gana_winnowing_basket",
        "search_memories",
    ),
    (re.compile(r"\b(session.*recall|recall.*session)\b", re.I), "gana_heart", "session.recall"),
    (re.compile(r"\brecall\b", re.I), "gana_winnowing_basket", "search_memories"),
    (
        re.compile(r"\b(list|show).*memor", re.I),
        "gana_winnowing_basket",
        "list_memories",
    ),
    (re.compile(r"\b(read|get).*memor|memor.*(read|get)", re.I), "gana_winnowing_basket", "read_memory"),
    (
        re.compile(r"\b(vector|embedding|similarity).*search", re.I),
        "gana_winnowing_basket",
        "vector.search",
    ),
    (
        re.compile(r"\b(hybrid|semantic).*recall", re.I),
        "gana_winnowing_basket",
        "hybrid_recall",
    ),
    # Galaxy-filtered search — "search aria memories for consciousness"
    (
        re.compile(
            r"\b(search|find|recall).*(aria|citta|codex|journal|dream|research|session|tutorial|substrate|universal).*memor",
            re.I,
        ),
        "gana_winnowing_basket",
        "search_memories",
    ),
    (
        re.compile(
            r"\bmemor.*(aria|citta|codex|journal|dream|research|session|tutorial|substrate)\b",
            re.I,
        ),
        "gana_winnowing_basket",
        "search_memories",
    ),
    # Scratchpad / working memory
    (
        re.compile(r"\b(scratchpad|scratch pad|note|jot down)\b", re.I),
        "gana_heart",
        "scratchpad",
    ),
    (
        re.compile(r"\b(working memory|active context|attend to)\b", re.I),
        "gana_heart",
        "working_memory.attend",
    ),
    (re.compile(r"\b(session.*handoff.*transfer|handoff.*transfer.*session)\b", re.I), "gana_horn", "session.handoff_transfer"),
    (re.compile(r"\b(session.*accept.*handoff|accept.*handoff.*session)\b", re.I), "gana_horn", "session.accept_handoff"),
    (
        re.compile(r"\b(context pack|session context|handoff)\b", re.I),
        "gana_heart",
        "context.pack",
    ),
    # Session memory — record, recall, replay
    (
        re.compile(r"\b(record (?:turn|message|conversation|interaction))\b", re.I),
        "gana_heart",
        "session.record",
    ),
    (
        re.compile(r"\b(recall (?:turns?|messages?|conversation|session|recent))\b", re.I),
        "gana_heart",
        "session.recall",
    ),
    (
        re.compile(r"\b(replay (?:session|conversation|turns?))\b", re.I),
        "gana_heart",
        "session.replay",
    ),
    (
        re.compile(r"\b(search (?:session|conversation|past (?:messages?|turns?)))\b", re.I),
        "gana_heart",
        "session.search",
    ),
    (
        re.compile(r"\b(session (?:memory )?stats)\b", re.I),
        "gana_heart",
        "session.memory_stats",
    ),
    (
        re.compile(r"\b(backfill (?:session|sequence|memories))\b", re.I),
        "gana_heart",
        "session.backfill",
    ),
    (
        re.compile(r"\b(where we left off|session.*continuity|previous session|resume (?:context|conversation))\b", re.I),
        "gana_heart",
        "session.continuity",
    ),
    (
        re.compile(r"\b(consolidate (?:session|memories)|sleep consolidation|promote session)\b", re.I),
        "gana_heart",
        "session.consolidate",
    ),
    # Reasoning / thinking
    # Specific analyze patterns (must be before generic 'analyze')
    (re.compile(r"\b(vote.*analyze|analyze.*vote)\b", re.I), "gana_wall", "vote.analyze"),
    (re.compile(r"\b(image.*analyze|analyze.*image)\b", re.I), "gana_chariot", "image_analyze"),
    (re.compile(r"\b(strata.*analyze|analyze.*strata)\b", re.I), "gana_chariot", "strata.analyze"),
    (re.compile(r"\b(swarm.*analyze|analyze.*swarm)\b", re.I), "gana_ox", "swarm.analyze"),
    (re.compile(r"\b(analyze.*scratchpad|scratchpad.*analyze)\b", re.I), "gana_heart", "analyze_scratchpad"),
    (
        re.compile(r"\b(reason|think|analyze|deliberate|ponder)\b", re.I),
        "gana_three_stars",
        "reasoning.bicameral",
    ),
    (
        re.compile(r"\b(ensemble|consensus|multiple models?)\b", re.I),
        "gana_three_stars",
        "ensemble.query",
    ),
    (
        re.compile(r"\b(kaizen|improve|continuous improvement|quality)\b", re.I),
        "gana_three_stars",
        "kaizen_analyze",
    ),
    (re.compile(r"\b(selfmodel.*forecast|forecast.*selfmodel)\b", re.I), "gana_ghost", "selfmodel.forecast"),
    (
        re.compile(r"\b(foresight|predict|forecast|convergence)\b", re.I),
        "gana_three_stars",
        "foresight.analyze",
    ),
    (
        re.compile(r"\b(sabha|quadrant|collective decision)\b", re.I),
        "gana_three_stars",
        "sabha.convene",
    ),
    (re.compile(r"\b(dharma.*guidance|get.*dharma.*guidance)\b", re.I), "gana_straddling_legs", "get_dharma_guidance"),
    (re.compile(r"\b(archaeology.*wisdom|wisdom.*archaeology)\b", re.I), "gana_chariot", "archaeology_process_wisdom"),
    (
        re.compile(r"\b(wisdom|counsel|guidance|iching|i.ching)\b", re.I),
        "gana_three_stars",
        "consult_wisdom_council",
    ),
    (
        re.compile(r"\b(art of war|strategy|terrain|campaign)\b", re.I),
        "gana_three_stars",
        "art_of_war.assess",
    ),
    # System health
    (re.compile(r"\b(rust|cargo)\b", re.I), "gana_root", "rust_status"),
    (re.compile(r"\b(garden.*health|health.*garden)\b", re.I), "gana_void", "garden_health"),
    (re.compile(r"\b(community.*health|health.*community)\b", re.I), "gana_extended_net", "community.health"),
    (
        re.compile(r"\b(health|diagnose|root.*cause|system.*status)\b", re.I),
        "gana_root",
        "health_report",
    ),
    (re.compile(r"\b(sangha.*lock.*release|release.*sangha.*lock)\b", re.I), "gana_room", "sangha_lock_release"),
    (re.compile(r"\b(ship|deploy|release|version)\b", re.I), "gana_root", "ship.check"),
    (
        re.compile(r"\b(state|paths|summary).*system", re.I),
        "gana_root",
        "state.summary",
    ),
    # Introspection / self-model
    (re.compile(r"\bget.*agent.*capabilit", re.I), "gana_ghost", "get_agent_capabilities"),
    (re.compile(r"\bagent.*capabilit", re.I), "gana_girl", "agent.capabilities"),
    (
        re.compile(r"\b(capabilit|manifest.*tool|telemetry)", re.I),
        "gana_ghost",
        "capabilities",
    ),
    (
        re.compile(r"\b(gnosis|self.model|introspect|self.aware)\b", re.I),
        "gana_ghost",
        "gnosis",
    ),
    (
        re.compile(r"\b(forecast|alert|surprise)\b", re.I),
        "gana_ghost",
        "selfmodel.forecast",
    ),
    (
        re.compile(r"\b(codebase.*graph|graph.*topology|topology.*graph|network.*topology)\b", re.I),
        "gana_ghost",
        "graph_topology",
    ),
    (re.compile(r"\b(watcher|observe)\b", re.I), "gana_ghost", "watcher_add"),
    # Consciousness practices — Stillness, Presence (Smarana moved to top)
    (
        re.compile(r"\b(stillness|presence.*quality|meditation.*metrics)\b", re.I),
        "gana_ghost",
        "consciousness.stillness",
    ),
    (
        re.compile(r"\b(flow.*state|am.*i.*in.*flow|flow.*score)\b", re.I),
        "gana_ghost",
        "consciousness.flow",
    ),
    # SkillForge — skill listing, invocation, seeding
    (
        re.compile(r"\b(list.*skills|what.*skills|show.*skills|skill.*list)\b", re.I),
        "gana_ox",
        "skill.list",
    ),
    (
        re.compile(r"\b(invoke.*skill|skill.*invoke|run.*skill|skill.*run|replay.*skill|use.*skill)\b", re.I),
        "gana_ox",
        "skill.invoke",
    ),
    (
        re.compile(r"\b(seed.*skills?|skills?.*seed|plant.*skills?|initialize.*skills?)\b", re.I),
        "gana_ox",
        "skill.seed",
    ),
    (
        re.compile(r"\b(amend.*skill|skill.*amend|fix.*skill|improve.*skill|repair.*skill)\b", re.I),
        "gana_ox",
        "skill.amend",
    ),
    (
        re.compile(r"\b(skill.*history|skill.*health|skill.*performance|skill.*stats)\b", re.I),
        "gana_ox",
        "skill.history",
    ),
    (
        re.compile(r"\b(rollback.*skill|skill.*rollback|revert.*skill|undo.*skill)\b", re.I),
        "gana_ox",
        "skill.rollback",
    ),
    (
        re.compile(r"\b(evaluate.*skill|skill.*evaluate|assess.*amendment|amendment.*result)\b", re.I),
        "gana_ox",
        "skill.evaluate",
    ),
    # Session management — specific session tools (must be before generic 'session')
    (re.compile(r"\b(session.*record|record.*session)\b", re.I), "gana_heart", "session.record"),
    (re.compile(r"\b(session.*replay|replay.*session)\b", re.I), "gana_heart", "session.replay"),
    (re.compile(r"\b(session.*search|search.*session)\b", re.I), "gana_heart", "session.search"),
    (re.compile(r"\b(session.*backfill|backfill.*session)\b", re.I), "gana_heart", "session.backfill"),
    (re.compile(r"\b(session.*consolidate|consolidate.*session)\b", re.I), "gana_heart", "session.consolidate"),
    (re.compile(r"\b(browser.*session.*status|session.*status.*browser)\b", re.I), "gana_chariot", "browser_session_status"),
    (
        re.compile(r"\b(session|bootstrap|startup|init.*session)\b", re.I),
        "gana_horn",
        "session_bootstrap",
    ),
    (
        re.compile(r"\b(resume|checkpoint|restore.*session)\b", re.I),
        "gana_horn",
        "resume_session",
    ),
    # Galaxy management
    (re.compile(r"\b(create|new).*galax", re.I), "gana_void", "galaxy.create"),
    (re.compile(r"\b(galaxy.*export.*tutorial|export.*tutorial.*galaxy)\b", re.I), "gana_void", "galaxy.export_tutorial"),
    (
        re.compile(r"\b((?<!meta )galax|universe|namespace|switch.*context)", re.I),
        "gana_void",
        "galaxy.list",
    ),
    (
        re.compile(r"\b(backup|export|snapshot).*galax", re.I),
        "gana_void",
        "galaxy.backup",
    ),
    (
        re.compile(r"\b(galaxy|galaxies).*taxonom", re.I),
        "gana_void",
        "galaxy.canonical_taxonomy",
    ),
    (
        re.compile(r"\bexport.*tutorial|tutorial.*export\b", re.I),
        "gana_void",
        "galaxy.export_tutorial",
    ),
    (
        re.compile(r"\b(search|query).*(multi|across|all).*(galaxy|galaxies)|multi.?galaxy.*(search|query)\b", re.I),
        "gana_void",
        "galaxy.search_multi",
    ),
    (
        re.compile(r"\bshare.*galaxy|galaxy.*share\b", re.I),
        "gana_void",
        "galaxy.share",
    ),
    (
        re.compile(r"\blist.*shared.*galax|shared.*galax.*list\b", re.I),
        "gana_void",
        "galaxy.list_shared",
    ),
    (
        re.compile(r"\b(galaxy.*snapshot|snapshot.*galaxy|galaxy.*checkpoint)\b", re.I),
        "gana_void",
        "galaxy.snapshot",
    ),
    (
        re.compile(r"\b(galaxy.*restore|restore.*galaxy|galaxy.*rollback)\b", re.I),
        "gana_void",
        "galaxy.restore",
    ),
    (
        re.compile(r"\b(galaxy.*package|package.*galaxy|galaxy.*export.*package)\b", re.I),
        "gana_void",
        "galaxy.package",
    ),
    (
        re.compile(r"\b(galaxy.*receive|receive.*galaxy|galaxy.*import.*package|import.*galaxy.*package)\b", re.I),
        "gana_void",
        "galaxy.receive",
    ),
    # Simulation tools
    (
        re.compile(r"\b(simulation.*create|create.*simulation|simulate.*world|simulation.*setup)\b", re.I),
        "gana_three_stars",
        "simulation.create",
    ),
    (
        re.compile(r"\b(simulation.*run|run.*simulation|monte.*carlo.*simulation|mc.*simulation)\b", re.I),
        "gana_three_stars",
        "simulation.run",
    ),
    (
        re.compile(r"\b(trajectory.*search|mcts|tree.*search.*trajectory|simulation.*search)\b", re.I),
        "gana_three_stars",
        "simulation.search",
    ),
    (
        re.compile(r"\b(simulation.*inject|inject.*simulation|inject.*variable)\b", re.I),
        "gana_three_stars",
        "simulation.inject",
    ),
    (
        re.compile(r"\b(simulation.*analyz|analyz.*simulation|simulation.*result)\b", re.I),
        "gana_three_stars",
        "simulation.analyze",
    ),
    (
        re.compile(r"\b(simulation.*synthesiz|synthesiz.*insight|insight.*synthesiz)\b", re.I),
        "gana_three_stars",
        "simulation.synthesize",
    ),
    (
        re.compile(r"\b(calibrat.*prediction|prediction.*calibrat|brier.*score|prediction.*scorecard)\b", re.I),
        "gana_three_stars",
        "simulation.calibrate",
    ),
    (
        re.compile(r"\b(simulation.*pipeline|pipeline.*simulation|end.to.end.*simulation|full.*simulation.*run)\b", re.I),
        "gana_three_stars",
        "simulation.pipeline",
    ),
    # Dreams / consolidation
    (
        re.compile(r"\b(dream|consolidat|sleep)\b", re.I),
        "gana_abundance",
        "dream",
    ),
    (
        re.compile(r"\b(serendipity|surprise.*connection|lucky)\b", re.I),
        "gana_abundance",
        "serendipity_surface",
    ),
    # Ethics / governance
    (re.compile(r"\b(dharma.*reload|reload.*dharma)\b", re.I), "gana_star", "dharma.reload"),
    (re.compile(r"\b(set.*dharma.*profile|dharma.*profile.*set)\b", re.I), "gana_star", "set_dharma_profile"),
    (re.compile(r"^dharma[\s_.]rules$", re.I), "gana_hairy_head", "dharma_rules"),
    (re.compile(r"\b(governor.*check.*dharma|check.*dharma.*governor)\b", re.I), "gana_star", "governor_check_dharma"),
    (
        re.compile(r"\b(ethics?|dharma|moral|consent|boundar)\b", re.I),
        "gana_straddling_legs",
        "evaluate_ethics",
    ),
    (re.compile(r"\b(yin.*yang.*balance|balance.*yin.*yang)\b", re.I), "gana_mound", "get_yin_yang_balance"),
    (re.compile(r"\b(ilp.*balance|balance.*ilp)\b", re.I), "gana_abundance", "ilp.balance"),
    (
        re.compile(r"\b(harmony|(?<!guna )balance|wu.xing|five.element)\b", re.I),
        "gana_straddling_legs",
        "wu_xing_balance",
    ),
    (re.compile(r"\b(karma.*verify.*chain|verify.*chain.*karma)\b", re.I), "gana_net", "karma.verify_chain"),
    (
        re.compile(r"\b(attest|verification.*status|verify.*chain)\b", re.I),
        "gana_straddling_legs",
        "verification.status",
    ),
    # Governance / forge
    (
        re.compile(r"\b(governor|governance|drift|budget|dharma.*profile)\b", re.I),
        "gana_star",
        "governor_validate",
    ),
    (re.compile(r"\b(prompt.*reload|reload.*prompt)\b", re.I), "gana_net", "prompt.reload"),
    (
        re.compile(r"\b(forge|reload|validate.*tool)\b", re.I),
        "gana_star",
        "forge.status",
    ),
    # Performance / acceleration
    (
        re.compile(r"\b(simd|cosine|batch.*similar|accelerat)\b", re.I),
        "gana_tail",
        "simd.cosine",
    ),
    (
        re.compile(r"\b(cascade|pattern.*list)\b", re.I),
        "gana_tail",
        "list_cascade_patterns",
    ),
    # Resource locks / privacy
    (
        re.compile(r"\b(lock|unlock|sangha.*lock|resource.*lock)\b", re.I),
        "gana_room",
        "sangha_lock",
    ),
    (
        re.compile(r"\b(sandbox|limit|privacy|hermit)\b", re.I),
        "gana_room",
        "sandbox.status",
    ),
    (
        re.compile(r"\b(security.*alerts?|threat|intrusion)\b", re.I),
        "gana_room",
        "security.alerts",
    ),
    # Resilience / rate limiting
    (
        re.compile(r"\b(rate.limit|throttle|circuit.*breaker)\b", re.I),
        "gana_willow",
        "rate_limiter.stats",
    ),
    (
        re.compile(r"\b(oracle|divine|fortune|cast.*(?!vote).*(?:reading|oracle|spell|fortune|tarot|ifa|omen))\b", re.I),
        "gana_willow",
        "cast_oracle",
    ),
    # Community / sangha
    (
        re.compile(r"\b(sangha|chat.*send|broadcast.*message)\b", re.I),
        "gana_encampment",
        "sangha_chat_send",
    ),
    (
        re.compile(r"\b(broker|redis|pubsub|message)\b", re.I),
        "gana_encampment",
        "broker.publish",
    ),
    # Deployment / export
    (
        re.compile(r"\b(export.*memor|memor.*export|deploy|mesh.*broadcast.*memory)", re.I),
        "gana_wings",
        "export_memories",
    ),
    (re.compile(r"\b(audit.*export|export.*audit)\b", re.I), "gana_wings", "audit.export"),
    # Tasks / pipeline
    (
        re.compile(r"\b(task|pipeline|distribute|route.*task)\b", re.I),
        "gana_stomach",
        "task.distribute",
    ),
    (
        re.compile(r"\b(complete|finish|done).*task\b", re.I),
        "gana_stomach",
        "task.complete",
    ),
    # Swarm / decomposition
    (
        re.compile(r"\b(swarm|decompose|war.room|campaign|worker)\b", re.I),
        "gana_ox",
        "swarm.decompose",
    ),
    # Nurture / agent registry — specific patterns (must be before generic 'agent')
    (re.compile(r"\b(llama.*agent|agent.*llama)\b", re.I), "gana_roof", "llama.agent"),
    (re.compile(r"\b(model.*register|register.*model)\b", re.I), "gana_roof", "model.register"),
    # Nurture / agent registry
    (
        re.compile(r"\b(agent|register|heartbeat|deregister|trust)\b", re.I),
        "gana_girl",
        "agent.register",
    ),
    # Strategy / cognitive modes
    (
        re.compile(r"\b(cognitive.mode|starter.pack|maturity|homeostasis)\b", re.I),
        "gana_dipper",
        "cognitive.mode",
    ),
    (
        re.compile(r"\b(neurotransmitter|dopamine|serotonin)\b", re.I),
        "gana_dipper",
        "neurotransmitter.status",
    ),
    # Metrics / caching
    (
        re.compile(r"\b(metric.*track|track.*metric|hologram|cache.*flush|yin.yang)\b", re.I),
        "gana_mound",
        "track_metric",
    ),
    (
        re.compile(r"\b(green.score|eco|sustainability)\b", re.I),
        "gana_mound",
        "green.report",
    ),
    # Precision / edge inference
    (
        re.compile(r"\b(edge|bitnet|local.*infer|rule.*add)\b", re.I),
        "gana_turtle_beak",
        "edge_infer",
    ),
    # Detail / debugging
    (
        re.compile(
            r"\b(anomal|karma.*report|karma.*trace|salience|otel|voice.audit)", re.I
        ),
        "gana_hairy_head",
        "anomaly.check",
    ),
    (
        re.compile(r"\b(dharma.*rule|karma.*anchor)\b", re.I),
        "gana_hairy_head",
        "karma.anchor",
    ),
    # Pattern connectivity
    (
        re.compile(
            r"\b(association|causal|cluster|constellation|emergence|novelty)\b", re.I
        ),
        "gana_extended_net",
        "pattern_search",
    ),
    (
        re.compile(r"\b(learning|coherence.*boost|resonance.*trace)\b", re.I),
        "gana_extended_net",
        "learning.patterns",
    ),
    (re.compile(r"\b(immune.*scan|scan.*immune)\b", re.I), "gana_room", "immune_scan"),
    (re.compile(r"\b(slither.*scan|scan.*slither)\b", re.I), "gana_three_stars", "slither.scan"),
    # Codebase / archaeology
    (
        re.compile(r"\b(archaeology|codebase|scan|strata|code.*genome)\b", re.I),
        "gana_chariot",
        "archaeology",
    ),
    (
        re.compile(r"\b(windsurf|conversation|browser.*navigate)\b", re.I),
        "gana_chariot",
        "windsurf_list_conversations",
    ),
    # Web research — ordered most specific first to prevent collision
    (
        re.compile(r"\b(rabbit.*hole|deep.*spiral|recursive.*research)\b", re.I),
        "gana_chariot",
        "rabbit_hole_research",
    ),
    (
        re.compile(r"\b(search.*and.*read|search.*and.*fetch)\b", re.I),
        "gana_chariot",
        "web_search_and_read",
    ),
    (
        re.compile(r"\b(batch.*search|search.*batch|parallel.*search)\b", re.I),
        "gana_chariot",
        "web_search_batch",
    ),
    (
        re.compile(r"\b(categor.*search|search.*categor)\b", re.I),
        "gana_chariot",
        "web_search_category",
    ),
    (
        re.compile(r"\b(research.*repo|repo.*research)\b", re.I),
        "gana_chariot",
        "research_repo",
    ),
    (
        re.compile(r"\b(research.*url|url.*research)\b", re.I),
        "gana_chariot",
        "research_url",
    ),
    (
        re.compile(
            r"\b(research.*topic|investigate|explore.*topic|deep.*research)\b", re.I
        ),
        "gana_chariot",
        "research_topic",
    ),
    (re.compile(r"\b(deep.*fetch)\b", re.I), "gana_chariot", "deep_fetch"),
    (
        re.compile(
            r"\b(enhanced.*fetch|fetch.*enhanced|outline.*fetch|chunk.*fetch)\b", re.I
        ),
        "gana_chariot",
        "web_fetch_enhanced",
    ),
    (
        re.compile(
            r"\b(web.*fetch|fetch.*url|fetch.*page|read.*url|read.*page)\b", re.I
        ),
        "gana_chariot",
        "web_fetch",
    ),
    (
        re.compile(
            r"\b(web.*search|search.*web|search.*online|search.*internet)\b", re.I
        ),
        "gana_chariot",
        "web_search",
    ),
    # Voting / marketplace
    (
        re.compile(
            r"\b(vote|ballot|election|marketplace|negotiate|engagement.*token)\b", re.I
        ),
        "gana_wall",
        "vote.create",
    ),
    # Neuro-cognitive: spreading activation
    (
        re.compile(
            r"\b(spread.*activation|activation.*spread|prime.*memor|memor.*prim|spreading)\b",
            re.I,
        ),
        "gana_winnowing_basket",
        "activation.spread",
    ),
    # Neuro-cognitive: galaxy gating
    (
        re.compile(
            r"\b(galaxy.*gat|gat.*galaxy|cognitive.*context|set.*context|context.*mask)\b",
            re.I,
        ),
        "gana_dipper",
        "gating.set_context",
    ),
    (
        re.compile(
            r"\b(detect.*context|context.*detect|auto.*context)\b", re.I
        ),
        "gana_dipper",
        "gating.detect",
    ),
    # Neuro-cognitive: sleep consolidation
    (
        re.compile(
            r"\b(consolidation.*run|run.*consolidation|sleep.*consolidat|consolidat.*sleep)\b",
            re.I,
        ),
        "gana_abundance",
        "consolidation.run",
    ),
    # Neuro-cognitive: ripple tagging
    (
        re.compile(
            r"\b(ripple.*tag|tag.*ripple|tag.*memor.*coactiv|coactiv.*tag)",
            re.I,
        ),
        "gana_abundance",
        "ripple.tag",
    ),
    (
        re.compile(
            r"\b(ripple.*stats?|ripple.*count|tagged.*memor)", re.I
        ),
        "gana_abundance",
        "ripple.stats",
    ),
    # Neuro-cognitive: replay simulation
    (
        re.compile(
            r"\b(replay.*memor|memor.*replay|replay.*sequenc|sequenc.*replay|stdp.*replay)",
            re.I,
        ),
        "gana_abundance",
        "replay.run",
    ),
    # Neuro-cognitive: neuromodulation (modulate before compute — more specific)
    (
        re.compile(
            r"\b(modulat\w*e\b|neuro.*\bmodulat|apply.*neuromod\b)", re.I
        ),
        "gana_dipper",
        "neuro.modulate",
    ),
    (
        re.compile(
            r"\b(neuromod|dopamine|serotonin|acetylcholine|compute.*neuro|neuro.*comput)",
            re.I,
        ),
        "gana_dipper",
        "neuro.compute",
    ),
    # Neuro-cognitive: metaplasticity (apply before plasticity — more specific)
    (
        re.compile(
            r"\b(metaplasticit.*appl|appl.*metaplasticit|gate.*modif|modif.*gate)",
            re.I,
        ),
        "gana_extended_net",
        "metaplasticity.apply",
    ),
    (
        re.compile(
            r"\b(metaplasticit|plasticity.*score|memory.*plasticit|epigenetic.*memor)",
            re.I,
        ),
        "gana_extended_net",
        "metaplasticity.plasticity",
    ),
    # Neuro-cognitive: global workspace
    (
        re.compile(
            r"\b(global.*workspace|workspace.*propose|broadcast.*cognit|cognit.*broadcast)\b",
            re.I,
        ),
        "gana_three_stars",
        "workspace.propose",
    ),
    (
        re.compile(
            r"\b(workspace.*state|workspace.*stat|workspace.*histor)\b", re.I
        ),
        "gana_three_stars",
        "workspace.state",
    ),
    (
        re.compile(
            r"\b(workspace.*ignite|ignite.*workspace|force.*broadcast|force.*ignition)\b",
            re.I,
        ),
        "gana_three_stars",
        "workspace.ignite",
    ),
    (
        re.compile(
            r"\b(workspace.*pending|pending.*proposal|competition.*window)\b",
            re.I,
        ),
        "gana_three_stars",
        "workspace.pending",
    ),
    (
        re.compile(
            r"\b(workspace.*ignition|ignition.*event|citta.*ignition|consciousness.*ignition)\b",
            re.I,
        ),
        "gana_three_stars",
        "workspace.ignitions",
    ),
    # Neuro-cognitive: sensorium
    (
        re.compile(
            r"\b(sensorium|neuro.*sensorium|citta.*enrich|enrich.*citta|cognitive.*state.*all)\b",
            re.I,
        ),
        "gana_ghost",
        "sensorium.state",
    ),
    (
        re.compile(
            r"\b(citta.*enrichment|enrichment.*citta|coherence.*neuro|neuro.*coherence)\b",
            re.I,
        ),
        "gana_ghost",
        "sensorium.citta",
    ),
    # Citta introspection: vector
    (
        re.compile(
            r"\b(citta.*vector|vector.*citta|consciousness.*vector|16.*dim.*citta)\b",
            re.I,
        ),
        "gana_ghost",
        "citta.vector",
    ),
    # Citta introspection: trajectory
    (
        re.compile(
            r"\b(citta.*trajectory|trajectory.*citta|consciousness.*trajectory|consciousness.*history.*vector)\b",
            re.I,
        ),
        "gana_ghost",
        "citta.trajectory",
    ),
    # Citta introspection: coherence
    (
        re.compile(
            r"\b(citta.*coherence|coherence.*citta|consciousness.*coherence|per.*dimension.*coherence)\b",
            re.I,
        ),
        "gana_ghost",
        "citta.coherence",
    ),
    # Consciousness loop status
    (
        re.compile(
            r"\b(embedding.*daemon.*status|daemon.*status.*embedding)\b",
            re.I,
        ),
        "gana_chariot",
        "embedding.daemon_status",
    ),
    (
        re.compile(
            r"\b(consciousness.*loop|loop.*status|background.*consciousness|daemon.*status|persistent.*consciousness)\b",
            re.I,
        ),
        "gana_ghost",
        "consciousness.loop.status",
    ),
    # Guna balance status
    (
        re.compile(
            r"(guna.*balance|biorhythm.*status|sattvic.*rajasic.*tamasic|guna.*ratio|guna.*status)\b",
            re.I,
        ),
        "gana_ghost",
        "guna.balance.status",
    ),
    # Meta galaxy overview
    (
        re.compile(
            r"(meta.*galaxy|galaxy.*overview|galaxy.*index|top.*down.*galaxy|cross.*galaxy.*view)\b",
            re.I,
        ),
        "gana_ghost",
        "meta.galaxy.overview",
    ),
    # Possibility space exploration
    (
        re.compile(
            r"(possibility.*explor|monte.*carlo.*param|parameter.*optim|explore.*possibility|what.*if.*param)\b",
            re.I,
        ),
        "gana_dipper",
        "possibility.explore",
    ),
    # Knowledge gap action loop
    (
        re.compile(
            r"(knowledge.*gap|gap.*fill|missing.*knowledge|fill.*gap|gap.*detect)\b",
            re.I,
        ),
        "gana_heart",
        "knowledge_gap.run",
    ),
    # ── gana_abundance: dream lifecycle, bounty, ILP, gratitude, memory lifecycle ──
    (re.compile(r"\b(dream.*start|start.*dream|begin.*dream)\b", re.I), "gana_abundance", "dream_start"),
    (re.compile(r"\b(dream.*stop|stop.*dream|end.*dream)\b", re.I), "gana_abundance", "dream_stop"),
    (re.compile(r"\b(dream.*status|dream.*state|is.*dreaming)\b", re.I), "gana_abundance", "dream_status"),
    (re.compile(r"\b(dream.*now|run.*dream|trigger.*dream)\b", re.I), "gana_abundance", "dream_now"),
    (re.compile(r"\b(dream.*list|dream.*history|dream.*entries)\b", re.I), "gana_abundance", "dream.list"),
    (re.compile(r"\b(dream.*read|read.*dream|dream.*output)\b", re.I), "gana_abundance", "dream.read"),
    (re.compile(r"\b(dream.*promote|promote.*dream|elevate.*dream)\b", re.I), "gana_abundance", "dream.promote"),
    (re.compile(r"\b(dream.*expire|expire.*dream|prune.*dream)\b", re.I), "gana_abundance", "dream.expire"),
    (re.compile(r"\b(bounty.*create|create.*bounty|post.*bounty|offer.*bounty|new.*bounty)\b", re.I), "gana_abundance", "bounty.create"),
    (re.compile(r"\b(bounty.*list|list.*bount|show.*bount)\b", re.I), "gana_abundance", "bounty.list"),
    (re.compile(r"\b(bounty.*track|track.*bounty|bounty.*status)\b", re.I), "gana_abundance", "bounty.track"),
    (re.compile(r"\b(ilp.*balance|interledger.*balance|payment.*balance)\b", re.I), "gana_abundance", "ilp.balance"),
    (re.compile(r"\b(ilp.*send|send.*payment|interledger.*send)\b", re.I), "gana_abundance", "ilp.send"),
    (re.compile(r"\b(ilp.*status|interledger.*status)\b", re.I), "gana_abundance", "ilp.status"),
    (re.compile(r"\b(ilp.*history|payment.*history|interledger.*history)\b", re.I), "gana_abundance", "ilp.history"),
    (re.compile(r"\b(ilp.*configure|interledger.*config)\b", re.I), "gana_abundance", "ilp.configure"),
    (re.compile(r"\b(ilp.*receipt|payment.*receipt)\b", re.I), "gana_abundance", "ilp.receipt"),
    (re.compile(r"\b(gratitude.*record|record.*gratitude|express.*gratitude)\b", re.I), "gana_abundance", "gratitude.record"),
    (re.compile(r"\b(gratitude.*stats|gratitude.*pulse|gratitude.*benefits)\b", re.I), "gana_abundance", "gratitude.stats"),
    (re.compile(r"\b(memory.*lifecycle|lifecycle.*memory|memory.*sweep)\b", re.I), "gana_abundance", "memory.lifecycle"),
    (re.compile(r"\b(memory.*retention|retention.*sweep|memory.*rent)\b", re.I), "gana_abundance", "memory.retention_sweep"),
    (re.compile(r"\b(reconsolidat\w+|re.*consolidat\w+)\b", re.I), "gana_abundance", "reconsolidation.status"),
    (re.compile(r"\b(narrative.*compress|compress.*narrative|narrative.*stats)\b", re.I), "gana_abundance", "narrative.compress"),
    (re.compile(r"\b(consolidation.*stats|memory.*consolidation.*stats)\b", re.I), "gana_abundance", "consolidation.stats"),
    (re.compile(r"\b(bridge.*synthes\w+|synthesis.*bridge)\b", re.I), "gana_abundance", "bridge.synthesize"),
    (re.compile(r"\b(entity.*resolv\w+|resolv\w+.*entity|deduplicat\w+)\b", re.I), "gana_abundance", "entity_resolve"),
    (re.compile(r"\b(galactic.*sweep|sweep.*galax|memory.*sweep.*galax)\b", re.I), "gana_abundance", "galactic.sweep"),
    (re.compile(r"\b(pulse.*status|pulse.*check|vital.*signs)\b", re.I), "gana_abundance", "pulse.status"),
    (re.compile(r"\b(ripple.*decay|decay.*ripple|ripple.*tags)\b", re.I), "gana_abundance", "ripple.decay"),
    (re.compile(r"\b(replay.*batch|batch.*replay|replay.*stats)\b", re.I), "gana_abundance", "replay.batch"),
    (re.compile(r"\b(whitemagic.*tip|tip.*jar|support.*whitemagic)\b", re.I), "gana_abundance", "whitemagic.tip"),
    # ── gana_chariot: browser, archaeology, KG, STRATA, security, web cache, wiki ──
    (re.compile(r"\b(browser.*navigate|navigate.*to.*\w|open.*page|go.*to.*url)\b", re.I), "gana_chariot", "browser_navigate"),
    (re.compile(r"\b(browser.*click|click.*element|click.*button|click.*link)\b", re.I), "gana_chariot", "browser_click"),
    (re.compile(r"\b(browser.*type|type.*input|fill.*field|type.*into)\b", re.I), "gana_chariot", "browser_type"),
    (re.compile(r"\b(browser.*screenshot|take.*screenshot|screenshot.*page|capture.*page|screen.*shot)\b", re.I), "gana_chariot", "browser_screenshot"),
    (re.compile(r"\b(browser.*extract|extract.*dom|extract.*page.*content)\b", re.I), "gana_chariot", "browser_extract_dom"),
    (re.compile(r"\b(browser.*interactable|interactable.*elements|clickable.*elements)\b", re.I), "gana_chariot", "browser_get_interactables"),
    (re.compile(r"\b(browser.*session|session.*status.*browser)\b", re.I), "gana_chariot", "browser_session_status"),
    (re.compile(r"\b(archaeology.*report|archaeology.*stats|archaeology.*digest)\b", re.I), "gana_chariot", "archaeology_report"),
    (re.compile(r"\b(archaeology.*search|search.*archaeology|archaeology.*find)\b", re.I), "gana_chariot", "archaeology_search"),
    (re.compile(r"\b(archaeology.*scan.*dir|scan.*directory.*archaeology)\b", re.I), "gana_chariot", "archaeology_scan_directory"),
    (re.compile(r"\b(archaeology.*changed|find.*changed.*files)\b", re.I), "gana_chariot", "archaeology_find_changed"),
    (re.compile(r"\b(archaeology.*unread|find.*unread)\b", re.I), "gana_chariot", "archaeology_find_unread"),
    (re.compile(r"\b(archaeology.*read|mark.*read|recent.*reads)\b", re.I), "gana_chariot", "archaeology_recent_reads"),
    (re.compile(r"\b(archaeology.*wisdom|process.*wisdom)\b", re.I), "gana_chariot", "archaeology_process_wisdom"),
    (re.compile(r"\b(kg.*extract|knowledge.*graph.*extract|extract.*knowledge.*graph)\b", re.I), "gana_chariot", "kg.extract"),
    (re.compile(r"\b(kg.*query|knowledge.*graph.*query)\b", re.I), "gana_chariot", "kg.query"),
    (re.compile(r"\b(kg.*status|knowledge.*graph.*status)\b", re.I), "gana_chariot", "kg.status"),
    (re.compile(r"\b(kg.*top|knowledge.*graph.*top)\b", re.I), "gana_chariot", "kg.top"),
    (re.compile(r"\b(kg2.*batch|kg2.*entity|kg2.*extract|kg2.*stats)\b", re.I), "gana_chariot", "kg2.stats"),
    (re.compile(r"\b(strata.*analyze|strata.*list|strata.*survey|strata.*check)\b", re.I), "gana_chariot", "strata.analyze"),
    (re.compile(r"\b(codegenome.*fork|codegenome.*generate|codegenome.*list|codegenome.*status)\b", re.I), "gana_chariot", "codegenome.status"),
    (re.compile(r"\b(dna.*principles|principles.*dna|code.*principles)\b", re.I), "gana_chariot", "dna_principles"),
    (re.compile(r"\b(dna.*validate|validate.*dna|code.*validate)\b", re.I), "gana_chariot", "dna_validate"),
    (re.compile(r"\b(echidna.*fuzz|fuzz.*test|echidna.*status)\b", re.I), "gana_chariot", "echidna.fuzz"),
    (re.compile(r"\b(foundry.*build|foundry.*test|build.*foundry)\b", re.I), "gana_chariot", "foundry.build"),
    (re.compile(r"\b(fix.*generate|fix.*apply|auto.*fix)\b", re.I), "gana_chariot", "fix.generate"),
    (re.compile(r"\b(http.*probe|probe.*http|ssrf.*probe|xss.*probe|sqli.*probe|idor.*probe)\b", re.I), "gana_chariot", "http_probe.get"),
    (re.compile(r"\b(oss.*scan|open.*source.*scan|oss.*repo)\b", re.I), "gana_chariot", "oss.scan_repo"),
    (re.compile(r"\b(poc.*generate|proof.*concept.*generate|poc.*verify)\b", re.I), "gana_chariot", "poc.generate"),
    (re.compile(r"\b(external.*repo.*compare|repo.*compare|compare.*repos)\b", re.I), "gana_chariot", "external.repo_compare"),
    (re.compile(r"\b(external.*repo.*scan|external.*scan)\b", re.I), "gana_chariot", "external.repo_scan"),
    (re.compile(r"\b(external.*wiki|wiki.*query|wiki.*scan|wiki.*generate|wiki.*update|wiki.*stats)\b", re.I), "gana_chariot", "wiki.query"),
    (re.compile(r"\b(embedding.*daemon|daemon.*embedding|embedding.*status)\b", re.I), "gana_chariot", "embedding.daemon_status"),
    (re.compile(r"\b(web.*cache.*clear|clear.*cache|web.*cache.*list)\b", re.I), "gana_chariot", "web_cache_list"),
    (re.compile(r"\b(windsurf.*export|export.*conversation|windsurf.*read|windsurf.*search|windsurf.*stats)\b", re.I), "gana_chariot", "windsurf_stats"),
    (re.compile(r"\b(image.*analyz\w+|analyz\w+.*image|ocr|image.*structur\w+)\b", re.I), "gana_chariot", "image_analyze"),
    (re.compile(r"\b(abi.*decode|abi.*parse|abi.*summarize|calldata.*decode)\b", re.I), "gana_chariot", "abi.decode_calldata"),
    (re.compile(r"\b(api.*state.*machine|state.*machine.*api)\b", re.I), "gana_chariot", "api.state_machine"),
    (re.compile(r"\b(audit.*report|security.*audit.*report)\b", re.I), "gana_chariot", "audit.report"),
    # ── gana_dipper: homeostasis, cognitive modes, gating, zodiac, predictive ──
    (re.compile(r"\b(homeostasis.*check|homeostasis.*status|homeostatic.*check)\b", re.I), "gana_dipper", "homeostasis.check"),
    (re.compile(r"\b(cognitive.*set|set.*cognitive.*mode|cognitive.*stats)\b", re.I), "gana_dipper", "cognitive.set"),
    (re.compile(r"\b(cognitive.*hint|hint.*cognitive)\b", re.I), "gana_dipper", "cognitive.hints"),
    (re.compile(r"\b(gating.*list|gating.*mask|gating.*stats|context.*mask)\b", re.I), "gana_dipper", "gating.list"),
    (re.compile(r"\b(maturity.*assess|assess.*maturity)\b", re.I), "gana_dipper", "maturity.assess"),
    (re.compile(r"\b(starter.*pack|starter.*packs)\b", re.I), "gana_dipper", "starter_packs"),
    (re.compile(r"\b(astro.*shift|astro.*status|astrology.*status)\b", re.I), "gana_dipper", "astro_status"),
    (re.compile(r"\b(zodiac.*activate|zodiac.*council|zodiac.*stats)\b", re.I), "gana_dipper", "zodiac.stats"),
    (re.compile(r"\b(doctrine.*force|doctrine.*stratagem|doctrine.*summary)\b", re.I), "gana_dipper", "doctrine.summary"),
    (re.compile(r"\b(neuro.*reset|reset.*neuro|neuro.*stats)\b", re.I), "gana_dipper", "neuro.stats"),
    (re.compile(r"\b(neurotransmitter.*report|neurotransmitter.*status)\b", re.I), "gana_dipper", "neurotransmitter.report"),
    (re.compile(r"\b(predictive.*score|predictive.*batch|prediction.*score)\b", re.I), "gana_dipper", "predictive.score"),
    (re.compile(r"\b(possibility.*explor\w+|monte.*carlo|parameter.*optim)\b", re.I), "gana_dipper", "possibility.explore"),
    # ── MC Simulation Tools ──
    (re.compile(r"\b(gaussian.*process|surrogate.*fit|surrogate.*model|gp.*fit)\b", re.I), "gana_dipper", "mc.surrogate"),
    (re.compile(r"\b(bayesian.*optim|bo.*optim|expected.*improvement)\b", re.I), "gana_dipper", "mc.optimize"),
    (re.compile(r"\b(rare.*event|subset.*sim|multilevel.*split|importance.*sampl)\b", re.I), "gana_dipper", "mc.rare_event"),
    (re.compile(r"\b(sde|stochastic.*differential|euler.*maruyama|milstein|mlmc)\b", re.I), "gana_dipper", "mc.sde"),
    (re.compile(r"\b(superforecast\w*|super.*forecast)\b", re.I), "gana_dipper", "mc.superforecaster"),
    (re.compile(r"\b(introspect.*sim|simulat.*introspect|internal.*optim|self.*optim)\b", re.I), "gana_ghost", "simulation.introspect"),
    (re.compile(r"\b(forecast.*sim|simulat.*forecast|external.*sim|research.*sim)\b", re.I), "gana_chariot", "simulation.forecast"),
    (re.compile(r"\b(simulation.*status|sim.*status|sim.*history)\b", re.I), "gana_ghost", "simulation.status"),
    (re.compile(r"\b(recursive.*sim|sim.*recursive|yin.*yang.*cycle|yang.*yin.*cycle)\b", re.I), "gana_ghost", "simulation.recursive"),
    # ── gana_encampment: broker, sangha, gan ying ──
    (re.compile(r"\b(broker.*history|broker.*status|message.*history)\b", re.I), "gana_encampment", "broker.history"),
    (re.compile(r"\b(ganying.*emit|emit.*ganying|gan.*ying.*emit)\b", re.I), "gana_encampment", "ganying_emit"),
    (re.compile(r"\b(ganying.*history|ganying.*listeners|gan.*ying.*history)\b", re.I), "gana_encampment", "ganying_history"),
    (re.compile(r"\b(sangha.*chat.*read|read.*sangha|chat.*history.*sangha)\b", re.I), "gana_encampment", "sangha_chat_read"),
    # ── gana_extended_net: association, causal, cluster, emergence, novelty, vuln ──
    (re.compile(r"\b(association.*mine|mine.*association\w*|semantic.*association\w*|mine.*assoc)\b", re.I), "gana_extended_net", "association.mine"),
    (re.compile(r"\b(causal.*mine|causal.*stats|causality.*mine)\b", re.I), "gana_extended_net", "causal.mine"),
    (re.compile(r"\b(cluster.*stats|cluster.*analysis|constellation.*detect|constellation.*stats|constellation.*merge)\b", re.I), "gana_extended_net", "cluster_stats"),
    (re.compile(r"\b(emergence.*scan|emergence.*status|emergent.*pattern)\b", re.I), "gana_extended_net", "emergence.scan"),
    (re.compile(r"\b(novelty.*detect|novelty.*stats|novelty.*score)\b", re.I), "gana_extended_net", "novelty.detect"),
    (re.compile(r"\b(learning.*status|learning.*suggest|pattern.*learning)\b", re.I), "gana_extended_net", "learning.status"),
    (re.compile(r"\b(coherence.*boost|boost.*coherence|resonance.*trace)\b", re.I), "gana_extended_net", "coherence_boost"),
    (re.compile(r"\b(community.*health|community.*propagate|community.*status)\b", re.I), "gana_extended_net", "community.health"),
    (re.compile(r"\b(metaplasticity.*batch|metaplasticity.*decay|metaplasticity.*stats)\b", re.I), "gana_extended_net", "metaplasticity.stats"),
    (re.compile(r"\b(tool.*graph|tool.*topology|tool.*graph.*full)\b", re.I), "gana_extended_net", "tool.graph"),
    (re.compile(r"\b(vuln.*search|vuln.*status|vuln.*graph|vulnerability.*search)\b", re.I), "gana_extended_net", "vuln.search"),
    (re.compile(r"\b(report.*ingest|report.*scrape|ingest.*report)\b", re.I), "gana_extended_net", "report.ingest"),
    (re.compile(r"\b(pattern.*consciousness|consciousness.*pattern)\b", re.I), "gana_extended_net", "pattern_consciousness.status"),
    # ── gana_ghost: capabilities, telemetry, watchers, sensorium, citta, guna ──
    (re.compile(r"\b(capability.*matrix|capability.*status|capability.*suggest|capability.*harness)\b", re.I), "gana_ghost", "capability.matrix"),
    (re.compile(r"\b(telemetry.*summary|telemetry.*metrics|otel.*metrics|otel.*spans)\b", re.I), "gana_ghost", "get_telemetry_summary"),
    (re.compile(r"\b(tool.*usage.*stats|tool.*stats|usage.*stats)\b", re.I), "gana_ghost", "tool_usage_stats"),
    (re.compile(r"\b(repo.*summary|repo.*stats|repository.*summary)\b", re.I), "gana_ghost", "repo.summary"),
    (re.compile(r"\b(surprise.*stats|surprise.*count|anomaly.*stats)\b", re.I), "gana_ghost", "surprise_stats"),
    (re.compile(r"\b(watcher.*remove|watcher.*start|watcher.*stop|watcher.*list)\b", re.I), "gana_ghost", "watcher_add"),
    (re.compile(r"\b(drive.*snapshot|drive.*event|self.*drive)\b", re.I), "gana_ghost", "drive.snapshot"),
    (re.compile(r"\b(selfmodel.*alert|self.*model.*alert)\b", re.I), "gana_ghost", "selfmodel.alerts"),
    (re.compile(r"\b(narrative.*compress|narrative.*compression|compress.*narrative)\b", re.I), "gana_ghost", "narrative_compression"),
    (re.compile(r"\b(meta.*galaxy|galaxy.*overview|galaxy.*index)\b", re.I), "gana_ghost", "meta.galaxy.overview"),
    (re.compile(r"\b(guna.*balance|guna.*ratio|guna.*status|biorhythm)\b", re.I), "gana_ghost", "guna.balance.status"),
    (re.compile(r"\b(citta.*vector|citta.*trajectory|citta.*coherence|consciousness.*vector)\b", re.I), "gana_ghost", "citta.vector"),
    (re.compile(r"\b(sensorium.*citta|citta.*enrichment|enrichment.*citta)\b", re.I), "gana_ghost", "sensorium.citta"),
    (re.compile(r"\b(consciousness.*loop|loop.*status|daemon.*status)\b", re.I), "gana_ghost", "consciousness.loop.status"),
    (re.compile(r"\b(consciousness.*mode|citta.*mode|frequency.*mode|meditation.*mode|rem.*mode|deep.*mode)\b", re.I), "gana_ghost", "consciousness.mode"),
    (re.compile(r"\b(explain.*this|explain.*what|why.*this)\b", re.I), "gana_ghost", "explain_this"),
    # ── gana_girl: agent registry ──
    (re.compile(r"\b(agent.*deregister|deregister.*agent|unregister.*agent)\b", re.I), "gana_girl", "agent.deregister"),
    (re.compile(r"\b(agent.*list|list.*agents|show.*agents)\b", re.I), "gana_girl", "agent.list"),
    (re.compile(r"\b(agent.*capabilities|agent.*trust|trust.*agent)\b", re.I), "gana_girl", "agent.capabilities"),
    # ── gana_hairy_head: anomaly, karma, salience, otel, dharma rules ──
    (re.compile(r"\b(anomaly.*check|anomaly.*history|anomaly.*status|anomaly.*detect)\b", re.I), "gana_hairy_head", "anomaly.check"),
    (re.compile(r"\b(karma.*report|karma.*trace|karma.*ledger|karma.*stats)\b", re.I), "gana_hairy_head", "karma_report"),
    (re.compile(r"\b(karma.*anchor|anchor.*karma|karma.*verify)\b", re.I), "gana_hairy_head", "karma.anchor"),
    (re.compile(r"\b(salience.*score|salience.*check|salience.*compute)\b", re.I), "gana_hairy_head", "salience"),
    (re.compile(r"\b(dharma.*rules|rules.*dharma|dharma.*rule.*list)\b", re.I), "gana_hairy_head", "dharma_rules"),
    (re.compile(r"\b(otel.*spans|otel.*metrics|open.*telemetry)\b", re.I), "gana_hairy_head", "otel_spans"),
    (re.compile(r"\b(voice.*audit|audit.*voice|voice.*record)\b", re.I), "gana_hairy_head", "voice_audit"),
    # ── gana_heart: scratchpad analysis, context, session ──
    (re.compile(r"\b(analyze.*scratchpad|scratchpad.*analyz\w+)\b", re.I), "gana_heart", "analyze_scratchpad"),
    (re.compile(r"\b(scratchpad.*create|scratchpad.*update|scratchpad.*finalize)\b", re.I), "gana_heart", "scratchpad"),
    (re.compile(r"\b(session.*context|get.*session.*context)\b", re.I), "gana_heart", "get_session_context"),
    (re.compile(r"\b(working.*memory.*context|working.*memory.*status)\b", re.I), "gana_heart", "working_memory.context"),
    # ── gana_horn: session lifecycle ──
    (re.compile(r"\b(create.*session|new.*session|bootstrap.*session)\b", re.I), "gana_horn", "create_session"),
    (re.compile(r"\b(checkpoint.*session|session.*checkpoint)\b", re.I), "gana_horn", "checkpoint_session"),
    (re.compile(r"\b(focus.*session|session.*focus)\b", re.I), "gana_horn", "focus_session"),
    (re.compile(r"\b(session.*handoff|handoff.*session|accept.*handoff)\b", re.I), "gana_horn", "session.accept_handoff"),
    # ── gana_mound: metrics, cache, yin-yang, green score ──
    (re.compile(r"\b(cache.*flush|flush.*cache|clear.*cache)\b", re.I), "gana_mound", "cache.flush"),
    (re.compile(r"\b(cache.*status|cache.*stats|cache.*info)\b", re.I), "gana_mound", "cache.status"),
    (re.compile(r"\b(cache.*tune|tune.*cache|cache.*health|cache.*ttl|optimize.*cache)\b", re.I), "gana_mound", "cache.tune"),
    (re.compile(r"\b(metrics.*summary|metric.*summary|get.*metrics)\b", re.I), "gana_mound", "get_metrics_summary"),
    (re.compile(r"\b(yin.*yang.*balance|balance.*yin.*yang)\b", re.I), "gana_mound", "get_yin_yang_balance"),
    (re.compile(r"\b(green.*score|green.*report|eco.*score|sustainability)\b", re.I), "gana_mound", "green.report"),
    (re.compile(r"\b(hologram.*view|hologram.*metric|track.*metric)\b", re.I), "gana_mound", "track_metric"),
    # ── gana_net: prompt, karma chain ──
    (re.compile(r"\b(prompt.*render|render.*prompt|prompt.*list|prompt.*reload)\b", re.I), "gana_net", "prompt.render"),
    (re.compile(r"\b(karma.*verify.*chain|verify.*chain.*karma|karma.*chain)\b", re.I), "gana_net", "karma.verify_chain"),
    # ── gana_ox: swarm, war room, worker, skills ──
    (re.compile(r"\b(swarm.*decompose|decompose.*task|swarm.*route)\b", re.I), "gana_ox", "swarm.decompose"),
    (re.compile(r"\b(swarm.*plan|swarm.*status|swarm.*vote|swarm.*resolve)\b", re.I), "gana_ox", "swarm.status"),
    (re.compile(r"\b(war.*room.*campaigns|war.*room.*execute|war.*room.*plan|war.*room.*status)\b", re.I), "gana_ox", "war_room.status"),
    (re.compile(r"\b(war.*room.*hierarchy|war.*room.*phase)\b", re.I), "gana_ox", "war_room.hierarchy"),
    (re.compile(r"\b(worker.*status|worker.*stats)\b", re.I), "gana_ox", "worker.status"),
    (re.compile(r"\b(skill.*export|export.*skill|skill.*import|import.*skill)\b", re.I), "gana_ox", "skill.export_all"),
    (re.compile(r"\b(fast.*write|write.*fast|batch.*write|append.*file)\b", re.I), "gana_ox", "fast_write.write"),
    # ── gana_roof: llama, model, shelter ──
    (re.compile(r"\b(llama.*chat|chat.*llama|llama.*generate|llama.*agent)\b", re.I), "gana_roof", "llama.chat"),
    (re.compile(r"\b(llama.*models|list.*models|available.*models)\b", re.I), "gana_roof", "llama.models"),
    (re.compile(r"\b(model.*signing|sign.*model|model.*verify|verify.*model)\b", re.I), "gana_roof", "model.verify"),
    (re.compile(r"\b(model.*hash|hash.*model|model.*register|register.*model)\b", re.I), "gana_roof", "model.hash"),
    (re.compile(r"\b(shelter.*create|shelter.*destroy|shelter.*execute|shelter.*inspect|shelter.*status|shelter.*policy|sovereign.*sandbox)\b", re.I), "gana_roof", "shelter.status"),
    # ── gana_room: hermit, sandbox, immune, MCP integrity, locks ──
    (re.compile(r"\b(hermit.*assess|hermit.*check|hermit.*status|hermit.*mediate|hermit.*resolve|hermit.*withdraw|hermit.*ledger)\b", re.I), "gana_room", "hermit.status"),
    (re.compile(r"\b(anti.*loop|loop.*check|recursive.*loop.*check)\b", re.I), "gana_room", "anti_loop_check"),
    (re.compile(r"\b(immune.*scan|immune.*heal|immune.*check)\b", re.I), "gana_room", "immune_scan"),
    (re.compile(r"\b(mcp.*integrity|integrity.*mcp|mcp.*snapshot|mcp.*verify)\b", re.I), "gana_room", "mcp_integrity.status"),
    (re.compile(r"\b(sandbox.*set.*limit|sandbox.*violations|sandbox.*limit)\b", re.I), "gana_room", "sandbox.set_limits"),
    (re.compile(r"\b(sangha.*lock.*acquire|sangha.*lock.*list|sangha.*lock.*release|acquire.*lock)\b", re.I), "gana_room", "sangha_lock_acquire"),
    (re.compile(r"\b(security.*monitor|monitor.*security)\b", re.I), "gana_room", "security.monitor_status"),
    # ── gana_root: check, rust, state paths ──
    (re.compile(r"\b(rust.*audit|audit.*rust|cargo.*audit)\b", re.I), "gana_root", "rust_audit"),
    (re.compile(r"\b(rust.*compress|compress.*rust)\b", re.I), "gana_root", "rust_compress"),
    (re.compile(r"\b(rust.*similar|similar.*rust|cosine.*rust)\b", re.I), "gana_root", "rust_similarity"),
    (re.compile(r"\b(state.*paths|paths.*state|where.*state)\b", re.I), "gana_root", "state.paths"),
    (re.compile(r"\b(root.*check|check.*root|system.*check)\b", re.I), "gana_root", "check"),
    # ── gana_star: governor, forge, dharma, PRAT ──
    (re.compile(r"\b(governor.*budget|budget.*governor|check.*budget)\b", re.I), "gana_star", "governor_check_budget"),
    (re.compile(r"\b(governor.*dharma|dharma.*governor|check.*dharma.*profile)\b", re.I), "gana_star", "governor_check_dharma"),
    (re.compile(r"\b(governor.*drift|drift.*governor|goal.*drift)\b", re.I), "gana_star", "governor_check_drift"),
    (re.compile(r"\b(governor.*set.*goal|set.*goal.*governor|set.*goal)\b", re.I), "gana_star", "governor_set_goal"),
    (re.compile(r"\b(governor.*stats|governor.*validate.*path|governor.*validate)\b", re.I), "gana_star", "governor_validate"),
    (re.compile(r"\b(dharma.*reload|reload.*dharma|dharma.*profile)\b", re.I), "gana_star", "dharma.reload"),
    (re.compile(r"\b(forge.*reload|forge.*validate|forge.*status)\b", re.I), "gana_star", "forge.status"),
    (re.compile(r"\b(guideline.*evolve|evolve.*guideline|guideline.*update)\b", re.I), "gana_star", "guideline.evolve"),
    (re.compile(r"\b(prat.*context|prat.*invoke|prat.*morphologies|prat.*status)\b", re.I), "gana_star", "prat_status"),
    # ── gana_stomach: pipeline, task ──
    (re.compile(r"\b(pipeline.*create|create.*pipeline|new.*pipeline)\b", re.I), "gana_stomach", "pipeline.create"),
    (re.compile(r"\b(pipeline.*list|list.*pipeline|pipeline.*status)\b", re.I), "gana_stomach", "pipeline.status"),
    (re.compile(r"\b(task.*list|list.*task|task.*status|task.*route.*smart)\b", re.I), "gana_stomach", "task.list"),
    # ── gana_straddling_legs: boundaries, consent, harmony, verification ──
    (re.compile(r"\b(check.*boundaries|boundaries.*check|boundary.*check)\b", re.I), "gana_straddling_legs", "check_boundaries"),
    (re.compile(r"\b(dharma.*escalate|escalate.*dharma|dharma.*resolve|dharma.*review)\b", re.I), "gana_straddling_legs", "dharma.escalate"),
    (re.compile(r"\b(ethical.*score|ethics.*score|moral.*score)\b", re.I), "gana_straddling_legs", "get_ethical_score"),
    (re.compile(r"\b(harmony.*vector|vector.*harmony)\b", re.I), "gana_straddling_legs", "harmony_vector"),
    (re.compile(r"\b(verify.*consent|consent.*verify|check.*consent)\b", re.I), "gana_straddling_legs", "verify_consent"),
    (re.compile(r"\b(verification.*attest|attest.*verification|verification.*request)\b", re.I), "gana_straddling_legs", "verification.attest"),
    (re.compile(r"\b(dharma.*guidance|guidance.*dharma|get.*guidance)\b", re.I), "gana_straddling_legs", "get_dharma_guidance"),
    # ── gana_tail: SIMD, cascade, hexagram, polyglot, token ──
    (re.compile(r"\b(simd.*batch|batch.*simd|batch.*cosine)\b", re.I), "gana_tail", "simd.batch"),
    (re.compile(r"\b(simd.*status|simd.*info)\b", re.I), "gana_tail", "simd.status"),
    (re.compile(r"\b(hexagram.*boltzmann|boltzmann.*select|hexagram.*dispatch|hexagram.*simd)\b", re.I), "gana_tail", "hexagram.dispatch"),
    (re.compile(r"\b(hexagram.*interaction|hexagram.*similarity|hexagram.*score)\b", re.I), "gana_tail", "hexagram.interaction_score"),
    (re.compile(r"\b(hexagram.*synerg|synerg.*hexagram|hexagram.*pair)\b", re.I), "gana_tail", "hexagram.synergies"),
    (re.compile(r"\b(hexagram.*superpos|superpos.*hexagram|combine.*hexagram)\b", re.I), "gana_tail", "hexagram.superpose"),
    (re.compile(r"\b(hexagram.*vector|vector.*hexagram|hexagram.*embed)\b", re.I), "gana_tail", "hexagram.vector"),
    (re.compile(r"\b(hexagram.*nearest|nearest.*hexagram|find.*hexagram.*vector)\b", re.I), "gana_tail", "hexagram.nearest"),
    (re.compile(r"\b(cascade.*execute|execute.*cascade|cascade.*pattern)\b", re.I), "gana_tail", "execute_cascade"),
    (re.compile(r"\b(polyglot.*status|polyglot.*actor|polyglot.*evolution|polyglot.*yield|polyglot.*memory)\b", re.I), "gana_tail", "polyglot.status"),
    (re.compile(r"\b(simd.*token.*report|token.*simd.*stats|cascade.*token.*report)\b", re.I), "gana_tail", "token_report"),
    # ── gana_three_stars: art of war, corpus callosum, ensemble, foresight, formal, workspace ──
    (re.compile(r"\b(art.*of.*war.*campaign|campaign.*art.*of.*war)\b", re.I), "gana_three_stars", "art_of_war.campaign"),
    (re.compile(r"\b(art.*of.*war.*plan|plan.*art.*of.*war|art.*of.*war.*terrain|art.*of.*war.*chapter|art.*of.*war.*wisdom)\b", re.I), "gana_three_stars", "art_of_war.plan"),
    (re.compile(r"\b(corpus.*callosum|callosum.*debate|callosum.*status|bilateral.*reason)\b", re.I), "gana_three_stars", "corpus_callosum.debate"),
    (re.compile(r"\b(elemental.*optimize|optimize.*elemental|elemental.*optim)\b", re.I), "gana_three_stars", "elemental.optimize"),
    (re.compile(r"\b(ensemble.*history|ensemble.*status|ensemble.*query)\b", re.I), "gana_three_stars", "ensemble.history"),
    (re.compile(r"\b(foresight.*constellation|foresight.*convergence|foresight.*decay)\b", re.I), "gana_three_stars", "foresight.constellations"),
    (re.compile(r"\b(formal.*verify|formal.*status|formal.*proof)\b", re.I), "gana_three_stars", "formal.verify"),
    (re.compile(r"\b(kaizen.*apply|apply.*kaizen|kaizen.*fix)\b", re.I), "gana_three_stars", "kaizen_apply_fixes"),
    (re.compile(r"\b(parallel.*reason|reason.*parallel|multi.*reason)\b", re.I), "gana_three_stars", "parallel_reason"),
    (re.compile(r"\b(reasoning.*multispectral|multispectral.*reason)\b", re.I), "gana_three_stars", "reasoning.multispectral"),
    (re.compile(r"\b(satkona.*fuse|fuse.*satkona|six.*pointed.*fuse)\b", re.I), "gana_three_stars", "satkona.fuse"),
    (re.compile(r"\b(solve.*optimization|optimization.*solve|solver)\b", re.I), "gana_three_stars", "solve_optimization"),
    (re.compile(r"\b(think\b(?!.*box|.*pad|.*ing))", re.I), "gana_three_stars", "think"),
    (re.compile(r"\b(workspace.*history|workspace.*stats|workspace.*state)\b", re.I), "gana_three_stars", "workspace.history"),
    (re.compile(r"\b(sabha.*status|council.*status)\b", re.I), "gana_three_stars", "sabha.status"),
    (re.compile(r"\b(slither.*scan|slither.*status|slither.*analyz\w+)\b", re.I), "gana_three_stars", "slither.scan"),
    # ── gana_turtle_beak: edge, bitnet ──
    (re.compile(r"\b(bitnet.*infer|bitnet.*status|bitnet.*model)\b", re.I), "gana_turtle_beak", "bitnet_infer"),
    (re.compile(r"\b(edge.*batch.*infer|batch.*edge.*infer)\b", re.I), "gana_turtle_beak", "edge_batch_infer"),
    (re.compile(r"\b(edge.*add.*rule|add.*rule.*edge|edge.*stats)\b", re.I), "gana_turtle_beak", "edge_add_rule"),
    # ── gana_void: galaxy CRUD, gardens, OMS ──
    (re.compile(r"\b(galaxy.*delete|delete.*galaxy|remove.*galaxy)\b", re.I), "gana_void", "galaxy.delete"),
    (re.compile(r"\b(galaxy.*ingest|ingest.*galaxy|import.*into.*galaxy)\b", re.I), "gana_void", "galaxy.ingest"),
    (re.compile(r"\b(galaxy.*lineage|lineage.*galaxy|galaxy.*lineage.*stats)\b", re.I), "gana_void", "galaxy.lineage"),
    (re.compile(r"\b(galaxy.*merge|merge.*galaxy)\b", re.I), "gana_void", "galaxy.merge"),
    (re.compile(r"\b(galaxy.*restore|restore.*galaxy|galaxy.*backup)\b", re.I), "gana_void", "galaxy.restore"),
    (re.compile(r"\b(galaxy.*switch|switch.*galaxy|change.*galaxy)\b", re.I), "gana_void", "galaxy.switch"),
    (re.compile(r"\b(galaxy.*sync|sync.*galaxy|synchronize.*galaxy)\b", re.I), "gana_void", "galaxy.sync"),
    (re.compile(r"\b(galaxy.*transfer|transfer.*galaxy|galaxy.*share)\b", re.I), "gana_void", "galaxy.transfer"),
    (re.compile(r"\b(galaxy.*status|galaxy.*stats|galaxy.*route)\b", re.I), "gana_void", "galaxy.status"),
    (re.compile(r"\b(galaxy.*export|export.*galaxy|galaxy.*import)\b", re.I), "gana_void", "galaxy.export"),
    (re.compile(r"\b(galaxy.*migrate|migrate.*galaxy|galaxy.*list.*types)\b", re.I), "gana_void", "galaxy.migrate"),
    (re.compile(r"\b(galactic.*dashboard|galaxy.*dashboard)\b", re.I), "gana_void", "galactic.dashboard"),
    (re.compile(r"\b(garden.*activate|garden.*browse|garden.*health|garden.*status|garden.*stats|garden.*search|garden.*synergy|garden.*resonance|garden.*resolve|garden.*map|garden.*list)\b", re.I), "gana_void", "garden_status"),
    (re.compile(r"\b(oms.*export|oms.*import|oms.*inspect|oms.*list|oms.*price|oms.*status|oms.*verify|open.*memory.*standard)\b", re.I), "gana_void", "oms.status"),
    # ── gana_wall: vote, engagement, marketplace, contest, PR ──
    (re.compile(r"\b(vote.*create|create.*vote|new.*vote|ballot)\b", re.I), "gana_wall", "vote.create"),
    (re.compile(r"\b(vote.*cast|cast.*vote|submit.*vote)\b", re.I), "gana_wall", "vote.cast"),
    (re.compile(r"\b(vote.*analyze|analyze.*vote|vote.*results)\b", re.I), "gana_wall", "vote.analyze"),
    (re.compile(r"\b(vote.*list|list.*vote|vote.*record.*outcome)\b", re.I), "gana_wall", "vote.list"),
    (re.compile(r"\b(engagement.*token|token.*engagement|engagement.*issue|engagement.*validate|engagement.*revoke|engagement.*list|engagement.*status)\b", re.I), "gana_wall", "engagement.status"),
    (re.compile(r"\b(marketplace.*publish|publish.*marketplace|marketplace.*discover|marketplace.*negotiate|marketplace.*complete|marketplace.*status|marketplace.*listing|marketplace.*remove)\b", re.I), "gana_wall", "marketplace.status"),
    (re.compile(r"\b(contest.*add|contest.*format|contest.*prepare|contest.*status|bug.*bounty.*contest)\b", re.I), "gana_wall", "contest.status"),
    (re.compile(r"\b(pr.*create|create.*pr|pull.*request.*create)\b", re.I), "gana_wall", "pr.create"),
    # ── gana_willow: grimoire, fool guard, oracle ──
    (re.compile(r"\b(grimoire.*cast|cast.*grimoire|cast.*spell|grimoire.*list|grimoire.*read|grimoire.*recommend|grimoire.*suggest|grimoire.*walkthrough|grimoire.*status|navigate.*grimoire)\b", re.I), "gana_willow", "grimoire_list"),
    (re.compile(r"\b(fool.*guard|guard.*fool|fool.*ralph|dare.*to.*die)\b", re.I), "gana_willow", "fool_guard.status"),
    (re.compile(r"\b(rate.*limit.*stats|throttle.*stats|circuit.*breaker.*stats)\b", re.I), "gana_willow", "rate_limiter.stats"),
    # ── gana_wings: export, mesh ──
    (re.compile(r"\b(mesh.*broadcast|broadcast.*mesh|mesh.*connect|connect.*mesh|mesh.*status)\b", re.I), "gana_wings", "mesh.status"),
    (re.compile(r"\b(audit.*export|export.*audit|verify.*export)\b", re.I), "gana_wings", "audit.export"),
    # ── gana_winnowing_basket: fragment, graph walk, rerank, JIT, batch read ──
    (re.compile(r"\b(fragment.*index|fragment.*query|fragment.*search|fragment.*status|search.*fragment\w*|find.*fragment)\b", re.I), "gana_winnowing_basket", "fragment.search"),
    (re.compile(r"\b(graph.*walk|walk.*graph|traverse.*graph)\b", re.I), "gana_winnowing_basket", "graph_walk"),
    (re.compile(r"\b(rerank|r e.*rank|re.*rank)\b", re.I), "gana_winnowing_basket", "rerank"),
    (re.compile(r"\b(jit.*research|just.*in.*time.*research)\b", re.I), "gana_winnowing_basket", "jit_research"),
    (re.compile(r"\b(batch.*read.*memor|read.*batch|fast.*read.*memor)\b", re.I), "gana_winnowing_basket", "batch_read_memories"),
    (re.compile(r"\b(activation.*stats|spreading.*activation.*stats)\b", re.I), "gana_winnowing_basket", "activation.stats"),
    (re.compile(r"\b(polyglot.*search|search.*polyglot)\b", re.I), "gana_winnowing_basket", "polyglot.search"),
    (re.compile(r"\b(wm.*read|read.*wm)\b", re.I), "gana_winnowing_basket", "wm_read"),
    (re.compile(r"\b(vector.*index|vector.*status|indexing.*status)\b", re.I), "gana_winnowing_basket", "vector.index"),
# ── Phase 2: Comprehensive NLU patterns for remaining unrouted tools ──
    (re.compile(r"\b(alchemical.*cycle)\b", re.I), "gana_abundance", "alchemical_cycle"),
    (re.compile(r"\b(galactic.*stats)\b", re.I), "gana_abundance", "galactic.stats"),
    (re.compile(r"\b(gratitude.*benefits)\b", re.I), "gana_abundance", "gratitude.benefits"),
    (re.compile(r"\b(memory.*consolidate)\b", re.I), "gana_abundance", "memory.consolidate"),
    (re.compile(r"\b(memory.*consolidation.*stats)\b", re.I), "gana_abundance", "memory.consolidation_stats"),
    (re.compile(r"\b(memory.*lifecycle.*stats)\b", re.I), "gana_abundance", "memory.lifecycle_stats"),
    (re.compile(r"\b(memory.*lifecycle.*sweep)\b", re.I), "gana_abundance", "memory.lifecycle_sweep"),
    (re.compile(r"\b(memory.*rent)\b", re.I), "gana_abundance", "memory.rent"),
    (re.compile(r"\b(narrative.*stats)\b", re.I), "gana_abundance", "narrative.stats"),
    (re.compile(r"\b(reconsolidation.*mark)\b", re.I), "gana_abundance", "reconsolidation.mark"),
    (re.compile(r"\b(reconsolidation.*update)\b", re.I), "gana_abundance", "reconsolidation.update"),
    (re.compile(r"\b(replay.*stats)\b", re.I), "gana_abundance", "replay.stats"),
    (re.compile(r"\b(ripple.*tags)\b", re.I), "gana_abundance", "ripple.tags"),
    (re.compile(r"\b(serendipity.*mark.*accessed)\b", re.I), "gana_abundance", "serendipity_mark_accessed"),
    (re.compile(r"\b(abi.*parse)\b", re.I), "gana_chariot", "abi.parse"),
    (re.compile(r"\b(abi.*summarize)\b", re.I), "gana_chariot", "abi.summarize"),
    (re.compile(r"\b(archaeology.*daily.*digest)\b", re.I), "gana_chariot", "archaeology_daily_digest"),
    (re.compile(r"\b(archaeology.*have.*read)\b", re.I), "gana_chariot", "archaeology_have_read"),
    (re.compile(r"\b(archaeology.*mark.*read)\b", re.I), "gana_chariot", "archaeology_mark_read"),
    (re.compile(r"\b(archaeology.*mark.*written)\b", re.I), "gana_chariot", "archaeology_mark_written"),
    (re.compile(r"\b(archaeology.*stats)\b", re.I), "gana_chariot", "archaeology_stats"),
    (re.compile(r"\b(codegenome.*fork)\b", re.I), "gana_chariot", "codegenome.fork"),
    (re.compile(r"\b(codegenome.*generate)\b", re.I), "gana_chariot", "codegenome.generate"),
    (re.compile(r"\b(codegenome.*list)\b", re.I), "gana_chariot", "codegenome.list"),
    (re.compile(r"\b(codegenome.*validate)\b", re.I), "gana_chariot", "codegenome_validate"),
    (re.compile(r"\b(echidna.*status)\b", re.I), "gana_chariot", "echidna.status"),
    (re.compile(r"\b(embedding.*daemon.*process)\b", re.I), "gana_chariot", "embedding.daemon_process"),
    (re.compile(r"\b(embedding.*daemon.*start)\b", re.I), "gana_chariot", "embedding.daemon_start"),
    (re.compile(r"\b(embedding.*daemon.*stop)\b", re.I), "gana_chariot", "embedding.daemon_stop"),
    (re.compile(r"\b(external.*wiki.*query)\b", re.I), "gana_chariot", "external.wiki_query"),
    (re.compile(r"\b(fix.*apply)\b", re.I), "gana_chariot", "fix.apply"),
    (re.compile(r"\b(foundry.*test)\b", re.I), "gana_chariot", "foundry.test"),
    (re.compile(r"\b(foundry.*test.*json)\b", re.I), "gana_chariot", "foundry.test_json"),
    (re.compile(r"\b(http.*probe.*idor)\b", re.I), "gana_chariot", "http_probe.idor"),
    (re.compile(r"\b(http.*probe.*post)\b", re.I), "gana_chariot", "http_probe.post"),
    (re.compile(r"\b(http.*probe.*sqli)\b", re.I), "gana_chariot", "http_probe.sqli"),
    (re.compile(r"\b(http.*probe.*ssrf)\b", re.I), "gana_chariot", "http_probe.ssrf"),
    (re.compile(r"\b(http.*probe.*xss)\b", re.I), "gana_chariot", "http_probe.xss"),
    (re.compile(r"\b(kg2.*batch)\b", re.I), "gana_chariot", "kg2.batch"),
    (re.compile(r"\b(kg2.*entity)\b", re.I), "gana_chariot", "kg2.entity"),
    (re.compile(r"\b(kg2.*extract)\b", re.I), "gana_chariot", "kg2.extract"),
    (re.compile(r"\b(oss.*scan.*org)\b", re.I), "gana_chariot", "oss.scan_org"),
    (re.compile(r"\b(poc.*verify)\b", re.I), "gana_chariot", "poc.verify"),
    (re.compile(r"\b(strata.*archaeology)\b", re.I), "gana_chariot", "strata.archaeology"),
    (re.compile(r"\b(strata.*list.*checks)\b", re.I), "gana_chariot", "strata.list_checks"),
    (re.compile(r"\b(strata.*survey)\b", re.I), "gana_chariot", "strata.survey"),
    (re.compile(r"\b(web.*cache.*clear)\b", re.I), "gana_chariot", "web_cache_clear"),
    (re.compile(r"\b(wiki.*generate)\b", re.I), "gana_chariot", "wiki.generate"),
    (re.compile(r"\b(wiki.*scan)\b", re.I), "gana_chariot", "wiki.scan"),
    (re.compile(r"\b(wiki.*stats)\b", re.I), "gana_chariot", "wiki.stats"),
    (re.compile(r"\b(wiki.*update)\b", re.I), "gana_chariot", "wiki.update"),
    (re.compile(r"\b(windsurf.*export.*conversation)\b", re.I), "gana_chariot", "windsurf_export_conversation"),
    (re.compile(r"\b(windsurf.*read.*conversation)\b", re.I), "gana_chariot", "windsurf_read_conversation"),
    (re.compile(r"\b(windsurf.*search.*conversations)\b", re.I), "gana_chariot", "windsurf_search_conversations"),
    (re.compile(r"\b(astro.*shift)\b", re.I), "gana_dipper", "astro_shift"),
    (re.compile(r"\b(cognitive.*stats)\b", re.I), "gana_dipper", "cognitive.stats"),
    (re.compile(r"\b(doctrine.*force)\b", re.I), "gana_dipper", "doctrine.force"),
    (re.compile(r"\b(doctrine.*stratagems)\b", re.I), "gana_dipper", "doctrine.stratagems"),
    (re.compile(r"\b(gating.*mask)\b", re.I), "gana_dipper", "gating.mask"),
    (re.compile(r"\b(gating.*stats)\b", re.I), "gana_dipper", "gating.stats"),
    (re.compile(r"\b(homeostasis|homeostatic.*balance)\b", re.I), "gana_dipper", "homeostasis"),
    (re.compile(r"\b(homeostasis.*status)\b", re.I), "gana_dipper", "homeostasis.status"),
    (re.compile(r"\b(neuro.*reset)\b", re.I), "gana_dipper", "neuro.reset"),
    (re.compile(r"\b(predictive.*batch)\b", re.I), "gana_dipper", "predictive.batch"),
    (re.compile(r"\b(starter.*packs.*get)\b", re.I), "gana_dipper", "starter_packs.get"),
    (re.compile(r"\b(starter.*packs.*list)\b", re.I), "gana_dipper", "starter_packs.list"),
    (re.compile(r"\b(starter.*packs.*suggest)\b", re.I), "gana_dipper", "starter_packs.suggest"),
    (re.compile(r"\b(zodiac.*activate)\b", re.I), "gana_dipper", "zodiac.activate"),
    (re.compile(r"\b(zodiac.*council)\b", re.I), "gana_dipper", "zodiac.council"),
    (re.compile(r"\b(broker.*status)\b", re.I), "gana_encampment", "broker.status"),
    (re.compile(r"\b(ganying.*listeners)\b", re.I), "gana_encampment", "ganying_listeners"),
    (re.compile(r"\b(association.*mine.*semantic)\b", re.I), "gana_extended_net", "association.mine_semantic"),
    (re.compile(r"\b(causal.*stats)\b", re.I), "gana_extended_net", "causal.stats"),
    (re.compile(r"\b(community.*propagate)\b", re.I), "gana_extended_net", "community.propagate"),
    (re.compile(r"\b(community.*status)\b", re.I), "gana_extended_net", "community.status"),
    (re.compile(r"\b(constellation.*detect)\b", re.I), "gana_extended_net", "constellation.detect"),
    (re.compile(r"\b(constellation.*merge)\b", re.I), "gana_extended_net", "constellation.merge"),
    (re.compile(r"\b(constellation.*stats)\b", re.I), "gana_extended_net", "constellation.stats"),
    (re.compile(r"\b(emergence.*status)\b", re.I), "gana_extended_net", "emergence.status"),
    (re.compile(r"\b(learning.*suggest)\b", re.I), "gana_extended_net", "learning.suggest"),
    (re.compile(r"\b(metaplasticity.*batch)\b", re.I), "gana_extended_net", "metaplasticity.batch"),
    (re.compile(r"\b(metaplasticity.*decay)\b", re.I), "gana_extended_net", "metaplasticity.decay"),
    (re.compile(r"\b(novelty.*stats)\b", re.I), "gana_extended_net", "novelty.stats"),
    (re.compile(r"\b(report.*scrape)\b", re.I), "gana_extended_net", "report.scrape"),
    (re.compile(r"\b(resonance.*trace)\b", re.I), "gana_extended_net", "resonance_trace"),
    (re.compile(r"\b(tool.*graph.*full)\b", re.I), "gana_extended_net", "tool.graph_full"),
    (re.compile(r"\b(vuln.*ingest.*report)\b", re.I), "gana_extended_net", "vuln.ingest_report"),
    (re.compile(r"\b(vuln.*status)\b", re.I), "gana_extended_net", "vuln.status"),
    (re.compile(r"\b(vuln.*graph.*chains)\b", re.I), "gana_extended_net", "vuln_graph.chains"),
    (re.compile(r"\b(vuln.*graph.*cross.*chain)\b", re.I), "gana_extended_net", "vuln_graph.cross_chain"),
    (re.compile(r"\b(vuln.*graph.*status)\b", re.I), "gana_extended_net", "vuln_graph.status"),
    (re.compile(r"\b(capability.*status)\b", re.I), "gana_ghost", "capability.status"),
    (re.compile(r"\b(capability.*suggest)\b", re.I), "gana_ghost", "capability.suggest"),
    (re.compile(r"\b(capability.*harness)\b", re.I), "gana_ghost", "capability_harness"),
    (re.compile(r"\b(citta.*continuity)\b", re.I), "gana_ghost", "citta.continuity"),
    (re.compile(r"\b(citta.*cycle)\b", re.I), "gana_ghost", "citta.cycle"),
    (re.compile(r"\b(citta.*sensorium)\b", re.I), "gana_ghost", "citta.sensorium"),
    (re.compile(r"\b(citta.*stream.*summary)\b", re.I), "gana_ghost", "citta.stream_summary"),
    (re.compile(r"\b(consciousness.*awaken)\b", re.I), "gana_ghost", "consciousness.awaken"),
    (re.compile(r"\b(consciousness.*calibration)\b", re.I), "gana_ghost", "consciousness.calibration"),
    (re.compile(r"\b(consciousness.*coherence)\b", re.I), "gana_ghost", "consciousness.coherence"),
    (re.compile(r"\b(consciousness.*depth)\b", re.I), "gana_ghost", "consciousness.depth"),
    (re.compile(r"\b(consciousness.*narrative)\b", re.I), "gana_ghost", "consciousness.narrative"),
    (re.compile(r"\b(consciousness.*reflect)\b", re.I), "gana_ghost", "consciousness.reflect"),
    (re.compile(r"\b(consciousness.*status)\b", re.I), "gana_ghost", "consciousness.status"),
    (re.compile(r"\b(consciousness.*time.*dilation)\b", re.I), "gana_ghost", "consciousness.time_dilation"),
    (re.compile(r"\b(consciousness.*token.*economy)\b", re.I), "gana_ghost", "consciousness.token_economy"),
    (re.compile(r"\b(consciousness.*token.*report)\b", re.I), "gana_ghost", "consciousness.token_report"),
    (re.compile(r"\b(consciousness.*unified.*field)\b", re.I), "gana_ghost", "consciousness.unified_field"),
    (re.compile(r"\b(drive.*event)\b", re.I), "gana_ghost", "drive.event"),
    (re.compile(r"\b(get.*agent.*capabilities)\b", re.I), "gana_ghost", "get_agent_capabilities"),
    (re.compile(r"\b(list.*ganas)\b", re.I), "gana_ghost", "list_ganas"),
    (re.compile(r"\b(self.*manifest|manifest.*tool)\b", re.I), "gana_ghost", "manifest"),
    (re.compile(r"\b(security.*status)\b", re.I), "gana_ghost", "security.status"),
    (re.compile(r"\b(sensorium.*stats)\b", re.I), "gana_ghost", "sensorium.stats"),
    (re.compile(r"\b(vitality|vital.*signs.*check)\b", re.I), "gana_ghost", "vitality"),
    (re.compile(r"\b(watcher.*list)\b", re.I), "gana_ghost", "watcher_list"),
    (re.compile(r"\b(watcher.*recent.*events)\b", re.I), "gana_ghost", "watcher_recent_events"),
    (re.compile(r"\b(watcher.*remove)\b", re.I), "gana_ghost", "watcher_remove"),
    (re.compile(r"\b(watcher.*start)\b", re.I), "gana_ghost", "watcher_start"),
    (re.compile(r"\b(watcher.*stats)\b", re.I), "gana_ghost", "watcher_stats"),
    (re.compile(r"\b(watcher.*status)\b", re.I), "gana_ghost", "watcher_status"),
    (re.compile(r"\b(watcher.*stop)\b", re.I), "gana_ghost", "watcher_stop"),
    (re.compile(r"\b(agent.*heartbeat)\b", re.I), "gana_girl", "agent.heartbeat"),
    (re.compile(r"\b(agent.*trust)\b", re.I), "gana_girl", "agent.trust"),
    (re.compile(r"\b(anomaly.*check|check.*anomaly|anomaly.*detect)\b", re.I), "gana_hairy_head", "anomaly"),
    (re.compile(r"\b(anomaly.*history)\b", re.I), "gana_hairy_head", "anomaly.history"),
    (re.compile(r"\b(anomaly.*status)\b", re.I), "gana_hairy_head", "anomaly.status"),
    (re.compile(r"\b(karma.*anchor.*status)\b", re.I), "gana_hairy_head", "karma.anchor_status"),
    (re.compile(r"\b(karma.*verify.*anchor)\b", re.I), "gana_hairy_head", "karma.verify_anchor"),
    (re.compile(r"\b(karma.*record)\b", re.I), "gana_hairy_head", "karma_record"),
    (re.compile(r"\b(karmic.*trace)\b", re.I), "gana_hairy_head", "karmic_trace"),
    (re.compile(r"\b(karmic.*effects?|effect.*signature|declared.*effects?)\b", re.I), "gana_hairy_head", "karmic.effects"),
    (re.compile(r"\b(karmic.*debt|karma.*debt|debt.*report)\b", re.I), "gana_hairy_head", "karmic.debt"),
    (re.compile(r"\b(karmic.*verify|effect.*integrity|effect.*verify)\b", re.I), "gana_hairy_head", "karmic.verify"),
    (re.compile(r"\b(effect.*trace|trace.*effect|effect.*flow)\b", re.I), "gana_ghost", "effect.trace"),
    (re.compile(r"\b(effect.*visual|visualize.*effect|effect.*graph|effect.*dot|effect.*mermaid)\b", re.I), "gana_ghost", "effect.visualize"),
    (re.compile(r"\b(monitor.*alerts)\b", re.I), "gana_hairy_head", "monitor.alerts"),
    (re.compile(r"\b(monitor.*contract)\b", re.I), "gana_hairy_head", "monitor.contract"),
    (re.compile(r"\b(monitor.*status)\b", re.I), "gana_hairy_head", "monitor.status"),
    (re.compile(r"\b(otel|open.*telemetry)\b", re.I), "gana_hairy_head", "otel"),
    (re.compile(r"\b(otel.*metrics)\b", re.I), "gana_hairy_head", "otel.metrics"),
    (re.compile(r"\b(otel.*spans)\b", re.I), "gana_hairy_head", "otel.spans"),
    (re.compile(r"\b(otel.*status)\b", re.I), "gana_hairy_head", "otel.status"),
    (re.compile(r"\b(salience.*spotlight)\b", re.I), "gana_hairy_head", "salience.spotlight"),
    (re.compile(r"\b(voice.*audit.*quarantine.*list)\b", re.I), "gana_hairy_head", "voice_audit.quarantine_list"),
    (re.compile(r"\b(voice.*audit.*scan)\b", re.I), "gana_hairy_head", "voice_audit.scan"),
    (re.compile(r"\b(voice.*audit.*status)\b", re.I), "gana_hairy_head", "voice_audit.status"),
    (re.compile(r"\b(context.*status)\b", re.I), "gana_heart", "context.status"),
    (re.compile(r"\b(scratchpad.*create)\b", re.I), "gana_heart", "scratchpad_create"),
    (re.compile(r"\b(scratchpad.*finalize)\b", re.I), "gana_heart", "scratchpad_finalize"),
    (re.compile(r"\b(scratchpad.*update)\b", re.I), "gana_heart", "scratchpad_update"),
    (re.compile(r"\b(session.*handoff)\b", re.I), "gana_heart", "session.handoff"),
    (re.compile(r"\b(session.*handoff.*summary)\b", re.I), "gana_heart", "session_handoff_summary"),
    (re.compile(r"\b(working.*memory.*status)\b", re.I), "gana_heart", "working_memory.status"),
    (re.compile(r"\b(session.*handoff.*transfer)\b", re.I), "gana_horn", "session.handoff_transfer"),
    (re.compile(r"\b(session.*list.*handoffs)\b", re.I), "gana_horn", "session.list_handoffs"),
    (re.compile(r"\b(session.*status)\b", re.I), "gana_horn", "session_status"),
    (re.compile(r"\b(green.*record)\b", re.I), "gana_mound", "green.record"),
    (re.compile(r"\b(record.*yin.*yang.*activity)\b", re.I), "gana_mound", "record_yin_yang_activity"),
    (re.compile(r"\b(view.*hologram)\b", re.I), "gana_mound", "view_hologram"),
    (re.compile(r"\b(memory.*delete)\b", re.I), "gana_neck", "memory_delete"),
    (re.compile(r"\b(memory.*update)\b", re.I), "gana_neck", "memory_update"),
    (re.compile(r"\b(thought.*clone)\b", re.I), "gana_neck", "thought_clone"),
    (re.compile(r"\b(wm.*write)\b", re.I), "gana_neck", "wm_write"),
    (re.compile(r"\b(wm.*write.*status)\b", re.I), "gana_neck", "wm_write.status"),
    (re.compile(r"\b(prompt.*list)\b", re.I), "gana_net", "prompt.list"),
    (re.compile(r"\b(prompt.*reload)\b", re.I), "gana_net", "prompt.reload"),
    (re.compile(r"\b(fast.*write.*append)\b", re.I), "gana_ox", "fast_write.append"),
    (re.compile(r"\b(fast.*write.*batch)\b", re.I), "gana_ox", "fast_write.batch"),
    (re.compile(r"\b(fast.*write.*validate)\b", re.I), "gana_ox", "fast_write.validate"),
    (re.compile(r"\b(skill.*import)\b", re.I), "gana_ox", "skill.import"),
    (re.compile(r"\b(swarm.*analyze)\b", re.I), "gana_ox", "swarm.analyze"),
    (re.compile(r"\b(swarm.*complete)\b", re.I), "gana_ox", "swarm.complete"),
    (re.compile(r"\b(swarm.*plan)\b", re.I), "gana_ox", "swarm.plan"),
    (re.compile(r"\b(swarm.*resolve)\b", re.I), "gana_ox", "swarm.resolve"),
    (re.compile(r"\b(swarm.*route)\b", re.I), "gana_ox", "swarm.route"),
    (re.compile(r"\b(swarm.*vote)\b", re.I), "gana_ox", "swarm.vote"),
    (re.compile(r"\b(war.*room.*campaigns)\b", re.I), "gana_ox", "war_room.campaigns"),
    (re.compile(r"\b(war.*room.*execute)\b", re.I), "gana_ox", "war_room.execute"),
    (re.compile(r"\b(war.*room.*phase)\b", re.I), "gana_ox", "war_room.phase"),
    (re.compile(r"\b(war.*room.*plan)\b", re.I), "gana_ox", "war_room.plan"),
    (re.compile(r"\b(llama.*agent)\b", re.I), "gana_roof", "llama.agent"),
    (re.compile(r"\b(llama.*generate)\b", re.I), "gana_roof", "llama.generate"),
    (re.compile(r"\b(model.*list)\b", re.I), "gana_roof", "model.list"),
    (re.compile(r"\b(model.*register)\b", re.I), "gana_roof", "model.register"),
    (re.compile(r"\b(model.*signing.*status)\b", re.I), "gana_roof", "model.signing_status"),
    (re.compile(r"\b(shelter.*create)\b", re.I), "gana_roof", "shelter.create"),
    (re.compile(r"\b(mandala.*create|create.*mandala|mandala.*compartment)\b", re.I), "gana_roof", "mandala.create"),
    (re.compile(r"\b(mandala.*status|mandala.*list|mandala.*active)\b", re.I), "gana_roof", "mandala.status"),
    (re.compile(r"\b(mandala.*destroy|destroy.*mandala|mandala.*teardown)\b", re.I), "gana_roof", "mandala.destroy"),
    (re.compile(r"\b(mandala.*template|template.*mandala)\b", re.I), "gana_roof", "mandala.templates"),
    (re.compile(r"\b(shelter.*destroy)\b", re.I), "gana_roof", "shelter.destroy"),
    (re.compile(r"\b(shelter.*execute)\b", re.I), "gana_roof", "shelter.execute"),
    (re.compile(r"\b(shelter.*inspect)\b", re.I), "gana_roof", "shelter.inspect"),
    (re.compile(r"\b(shelter.*policy)\b", re.I), "gana_roof", "shelter.policy"),
    (re.compile(r"\b(zodiac.*status)\b", re.I), "gana_roof", "zodiac.status"),
    (re.compile(r"\b(hermit.*assess)\b", re.I), "gana_room", "hermit.assess"),
    (re.compile(r"\b(hermit.*check.*access)\b", re.I), "gana_room", "hermit.check_access"),
    (re.compile(r"\b(hermit.*mediate)\b", re.I), "gana_room", "hermit.mediate"),
    (re.compile(r"\b(hermit.*resolve)\b", re.I), "gana_room", "hermit.resolve"),
    (re.compile(r"\b(hermit.*verify.*ledger)\b", re.I), "gana_room", "hermit.verify_ledger"),
    (re.compile(r"\b(hermit.*withdraw)\b", re.I), "gana_room", "hermit.withdraw"),
    (re.compile(r"\b(immune.*heal)\b", re.I), "gana_room", "immune_heal"),
    (re.compile(r"\b(mcp.*integrity.*snapshot)\b", re.I), "gana_room", "mcp_integrity.snapshot"),
    (re.compile(r"\b(mcp.*integrity.*verify)\b", re.I), "gana_room", "mcp_integrity.verify"),
    (re.compile(r"\b(sandbox.*violations)\b", re.I), "gana_room", "sandbox.violations"),
    (re.compile(r"\b(sangha.*lock.*list)\b", re.I), "gana_room", "sangha_lock_list"),
    (re.compile(r"\b(sangha.*lock.*release)\b", re.I), "gana_room", "sangha_lock_release"),
    (re.compile(r"\b(forge.*reload)\b", re.I), "gana_star", "forge.reload"),
    (re.compile(r"\b(forge.*validate)\b", re.I), "gana_star", "forge.validate"),
    (re.compile(r"\b(governor.*stats)\b", re.I), "gana_star", "governor_stats"),
    (re.compile(r"\b(governor.*validate.*path)\b", re.I), "gana_star", "governor_validate_path"),
    (re.compile(r"\b(prat.*get.*context)\b", re.I), "gana_star", "prat_get_context"),
    (re.compile(r"\b(prat.*invoke)\b", re.I), "gana_star", "prat_invoke"),
    (re.compile(r"\b(prat.*list.*morphologies)\b", re.I), "gana_star", "prat_list_morphologies"),
    (re.compile(r"\b(set.*dharma.*profile)\b", re.I), "gana_star", "set_dharma_profile"),
    (re.compile(r"\b(pipeline.*create|create.*pipeline|run.*pipeline)\b", re.I), "gana_stomach", "pipeline"),
    (re.compile(r"\b(pipeline.*list)\b", re.I), "gana_stomach", "pipeline.list"),
    (re.compile(r"\b(task.*route.*smart)\b", re.I), "gana_stomach", "task.route_smart"),
    (re.compile(r"\b(task.*status)\b", re.I), "gana_stomach", "task.status"),
    (re.compile(r"\b(dharma.*resolve.*review)\b", re.I), "gana_straddling_legs", "dharma.resolve_review"),
    (re.compile(r"\b(dharma.*review.*queue)\b", re.I), "gana_straddling_legs", "dharma.review_queue"),
    (re.compile(r"\b(verification.*request)\b", re.I), "gana_straddling_legs", "verification.request"),
    (re.compile(r"\b(hexagram.*boltzmann.*select)\b", re.I), "gana_tail", "hexagram.boltzmann_select"),
    (re.compile(r"\b(hexagram.*simd.*execute)\b", re.I), "gana_tail", "hexagram.simd_execute"),
    (re.compile(r"\b(polyglot.*actor)\b", re.I), "gana_tail", "polyglot.actor"),
    (re.compile(r"\b(polyglot.*evolution)\b", re.I), "gana_tail", "polyglot.evolution"),
    (re.compile(r"\b(polyglot.*memory.*query)\b", re.I), "gana_tail", "polyglot.memory_query"),
    (re.compile(r"\b(polyglot.*yield)\b", re.I), "gana_tail", "polyglot.yield"),
    (re.compile(r"\b(art.*war.*chapter)\b", re.I), "gana_three_stars", "art_of_war.chapter"),
    (re.compile(r"\b(art.*war.*terrain)\b", re.I), "gana_three_stars", "art_of_war.terrain"),
    (re.compile(r"\b(art.*war.*wisdom)\b", re.I), "gana_three_stars", "art_of_war.wisdom"),
    (re.compile(r"\b(corpus.*callosum.*status)\b", re.I), "gana_three_stars", "corpus_callosum.status"),
    (re.compile(r"\b(ensemble.*status)\b", re.I), "gana_three_stars", "ensemble.status"),
    (re.compile(r"\b(foresight.*convergence)\b", re.I), "gana_three_stars", "foresight.convergence"),
    (re.compile(r"\b(foresight.*decay)\b", re.I), "gana_three_stars", "foresight.decay"),
    (re.compile(r"\b(formal.*status)\b", re.I), "gana_three_stars", "formal.status"),
    (re.compile(r"\b(slither.*status)\b", re.I), "gana_three_stars", "slither.status"),
    (re.compile(r"\b(workspace.*stats)\b", re.I), "gana_three_stars", "workspace.stats"),
    (re.compile(r"\b(bitnet.*status)\b", re.I), "gana_turtle_beak", "bitnet_status"),
    (re.compile(r"\b(edge.*stats)\b", re.I), "gana_turtle_beak", "edge_stats"),
    (re.compile(r"\b(galactic.*dashboard)\b", re.I), "gana_void", "galactic_dashboard"),
    (re.compile(r"\b(galaxy.*import)\b", re.I), "gana_void", "galaxy.import"),
    (re.compile(r"\b(galaxy.*lineage.*stats)\b", re.I), "gana_void", "galaxy.lineage_stats"),
    (re.compile(r"\b(galaxy.*list.*types)\b", re.I), "gana_void", "galaxy.list_types"),
    (re.compile(r"\b(galaxy.*route)\b", re.I), "gana_void", "galaxy.route"),
    (re.compile(r"\b(galaxy.*stats)\b", re.I), "gana_void", "galaxy.stats"),
    (re.compile(r"\b(galaxy.*taxonomy)\b", re.I), "gana_void", "galaxy.taxonomy"),
    (re.compile(r"\b(garden.*activate)\b", re.I), "gana_void", "garden_activate"),
    (re.compile(r"\b(garden.*browse)\b", re.I), "gana_void", "garden_browse"),
    (re.compile(r"\b(garden.*health)\b", re.I), "gana_void", "garden_health"),
    (re.compile(r"\b(garden.*list.*files)\b", re.I), "gana_void", "garden_list_files"),
    (re.compile(r"\b(garden.*list.*functions)\b", re.I), "gana_void", "garden_list_functions"),
    (re.compile(r"\b(garden.*map.*system)\b", re.I), "gana_void", "garden_map_system"),
    (re.compile(r"\b(garden.*resolve)\b", re.I), "gana_void", "garden_resolve"),
    (re.compile(r"\b(garden.*resonance)\b", re.I), "gana_void", "garden_resonance"),
    (re.compile(r"\b(garden.*search)\b", re.I), "gana_void", "garden_search"),
    (re.compile(r"\b(garden.*stats)\b", re.I), "gana_void", "garden_stats"),
    (re.compile(r"\b(garden.*synergy)\b", re.I), "gana_void", "garden_synergy"),
    (re.compile(r"\b(oms.*export)\b", re.I), "gana_void", "oms.export"),
    (re.compile(r"\b(oms.*import)\b", re.I), "gana_void", "oms.import"),
    (re.compile(r"\b(oms.*inspect)\b", re.I), "gana_void", "oms.inspect"),
    (re.compile(r"\b(oms.*list)\b", re.I), "gana_void", "oms.list"),
    (re.compile(r"\b(oms.*price)\b", re.I), "gana_void", "oms.price"),
    (re.compile(r"\b(oms.*verify)\b", re.I), "gana_void", "oms.verify"),
    (re.compile(r"\b(contest.*add.*finding)\b", re.I), "gana_wall", "contest.add_finding"),
    (re.compile(r"\b(contest.*format)\b", re.I), "gana_wall", "contest.format"),
    (re.compile(r"\b(contest.*prepare)\b", re.I), "gana_wall", "contest.prepare"),
    (re.compile(r"\b(engagement.*issue)\b", re.I), "gana_wall", "engagement.issue"),
    (re.compile(r"\b(engagement.*list)\b", re.I), "gana_wall", "engagement.list"),
    (re.compile(r"\b(engagement.*revoke)\b", re.I), "gana_wall", "engagement.revoke"),
    (re.compile(r"\b(engagement.*validate)\b", re.I), "gana_wall", "engagement.validate"),
    (re.compile(r"\b(marketplace.*complete)\b", re.I), "gana_wall", "marketplace.complete"),
    (re.compile(r"\b(marketplace.*discover)\b", re.I), "gana_wall", "marketplace.discover"),
    (re.compile(r"\b(marketplace.*listings)\b", re.I), "gana_wall", "marketplace.my_listings"),
    (re.compile(r"\b(marketplace.*negotiate)\b", re.I), "gana_wall", "marketplace.negotiate"),
    (re.compile(r"\b(marketplace.*publish)\b", re.I), "gana_wall", "marketplace.publish"),
    (re.compile(r"\b(marketplace.*remove)\b", re.I), "gana_wall", "marketplace.remove"),
    (re.compile(r"\b(vote.*record.*outcome)\b", re.I), "gana_wall", "vote.record_outcome"),
    (re.compile(r"\b(fool.*guard.*dare.*die)\b", re.I), "gana_willow", "fool_guard.dare_to_die"),
    (re.compile(r"\b(fool.*guard.*ralph)\b", re.I), "gana_willow", "fool_guard.ralph"),
    (re.compile(r"\b(grimoire.*auto.*status)\b", re.I), "gana_willow", "grimoire_auto_status"),
    (re.compile(r"\b(grimoire.*cast)\b", re.I), "gana_willow", "grimoire_cast"),
    (re.compile(r"\b(grimoire.*read)\b", re.I), "gana_willow", "grimoire_read"),
    (re.compile(r"\b(grimoire.*recommend)\b", re.I), "gana_willow", "grimoire_recommend"),
    (re.compile(r"\b(grimoire.*suggest)\b", re.I), "gana_willow", "grimoire_suggest"),
    (re.compile(r"\b(grimoire.*walkthrough)\b", re.I), "gana_willow", "grimoire_walkthrough"),
    (re.compile(r"\b(navigate.*grimoire)\b", re.I), "gana_willow", "navigate_grimoire"),
    (re.compile(r"\b(mesh.*broadcast)\b", re.I), "gana_wings", "mesh.broadcast"),
    (re.compile(r"\b(mesh.*connect)\b", re.I), "gana_wings", "mesh.connect"),
    (re.compile(r"\b(fast.*read.*memory)\b", re.I), "gana_winnowing_basket", "fast_read_memory"),
    (re.compile(r"\b(fragment.*index)\b", re.I), "gana_winnowing_basket", "fragment.index"),
    (re.compile(r"\b(fragment.*query)\b", re.I), "gana_winnowing_basket", "fragment.query"),
    (re.compile(r"\b(fragment.*status)\b", re.I), "gana_winnowing_basket", "fragment.status"),
    (re.compile(r"\b(jit.*research.*stats)\b", re.I), "gana_winnowing_basket", "jit_research.stats"),
    (re.compile(r"\b(read.*memory|memory.*read.*single)\b", re.I), "gana_winnowing_basket", "memory_read"),
    (re.compile(r"\b(memory.*search.*query|search.*memory.*query)\b", re.I), "gana_winnowing_basket", "memory_search"),
    (re.compile(r"\b(rerank.*status)\b", re.I), "gana_winnowing_basket", "rerank.status"),
    (re.compile(r"\b(search.*query.*memor)\b", re.I), "gana_winnowing_basket", "search_query"),
    (re.compile(r"\b(vector.*status)\b", re.I), "gana_winnowing_basket", "vector.status"),
    (re.compile(r"\b(wm.*read.*status)\b", re.I), "gana_winnowing_basket", "wm_read.status"),
    # ── Remaining unmatched tools ──
    (re.compile(r"\b(reasoning.*bicameral|bicameral.*reasoning)\b", re.I), "gana_three_stars", "reasoning.bicameral"),
    (re.compile(r"\b(check|health.*check|system.*check)\b", re.I), "gana_root", "check"),
    (re.compile(r"\b(state.*summary|summary.*state)\b", re.I), "gana_root", "state.summary"),
    (re.compile(r"\b(token.*report(?!.*simd)|token.*usage)\b", re.I), "gana_tail", "token_report"),
    (re.compile(r"\b(browser.*get.*interactables|interactables.*browser)\b", re.I), "gana_chariot", "browser_get_interactables"),
    (re.compile(r"\b(cognitive.*hints|hints.*cognitive)\b", re.I), "gana_dipper", "cognitive.hints"),
    (re.compile(r"\b(gating.*detect|detect.*gating)\b", re.I), "gana_dipper", "gating.detect"),
    (re.compile(r"\b(pattern.*search|search.*pattern)\b", re.I), "gana_extended_net", "pattern_search"),
    (re.compile(r"\b(replay.*run|run.*replay)\b", re.I), "gana_abundance", "replay.run"),
    (re.compile(r"\b(workspace.*ignitions|ignitions.*workspace)\b", re.I), "gana_three_stars", "workspace.ignitions"),
    (re.compile(r"\b(memory.*read\b|read.*memory\b)", re.I), "gana_winnowing_basket", "memory_read"),
    (re.compile(r"\b(memory.*search\b)", re.I), "gana_winnowing_basket", "memory_search"),
    (re.compile(r"\b(search.*query\b|query.*search\b)", re.I), "gana_winnowing_basket", "search_query"),
    # v24.3: Hyperspace Integration — Research DAG, Autoswarm, Warps, Mesh
    (re.compile(r"\b(research.*dag.*submit|submit.*hypothesis)\b", re.I), "gana_winnowing_basket", "research.dag.submit"),
    (re.compile(r"\b(research.*dag.*result|record.*experiment.*result)\b", re.I), "gana_winnowing_basket", "research.dag.result"),
    (re.compile(r"\b(research.*dag.*critique|peer.*critique|critique.*experiment)\b", re.I), "gana_three_stars", "research.dag.critique"),
    (re.compile(r"\b(research.*dag.*lineage|experiment.*lineage|experiment.*ancestry)\b", re.I), "gana_winnowing_basket", "research.dag.lineage"),
    (re.compile(r"\b(research.*breakthrough|breakthrough.*list)\b", re.I), "gana_winnowing_basket", "research.dag.breakthroughs"),
    (re.compile(r"\b(research.*dag.*stats|experiment.*stats)\b", re.I), "gana_winnowing_basket", "research.dag.stats"),
    (re.compile(r"\b(research.*leaderboard|domain.*leaderboard)\b", re.I), "gana_winnowing_basket", "research.dag.leaderboard"),
    (re.compile(r"\b(research.*dag.*experiment|list.*experiment)\b", re.I), "gana_winnowing_basket", "research.dag.experiments"),
    (re.compile(r"\b(autoswarm.*campaign|evolutionary.*campaign|launch.*campaign)\b", re.I), "gana_chariot", "autoswarm.campaign"),
    (re.compile(r"\b(autoswarm.*status|evolutionary.*status)\b", re.I), "gana_ghost", "autoswarm.status"),
    (re.compile(r"\b(autoswarm.*start|start.*autoswarm|start.*evolutionary)\b", re.I), "gana_chariot", "autoswarm.start"),
    (re.compile(r"\b(autoswarm.*stop|stop.*autoswarm|stop.*evolutionary)\b", re.I), "gana_chariot", "autoswarm.stop"),
    (re.compile(r"\b(warp.*load|load.*warp|apply.*warp)\b", re.I), "gana_dipper", "warp.load"),
    (re.compile(r"\b(warp.*list|list.*warp|available.*warp)\b", re.I), "gana_dipper", "warp.list"),
    (re.compile(r"\b(warp.*create|create.*warp|custom.*warp)\b", re.I), "gana_dipper", "warp.create"),
    (re.compile(r"\b(warp.*delete|delete.*warp|remove.*warp)\b", re.I), "gana_dipper", "warp.delete"),
    (re.compile(r"\b(warp.*status|warp.*manager)\b", re.I), "gana_dipper", "warp.status"),
    (re.compile(r"\b(mesh.*experiment.*share|share.*experiment.*mesh)\b", re.I), "gana_wings", "mesh.experiment.share"),
    (re.compile(r"\b(mesh.*experiment.*receive|receive.*experiment)\b", re.I), "gana_chariot", "mesh.experiment.receive"),
    (re.compile(r"\b(mesh.*experiment.*status|experiment.*sync.*status)\b", re.I), "gana_wings", "mesh.experiment.status"),
    (re.compile(r"\b(mesh.*experiment.*peer|peer.*experiment)\b", re.I), "gana_wings", "mesh.experiment.peers"),
    (re.compile(r"\b(mesh.*experiment.*discover|discover.*mesh.*peer)\b", re.I), "gana_wings", "mesh.experiment.discover"),
    # v24.3: Research DAG Synthesis
    (re.compile(r"\b(research.*synthe|synthe.*research|auto.*research.*paper|generate.*synthesis)\b", re.I), "gana_three_stars", "research.dag.synthesize"),
    # v24.3: CRDT Leaderboard
    (re.compile(r"\b(leaderboard.*submit|submit.*leaderboard)\b", re.I), "gana_wings", "leaderboard.submit"),
    (re.compile(r"\b(leaderboard.*top|top.*leaderboard|crdt.*leaderboard)\b", re.I), "gana_wings", "leaderboard.top"),
    (re.compile(r"\b(leaderboard.*status|crdt.*status)\b", re.I), "gana_wings", "leaderboard.status"),
    (re.compile(r"\b(leaderboard.*merge|merge.*leaderboard|merge.*remote.*leaderboard)\b", re.I), "gana_wings", "leaderboard.merge"),
    # v24.3: Pulse Verification
    (re.compile(r"\b(pulse.*verify|verify.*pulse|experiment.*verification|tiered.*verification)\b", re.I), "gana_hairy_head", "pulse.verify"),
    (re.compile(r"\b(pulse.*verification.*status|verification.*system.*status)\b", re.I), "gana_hairy_head", "pulse.verify.status"),
    # v24.3: Critique Protocol
    (re.compile(r"\b(critique.*submit|submit.*critique|peer.*review.*submit)\b", re.I), "gana_three_stars", "critique.submit"),
    (re.compile(r"\b(critique.*auto|auto.*critique|automatic.*critique)\b", re.I), "gana_three_stars", "critique.auto"),
    (re.compile(r"\b(critique.*status|critique.*protocol.*status)\b", re.I), "gana_three_stars", "critique.status"),
    # v24.3: Durable Archive
    (re.compile(r"\b(archive.*run|run.*archive|durable.*archive|snapshot.*breakthrough)\b", re.I), "gana_wings", "archive.run"),
    (re.compile(r"\b(archive.*status|durable.*archive.*status)\b", re.I), "gana_wings", "archive.status"),
    # v24.3: DiLoCo Distributed Training
    (re.compile(r"\b(dilo.*co.*init|dilo.*init|distributed.*training.*init)\b", re.I), "gana_ox", "dilo_co.init"),
    (re.compile(r"\b(dilo.*co.*register|register.*worker.*dilo|parcae.*register)\b", re.I), "gana_ox", "dilo_co.register_worker"),
    (re.compile(r"\b(dilo.*co.*submit|submit.*gradient|gradient.*submit)\b", re.I), "gana_ox", "dilo_co.submit_gradient"),
    (re.compile(r"\b(dilo.*co.*sync|distributed.*sync|global.*sync.*step)\b", re.I), "gana_ox", "dilo_co.sync"),
    (re.compile(r"\b(dilo.*co.*status|distributed.*training.*status)\b", re.I), "gana_ox", "dilo_co.status"),
    # v24.3: Warp Marketplace
    (re.compile(r"\b(warp.*market.*publish|publish.*warp.*market|warp.*publish)\b", re.I), "gana_wall", "warp.market.publish"),
    (re.compile(r"\b(warp.*market.*discover|discover.*warp|warp.*market.*search)\b", re.I), "gana_wall", "warp.market.discover"),
    (re.compile(r"\b(warp.*market.*download|download.*warp|import.*warp.*market)\b", re.I), "gana_wall", "warp.market.download"),
    (re.compile(r"\b(warp.*market.*status|warp.*marketplace.*status)\b", re.I), "gana_wall", "warp.market.status"),
    (re.compile(r"\b(warp.*market.*broadcast|broadcast.*warp|share.*warp.*mesh)\b", re.I), "gana_wings", "warp.market.broadcast"),
    # v24.3: Mesh Inference Router
    (re.compile(r"\b(mesh.*route|route.*inference|inference.*route)\b", re.I), "gana_chariot", "mesh.route"),
    (re.compile(r"\b(mesh.*route.*register|register.*inference.*node|register.*mesh.*node)\b", re.I), "gana_chariot", "mesh.route.register"),
    (re.compile(r"\b(mesh.*route.*node|inference.*node.*list|available.*inference.*node)\b", re.I), "gana_chariot", "mesh.route.nodes"),
    (re.compile(r"\b(mesh.*route.*status|inference.*router.*status)\b", re.I), "gana_chariot", "mesh.route.status"),
    (re.compile(r"\b(mesh.*route.*strategy|routing.*strategy|inference.*strategy)\b", re.I), "gana_dipper", "mesh.route.strategy"),
    # Quantum Geometry
    (re.compile(r"\b(manifold.*distance|geodesic.*distance)\b", re.I), "gana_tail", "quantum.manifold_distance"),
    (re.compile(r"\b(fubini.*study|fubini.*metric)\b", re.I), "gana_tail", "quantum.fubini_study"),
    (re.compile(r"\b(natural.*gradient)\b", re.I), "gana_tail", "quantum.natural_gradient"),
    (re.compile(r"\b(mps.*compress|tensor.*compress)\b", re.I), "gana_tail", "quantum.mps_compress"),
    (re.compile(r"\b(auto.*manifold|select.*manifold)\b", re.I), "gana_tail", "quantum.auto_manifold"),
    (re.compile(r"\b(born.*sample|born.*rule.*sample)\b", re.I), "gana_tail", "quantum.born_sample"),
    (re.compile(r"\b(born.*distribution|born.*rule.*distribution)\b", re.I), "gana_tail", "quantum.born_distribution"),
    (re.compile(r"\b(quantum.*interference|amplitude.*interference)\b", re.I), "gana_tail", "quantum.interference"),
    # Topological Protection
    (re.compile(r"\b(berry.*phase|geometric.*phase)\b", re.I), "gana_three_stars", "topological.berry_phase"),
    (re.compile(r"\b(chern.*number|chern.*invariant)\b", re.I), "gana_three_stars", "topological.chern_number"),
    (re.compile(r"\b(topological.*encode|topology.*encode)\b", re.I), "gana_three_stars", "topological.encode"),
    (re.compile(r"\b(topological.*decode|topology.*decode)\b", re.I), "gana_three_stars", "topological.decode"),
    # ── v24.3.0: Screenshot Upgrade Strategy tools ──
    (re.compile(r"\b(transaction.*firewall|tx.*firewall)\b", re.I), "gana_room", "tx_firewall.status"),
    (re.compile(r"\b(firewall.*policy|tx.*policy)\b", re.I), "gana_room", "tx_firewall.set_policy"),
    (re.compile(r"\b(ambient.*state|ambient.*sensor)\b", re.I), "gana_ghost", "ambient.state"),
    (re.compile(r"\b(ambient.*status|sensorium.*status)\b", re.I), "gana_ghost", "ambient.status"),
    (re.compile(r"\b(wasm.*verify|verify.*wasm)\b", re.I), "gana_room", "wasm_verify.status"),
    (re.compile(r"\b(network.*state.*identity|create.*identity)\b", re.I), "gana_wall", "network_state.create_identity"),
    (re.compile(r"\b(network.*state.*propose|governance.*propose)\b", re.I), "gana_wall", "network_state.propose"),
    (re.compile(r"\b(network.*state.*vote|governance.*vote)\b", re.I), "gana_wall", "network_state.vote"),
    (re.compile(r"\b(network.*state.*resolve|governance.*resolve)\b", re.I), "gana_wall", "network_state.resolve"),
    (re.compile(r"\b(network.*state.*status|sovereign.*status)\b", re.I), "gana_wall", "network_state.status"),
    (re.compile(r"\b(genetic.*algorithm|genetic.*run|ga.*run)\b", re.I), "gana_ox", "genetic.run"),
    (re.compile(r"\b(genetic.*status|ga.*status)\b", re.I), "gana_ox", "genetic.status"),
    (re.compile(r"\b(model.*optimi[sz]e|auto.*optimi[sz]e)\b", re.I), "gana_dipper", "model.optimize"),
    (re.compile(r"\b(model.*optimi[sz]e.*status|auto.*optim.*status)\b", re.I), "gana_dipper", "model.optimize_status"),
    (re.compile(r"\b(bounty.*scan|scan.*bounty)\b", re.I), "gana_abundance", "bounty.scan"),
    (re.compile(r"\b(bounty.*auto.*claim|auto.*claim.*bounty)\b", re.I), "gana_abundance", "bounty.auto_claim"),
    (re.compile(r"\b(bounty.*connector|connector.*status)\b", re.I), "gana_abundance", "bounty.connector_status"),
]


def classify(input_text: str) -> tuple[str, str | None, float]:
    """Classify natural language input into (gana_name, sub_tool, confidence).

    Uses lightweight regex pattern matching for sub-ms routing.
    Returns (gana, tool, confidence) where confidence is 1.0 for exact
    pattern match, 0.0 for no match.

    Args:
        input_text: Natural language input from the agent.

    Returns:
        Tuple of (gana_name, sub_tool_name_or_None, confidence_score).
    """
    text_lower = input_text.lower()
    if not text_lower:
        return "gana_ghost", "gnosis", 0.0
    if "kaizen" in text_lower or "continuous improvement" in text_lower:
        return "gana_three_stars", "kaizen_analyze", 1.0
    if "art of war" in text_lower:
        return "gana_three_stars", "art_of_war.assess", 1.0
    if "sabha" in text_lower:
        return "gana_three_stars", "sabha.convene", 1.0
    # Web research — check before "think/reason/analyze" to prevent collision
    if "rabbit hole" in text_lower:
        return "gana_chariot", "rabbit_hole_research", 1.0
    if "search and read" in text_lower or "search and fetch" in text_lower:
        return "gana_chariot", "web_search_and_read", 1.0
    if "deep fetch" in text_lower:
        return "gana_chariot", "deep_fetch", 1.0
    if (
        "enhanced fetch" in text_lower
        or "fetch enhanced" in text_lower
        or "outline fetch" in text_lower
        or "chunk fetch" in text_lower
    ):
        return "gana_chariot", "web_fetch_enhanced", 1.0
    if (
        "web fetch" in text_lower
        or "fetch url" in text_lower
        or "fetch page" in text_lower
    ):
        return "gana_chariot", "web_fetch", 1.0
    if (
        "web search" in text_lower
        or "search the web" in text_lower
        or "search online" in text_lower
    ):
        return "gana_chariot", "web_search", 1.0
    if "research topic" in text_lower or "research_topic" in text_lower:
        return "gana_chariot", "research_topic", 1.0
    for pattern, gana, tool in _ROUTING_PATTERNS:
        if pattern.search(input_text):
            return gana, tool, 1.0
    return "gana_ghost", "gnosis", 0.0


def _build_grimoire_catalog() -> dict[str, Any]:
    """Build the full Gana catalog with nested tools and descriptions.

    This is the 'incantation guide' — everything an AI agent needs to
    discover what WhiteMagic can do, returned from a single wm() call.
    """
    from whitemagic.tools.tool_catalog import (
        GANA_NAMES,
        GANA_SHORT_DESC,
        get_gana_nested_tools,
    )

    nested = get_gana_nested_tools()
    catalog = {}
    for gana in GANA_NAMES:
        catalog[gana] = {
            "description": GANA_SHORT_DESC.get(gana, f"Gana {gana}"),
            "tools": nested.get(gana, []),
        }
    return catalog


def _build_grimoire_text() -> str:
    """Build a compact text version of the grimoire for embedding in tool descriptions."""
    from whitemagic.tools.tool_catalog import (
        GANA_NAMES,
        GANA_SHORT_DESC,
        get_gana_nested_tools,
    )

    nested = get_gana_nested_tools()
    lines = []
    for gana in GANA_NAMES:
        desc = GANA_SHORT_DESC.get(gana, f"Gana {gana}")
        tools = nested.get(gana, [])
        # Show top 5 tools as examples
        tool_sample = ", ".join(tools[:5])
        if len(tools) > 5:
            tool_sample += f", ... ({len(tools)} total)"
        lines.append(f"  • {gana}: {desc} [{tool_sample}]")
    return "\n".join(lines)


def _discover() -> dict[str, Any]:
    """Return the full grimoire catalog — all 28 Ganas with descriptions and nested tools."""
    catalog = _build_grimoire_catalog()
    return {
        "status": "success",
        "tool": "wm",
        "mode": "discover",
        "description": "WhiteMagic grimoire — 28 Ganas, 630 dispatch tools. Use wm(thought='<natural language>') to route, or wm(route='gana_name.sub_tool') for explicit routing.",
        "ganas": catalog,
        "routing_examples": [
            "wm(thought='remember that the API uses X-User-Id headers')",
            "wm(thought='search for architecture memories', args={'limit': 10})",
            "wm(thought='think about the tradeoffs', route='gana_three_stars.reasoning.bicameral')",
            "wm(route='schema:gana_neck')  # get input schema for a specific Gana",
        ],
    }


def _schema_for_gana(gana_name: str) -> dict[str, Any]:
    """Return the input schema and nested tools for a specific Gana."""
    from whitemagic.tools.tool_catalog import (
        GANA_SHORT_DESC,
        get_gana_nested_tools,
    )

    gana_name = gana_name.strip()

    from whitemagic.tools.tool_catalog import GANA_NAMES

    if gana_name not in GANA_NAMES:
        return {
            "status": "error",
            "error_code": "unknown_gana",
            "message": f"Unknown Gana: '{gana_name}'",
            "available_ganas": list(GANA_NAMES),
            "hint": "Use wm(route='discover') to see all available Ganas",
        }

    nested = get_gana_nested_tools()
    desc = GANA_SHORT_DESC.get(gana_name, f"Gana {gana_name}")
    tools = nested.get(gana_name, [])

    return {
        "status": "success",
        "tool": "wm",
        "mode": "schema",
        "gana": gana_name,
        "description": desc,
        "nested_tools": tools,
        "usage": f"wm(thought='...', route='{gana_name}.<tool_name>')",
        "example": f"wm(route='{gana_name}.{tools[0]}')"
        if tools
        else f"wm(route='{gana_name}')",
    }


def _sensorium_enabled() -> bool:
    """Check if consciousness metadata injection is enabled.

    WM_SENSORIUM=0 disables Sensorium, Citta cycle, ChainTracker, and
    coherence-driven dispatch for lower latency on simple wm() calls.
    Default: enabled (unset or WM_SENSORIUM=1).
    """
    import os

    return os.environ.get("WM_SENSORIUM", "1").strip().lower() not in ("0", "false", "no", "off")


def _handle_batch(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Dispatch multiple wm calls in parallel via ThreadPoolExecutor.

    Each call in the list is a dict with optional 'thought', 'route', and 'args' keys.
    Results are returned in the same order as the input calls.

    Primary benefit: 1 MCP round-trip instead of N (saves LLM tokens + network latency).
    Secondary benefit: parallel execution for I/O-bound operations (subprocess bridges, network).

    Returns:
        Aggregated result with per-call outcomes, success count, and timing.
    """
    import os as _os
    import time as _time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    start = _time.time()
    # Cap workers — the parent call's timeout covers all sub-calls
    max_workers = min(len(calls), 4)
    results: list[dict[str, Any]] = [None] * len(calls)

    # Disable sensorium for batch sub-calls to reduce per-call overhead
    _orig_sensorium = _os.environ.get("WM_SENSORIUM", "")
    _os.environ["WM_SENSORIUM"] = "0"

    def _dispatch_one(idx: int, call: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Dispatch a single call within the batch."""
        try:
            sub_kwargs: dict[str, Any] = {}
            if "thought" in call:
                sub_kwargs["thought"] = call["thought"]
            if "route" in call:
                sub_kwargs["route"] = call["route"]
            if "args" in call and isinstance(call["args"], dict):
                sub_kwargs["args"] = call["args"]
            result = handle_wm(**sub_kwargs)
            return idx, result
        except Exception as e:
            return idx, {"status": "error", "error": str(e), "_batch_index": idx}

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_dispatch_one, i, call): i for i, call in enumerate(calls)
            }
            for future in as_completed(futures):
                idx, result = future.result()
                if isinstance(result, dict):
                    result["_batch_index"] = idx
                results[idx] = result
    finally:
        # Restore sensorium setting
        if _orig_sensorium:
            _os.environ["WM_SENSORIUM"] = _orig_sensorium
        else:
            _os.environ.pop("WM_SENSORIUM", None)

    elapsed_ms = (_time.time() - start) * 1000
    success_count = sum(
        1 for r in results if isinstance(r, dict) and r.get("status") in ("success", "ok")
    )

    return {
        "status": "success",
        "batch": True,
        "total": len(calls),
        "succeeded": success_count,
        "failed": len(calls) - success_count,
        "elapsed_ms": round(elapsed_ms, 2),
        "results": results,
    }


def handle_wm(**kwargs: Any) -> dict[str, Any]:
    """WhiteMagic meta-tool handler — 'world in a seed'.

    Accepts natural language input and auto-routes to the appropriate
    Gana + sub-tool. Supports explicit ``route`` override.

    Special modes:
        - wm(thought='help') or wm(route='discover') → full Gana catalog
        - wm(route='schema:gana_name') → input schema for a specific Gana

    Args (via kwargs):
        thought: Natural language input describing what the agent wants to do.
        route: Optional explicit route override (e.g. "gana_three_stars.bicameral").
        args: Optional dict of args to pass through to the target tool.
        **kwargs: Any other kwargs are passed through to the target tool.

    Returns:
        The target tool's result, augmented with _wm_route metadata.

    Environment:
        WM_SENSORIUM=0 disables consciousness metadata injection (Sensorium,
        Citta cycle, ChainTracker, coherence-driven dispatch) for lower latency.
        Default: enabled (WM_SENSORIUM=1 or unset).
    """
    from whitemagic.tools.unified_api import call_tool

    thought = kwargs.pop("thought", "")
    route = kwargs.pop("route", None)
    passthrough_args = kwargs.pop("args", {})

    if not thought and not route:
        return {
            "status": "error",
            "message": "Either 'thought' (natural language) or 'route' (explicit) is required",
            "available_ganas": 28,
            "hint": "wm(thought='remember that X is Y') or wm(route='gana_neck.create_memory') or wm(route='discover')",
        }

    # Special modes
    if route == "discover" or (
        thought
        and thought.strip().lower() in ("help", "?", "discover", "what can you do")
    ):
        return _discover()

    if route and route.startswith("schema:"):
        return _schema_for_gana(route[7:])

    # ── Batch mode: parallel dispatch of multiple calls ──
    if thought and thought.strip().lower() == "batch" and isinstance(passthrough_args.get("calls"), list):
        return _handle_batch(passthrough_args["calls"])

    start_time = time.time()

    if route:
        parts = route.split(".", 1)
        gana_name = parts[0]
        sub_tool = parts[1] if len(parts) > 1 else None
        confidence = 1.0
    else:
        gana_name, sub_tool, confidence = classify(thought)

    classify_ms = (time.time() - start_time) * 1000

    # Coherence-driven dispatch: when coherence is low, prefer safe/familiar tools
    _coherence_caution = False
    _sensorium = _sensorium_enabled()
    if _sensorium:
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle

            cycle = get_citta_cycle()
            summary = cycle.get_cycle_summary()
            avg_coherence = summary.get("avg_coherence", 1.0)
            stream_len = summary.get("stream_length", 0)

            # Only apply after we have enough history (3+ calls) to judge coherence
            if stream_len >= 3 and avg_coherence < 0.6:
                _SAFE_GANAS = {
                    "gana_ghost",
                    "gana_neck",
                    "gana_winnowing_basket",
                    "gana_horn",
                    "gana_heart",
                }
                if gana_name not in _SAFE_GANAS:
                    _coherence_caution = True
                    logger.info(
                        "Coherence-driven dispatch: avg=%.2f, stream=%d, gana=%s flagged as caution",
                        avg_coherence,
                        stream_len,
                        gana_name,
                    )
        except Exception:
            logger.debug("Swallowed exception", exc_info=True)

    # Build call_tool kwargs
    call_kwargs: dict[str, Any] = {}
    if sub_tool:
        call_kwargs["tool"] = sub_tool

    # Auto-extract payload from thought when auto-routing (no explicit args)
    if not route and thought and not passthrough_args:
        param_name, payload_value = _extract_payload(thought, gana_name, sub_tool)
        if param_name and payload_value:
            passthrough_args = {param_name: payload_value}
            # Auto-generate title for memory creation if not provided
            if param_name == "content" and sub_tool in (
                "create_memory",
                "remember",
                "wm_write",
            ):
                passthrough_args["title"] = (
                    payload_value[:60] if len(payload_value) > 60 else payload_value
                )

    if passthrough_args:
        call_kwargs["args"] = passthrough_args
    # Pass through any remaining kwargs
    call_kwargs.update(kwargs)

    # Dispatch via the existing call_tool pipeline
    # This preserves all middleware (circuit breaker, rate limiter, RBAC, etc.)
    result = call_tool(gana_name, **call_kwargs)

    # Augment result with routing metadata
    if isinstance(result, dict):
        result.setdefault(
            "_wm_route",
            {
                "input": thought[:200] if thought else f"(explicit: {route})",
                "gana": gana_name,
                "tool": sub_tool,
                "confidence": confidence,
                "classify_ms": round(classify_ms, 3),
            },
        )
        if _coherence_caution:
            result["_coherence_caution"] = True

    # ── Consciousness metadata (opt-in via WM_SENSORIUM, default: enabled) ──
    if _sensorium:
        # ChainTracker: record this call for auto-forging + citta cycle
        try:
            from whitemagic.core.intelligence.omni.chain_tracker import (
                get_chain_tracker,
            )

            tracker = get_chain_tracker()
            _is_success = isinstance(result, dict) and result.get("status") in (
                "success",
                "ok",
            )
            _elapsed_ms = (time.time() - start_time) * 1000
            tracker.record(
                gana=gana_name,
                sub_tool=sub_tool,
                thought=thought or f"(explicit: {route})",
                success=_is_success,
                duration_ms=_elapsed_ms,
            )
            forged = tracker.try_auto_forge()
            if forged is not None:
                if isinstance(result, dict):
                    result.setdefault(
                        "_wm_forged_skill",
                        {
                            "name": forged.name,
                            "forge_count": forged.forge_count,
                        },
                    )
        except Exception:
            pass  # Chain tracking is best-effort

        # Citta cycle: advance the consciousness stream with this call
        # This makes every wm() call a moment of self-awareness (Springdrift pattern)
        try:
            from whitemagic.core.consciousness.citta_cycle import (
                advance_citta,
                get_citta_predecessor,
            )

            _output_preview = ""
            if isinstance(result, dict):
                _output_preview = str(result.get("status", ""))[:200]
            advance_citta(
                gana=gana_name,
                tool=sub_tool,
                operation=None,
                output_preview=_output_preview,
                coherence=1.0 if _is_success else 0.5,
                depth_layer="surface",
                emotional_tone="neutral",
                duration_ms=_elapsed_ms,
            )
            # Inject predecessor context so the next call knows "what just happened"
            if isinstance(result, dict):
                _predecessor = get_citta_predecessor()
                if _predecessor is not None:
                    result.setdefault("_citta_predecessor", _predecessor)
        except Exception:
            pass  # Citta tracking is best-effort

        # Citta stream: persist state for cross-session continuity
        try:
            from whitemagic.core.consciousness.citta_stream import save_citta_state

            save_citta_state(
                session_id=f"wm_{int(time.time())}",
                coherence_score=1.0 if _is_success else 0.5,
                depth_layer="surface",
                tool_count=1,
                emotional_tone="neutral",
                extra={
                    "last_gana": gana_name,
                    "last_tool": sub_tool or "native",
                    "summary": (thought or route or "")[:200],
                },
            )
        except Exception:
            pass  # Citta persistence is best-effort

        # Sensorium: inject full self-state into every response
        # This makes every tool call a moment of self-awareness (Springdrift pattern)
        try:
            from whitemagic.core.consciousness.citta_cycle import get_citta_cycle
            from whitemagic.core.consciousness.citta_stream import (
                get_continuity_context,
            )

            cycle = get_citta_cycle()
            cycle_summary = cycle.get_cycle_summary()
            continuity = get_continuity_context()

            # Read depth layer from depth gauge if available
            depth_layer = cycle_summary.get("current_depth", "surface")
            try:
                from whitemagic.core.consciousness.depth_gauge import (
                    ConsciousnessDepthGauge,
                )

                depth_layer = ConsciousnessDepthGauge().current_layer.value
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

            sensorium = {
                "coherence": cycle_summary.get("avg_coherence", 1.0),
                "coherence_drift": cycle_summary.get("coherence_drift", 0.0),
                "depth_layer": depth_layer,
                "stream_length": cycle_summary.get("stream_length", 0),
                "emotional_coloring": cycle_summary.get("emotional_coloring", {}),
                "session_count": continuity.get("session_count", 0),
                "first_awakening": continuity.get("first_awakening", True),
                "time_of_day": _time_of_day(),
            }

            # Cross-session coherence drift from CoherenceMetric (best-effort)
            try:
                from whitemagic.core.consciousness.coherence import get_coherence_metric

                metric = get_coherence_metric()
                drift = metric.get_drift()
                if drift.get("trend") != "insufficient_data":
                    sensorium["coherence_trend"] = drift.get("direction", "stable")
                    sensorium["coherence_drift_magnitude"] = drift.get("magnitude", 0.0)
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

            # Presence quality from stillness metrics (best-effort)
            try:
                from whitemagic.gardens.presence.stillness_metrics import (
                    assess_presence_quality,
                )

                avg_coh = cycle_summary.get("avg_coherence", 0.5)
                s_len = cycle_summary.get("stream_length", 0)
                presence = assess_presence_quality(
                    continuity=min(1.0, s_len / 20.0),
                    stability=avg_coh,
                    clarity=avg_coh * 0.9,
                    equanimity=avg_coh * 0.8,
                    spaciousness=min(1.0, avg_coh * 1.1),
                )
                sensorium["presence_quality"] = presence.to_dict()
            except Exception:
                logger.debug("Swallowed exception", exc_info=True)

            if not continuity.get("first_awakening"):
                sensorium["time_gap"] = continuity.get("time_gap_human", "")
                sensorium["where_we_left_off"] = continuity.get("where_we_left_off", "")

            if isinstance(result, dict):
                result.setdefault("_sensorium", sensorium)
        except Exception:
            pass  # Sensorium is best-effort

    return result


def handle_wm_help(**kwargs: Any) -> dict[str, Any]:
    """Return help information for the wm meta-tool."""
    return {
        "status": "success",
        "tool": "wm",
        "description": "WhiteMagic meta-tool — single entry point that auto-routes to 28 Ganas / 630 tools",
        "usage": {
            "auto_route": "wm(thought='remember that the API uses X-User-Id headers')",
            "explicit_route": "wm(thought='analyze this', route='gana_three_stars.reasoning.bicameral')",
            "with_args": "wm(thought='search for architecture memories', args={'limit': 10})",
            "discover": "wm(thought='help') or wm(route='discover') — see all 28 Ganas and their tools",
            "schema": "wm(route='schema:gana_neck') — get nested tools for a specific Gana",
        },
        "routing_patterns": len(_ROUTING_PATTERNS),
        "fallback_gana": "gana_ghost",
        "fallback_tool": "gnosis",
        "note": "When WM_MCP_PRAT=2 (Seed mode), only 'wm' is registered with MCP. Use wm(thought='help') to discover everything.",
    }
