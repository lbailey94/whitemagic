/**
 * Librarian tool system.
 *
 * Each tool has an OpenAI-compatible schema (for function calling) and a
 * server-side handler. Handlers run after Dharma + rate-limit + budget
 * checks have passed — tools can always assume the caller is authorized.
 *
 * Every tool invocation is recorded in the Karma ledger (via the API
 * route, not here — tools should stay pure-ish).
 */

import { getService, SERVICES_LIST } from "@/lib/data/services";
import {
  getTier,
  PRICING_TIERS_LIST,
  resolveCheckoutUrl,
  type PricingTier,
} from "@/lib/data/pricing";
import {
  getCapability,
  searchCapabilities,
  CAPABILITIES_LIST,
} from "@/lib/data/platform";
import { TIMELINE_DATA, type TimelineEntry } from "@/components/timeline-data";
import { getKV } from "./rate-limit";

// ---------------------------------------------------------------------------
// Tool result types (discriminated union — client renders one card per kind)
// ---------------------------------------------------------------------------

export type ToolResult =
  | { kind: "service_detail"; data: ReturnType<typeof getService> }
  | { kind: "service_list"; data: typeof SERVICES_LIST }
  | { kind: "pricing_tier"; data: PricingTier | null }
  | { kind: "pricing_list"; data: PricingTier[] }
  | { kind: "platform_capability"; data: ReturnType<typeof getCapability> }
  | { kind: "platform_search"; data: ReturnType<typeof searchCapabilities> }
  | {
      kind: "timeline_matches";
      data: { query: string; entries: TimelineEntry[]; total: number };
    }
  | {
      kind: "booking_initiated";
      data: {
        tierName: string;
        tierSlug: string;
        checkoutUrl: string;
        isStripe: boolean;
        topic: string;
      };
    }
  | {
      kind: "contact_submitted";
      data: { reference: string; topic: string; summary: string };
    }
  | { kind: "error"; data: { message: string } };

export interface ToolContext {
  sessionId: string | undefined;
  pageContext: { path: string; title?: string } | undefined;
  ip: string;
}

// ---------------------------------------------------------------------------
// OpenAI function-calling schemas (what the LLM sees)
// ---------------------------------------------------------------------------

