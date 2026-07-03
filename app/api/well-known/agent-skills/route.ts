/**
 * GET /.well-known/agent-skills.json
 *
 * Per-category skill tree for WhiteMagic Labs. The main A2A Agent Card
 * (/.well-known/agent.json) lists 7 high-level skills; this endpoint
 * exposes the full 21-category skill set mapped to the 143 bridge
 * functions in /api/mcp-bridge.
 *
 * Each skill entry is shaped to be friendly to A2A peers that want to
 * route a sub-task to the right surface. examples[] shows the exact
 * JSON body to POST to /api/run-bridge-fn.
 *
 * Spec: A2A v1.2 skills (id, name, description, tags, examples, inputModes, outputModes).
 */
import { BRIDGE_MODULES } from "@/lib/data/mcp-bridge";

export const runtime = "nodejs";
export const revalidate = 300;

const BASE = "https://whitemagic.dev";

// Per-category descriptions. Stable, hand-curated.
const CATEGORY_DESCRIPTIONS: Record<
  string,
  { name: string; description: string; tags: string[] }
> = {
  meditation: {
    name: "Meditation cycle",
    description:
      "Pause, reflect, and meditate primitives for slowing the agent loop. Returns duration + a status flag.",
    tags: ["meditation", "rhythm", "governance"],
  },
  zodiac: {
    name: "Zodiac core coordination",
    description:
      "12 zodiac cores (aries, taurus, gemini, ..., pisces) plus 4 council/workflows: list_cores, activate_core, consult_council, run_cycle. Each core is a coordination persona with element, mode, and planetary ruler.",
    tags: ["zodiac", "core", "council", "coordination"],
  },
  gana: {
    name: "Gana meta-tools (28 mansions)",
    description:
      "28 Gana wrappers collapse 488 dispatch tools into named personas. gana_horn (session), gana_neck (memory), gana_root (system), ..., gana_wall (ethics boundary). Per-Gana details in /.well-known/agents.json.",
    tags: ["gana", "meta-tool", "prat", "router"],
  },
  dharma: {
    name: "Dharma ethical governance",
    description:
      "Pre-flight any action through dharma_check_boundaries before commit. Also: dharma_evaluate_ethics, dharma_verify_consent, dharma_get_guidance, dharma_get_ethical_score, dharma_list_principles.",
    tags: ["dharma", "ethics", "consent", "ahimsa"],
  },
  archaeology: {
    name: "Archaeology (memory + excavation)",
    description:
      "Read/write the memory archaeology ledger: mark_read, mark_written, find_unread, find_changed, recent_reads, stats, report, search, extract_wisdom, generate_report, scan_directory, process_wisdom, daily_digest.",
    tags: ["archaeology", "memory", "excavation", "wisdom"],
  },
  wisdom: {
    name: "Wisdom council (I Ching + Art of War)",
    description:
      "consult_full_council, consult_iching, consult_art_of_war, synthesize_wisdom. Multi-source wisdom synthesis with urgency tiers.",
    tags: ["wisdom", "iching", "art-of-war", "council"],
  },
  reasoning: {
    name: "Bicameral reasoning",
    description:
      "apply_reasoning_methods, analyze_pattern, detect_patterns, conduct_reasoning, execute_cascade, list_cascade_patterns. Pattern detection + multi-step cascades.",
    tags: ["reasoning", "pattern", "cascade", "bicameral"],
  },
  session: {
    name: "Session lifecycle",
    description:
      "7 session functions: init, get_context, checkpoint, list, create_handoff, handoff, plus get_system_time. Move state between agents, checkpoint mid-conversation.",
    tags: ["session", "handoff", "checkpoint"],
  },
  memory: {
    name: "5D holographic memory",
    description:
      "memory_create, memory_read, memory_update, memory_delete, memory_list, memory_search, parallel_search, manage_memories. 5D holographic coordinates (x, y, z, w, v).",
    tags: ["memory", "5d", "holographic", "search"],
  },
  garden: {
    name: "Garden activation",
    description:
      "garden_list, garden_activate, garden_resonance_map, garden_garden_status, garden_garden_activate, garden_sangha_workspace_info, manage_gardens, protect_context. 28 named gardens with resonance maps.",
    tags: ["garden", "resonance", "activation"],
  },
  system: {
    name: "System health + initialization",
    description:
      "system_initialize_all, system_get_status, check_system_health, check_memory_health, check_resonance_health, check_integrations_health, validate_integrations, debug_system, protect_context.",
    tags: ["system", "health", "integrations"],
  },
  voice: {
    name: "Voice patterns",
    description:
      "manage_voice_patterns: inspect and modify the librarian's voice patterns (markdown style, register, citation density).",
    tags: ["voice", "patterns", "librarian"],
  },
  autonomous: {
    name: "Autonomous cycle",
    description:
      "run_autonomous_cycle: kick off a self-driving loop with the configured goal/intention. Bounded by Dharma + Karma.",
    tags: ["autonomous", "loop", "self-drive"],
  },
  benchmark: {
    name: "Benchmarks",
    description:
      "run_benchmarks: run the full benchmark suite (gauntlet + MCP). Reports latency, success rate, memory per call.",
    tags: ["benchmark", "performance"],
  },
  inference: {
    name: "Local inference + bitnet",
    description:
      "local_ml_status, local_ml_infer, bitnet_infer, bitnet_status, run_local_inference. Optional — disabled by default. Set WHITEMAGIC_ENABLE_LOCAL_MODELS=1 on self-hosted deployments.",
    tags: ["inference", "local-ml", "bitnet"],
  },
  kaizen: {
    name: "Kaizen (continuous improvement)",
    description:
      "run_kaizen_analysis, kaizen_analyze, analyze_wu_xing_phase. Five-element balance check + auto-fix loop.",
    tags: ["kaizen", "wu-xing", "improvement"],
  },
  collaboration: {
    name: "Multi-agent collaboration",
    description:
      "sangha_lock_acquire/release/list, sangha_chat_read/send, manage_agent_collaboration, profile_get_profile, profile_update_preferences, windsurf_backup/merge_backups, garden_sangha_workspace_info.",
    tags: ["collaboration", "sangha", "lock", "profile"],
  },
  infrastructure: {
    name: "Rust + infrastructure accelerators",
    description:
      "enable_rust_acceleration, rust_check_available, rust_compress, rust_consolidate_memories, rust_extract_patterns, rust_extract_todos, rust_fast_search, rust_fast_similarity, rust_parallel_grep, rust_read_files_batch, rust_scan_codebase. Rust-backed performance primitives.",
    tags: ["infrastructure", "rust", "accelerator"],
  },
  metrics: {
    name: "Metrics + time",
    description:
      "get_metrics_summary, track_metric, get_system_time, get_timestamp. Per-call metric tracking + canonical time source.",
    tags: ["metrics", "telemetry", "time"],
  },
  optimization: {
    name: "Optimization",
    description:
      "optimize_cache, optimize_models, solve_optimization. Cache pressure + model selection + objective solving.",
    tags: ["optimization", "cache", "models"],
  },
  tool: {
    name: "Tool router + shims",
    description:
      "execute_mcp_tool, cast, ensure_string, adapt_response, parallel_search. Router shims used by the librarian and gana dispatch.",
    tags: ["tool", "router", "shim"],
  },
};

