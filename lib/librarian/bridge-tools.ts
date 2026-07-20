/**
 * Bridge tool subset for the Librarian.
 *
 * The full whitemagic.mcp_api_bridge surface has 143 functions across 21
 * categories. The librarian uses a curated subset (~20) most useful for
 * chat. The full 143 remain callable via /api/run-bridge-fn, but the
 * LLM only sees these schemas so the tool-use loop stays focused.
 *
 * Each schema is OpenAI-compatible (the OpenRouter + Ollama providers
 * both accept this format). The dispatcher in `lib/bridge/impl.ts`
 * handles the actual execution.
 *
 * To add a new bridge tool to the librarian:
 *   1. Add an entry below with name, description, and parameters.
 *   2. The bridge function must already exist in BRIDGE_MODULES.
 *   3. Test by asking the librarian a question that triggers it.
 */
import { BRIDGE_MODULES } from "@/lib/data/mcp-bridge";

/**
 * Hand-curated subset of bridge functions the librarian can call.
 * Each entry maps a function name to a brief description and JSON Schema
 * for its parameters. Parameter types follow JSON Schema draft-07.
 */
export interface BridgeToolDef {
  functionName: string;
  category: string;
  description: string;
  parameters: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
  };
}

export const LIBRARIAN_BRIDGE_TOOLS: BridgeToolDef[] = [
  // ─── Dharma (ethics, governance) ────────────────────────────
  {
    functionName: "dharma_check_boundaries",
    category: "dharma",
    description:
      "Pre-flight any action through the dharma ethics check. Returns ok/refused plus the principle invoked. Use when the user asks about ethical implications.",
    parameters: {
      type: "object",
      properties: {
        action: {
          type: "object",
          description:
            "Object describing the proposed action. Common fields: type, target, scope.",
        },
        strict_mode: {
          type: "boolean",
          description: "If true, use stricter principle interpretation.",
        },
      },
      required: ["action"],
    },
  },
  {
    functionName: "dharma_list_principles",
    category: "dharma",
    description:
      "List the dharma principles the substrate enforces. Useful when the user asks what ethical rules govern the system.",
    parameters: {
      type: "object",
      properties: {
        level: {
          type: "string",
          description: "Optional filter: 'ahimsa', 'satya', 'asteya', etc.",
        },
      },
    },
  },

  // ─── Session (state, handoff) ───────────────────────────────
  {
    functionName: "session_get_context",
    category: "session",
    description:
      "Fetch the current session's context (active session, working memory, recent tool calls). Use when the user asks 'what are we doing?' or 'where are we?'.",
    parameters: {
      type: "object",
      properties: {},
    },
  },
  {
    functionName: "session_list",
    category: "session",
    description:
      "List all sessions, optionally including archived ones. Use when the user wants to see past conversations.",
    parameters: {
      type: "object",
      properties: {
        include_archived: {
          type: "boolean",
          description: "Include archived sessions (default false).",
        },
      },
    },
  },

  // ─── Archaeology (memory + excavation) ──────────────────────
  {
    functionName: "archaeology_search",
    category: "archaeology",
    description:
      "Search the memory archaeology ledger for past reads, writes, and insights. Use when the user asks 'have I read about X?' or 'find past notes on Y'.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search query (semantic match).",
        },
        limit: {
          type: "number",
          description: "Max results to return (default 10).",
        },
      },
      required: ["query"],
    },
  },
  {
    functionName: "archaeology_recent_reads",
    category: "archaeology",
    description:
      "List recent files/docs the user has read. Use when the user asks 'what was I just looking at?' or 'what did I read recently?'.",
    parameters: {
      type: "object",
      properties: {
        limit: {
          type: "number",
          description: "Max items to return (default 20).",
        },
      },
    },
  },
  {
    functionName: "archaeology_daily_digest",
    category: "archaeology",
    description:
      "Get today's wisdom digest — the curated summary of recent insights. Use when the user asks 'what's the daily briefing?' or 'what's new today?'.",
    parameters: {
      type: "object",
      properties: {},
    },
  },

  // ─── Memory (6D holographic) ───────────────────────────────
  {
    functionName: "memory_search",
    category: "memory",
    description:
      "Search 6D holographic memory by query. Returns memory IDs + similarity scores. Use when the user asks 'find memories about X'.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search query.",
        },
        limit: {
          type: "number",
          description: "Max results (default 10).",
        },
      },
      required: ["query"],
    },
  },
  {
    functionName: "memory_list",
    category: "memory",
    description:
      "List recent memories. Use when the user wants to see what they've stored recently.",
    parameters: {
      type: "object",
      properties: {
        limit: {
          type: "number",
          description: "Max items (default 20).",
        },
        memory_type: {
          type: "string",
          description: "Filter by type: long_term, working, episodic, etc.",
        },
      },
    },
  },

  // ─── Zodiac (12 cores) ──────────────────────────────────────
  {
    functionName: "zodiac_list_cores",
    category: "zodiac",
    description:
      "List the 12 zodiac cores (Aries, Taurus, ..., Pisces) with their element, mode, and capabilities. Use when the user asks about the zodiac system.",
    parameters: {
      type: "object",
      properties: {},
    },
  },
  {
    functionName: "zodiac_consult_council",
    category: "zodiac",
    description:
      "Run a query through the 12-core zodiac council. Returns the consolidated answer. Use for complex multi-perspective questions.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "The question to consult the council on.",
        },
      },
      required: ["query"],
    },
  },

  // ─── Wisdom (I Ching + Art of War) ──────────────────────────
  {
    functionName: "consult_iching",
    category: "wisdom",
    description:
      "Cast an I Ching reading for a question. Returns the hexagram, judgment, and lines. Use for reflective / decision-support questions.",
    parameters: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The question to consult the I Ching on.",
        },
        method: {
          type: "string",
          description: "Casting method: 'coins' (default) or 'yarrow'.",
        },
      },
      required: ["question"],
    },
  },
  {
    functionName: "synthesize_wisdom",
    category: "wisdom",
    description:
      "Synthesize wisdom across multiple sources. Use when the user wants a multi-source deep answer.",
    parameters: {
      type: "object",
      properties: {
        sources: {
          type: "array",
          items: { type: "string" },
          description: "Sources to consult: 'council', 'iching', 'art_of_war', etc.",
        },
        urgency: {
          type: "string",
          description: "Urgency: 'low', 'normal', 'high'.",
        },
      },
      required: ["sources"],
    },
  },

  // ─── Reasoning (bicameral) ─────────────────────────────────
  {
    functionName: "apply_reasoning_methods",
    category: "reasoning",
    description:
      "Apply multiple reasoning methods to a question. Returns each method's answer. Use for analytical / strategic questions.",
    parameters: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The question to reason about.",
        },
      },
      required: ["question"],
    },
  },
  {
    functionName: "detect_patterns",
    category: "reasoning",
    description:
      "Detect patterns in a query or content. Use when the user asks 'what pattern is this?' or 'am I seeing X again?'.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Text or query to scan for patterns.",
        },
      },
    },
  },

  // ─── Gana meta-tools (28 mansions) ──────────────────────────
  {
    functionName: "gana_horn",
    category: "gana",
    description:
      "Horn Gana — session bootstrap, resume, checkpoint, handoff. Use when the user wants to start/end a session.",
    parameters: {
      type: "object",
      properties: {
        operation: {
          type: "string",
          description: "Operation: 'invoke', 'create_session', 'checkpoint', 'handoff'.",
        },
      },
    },
  },
  {
    functionName: "gana_dipper",
    category: "gana",
    description:
      "Dipper Gana — predictive intelligence. Supports 'intelligence_briefing' (daily insights), 'predict' (forecasts), 'search_memories', 'surface_dormant' (serendipity). Use for forward-looking questions.",
    parameters: {
      type: "object",
      properties: {
        task: {
          type: "string",
          description:
            "Task: 'intelligence_briefing', 'predict', 'search_memories', 'surface_dormant', or default 'measuring'.",
        },
      },
    },
  },
  {
    functionName: "gana_wall",
    category: "gana",
    description:
      "Wall Gana — ethical boundary enforcement. Use when the user wants to verify an action is ethical before committing.",
    parameters: {
      type: "object",
      properties: {
        operation: {
          type: "string",
          description: "Operation: 'invoke', 'check_boundaries', 'list_principles'.",
        },
      },
    },
  },

  // ─── Meditation (stillness) ────────────────────────────────
  {
    functionName: "meditation_pause",
    category: "meditation",
    description:
      "Pause for a moment. Use when the user needs a beat, or when the answer is 'take a moment'.",
    parameters: {
      type: "object",
      properties: {
        duration: {
          type: "number",
          description: "Pause duration in seconds (default 5).",
        },
      },
    },
  },

  // ─── Metrics + time ────────────────────────────────────────
  {
    functionName: "get_system_time",
    category: "metrics",
    description: "Get the current canonical system time. Use for date/time questions.",
    parameters: {
      type: "object",
      properties: {},
    },
  },
  {
    functionName: "get_metrics_summary",
    category: "metrics",
    description:
      "Get the current run's metrics summary. Use when the user asks about performance, success rates, etc.",
    parameters: {
      type: "object",
      properties: {},
    },
  },
];

