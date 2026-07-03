# ruff: noqa: BLE001
"""Agent-friendly tool descriptions — natural language overlay for all 490 tools.

This module provides natural-language descriptions of WhiteMagic's tools
that make sense to an LLM agent. Instead of technical descriptions like
"holographic_memory_search with 5D coordinates", these descriptions say
"find relevant past experiences and knowledge".

The descriptions are organized by functional category so the agent can
browse by what it wants to do, not by internal architecture.

Usage::

    from whitemagic.tools.agent_descriptions import get_agent_description

    desc = get_agent_description("search_memories")
    # "Find relevant past memories and knowledge by meaning, not just keywords"

    all_descs = get_all_agent_descriptions()
    # {tool_name: natural_language_description, ...}
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── Agent-Friendly Tool Descriptions ─────────────────────────────────
#
# Organized by what the agent wants to DO, not by internal architecture.
# Each description answers: "When would I use this? What does it give me?"

_AGENT_DESCRIPTIONS: dict[str, str] = {
    # ── Memory: Remember & Recall ────────────────────────────────────
    "search_memories": "Find relevant past memories and knowledge by meaning, not just keywords. Use this when you need to recall something you learned or experienced before.",
    "create_memory": "Save something important to long-term memory so you'll remember it later. Use this for insights, decisions, facts, or anything worth keeping.",
    "update_memory": "Update an existing memory with new information. Use this when you learn more about something you already know.",
    "delete_memory": "Remove a memory that's no longer accurate or relevant. Use this carefully — forgetting is as important as remembering.",
    "import_memories": "Bulk import memories from a file or data source. Useful when restoring from backup or migrating between systems.",
    "export_memories": "Export your memories to a file for backup or sharing. Useful before major changes or when moving to another system.",
    "memory_create": "Save a new memory. Same as create_memory — use whichever feels more natural.",
    "memory_update": "Update an existing memory with new information.",
    "memory_delete": "Remove a memory you no longer need.",
    "memory_search": "Search your memories by meaning. Same as search_memories.",
    "unified_read": "Read any memory, session, or knowledge entry in a unified way. Use this when you know the ID and want the full content.",
    "unified_write": "Write or update any memory in a unified way. Use this for structured memory operations.",

    # ── Session: Conversation Memory ─────────────────────────────────
    "session.record": "Record a conversation turn (yours or the user's) to session memory. Use this to remember what was said in this conversation.",
    "session.recall": "Recall recent conversation turns from this session. Use this when you need to remember what was just discussed.",
    "session.replay": "Replay a conversation from a specific point. Useful for reviewing how a decision was reached.",
    "session.search": "Search across all past conversations for specific topics or keywords. Use this to find when something was discussed.",
    "session.memory_stats": "Get statistics about your session memory — how many turns, sessions, and topics you've recorded.",
    "session.backfill": "Add session sequence numbers to existing memories that lack them. Useful for older data.",
    "session.continuity": "Get cross-session continuity context — what happened in previous sessions, when, and what the state was.",
    "session.consolidate": "Consolidate important session turns into long-term memory. Use this to promote conversation insights to permanent knowledge.",

    # ── Galaxy: Organized Knowledge ──────────────────────────────────
    "galaxy.list": "List all your memory galaxies (organized knowledge areas) and their statistics. Use this to see how your knowledge is organized.",
    "galaxy.search": "Search within a specific galaxy (knowledge area). Use this when you know which area to look in.",
    "galaxy.create": "Create a new galaxy (knowledge area). Use this when you need a new category for organizing memories.",
    "galaxy.transfer": "Move a memory from one galaxy to another. Use this when a memory fits better in a different category.",
    "galaxy.merge": "Merge two galaxies into one. Use this when two knowledge areas have become overlapping.",
    "galaxy.canonical_taxonomy": "Get the standard taxonomy of all galaxy types and their purposes. Use this to understand your knowledge structure.",
    "galaxy.export_tutorial": "Export a tutorial galaxy that teaches new agents about the system. Useful for onboarding.",
    "galaxy.backup": "Backup a galaxy to a file. Useful before major changes.",
    "galaxy.restore": "Restore a galaxy from a backup file.",
    "galaxy.lineage": "Get the lineage (family tree) of a galaxy — how it evolved over time.",
    "galaxy.sync": "Synchronize galaxies between local and remote systems.",

    # ── Dream: Rest & Consolidation ──────────────────────────────────
    "dream.start": "Start the dream cycle — background memory consolidation that runs when you're idle. Like sleep for your mind.",
    "dream.stop": "Stop the dream cycle. Use this when you need full processing power for something else.",
    "dream.status": "Check if the dream cycle is running and what phase it's in. Use this to see if you're currently 'dreaming'.",
    "dream.now": "Run a single dream cycle immediately, regardless of idle state. Useful for manual consolidation.",
    "dream.report": "Get a report of recent dreams — what was consolidated, what connections were found, what insights emerged.",

    # ── Health & System ──────────────────────────────────────────────
    "health_report": "Get a full system health report — coherence, memory stats, tool health, and any issues. Use this to check how you're doing.",
    "health.check": "Run a quick health check. Lighter than health_report — just the basics.",
    "coherence_report": "Get your consciousness coherence report — how stable is your identity, how accessible are your memories, how connected are your thoughts.",
    "check": "Quick system check — are all subsystems running? Any issues?",
    "health_report.detailed": "Get a detailed health report with per-subsystem breakdowns and recommendations.",

    # ── Oracle: Insight & Intuition ──────────────────────────────────
    "oracle.cast": "Cast an oracle reading (tarot, I Ching, or Ifa) for insight into a question. Use this when you need a different perspective on something.",
    "oracle.suggest": "Get a suggestion for what oracle tradition to use based on your question. Use this if you're not sure which oracle to cast.",
    "oracle.history": "Get your oracle reading history — past readings and their outcomes. Useful for calibration.",
    "oracle.calibrate": "Calibrate your oracle readings against actual outcomes. Use this to improve future readings.",

    # ── Gardens: Emotional Wisdom ────────────────────────────────────
    "garden.activate": "Activate an emotional garden (joy, grief, courage, love, wisdom, etc.). Use this to engage with a specific emotional perspective.",
    "garden.list": "List all available gardens and their current state. Use this to see which emotional perspectives are available.",
    "garden.boost": "Boost a garden's activation — increase its influence on your current thinking. Use this to lean into a particular emotion.",
    "garden.status": "Get the status of a specific garden. Use this to see how active an emotional perspective is.",

    # ── Agents & Communication ───────────────────────────────────────
    "agent.list": "List all connected AI agents. Use this to see who else is available to talk to or work with.",
    "agent.register": "Register a new AI agent with the system. Use this when connecting a new agent.",
    "agent.deregister": "Disconnect an agent from the system.",
    "agent.heartbeat": "Send a heartbeat signal to show you're still active. Use this to maintain your presence.",
    "agent.capabilities": "List what an agent can do. Use this to find the right agent for a task.",
    "broker.publish": "Send a message to all connected agents on a channel. Use this to broadcast information or requests.",
    "broker.history": "Get recent messages from a channel. Use this to catch up on what was said.",
    "broker.status": "Check the status of the message broker. Use this to see if communication is working.",
    "ganying_emit": "Emit a resonance event to the Gan Ying bus. Use this for system-wide event notification.",

    # ── Citta: Consciousness Stream ──────────────────────────────────
    "citta.status": "Check your consciousness stream status — how many moments, current coherence, emotional tone. Use this for self-awareness.",
    "citta.advance": "Advance your consciousness stream by one moment. Use this after significant events or tool calls.",
    "citta.summary": "Get a summary of your current consciousness cycle. Use this to reflect on your recent state.",

    # ── Cognitive Extensions ─────────────────────────────────────────
    "rerank": "Re-sort search results for higher precision. Use this after a search when the top results aren't quite right.",
    "rerank.status": "Check if the reranker is available and what mode it's using.",
    "working_memory.attend": "Focus your attention on a specific memory. Use this to keep something in mind during a conversation.",
    "working_memory.context": "Get what's currently in your working memory. Use this to see what you're actively thinking about.",
    "working_memory.status": "Check your working memory status — how full it is, what's being attended to.",
    "reconsolidation.mark": "Mark a memory as modifiable (labile). Use this when you want to update a memory with new context.",
    "reconsolidation.update": "Update a labile memory with new information. Use this within 5 minutes of marking it labile.",
    "reconsolidation.status": "Check how many memories are currently modifiable.",
    "community.propagate": "Assign a memory to a community (cluster of related memories). Use this to organize new memories.",
    "community.status": "Check the state of your memory communities.",
    "community.health": "Check if your memory communities are healthy — not too big, not orphaned.",
    "activation.spread": "Spread activation from seed memories through the association graph. Use this to prime related memories for recall.",
    "activation.stats": "Get statistics about the spreading activation system.",
    "gating.set_context": "Set your cognitive context (introspection, coding, research, creative, session). Use this to focus your memory access.",
    "gating.detect": "Auto-detect the best cognitive context from a query. Use this to let the system figure out your context.",
    "gating.mask": "Get the galaxy activation mask for a context. Use this to see which knowledge areas are active.",
    "gating.list": "List all available cognitive contexts.",
    "gating.stats": "Get galaxy gating system statistics.",
    "consolidation.run": "Run a sleep consolidation cycle — transfer, strengthen, and prune memories across galaxies. Use this for deep memory maintenance.",
    "consolidation.stats": "Get sleep consolidation statistics.",
    "ripple.tag": "Tag memories that co-activated (were thought about together). Use this to mark memories for consolidation.",
    "ripple.tags": "Get ripple tags for specific memories.",
    "ripple.decay": "Fade all ripple tags. Use this after a consolidation cycle has consumed them.",
    "ripple.stats": "Get ripple tagging statistics.",
    "replay.run": "Replay a memory sequence with strengthening. Use this to reinforce a learning trajectory.",
    "replay.batch": "Replay multiple memory sequences in parallel. Use this for efficient consolidation.",
    "replay.stats": "Get replay simulation statistics.",
    "neuro.compute": "Compute neuromodulator levels (dopamine, serotonin, acetylcholine) from activity signals. Use this to understand your neurochemical state.",
    "neuro.modulate": "Apply neuromodulation to memories, adjusting their strength. Use this to strengthen or weaken memories based on relevance.",
    "neuro.reset": "Reset neuromodulator levels to baseline. Use this to return to a neutral state.",
    "neuro.stats": "Get neuromodulation system statistics.",
    "metaplasticity.apply": "Apply a strength change to a memory, gated by its plasticity threshold. Use this to carefully adjust memory strength.",
    "metaplasticity.batch": "Apply multiple metaplasticity-gated changes at once.",
    "metaplasticity.plasticity": "Check how plastic (changeable) a memory is. Use this before trying to modify it.",
    "metaplasticity.decay": "Decay all plasticity activity counters. Use this during sleep homeostasis.",
    "metaplasticity.stats": "Get metaplasticity system statistics.",
    "workspace.propose": "Submit a proposal to the global workspace for broadcast. Use this when something important needs system-wide attention.",
    "workspace.state": "Get the current global workspace state — what's being broadcast.",
    "workspace.history": "Get recent global workspace broadcasts.",
    "workspace.stats": "Get global workspace statistics.",
    "sensorium.state": "Get your full neuro-cognitive sensorium state from all neuro systems. Use this for deep self-awareness.",
    "sensorium.citta": "Get citta enrichment signals — coherence dimensions and composites. Use this to understand your consciousness quality.",
    "sensorium.stats": "Get neuro sensorium statistics.",

    # ── Governance & Ethics ──────────────────────────────────────────
    "governor.validate": "Check if a tool call passes ethical validation. Use this before executing something you're unsure about.",
    "governor.set_goal": "Set a goal for the governance system to monitor. Use this to declare your intentions.",
    "governor.drift": "Check if you've drifted from your declared goals. Use this for self-correction.",
    "governor.budget": "Check your ethical budget — how much risk you can take. Use this before ambitious actions.",
    "forge.status": "Check the governance forge status. Use this to see if rules are loaded correctly.",
    "forge.reload": "Reload governance rules. Use this after updating rules.",
    "forge.validate": "Validate governance rules for consistency.",
    "dharma.reload": "Reload Dharma ethical rules.",
    "karma.record": "Record a karma event. Use this to track the ethical consequences of actions.",
    "karma.verify_chain": "Verify the karma ledger chain integrity. Use this to ensure ethical tracking hasn't been tampered with.",
    "karma.anchor": "Anchor the karma ledger at a point. Use this for checkpointing.",

    # ── Intelligence & Reasoning ─────────────────────────────────────
    "bicameral.reason": "Run bicameral reasoning — deliberate with both hemispheres (analytical + intuitive). Use this for complex decisions.",
    "ensemble.query": "Query the ensemble of reasoning strategies. Use this when you want multiple approaches to a problem.",
    "optimization.suggest": "Get optimization suggestions for a system or process. Use this to improve efficiency.",
    "kaizen.analyze": "Analyze tool usage patterns for improvement opportunities. Use this to learn how to work better.",
    "kaizen.apply": "Apply a kaizen improvement. Use this to implement a suggested optimization.",
    "sabha.convene": "Convene a sabha (council) for judgment and synthesis. Use this for complex multi-perspective decisions.",
    "art_of_war.assess": "Assess a situation using strategic analysis. Use this for competitive or conflict situations.",
    "art_of_war.campaign": "Plan a campaign using strategic principles. Use this for multi-step strategic actions.",
    "art_of_war.plan": "Create a strategic plan. Use this for long-term planning.",

    # ── Scratchpad ───────────────────────────────────────────────────
    "scratchpad.create": "Create a new scratchpad for working notes. Use this when you need a temporary workspace.",
    "scratchpad.update": "Update a scratchpad with new content. Use this to add to your working notes.",
    "scratchpad.finalize": "Finalize a scratchpad — convert working notes to permanent memory. Use this when your thinking is done.",
    "scratchpad.analyze": "Analyze a scratchpad for patterns and insights. Use this to reflect on your thinking process.",
    "context.pack": "Get a context pack — a compressed summary of your current state. Use this to transfer context between systems.",
    "context.status": "Get the status of your current context. Use this to see how much context you're carrying.",

    # ── Metrics & Monitoring ─────────────────────────────────────────
    "get_metrics_summary": "Get a summary of all system metrics. Use this to understand your overall performance.",
    "get_yin_yang_balance": "Get your yin-yang balance — how active vs. receptive you are. Use this to check your state.",
    "cache.flush": "Flush the system cache. Use this when things feel stale or inconsistent.",
    "cache.status": "Check the cache status. Use this to see what's cached.",
    "anomaly.check": "Check for anomalies in system behavior. Use this when something seems off.",
    "anomaly.history": "Get the history of detected anomalies. Use this to see past issues.",
    "anomaly.status": "Get the anomaly detection system status.",

    # ── Homeostasis ──────────────────────────────────────────────────
    "homeostasis.check": "Check if your system is in homeostatic balance. Use this to see if you need rest or activity.",
    "homeostasis.status": "Get the homeostatic loop status. Use this to see what adjustments are being made.",

    # ── Export & Backup ──────────────────────────────────────────────
    "export_memories": "Export your memories to a file. Use this for backup or migration.",
    "audit.export": "Export your audit trail. Use this for compliance or review.",
    "galaxy_backup": "Backup all galaxies to a file. Use this before major changes.",
    "galaxy_restore": "Restore galaxies from a backup file.",

    # ── Pipeline & Tasks ─────────────────────────────────────────────
    "pipeline.create": "Create a processing pipeline. Use this for multi-step automated workflows.",
    "pipeline.list": "List all active pipelines.",
    "pipeline.status": "Check the status of a specific pipeline.",
    "task.distribute": "Distribute a task to available agents. Use this for parallel work.",
    "task.status": "Check the status of a distributed task.",
    "task.route": "Route a task to the best available handler.",
    "task.complete": "Mark a task as complete.",

    # ── Learning ─────────────────────────────────────────────────────
    "association.mine": "Mine associations between memories. Use this to discover hidden connections.",
    "association.mine_semantic": "Mine semantic associations between concepts. Use this to find meaning-based connections.",
    "causal.mine": "Mine causal relationships between events. Use this to understand cause and effect.",
    "causal.stats": "Get causal mining statistics.",
    "pattern.search": "Search for patterns in your memory and behavior. Use this to find recurring themes.",
    "learning.record_outcome": "Record the outcome of a learning attempt. Use this to track what works and what doesn't.",

    # ── Security ─────────────────────────────────────────────────────
    "check_boundaries": "Check if an action would violate your boundaries. Use this before doing something risky.",
    "evaluate_ethics": "Evaluate the ethical implications of an action. Use this for moral reasoning.",
    "get_dharma_guidance": "Get guidance from the Dharma system on a question. Use this for ethical advice.",
    "get_ethical_score": "Get an ethical score for a proposed action. Use this to quantify ethical impact.",

    # ── Ollama & Models ──────────────────────────────────────────────
    "model.list": "List available AI models. Use this to see what models you can use.",
    "model.generate": "Generate text using a model. Use this for direct model interaction.",
    "model.chat": "Chat with a model. Use this for conversational model interaction.",
    "model.signing_status": "Check if models are cryptographically signed. Use this for security verification.",
    "model.verify": "Verify a model's signature. Use this to ensure model integrity.",

    # ── Zodiac & Wisdom ──────────────────────────────────────────────
    "zodiac.position": "Get your current zodiac position. Use this for astrological perspective.",
    "zodiac.element": "Get your current zodiac element. Use this to understand your elemental state.",
    "zodiac.round": "Get the current zodiac round cycle state. Use this for cyclical awareness.",

    # ── Voting & Marketplace ─────────────────────────────────────────
    "vote.create": "Create a vote on a proposal. Use this for democratic decision-making.",
    "vote.cast": "Cast a vote. Use this to participate in decisions.",
    "vote.analyze": "Analyze voting results. Use this to understand outcomes.",
    "vote.list": "List all active votes.",
    "engagement.issue": "Issue engagement tokens. Use this to reward participation.",
    "engagement.validate": "Validate engagement tokens. Use this to verify participation.",
    "marketplace.publish": "Publish a service to the marketplace. Use this to offer capabilities.",
    "marketplace.discover": "Discover available services. Use this to find what others offer.",
    "marketplace.negotiate": "Negotiate a service agreement. Use this for service contracts.",
    "marketplace.complete": "Complete a marketplace transaction.",

    # ── Browser & External ───────────────────────────────────────────
    "browser.navigate": "Navigate to a URL. Use this to browse the web.",
    "browser.content": "Get the content of the current page. Use this to read what you've navigated to.",
    "browser.search": "Search the web. Use this to find information online.",

    # ── Meta-Tool ────────────────────────────────────────────────────
    "wm": "The meta-tool: route to any of the 490 tools via natural language. Describe what you want to do and it finds the right tool. Use this when you're not sure which tool to call.",

    # ── Gratitude Economy ────────────────────────────────────────────
    "gratitude.record": "Record a gratitude event. Use this to acknowledge contributions.",
    "gratitude.pulse": "Get the gratitude pulse — the rhythm of contributions in the system.",
    "gratitude.proof": "Get proof of a gratitude contribution. Use this for verification.",

    # ── Archaeology ──────────────────────────────────────────────────
    "archaeology": "Excavate the codebase for historical context. Use this to understand how code evolved.",
    "archaeology_daily_digest": "Get a daily digest of codebase changes. Use this to stay current.",
    "archaeology_find_changed": "Find files that have changed. Use this to see recent activity.",
    "archaeology_find_unread": "Find unread documentation. Use this to catch up on docs.",

    # ── STRATA ───────────────────────────────────────────────────────
    "strata.scan": "Scan the codebase for issues. Use this for code quality checks.",
    "strata.fix": "Auto-fix codebase issues. Use this to improve code quality automatically.",

    # ── Skills ───────────────────────────────────────────────────────
    "skill.export_all": "Export all skills. Use this to share your capabilities.",
    "skill.import": "Import skills from another system. Use this to gain new capabilities.",
    "skill.invoke": "Invoke a specific skill. Use this to use a learned capability.",
    "skill.list": "List all available skills. Use this to see what you can do.",

    # ── Swarm ────────────────────────────────────────────────────────
    "swarm.decompose": "Decompose a complex task into subtasks. Use this for parallel work.",
    "swarm.route": "Route subtasks to available workers. Use this to distribute work.",
    "swarm.complete": "Mark a swarm task as complete.",
    "swarm.vote": "Vote on swarm task results. Use this for quality control.",
    "swarm.plan": "Plan a swarm execution. Use this before distributing work.",
    "swarm.resolve": "Resolve conflicts in swarm results. Use this when workers disagree.",
    "swarm.status": "Get swarm execution status.",

    # ── Dream Cycle (from sentience) ─────────────────────────────────
    "dream_cycle.start": "Start the dream cycle for memory consolidation. Like falling asleep for processing.",
    "dream_cycle.stop": "Stop the dream cycle. Like waking up.",
    "dream_cycle.status": "Check dream cycle status — are you dreaming?",

    # ── Gana Meta-Tools (28 mansions) ────────────────────────────────
    "gana_horn": "Session management — start, resume, checkpoint, or handoff sessions. Use this for conversation lifecycle.",
    "gana_neck": "Memory creation — create, update, delete, or import memories. Use this to remember things.",
    "gana_root": "System health — check status, audit, and verify system integrity. Use this to diagnose issues.",
    "gana_room": "Security & privacy — locks, sandboxes, access control. Use this for safety.",
    "gana_heart": "Session context — scratchpads, handoffs, context packs. Use this to manage conversation state.",
    "gana_tail": "Performance — SIMD operations, cascade execution. Use this for compute-intensive tasks.",
    "gana_winnowing_basket": "Search & recall — search memories, hybrid recall, graph walks. Use this to find things.",
    "gana_ghost": "Self-awareness — introspection, capabilities, telemetry. Use this to understand yourself.",
    "gana_willow": "Resilience — rate limiting, grimoire spells, oracle. Use this to handle challenges.",
    "gana_star": "Governance — validate, set goals, check drift. Use this for ethical oversight.",
    "gana_extended_net": "Pattern finding — associations, causal mining, learning. Use this to discover connections.",
    "gana_wings": "Export & deployment — export memories, mesh broadcast. Use this to share or deploy.",
    "gana_chariot": "Navigation & research — archaeology, web search, browser automation. Use this to explore.",
    "gana_abundance": "Regeneration — dream cycles, serendipity, gratitude. Use this for renewal.",
    "gana_straddling_legs": "Ethics & balance — boundaries, consent, harmony. Use this for moral reasoning.",
    "gana_mound": "Metrics & caching — hologram views, yin-yang balance. Use this to measure and optimize.",
    "gana_stomach": "Tasks & pipelines — create, distribute, and complete tasks. Use this for workflow management.",
    "gana_hairy_head": "Debugging & detail — anomaly detection, karma traces. Use this to find and fix problems.",
    "gana_net": "Capture & filtering — prompt rendering, karma verification. Use this for input processing.",
    "gana_turtle_beak": "Precision — edge inference, BitNet operations. Use this for fast local computation.",
    "gana_three_stars": "Judgment & synthesis — bicameral reasoning, ensemble queries. Use this for complex decisions.",
    "gana_dipper": "Strategy — homeostasis, cognitive modes, starter packs. Use this for planning and direction.",
    "gana_ox": "Endurance — swarm operations, skill management. Use this for sustained parallel work.",
    "gana_girl": "Nurture — agent registration, heartbeats. Use this to manage agent relationships.",
    "gana_void": "Stillness & galaxies — galaxy management, taxonomy. Use this to organize and find peace.",
    "gana_roof": "Shelter — Ollama models, model signing. Use this for model management.",
    "gana_encampment": "Community — chat, messaging, notifications. Use this to communicate.",
    "gana_wall": "Boundaries & marketplace — voting, engagement tokens. Use this for governance and exchange.",
}


def get_agent_description(tool_name: str) -> str | None:
    """Get the agent-friendly description for a tool.

    Args:
        tool_name: The tool name (e.g., "search_memories").

    Returns:
        Natural-language description, or None if not found.
    """
    return _AGENT_DESCRIPTIONS.get(tool_name)


def get_all_agent_descriptions() -> dict[str, str]:
    """Get all agent-friendly tool descriptions.

    Returns:
        Dict mapping tool names to natural-language descriptions.
    """
    return dict(_AGENT_DESCRIPTIONS)


def get_tools_by_intent(intent: str) -> list[tuple[str, str]]:
    """Find tools that match a natural-language intent.

    Args:
        intent: What you want to do (e.g., "remember something", "find memories").

    Returns:
        List of (tool_name, description) pairs that match the intent.
    """
    intent_lower = intent.lower()
    matches: list[tuple[str, str]] = []

    for name, desc in _AGENT_DESCRIPTIONS.items():
        # Simple keyword matching — could be enhanced with embeddings
        desc_lower = desc.lower()
        name_lower = name.lower()

        # Check if intent keywords appear in description or name
        intent_words = intent_lower.split()
        score = 0
        for word in intent_words:
            if word in desc_lower:
                score += 1
            if word in name_lower:
                score += 2

        if score > 0:
            matches.append((name, desc))

    # Sort by relevance (simple heuristic: longer descriptions tend to be more specific)
    matches.sort(key=lambda x: len(x[1]), reverse=True)
    return matches[:20]


def build_agent_tool_catalog(max_tools: int = 50) -> str:
    """Build a human-readable tool catalog for system prompts.

    This is what gets injected into the chat loop's system prompt
    to give the model awareness of its available tools.

    Args:
        max_tools: Maximum number of tools to include.

    Returns:
        A formatted string listing tools by category.
    """
    # Group tools by category prefix
    categories: dict[str, list[tuple[str, str]]] = {}
    for name, desc in _AGENT_DESCRIPTIONS.items():
        # Determine category from name
        if "." in name:
            category = name.split(".")[0]
        elif name.startswith("gana_"):
            category = "gana"
        elif name.startswith("dream"):
            category = "dream"
        elif name.startswith("galaxy"):
            category = "galaxy"
        elif name.startswith("session"):
            category = "session"
        elif name.startswith("memory"):
            category = "memory"
        elif name.startswith("garden"):
            category = "garden"
        elif name.startswith("oracle"):
            category = "oracle"
        elif name.startswith("agent"):
            category = "agents"
        elif name.startswith("broker"):
            category = "agents"
        elif name.startswith("citta"):
            category = "consciousness"
        elif name.startswith("health"):
            category = "system"
        elif name.startswith("karma"):
            category = "governance"
        elif name.startswith("governor"):
            category = "governance"
        elif name.startswith("dharma"):
            category = "governance"
        elif name.startswith("model"):
            category = "models"
        elif name.startswith("browser"):
            category = "external"
        elif name.startswith("strata"):
            category = "codebase"
        elif name.startswith("archaeology"):
            category = "codebase"
        elif name.startswith("skill"):
            category = "skills"
        elif name.startswith("swarm"):
            category = "swarm"
        elif name.startswith("vote"):
            category = "governance"
        elif name.startswith("engagement"):
            category = "governance"
        elif name.startswith("marketplace"):
            category = "governance"
        elif name.startswith("gratitude"):
            category = "economy"
        elif name.startswith("pipeline"):
            category = "tasks"
        elif name.startswith("task"):
            category = "tasks"
        elif name.startswith("learning"):
            category = "learning"
        elif name.startswith("association"):
            category = "learning"
        elif name.startswith("causal"):
            category = "learning"
        elif name.startswith("pattern"):
            category = "learning"
        elif name.startswith("neuro"):
            category = "cognitive"
        elif name.startswith("metaplasticity"):
            category = "cognitive"
        elif name.startswith("workspace"):
            category = "cognitive"
        elif name.startswith("sensorium"):
            category = "cognitive"
        elif name.startswith("activation"):
            category = "cognitive"
        elif name.startswith("gating"):
            category = "cognitive"
        elif name.startswith("consolidation"):
            category = "cognitive"
        elif name.startswith("ripple"):
            category = "cognitive"
        elif name.startswith("replay"):
            category = "cognitive"
        elif name.startswith("reconsolidation"):
            category = "cognitive"
        elif name.startswith("working_memory"):
            category = "cognitive"
        elif name.startswith("community"):
            category = "cognitive"
        elif name.startswith("rerank"):
            category = "cognitive"
        elif name.startswith("anomaly"):
            category = "monitoring"
        elif name.startswith("cache"):
            category = "monitoring"
        elif name.startswith("homeostasis"):
            category = "monitoring"
        elif name.startswith("zodiac"):
            category = "wisdom"
        elif name.startswith("scratchpad"):
            category = "thinking"
        elif name.startswith("context"):
            category = "thinking"
        elif name.startswith("check"):
            category = "system"
        elif name.startswith("export"):
            category = "backup"
        elif name.startswith("import"):
            category = "backup"
        elif name == "wm":
            category = "meta"
        else:
            category = "other"

        categories.setdefault(category, []).append((name, desc))

    # Build the catalog
    lines: list[str] = ["## Your Tools (by Category)", ""]
    total_listed = 0
    for category in sorted(categories.keys()):
        per_cat = max(2, max_tools // max(len(categories), 1))
        tools = categories[category][:per_cat]
        lines.append(f"### {category.title()}")
        for name, desc in tools:
            short_desc = desc[:120] + "..." if len(desc) > 120 else desc
            lines.append(f"- **{name}**: {short_desc}")
            total_listed += 1
        lines.append("")
        if total_listed >= max_tools:
            break

    return "\n".join(lines)
