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
    # Memory search / recall
    (
        re.compile(r"\b(search|find|recall|look up|query).*memor", re.I),
        "gana_winnowing_basket",
        "search_memories",
    ),
    (re.compile(r"\brecall\b", re.I), "gana_winnowing_basket", "search_memories"),
    (
        re.compile(r"\b(list|show).*memor", re.I),
        "gana_winnowing_basket",
        "list_memories",
    ),
    (re.compile(r"\b(read|get).*memor", re.I), "gana_winnowing_basket", "read_memory"),
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
    (
        re.compile(r"\b(context pack|session context|handoff)\b", re.I),
        "gana_heart",
        "context.pack",
    ),
    # Reasoning / thinking
    (
        re.compile(r"\b(reason|think|analyze|deliberate|ponder)\b", re.I),
        "gana_three_stars",
        "reasoning.bicameral",
    ),
    (
        re.compile(r"\b(ensemble|consensus|multiple models?|vote)\b", re.I),
        "gana_three_stars",
        "ensemble.query",
    ),
    (
        re.compile(r"\b(kaizen|improve|continuous improvement|quality)\b", re.I),
        "gana_three_stars",
        "kaizen_analyze",
    ),
    (
        re.compile(r"\b(foresight|predict|forecast|decay|convergence)\b", re.I),
        "gana_three_stars",
        "foresight.analyze",
    ),
    (
        re.compile(r"\b(council|sabha|quadrant|collective decision)\b", re.I),
        "gana_three_stars",
        "sabha.convene",
    ),
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
    (
        re.compile(r"\b(health|diagnose|root.*cause|system.*status)\b", re.I),
        "gana_root",
        "health_report",
    ),
    (re.compile(r"\b(ship|deploy|release|version)\b", re.I), "gana_root", "ship.check"),
    (
        re.compile(r"\b(state|paths|summary).*system", re.I),
        "gana_root",
        "state.summary",
    ),
    # Introspection / self-model
    (
        re.compile(r"\b(capabilit|manifest|telemetry|metrics)", re.I),
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
        re.compile(r"\b(graph|topology|network|connections)\b", re.I),
        "gana_ghost",
        "graph_topology",
    ),
    (re.compile(r"\b(watcher|monitor|observe)\b", re.I), "gana_ghost", "watcher_add"),
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
        re.compile(r"\b(invoke.*skill|run.*skill|replay.*skill|use.*skill)\b", re.I),
        "gana_ox",
        "skill.invoke",
    ),
    (
        re.compile(r"\b(seed.*skills|plant.*skills|initialize.*skills)\b", re.I),
        "gana_ox",
        "skill.seed",
    ),
    # Session management
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
    (
        re.compile(r"\b(galax|universe|namespace|switch.*context)", re.I),
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
    # Dreams / consolidation
    (
        re.compile(r"\b(dream|consolidat|sleep|cycle)\b", re.I),
        "gana_abundance",
        "dream",
    ),
    (
        re.compile(r"\b(serendipity|surprise.*connection|lucky)\b", re.I),
        "gana_abundance",
        "serendipity_surface",
    ),
    # Ethics / governance
    (
        re.compile(r"\b(ethics?|dharma|moral|consent|boundar)\b", re.I),
        "gana_straddling_legs",
        "evaluate_ethics",
    ),
    (
        re.compile(r"\b(harmony|balance|wu.xing|five.element)\b", re.I),
        "gana_straddling_legs",
        "wu_xing_balance",
    ),
    (
        re.compile(r"\b(verify|attest|verification)\b", re.I),
        "gana_straddling_legs",
        "verification.status",
    ),
    # Governance / forge
    (
        re.compile(r"\b(governor|governance|drift|budget|dharma.*profile)\b", re.I),
        "gana_star",
        "governor_validate",
    ),
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
        re.compile(r"\b(cascade|pattern.*list|hexagram)\b", re.I),
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
        re.compile(r"\b(security|alert|threat|intrusion)\b", re.I),
        "gana_room",
        "security.alerts",
    ),
    # Resilience / rate limiting
    (
        re.compile(r"\b(rate.limit|throttle|circuit.*breaker|grimoire|spell)\b", re.I),
        "gana_willow",
        "rate_limiter.stats",
    ),
    (
        re.compile(r"\b(oracle|divine|cast|fortune)\b", re.I),
        "gana_willow",
        "cast_oracle",
    ),
    # Community / sangha
    (
        re.compile(r"\b(sangha|chat|community|broadcast|publish)\b", re.I),
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
        re.compile(r"\b(export|deploy|mesh|broadcast.*memory)\b", re.I),
        "gana_wings",
        "export_memories",
    ),
    (re.compile(r"\b(audit|verify.*export)\b", re.I), "gana_wings", "audit.export"),
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
        re.compile(r"\b(metric|track|hologram|cache|yin.yang)\b", re.I),
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
    if "sabha" in text_lower or "council" in text_lower:
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
    if (
        "think" in text_lower
        or "reason" in text_lower
        or "analyze" in text_lower
        or "deliberate" in text_lower
        or "ponder" in text_lower
    ):
        return "gana_three_stars", "reasoning.bicameral", 1.0
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
        "description": "WhiteMagic grimoire — 28 Ganas, 490 dispatch tools. Use wm(thought='<natural language>') to route, or wm(route='gana_name.sub_tool') for explicit routing.",
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

    # ChainTracker: record this call for auto-forging + citta cycle
    try:
        from whitemagic.core.intelligence.omni.chain_tracker import get_chain_tracker

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
        from whitemagic.core.consciousness.citta_stream import get_continuity_context

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
        "description": "WhiteMagic meta-tool — single entry point that auto-routes to 28 Ganas / 490 tools",
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