export async function GET() {
  // Group BRIDGE_MODULES by category and build a skill per category.
  const byCategory = new Map<string, typeof BRIDGE_MODULES>();
  for (const fn of BRIDGE_MODULES) {
    const arr = byCategory.get(fn.category) ?? [];
    arr.push(fn);
    byCategory.set(fn.category, arr);
  }

  const skills = Array.from(byCategory.entries())
    .map(([category, fns]) => {
      const meta = CATEGORY_DESCRIPTIONS[category] ?? {
        name: category,
        description: `${fns.length} bridge functions in the ${category} category.`,
        tags: [category],
      };
      return {
        id: `category-${category}`,
        name: meta.name,
        description: meta.description,
        tags: meta.tags,
        category,
        function_count: fns.length,
        // Show the first 3 example payloads as a teaser. Full catalog at /api/mcp-bridge.
        examples: fns.slice(0, 3).map((f) => ({
          function: f.name,
          payload: f.example_payload,
          // Pre-shaped curl equivalent for quick copy-paste.
          curl: `curl -X POST ${BASE}/api/run-bridge-fn -H 'content-type: application/json' -d '${JSON.stringify({ function: f.name, payload: f.example_payload }).replace(/'/g, "'\\''")}'`,
        })),
        // Link to the full per-category listing.
        catalog_url: `${BASE}/api/mcp-bridge#category-${category}`,
        inputModes: ["application/json"],
        outputModes: ["application/json"],
      };
    })
    .sort((a, b) => a.category.localeCompare(b.category));

  return Response.json(
    {
      schema_version: "1.0.0",
      generated_at: new Date().toISOString(),
      spec: "A2A v1.2 skills (per-category expansion)",
      main_agent_card: `${BASE}/.well-known/agent.json`,
      categories_total: skills.length,
      functions_total: BRIDGE_MODULES.length,
      skills,
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
