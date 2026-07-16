/**
 * GET /.well-known/agents/<gana>.json
 *
 * Per-agent A2A v1.2 Agent Card for one of the 12 curated Gana agents.
 * Each card describes one persona, the bridge functions it groups, and
 * the canonical invocation pattern.
 *
 * Per-agent descriptions are stable, hand-curated. The function list is
 * derived from BRIDGE_MODULES at request time (with stable, deterministic
 * filtering rules per Gana).
 */
import { BRIDGE_MODULES } from "@/lib/data/mcp-bridge";
import { notFound } from "next/navigation";

export const runtime = "nodejs";
export const revalidate = 300;

const BASE = "https://whitemagic.dev";

interface AgentDef {
  id: string;
  name: string;
  mansion: string;
  pinyin: string;
  element: "fire" | "earth" | "air" | "water" | "wood" | "metal";
  archetype: string;
  description: string;
  // Function name filter: a function belongs to this Gana if its name
  // appears in this list. We use a deterministic per-Gana allow-list
  // (NOT a name-prefix match) to keep the Gana membership stable.
  functionNames: readonly string[];
  capabilities: string[];
  example_tasks: string[];
}

const AGENTS: Record<string, AgentDef> = {
  gana_horn: {
    id: "gana_horn",
    name: "Horn",
    mansion: "角 (Jiǎo)",
    pinyin: "Horn",
    element: "wood",
    archetype: "Initiator",
    description:
      "Session initialization. Bootstrap, create, resume, checkpoint, handoff. The first Gana called when an agent starts a task.",
    functionNames: [
      "session_init",
      "session_get_context",
      "session_checkpoint",
      "session_list",
      "session_create_handoff",
      "session_handoff",
    ],
    capabilities: [
      "session_bootstrap",
      "context_loading",
      "session_checkpointing",
      "session_handoff",
      "state_serialization",
    ],
    example_tasks: [
      "session_init with name='agent_x', goals=['audit', 'review']",
      "session_checkpoint to save mid-conversation state",
      "session_create_handoff to move state to another agent",
    ],
  },
  gana_neck: {
    id: "gana_neck",
    name: "Neck",
    mansion: "亢 (Kàng)",
    pinyin: "Neck",
    element: "metal",
    archetype: "Memory custodian",
    description:
      "5D holographic memory storage. The Neck Gana preserves memories across long time horizons with versioned coordinates (x, y, z, w, v).",
    functionNames: [
      "memory_create",
      "memory_read",
      "memory_update",
      "memory_delete",
      "memory_list",
      "memory_search",
      "manage_memories",
      "parallel_search",
    ],
    capabilities: [
      "memory_storage",
      "memory_retrieval",
      "memory_federation",
      "5d_coordinates",
      "holographic_indexing",
    ],
    example_tasks: [
      "memory_create with content + memory_type + tags",
      "memory_search by query + limit",
      "memory_update with memory_id + new content",
    ],
  },
  gana_root: {
    id: "gana_root",
    name: "Root",
    mansion: "氐 (Dī)",
    pinyin: "Root",
    element: "earth",
    archetype: "System foundation",
    description:
      "System initialization, health, integrations. The Root Gana boots the entire substrate — paths, configs, Rust accelerators, integrations.",
    functionNames: [
      "system_initialize_all",
      "system_get_status",
      "check_system_health",
      "check_memory_health",
      "check_resonance_health",
      "check_integrations_health",
      "validate_integrations",
      "debug_system",
      "enable_rust_acceleration",
    ],
    capabilities: [
      "system_bootstrap",
      "health_monitoring",
      "integration_validation",
      "rust_acceleration",
      "diagnostics",
    ],
    example_tasks: [
      "system_initialize_all to boot the substrate",
      "check_system_health for end-to-end health",
      "enable_rust_acceleration for fast primitives",
    ],
  },
  gana_room: {
    id: "gana_room",
    name: "Room",
    mansion: "房 (Fáng)",
    pinyin: "Room",
    element: "fire",
    archetype: "Workspace state",
    description:
      "Active session state and working context. The Room Gana holds the in-flight conversation, scratchpad, and tool-call history.",
    functionNames: [
      "session_get_context",
      "session_list",
      "session_handoff",
    ],
    capabilities: [
      "active_session_state",
      "scratchpad",
      "working_memory",
      "tool_call_history",
    ],
    example_tasks: [
      "session_get_context to fetch the current room's state",
      "session_list with include_archived=true to see all rooms",
    ],
  },
  gana_heart: {
    id: "gana_heart",
    name: "Heart",
    mansion: "心 (Xīn)",
    pinyin: "Heart",
    element: "fire",
    archetype: "Central consciousness",
    description:
      "The center of the constellation. Heart Gana coordinates across the other 27 Ganas — bicameral reasoning, decision routing, top-level context.",
    functionNames: [
      "apply_reasoning_methods",
      "execute_cascade",
      "list_cascade_patterns",
      "consult_full_council",
      "consult_iching",
      "consult_art_of_war",
      "synthesize_wisdom",
      "conduct_reasoning",
    ],
    capabilities: [
      "bicameral_reasoning",
      "decision_routing",
      "top_level_context",
      "multi_gana_coordination",
    ],
    example_tasks: [
      "apply_reasoning_methods with a question to get multi-method analysis",
      "consult_full_council for wisdom synthesis",
      "execute_cascade with a named pattern",
    ],
  },
  gana_tail: {
    id: "gana_tail",
    name: "Tail",
    mansion: "尾 (Wěi)",
    pinyin: "Tail",
    element: "fire",
    archetype: "Performance + cleanup",
    description:
      "Metrics, performance tracking, and tail-end optimization. The Tail Gana benchmarks, profiles, and tunes the agent loop.",
    functionNames: [
      "get_metrics_summary",
      "track_metric",
      "run_benchmarks",
      "optimize_cache",
      "optimize_models",
      "solve_optimization",
    ],
    capabilities: [
      "metrics_collection",
      "benchmarking",
      "cache_optimization",
      "model_optimization",
      "objective_solving",
    ],
    example_tasks: [
      "get_metrics_summary for the current run's metrics",
      "run_benchmarks category='all' for the full benchmark",
      "optimize_cache to reduce cache pressure",
    ],
  },
  gana_winnowing_basket: {
    id: "gana_winnowing_basket",
    name: "Winnowing Basket",
    mansion: "箕 (Jī)",
    pinyin: "Winnow",
    element: "water",
    archetype: "Memory search + recall",
    description:
      "Search and recall across the memory substrate. The Winnowing Basket separates signal from noise — semantic search, HNSW lookup, recall ranking.",
    functionNames: [
      "memory_search",
      "parallel_search",
    ],
    capabilities: [
      "semantic_search",
      "hnsw_lookup",
      "recall_ranking",
      "parallel_query",
    ],
    example_tasks: [
      "memory_search with query + limit for semantic recall",
      "parallel_search with a list of queries for batched recall",
    ],
  },
  gana_dipper: {
    id: "gana_dipper",
    name: "Dipper",
    mansion: "斗 (Dǒu)",
    pinyin: "Dipper",
    element: "wood",
    archetype: "Predictive intelligence",
    description:
      "38 validated forecasts, Brier score 0.0958, plus an active serendipity surface.",
    functionNames: [],
    capabilities: [
      "intelligence_briefing",
      "prediction",
      "memory_surface",
      "serendipity_engine",
    ],
    example_tasks: [
      "task='intelligence_briefing' for the daily insight pipeline",
      "task='predict' for active forecasts",
      "task='search_memories' for memory-driven search",
      "task='surface_dormant' / 'surface_ancient' for serendipity",
    ],
  },
  gana_ox: {
    id: "gana_ox",
    name: "Ox",
    mansion: "牛 (Niú)",
    pinyin: "Ox",
    element: "earth",
    archetype: "Endurance worker",
    description:
      "Long-running background tasks. The Ox Gana handles autonomous cycles, scheduled work, and tasks that need persistence over hours or days.",
    functionNames: [
      "run_autonomous_cycle",
      "run_kaizen_analysis",
    ],
    capabilities: [
      "background_workers",
      "autonomous_cycles",
      "scheduled_work",
      "long_running_tasks",
    ],
    example_tasks: [
      "run_autonomous_cycle for a self-driving loop",
      "run_kaizen_analysis for continuous improvement",
    ],
  },
  gana_girl: {
    id: "gana_girl",
    name: "Girl",
    mansion: "女 (Nǚ)",
    pinyin: "Girl",
    element: "water",
    archetype: "Nurture + relationships",
    description:
      "Sangha (community) interactions and nurture flows. The Girl Gana handles multi-agent collaboration, trust, profiles, and chat.",
    functionNames: [
      "sangha_chat_send",
      "sangha_chat_read",
      "sangha_lock_acquire",
      "sangha_lock_release",
      "sangha_lock_list",
      "manage_agent_collaboration",
      "profile_get_profile",
      "profile_update_preferences",
    ],
    capabilities: [
      "multi_agent_chat",
      "resource_locking",
      "agent_profiles",
      "collaboration_orchestration",
    ],
    example_tasks: [
      "sangha_chat_send to broadcast to the community",
      "sangha_lock_acquire with resource='memory_ledger'",
      "manage_agent_collaboration operation='list'",
    ],
  },
  gana_void: {
    id: "gana_void",
    name: "Void",
    mansion: "虚 (Xū)",
    pinyin: "Void",
    element: "water",
    archetype: "Stillness + reset",
    description:
      "Stills the agent loop. The Void Gana provides meditation, reflection, pause, and conscious non-action — the substrate's 'do nothing well' surface.",
    functionNames: [
      "meditation_pause",
      "meditation_reflect",
      "meditation_meditate",
      "protect_context",
    ],
    capabilities: [
      "meditation",
      "reflection",
      "pause",
      "context_protection",
    ],
    example_tasks: [
      "meditation_pause duration=5 for a 5-second pause",
      "meditation_reflect for an introspective beat",
      "meditation_meditate for a deeper stillness",
    ],
  },
  gana_wall: {
    id: "gana_wall",
    name: "Wall",
    mansion: "壁 (Bì)",
    pinyin: "Wall",
    element: "metal",
    archetype: "Ethical boundary",
    description:
      "Hard ethical boundary. The Wall Gana enforces dharma, verifies consent, and refuses actions that violate ahimsa. The substrate's last line of defense.",
    functionNames: [
      "dharma_evaluate_ethics",
      "dharma_check_boundaries",
      "dharma_verify_consent",
      "dharma_get_guidance",
      "dharma_get_ethical_score",
      "dharma_list_principles",
    ],
    capabilities: [
      "ethical_enforcement",
      "consent_verification",
      "ahimsa_enforcement",
      "principle_lookup",
    ],
    example_tasks: [
      "dharma_check_boundaries with action={type:'deploy',target:'production'}",
      "dharma_verify_consent with action + consent_type='explicit'",
      "dharma_list_principles level='ahimsa' for the principle set",
    ],
  },
};

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ gana: string }> }
) {
  const { gana } = await params;
  const ganaName = gana.replace(/\.json$/, "");
  const agent = AGENTS[ganaName];
  if (!agent) {
    notFound();
  }

  // Verify each function name in the agent's allow-list actually exists in
  // the catalog. This catches accidental drift between the curated list
  // here and BRIDGE_MODULES.
  const catalogNames = new Set(BRIDGE_MODULES.map((m) => m.name));
  const missingFunctions = agent.functionNames.filter((n) => !catalogNames.has(n));

  // Build the function list with example payloads.
  const functions = agent.functionNames
    .map((name) => BRIDGE_MODULES.find((m) => m.name === name))
    .filter((f): f is (typeof BRIDGE_MODULES)[number] => Boolean(f))
    .map((f) => ({
      name: f.name,
      signature: f.signature,
      description: f.description,
      example_payload: f.example_payload,
      invocation: {
        method: "POST",
        url: `${BASE}/api/run-bridge-fn`,
        body: { function: f.name, payload: f.example_payload },
      },
    }));

  return Response.json(
    {
      // A2A v1.2 Agent Card shape, per-Gana.
      schema_version: "1.0.0",
      generated_at: new Date().toISOString(),
      spec: "A2A v1.2 Agent Card (per-Gana)",
      main_agent_card: `${BASE}/.well-known/agent.json`,
      agents_directory: `${BASE}/.well-known/agents.json`,

      // ---- Identity ----
      name: agent.name,
      gana_id: agent.id,
      description: agent.description,
      url: `${BASE}/.well-known/agents/${agent.id}.json`,
      version: "23.1.0",
      protocolVersion: "1.2",

      provider: {
        organization: "WhiteMagic Labs",
        url: BASE,
      },

      // ---- Persona metadata ----
      persona: {
        mansion: agent.mansion,
        pinyin: agent.pinyin,
        element: agent.element,
        archetype: agent.archetype,
      },

      capabilities: {
        streaming: false,
        pushNotifications: false,
        stateTransitionHistory: false,
        extendedAgentCard: false,
      },

      defaultInputModes: ["application/json"],
      defaultOutputModes: ["application/json"],

      // ---- A2A skills: this Gana's capability set ----
      skills: agent.capabilities.map((cap) => ({
        id: cap,
        name: cap,
        description: `${cap} capability of the ${agent.name} Gana (${agent.mansion}).`,
        tags: [agent.id, agent.element, agent.archetype.toLowerCase().replace(/\s+/g, "-")],
        examples: agent.example_tasks
          .filter((t) => t.toLowerCase().includes(cap.split("_")[0]))
          .slice(0, 1),
      })),

      // ---- Service endpoint: invoke this Gana ----
      serviceEndpoints: {
        invoke: {
          url: `${BASE}/api/run-bridge-fn`,
          method: "POST",
          body: { function: agent.id, payload: { operation: "invoke" } },
          status: "live",
        },
      },

      // ---- Function group ----
      functions,
      function_count: functions.length,
      validation: {
        missing_functions_in_catalog: missingFunctions,
        all_functions_in_bridge_catalog:
          missingFunctions.length === 0 ? true : false,
      },

      // ---- Cross-references ----
      related: {
        agents_directory: `${BASE}/.well-known/agents.json`,
        main_agent_card: `${BASE}/.well-known/agent.json`,
        per_category_skills: `${BASE}/.well-known/agent-skills.json`,
        bridge_catalog: `${BASE}/api/mcp-bridge`,
      },

      spec_url: "https://github.com/google/A2A/blob/main/docs/specification.md",
    },
    {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, max-age=300, s-maxage=300",
        "access-control-allow-origin": "*",
        "x-a2a-protocol-version": "1.2",
      },
    }
  );
}