/**
 * Build OpenAI-compatible tool schemas for the curated bridge subset.
 * The returned array is what gets passed to OpenRouter / Ollama as `tools`.
 */
export function buildBridgeToolSchemas() {
  return LIBRARIAN_BRIDGE_TOOLS.map((t) => {
    // Verify the function name actually exists in the catalog at module-load.
    // This catches drift between the curated list and BRIDGE_MODULES.
    if (!BRIDGE_MODULES.find((m) => m.name === t.functionName)) {
      console.warn(
        `[librarian-bridge] Tool ${t.functionName} is in LIBRARIAN_BRIDGE_TOOLS but not in BRIDGE_MODULES — will be skipped at runtime`,
      );
    }
    return {
      type: "function" as const,
      function: {
        name: t.functionName,
        description: t.description,
        parameters: t.parameters,
      },
    };
  });
}

/**
 * Validate that every curated bridge tool exists in the live catalog.
 * Returns a list of any mismatches. Used at build time and on first request.
 */
export function validateBridgeTools(): { missing: string[]; total: number } {
  const catalogNames = new Set(BRIDGE_MODULES.map((m) => m.name));
  const missing = LIBRARIAN_BRIDGE_TOOLS
    .filter((t) => !catalogNames.has(t.functionName))
    .map((t) => t.functionName);
  return { missing, total: LIBRARIAN_BRIDGE_TOOLS.length };
}