export const TOOL_SCHEMAS = [
  {
    type: "function" as const,
    function: {
      name: "get_service_detail",
      description:
        "Get full details for one of the three consulting services. Use this when a visitor asks specifics about what's included, who it's for, timelines, or price. If no slug is given, returns the full list.",
      parameters: {
        type: "object",
        properties: {
          slug: {
            type: "string",
            enum: ["private-ai-deployment", "agent-governance", "mcp-engineering"],
            description: "Which service. Omit to list all three.",
          },
        },
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "get_pricing_tier",
      description:
        "Get full details for one of the three pricing tiers (Office Hours, Architecture Review, Engagement). Use this when a visitor asks about price, what's included at a tier, or which tier fits their need. If no slug is given, returns the full list.",
      parameters: {
        type: "object",
        properties: {
          slug: {
            type: "string",
            enum: ["office-hours", "architecture-review", "engagement"],
            description: "Which tier. Omit to list all three.",
          },
        },
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "get_platform_capability",
      description:
        "Get technical details about a WhiteMagic platform capability — e.g. Dharma Rules, Karma Ledger, Harmony Vector, Circuit Breaker, 28-Gana MCP compression, Gnosis Portal, Galaxy Backup, Tiered Memory. Use this when a visitor asks how something works or wants specifics about a feature.",
      parameters: {
        type: "object",
        properties: {
          slug: {
            type: "string",
            description:
              "Capability slug (e.g. 'dharma-rules', 'karma-ledger'). If the visitor's question doesn't match a slug, use 'search' parameter instead.",
          },
          search: {
            type: "string",
            description:
              "Free-text search across capabilities. Returns up to 5 matches.",
          },
        },
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "search_timeline",
      description:
        "Search the public WhiteMagic timeline for entries matching a query. Use this when visitors ask about when something shipped, what happened around a date, or want evidence of the prescience thesis (WhiteMagic shipping before industry standards named the primitive).",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description:
              "Search text. Matched against title, description, version.",
          },
          limit: {
            type: "number",
            description: "Max results (default 5, max 15)",
          },
        },
        required: ["query"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "request_office_hours_booking",
      description:
        "Initiate an Office Hours booking. Returns a checkout URL the visitor can click to pay and schedule. Use this ONLY when the visitor explicitly wants to book, not just to explain tiers. Always confirm their topic first in conversation.",
      parameters: {
        type: "object",
        properties: {
          topic: {
            type: "string",
            description:
              "What the visitor wants to discuss, in their own words. 1–2 sentences.",
          },
          tier: {
            type: "string",
            enum: ["office-hours", "architecture-review"],
            description:
              "Which tier they want to book. Engagement is not bookable via this tool — use submit_contact_request for engagement interest.",
          },
        },
        required: ["topic", "tier"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "submit_contact_request",
      description:
        "Submit a contact request on the visitor's behalf — for engagement interest, general questions, or when they'd rather have Lucas reach out than book a paid session. Requires explicit consent from the visitor with their email.",
      parameters: {
        type: "object",
        properties: {
          email: {
            type: "string",
            description: "Visitor's email address. Must be syntactically valid.",
          },
          topic: {
            type: "string",
            description:
              "Short subject: 'Engagement — MCP for fintech', 'General question', etc.",
          },
          summary: {
            type: "string",
            description:
              "1–3 sentence summary of what they want to discuss, as if writing a short cold email.",
          },
        },
        required: ["email", "topic", "summary"],
      },
    },
  },
];

// ---------------------------------------------------------------------------
// Tool handlers
// ---------------------------------------------------------------------------

type ToolHandler = (
  args: Record<string, unknown>,
  ctx: ToolContext,
) => Promise<ToolResult>;

function isEmail(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

function genReference(): string {
  return `wm-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

const HANDLERS: Record<string, ToolHandler> = {
  async get_service_detail(args) {
    const slug = typeof args.slug === "string" ? args.slug : undefined;
    if (!slug) {
      return { kind: "service_list", data: SERVICES_LIST };
    }
    const svc = getService(slug);
    return { kind: "service_detail", data: svc };
  },

  async get_pricing_tier(args) {
    const slug = typeof args.slug === "string" ? args.slug : undefined;
    if (!slug) {
      return { kind: "pricing_list", data: PRICING_TIERS_LIST };
    }
    const tier = getTier(slug);
    return { kind: "pricing_tier", data: tier };
  },

  async get_platform_capability(args) {
    const slug = typeof args.slug === "string" ? args.slug : undefined;
    const search = typeof args.search === "string" ? args.search : undefined;
    if (slug) {
      const cap = getCapability(slug);
      if (cap) return { kind: "platform_capability", data: cap };
    }
    if (search) {
      return { kind: "platform_search", data: searchCapabilities(search, 5) };
    }
    if (!slug && !search) {
      return { kind: "platform_search", data: CAPABILITIES_LIST.slice(0, 5) };
    }
    return {
      kind: "error",
      data: { message: `No capability matches "${slug ?? search}".` },
    };
  },

  async search_timeline(args) {
    const query = typeof args.query === "string" ? args.query : "";
    const limit = Math.min(
      typeof args.limit === "number" ? args.limit : 5,
      15,
    );
    if (!query.trim()) {
      return {
        kind: "error",
        data: { message: "search_timeline requires a non-empty query." },
      };
    }
    const q = query.toLowerCase();
    const matches = TIMELINE_DATA.filter(
      (e) =>
        e.title.toLowerCase().includes(q) ||
        e.description.toLowerCase().includes(q) ||
        (e.version ?? "").toLowerCase().includes(q) ||
        (e.gap ?? "").toLowerCase().includes(q),
    );
    return {
      kind: "timeline_matches",
      data: {
        query,
        entries: matches.slice(0, limit),
        total: matches.length,
      },
    };
  },

  async request_office_hours_booking(args) {
    const topic = typeof args.topic === "string" ? args.topic.trim() : "";
    const tierSlug = typeof args.tier === "string" ? args.tier : "office-hours";
    if (topic.length < 5) {
      return {
        kind: "error",
        data: {
          message:
            "Topic must be at least 5 characters. Ask the visitor to describe what they want to discuss.",
        },
      };
    }
    if (topic.length > 500) {
      return {
        kind: "error",
        data: { message: "Topic is too long — keep it to 1-2 sentences." },
      };
    }
    const tier = getTier(tierSlug);
    if (!tier) {
      return {
        kind: "error",
        data: { message: `Unknown tier: ${tierSlug}` },
      };
    }
    const { url, isStripe } = resolveCheckoutUrl(tier);
    // Append topic as query param so Lucas sees it on the Stripe dashboard
    // or pre-fills the contact form.
    const sep = url.includes("?") ? "&" : "?";
    const fullUrl = `${url}${sep}client_reference_id=${encodeURIComponent(topic.slice(0, 200))}`;
    return {
      kind: "booking_initiated",
      data: {
        tierName: tier.name,
        tierSlug: tier.slug,
        checkoutUrl: fullUrl,
        isStripe,
        topic,
      },
    };
  },

  async submit_contact_request(args, ctx) {
    const email =
      typeof args.email === "string" ? args.email.trim().toLowerCase() : "";
    const topic = typeof args.topic === "string" ? args.topic.trim() : "";
    const summary = typeof args.summary === "string" ? args.summary.trim() : "";
    if (!isEmail(email)) {
      return {
        kind: "error",
        data: {
          message: "Invalid email address. Ask the visitor to provide a valid email.",
        },
      };
    }
    if (topic.length < 3 || summary.length < 10) {
      return {
        kind: "error",
        data: {
          message:
            "Topic must be at least 3 chars and summary at least 10 chars.",
        },
      };
    }
    if (summary.length > 2000) {
      return {
        kind: "error",
        data: { message: "Summary too long — keep it under 2000 chars." },
      };
    }
    const reference = genReference();
    const kv = getKV();
    const entry = {
      reference,
      timestamp: Date.now(),
      email,
      topic: topic.slice(0, 200),
      summary: summary.slice(0, 2000),
      sessionId: ctx.sessionId,
      pagePath: ctx.pageContext?.path,
    };
    // Store to a list so /admin can surface recent submissions
    try {
      await kv.set(
        `contact:${reference}`,
        JSON.stringify(entry),
        60 * 60 * 24 * 30,
      );
      // Also push onto a lightweight index list (capped by timestamp sort)
      const indexRaw = (await kv.get("contact:index")) ?? "[]";
      const index: string[] = JSON.parse(indexRaw);
      index.unshift(reference);
      await kv.set(
        "contact:index",
        JSON.stringify(index.slice(0, 200)),
        60 * 60 * 24 * 90,
      );
    } catch (e) {
      console.error("[librarian/tools] contact submit KV write failed:", e);
    }
    // TODO: when RESEND_API_KEY is configured, also send an email to Lucas.
    // For now, /admin is the notification surface.
    return {
      kind: "contact_submitted",
      data: { reference, topic, summary },
    };
  },
};

export async function executeTool(
  name: string,
  args: Record<string, unknown>,
  ctx: ToolContext,
): Promise<ToolResult> {
  const handler = HANDLERS[name];
  if (!handler) {
    return {
      kind: "error",
      data: { message: `Unknown tool: ${name}` },
    };
  }
  try {
    return await handler(args, ctx);
  } catch (e) {
    console.error(`[librarian/tools] ${name} failed:`, e);
    return {
      kind: "error",
      data: {
        message: `Tool ${name} failed: ${(e as Error).message ?? "unknown error"}`,
      },
    };
  }
}

// List of tool names (used by Karma ledger for display filters).
export const TOOL_NAMES = TOOL_SCHEMAS.map((t) => t.function.name);
