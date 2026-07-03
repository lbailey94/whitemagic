/**
 * LLM client for the Librarian — multi-provider, env-driven.
 *
 * Providers (selected via LLM_PROVIDER env var):
 *   - "stub"     (default): keyword-routed mock that uses bridge tools.
 *   - "openrouter": OpenRouter API (Anthropic, OpenAI, Mistral, ...).
 *   - "ollama":   Self-hosted Ollama on Hetzner (e.g. llama3, qwen2.5).
 *
 * All providers accept the same OpenAI-compatible tool schema and stream
 * the same LlmChunk format. The route /api/librarian/chat calls streamLLM
 * once per LLM round-trip and orchestrates multi-turn tool loops.
 *
 * Stream protocol: yields LlmChunk values. The route transcodes to the
 * public StreamChunk format after executing any tool calls.
 */

import type { ChatMessage } from "./types";

// ─── Provider selection ─────────────────────────────────────────
export type LLMProvider = "stub" | "openrouter" | "ollama";

export function getLLMProvider(): LLMProvider {
  const p = process.env.LLM_PROVIDER?.toLowerCase();
  if (p === "openrouter" || p === "ollama" || p === "stub") return p;
  // Auto-detect: if OpenRouter key is set, use it. If Ollama URL is set, use it.
  if (process.env.OPENROUTER_API_KEY) return "openrouter";
  if (process.env.OLLAMA_BASE_URL) return "ollama";
  return "stub";
}

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";

// Pricing for cost estimation — update when OpenRouter adjusts.
const MODEL_PRICING: Record<
  string,
  { inputPer1M: number; outputPer1M: number }
> = {
  "anthropic/claude-sonnet-4.5": { inputPer1M: 3.0, outputPer1M: 15.0 },
  "openai/gpt-4o": { inputPer1M: 2.5, outputPer1M: 10.0 },
  "mistralai/mistral-large": { inputPer1M: 2.0, outputPer1M: 6.0 },
  // Local Ollama models are free; cost = 0.
  "llama3.1:8b": { inputPer1M: 0, outputPer1M: 0 },
  "qwen2.5:7b": { inputPer1M: 0, outputPer1M: 0 },
};

export const DEFAULT_MODEL = "anthropic/claude-sonnet-4.5";
export const DEFAULT_OLLAMA_MODEL = "llama3.1:8b";

export interface PendingToolCall {
  id: string;
  name: string;
  /** Fully assembled JSON arguments string. Parse before use. */
  arguments: string;
}

export type LlmChunk =
  | { kind: "delta"; text: string }
  | { kind: "tool_calls"; calls: PendingToolCall[] }
  | {
      kind: "done";
      inputTokens: number;
      outputTokens: number;
      costUsd: number;
      model: string;
      provider: LLMProvider;
      finishReason: string | null;
    }
  | { kind: "error"; message: string };

export interface LLMStreamOptions {
  model?: string;
  messages: ChatMessage[];
  maxTokens: number;
  temperature: number;
  tools?: unknown[]; // OpenAI-compatible tool schemas
}

/**
 * Stream one LLM round-trip. Dispatches to the configured provider
 * (env-driven). Yields text deltas, then exactly one of:
 *   - tool_calls (LLM wants to invoke tools; route must execute + loop)
 *   - done (final response; no more tools)
 */
export async function* streamLLM(
  opts: LLMStreamOptions,
): AsyncGenerator<LlmChunk> {
  const provider = getLLMProvider();

  if (provider === "stub") {
    yield* stubStream(opts.messages, !!opts.tools);
    return;
  }
  if (provider === "ollama") {
    yield* ollamaStream(opts);
    return;
  }
  // openrouter
  yield* openRouterStream(opts);
}

/**
 * OpenRouter provider — proxies to Anthropic, OpenAI, Mistral, etc.
 */
async function* openRouterStream(
  opts: LLMStreamOptions,
): AsyncGenerator<LlmChunk> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = opts.model ?? DEFAULT_MODEL;

  const body: Record<string, unknown> = {
    model,
    messages: opts.messages,
    max_tokens: opts.maxTokens,
    temperature: opts.temperature,
    stream: true,
    usage: { include: true },
  };
  if (opts.tools && opts.tools.length > 0) {
    body.tools = opts.tools;
    body.tool_choice = "auto";
  }

  const res = await fetch(OPENROUTER_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://whitemagic.dev",
      "X-Title": "WhiteMagic Librarian",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "(no body)");
    yield {
      kind: "error",
      message: `Librarian upstream error (${res.status}): ${text.slice(0, 200)}`,
    };
    return;
  }

  yield* parseOpenAIStream(res.body, model, "openrouter");
}

/**
 * Ollama provider — self-hosted local LLM. Uses Ollama's OpenAI-compatible
 * /v1/chat/completions endpoint. Set OLLAMA_BASE_URL (default http://localhost:11434)
 * and OLLAMA_MODEL (default llama3.1:8b) in the environment.
 *
 * No API key required. Cost is always $0.
 */
async function* ollamaStream(
  opts: LLMStreamOptions,
): AsyncGenerator<LlmChunk> {
  const baseUrl = process.env.OLLAMA_BASE_URL || "http://localhost:11434";
  const model = opts.model ?? process.env.OLLAMA_MODEL ?? DEFAULT_OLLAMA_MODEL;
  const url = `${baseUrl.replace(/\/$/, "")}/v1/chat/completions`;

  const body: Record<string, unknown> = {
    model,
    messages: opts.messages,
    max_tokens: opts.maxTokens,
    temperature: opts.temperature,
    stream: true,
  };
  if (opts.tools && opts.tools.length > 0) {
    body.tools = opts.tools;
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    yield {
      kind: "error",
      message: `Cannot reach Ollama at ${url}. Is the Ollama server running and accessible? Set OLLAMA_BASE_URL or run: ollama serve. Error: ${
        e instanceof Error ? e.message : String(e)
      }`,
    };
    return;
  }

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "(no body)");
    yield {
      kind: "error",
      message: `Ollama error (${res.status}): ${text.slice(0, 200)}`,
    };
    return;
  }

  yield* parseOpenAIStream(res.body, model, "ollama");
}

/**
 * Shared OpenAI-compatible stream parser. Used by both OpenRouter and Ollama
 * since they share the same wire format.
 */
async function* parseOpenAIStream(
  body: ReadableStream<Uint8Array>,
  model: string,
  provider: "openrouter" | "ollama",
): AsyncGenerator<LlmChunk> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let inputTokens = 0;
  let outputTokens = 0;
  let finishReason: string | null = null;
  const toolCallsByIndex: Record<number, PendingToolCall> = {};

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;
        const payload = trimmed.slice(5).trim();
        if (payload === "[DONE]") continue;
        try {
          const json = JSON.parse(payload);
          const choice = json?.choices?.[0];
          const delta = choice?.delta;

          // Text delta
          const textDelta = delta?.content;
          if (typeof textDelta === "string" && textDelta.length > 0) {
            yield { kind: "delta", text: textDelta };
          }

          // Tool-call deltas
          const tcDeltas = delta?.tool_calls;
          if (Array.isArray(tcDeltas)) {
            for (const tc of tcDeltas) {
              const idx: number = typeof tc.index === "number" ? tc.index : 0;
              if (!toolCallsByIndex[idx]) {
                toolCallsByIndex[idx] = {
                  id: tc.id ?? `call_${idx}`,
                  name: tc.function?.name ?? "",
                  arguments: "",
                };
              }
              const entry = toolCallsByIndex[idx];
              if (tc.id) entry.id = tc.id;
              if (tc.function?.name) entry.name = tc.function.name;
              if (typeof tc.function?.arguments === "string") {
                entry.arguments += tc.function.arguments;
              }
            }
          }

          if (typeof choice?.finish_reason === "string") {
            finishReason = choice.finish_reason;
          }

          if (json?.usage) {
            inputTokens = json.usage.prompt_tokens ?? inputTokens;
            outputTokens = json.usage.completion_tokens ?? outputTokens;
          }
        } catch {
          // swallow parse errors for partial frames
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  const calls = Object.keys(toolCallsByIndex)
    .sort((a, b) => Number(a) - Number(b))
    .map((k) => toolCallsByIndex[Number(k)])
    .filter((c) => c.name.length > 0);

  if (calls.length > 0 && finishReason === "tool_calls") {
    yield { kind: "tool_calls", calls };
  }

  const pricing = MODEL_PRICING[model];
  const costUsd = pricing
    ? (inputTokens * pricing.inputPer1M + outputTokens * pricing.outputPer1M) /
      1_000_000
    : 0;

  yield {
    kind: "done",
    inputTokens,
    outputTokens,
    costUsd,
    model,
    provider,
    finishReason,
  };
}

/**
 * Stub LLM for development, demos, and the default config.
 *
 * Uses simple keyword matching to decide which bridge tool to call.
 * On the second round (after tool results), streams a short natural-
 * language summary. Never loops forever.
 *
 * Works with the bridge tools (not the legacy librarian tools) so the
 * librarian can actually demonstrate real bridge invocations even
 * without a real LLM.
 */
async function* stubStream(
  messages: ChatMessage[],
  toolsAvailable: boolean,
): AsyncGenerator<LlmChunk> {
  const last = messages[messages.length - 1]?.content ?? "";
  const alreadyToolLooped = messages.some(
    (m) => (m as unknown as { role: string }).role === "tool",
  );

  // First round: emit a tool call based on keyword matching.
  if (toolsAvailable && !alreadyToolLooped && last.length > 0) {
    const { name, args } = pickStubTool(last);
    yield {
      kind: "tool_calls",
      calls: [
        {
          id: `stub_call_${Date.now()}`,
          name,
          arguments: JSON.stringify(args),
        },
      ],
    };
    yield {
      kind: "done",
      inputTokens: 0,
      outputTokens: 0,
      costUsd: 0,
      model: "stub-keyword-router",
      provider: "stub",
      finishReason: "tool_calls",
    };
    return;
  }

  // Second round (after tool results came back): stream a short
  // natural-language summary.
  const lastToolResult = [...messages]
    .reverse()
    .find((m) => (m as unknown as { role: string }).role === "tool");
  const toolName = (() => {
    const lastAssistant = [...messages]
      .reverse()
      .find((m) => m.role === "assistant");
    const tc = (lastAssistant as unknown as { tool_calls?: Array<{ function: { name: string } }> })
      ?.tool_calls?.[0]?.function?.name;
    return tc ?? "the bridge";
  })();

  let resultSummary = "(no result)";
  if (lastToolResult && typeof lastToolResult.content === "string") {
    try {
      const parsed = JSON.parse(lastToolResult.content);
      resultSummary = JSON.stringify(parsed).slice(0, 200);
    } catch {
      resultSummary = lastToolResult.content.slice(0, 200);
    }
  }

  const canned = `(Stub Librarian — no LLM provider configured.)

You asked: "${last.slice(0, 140)}${last.length > 140 ? "..." : ""}"

I called **${toolName}** for you. Result: \`${resultSummary}\`.

To enable a real LLM, set one of:
  - \`LLM_PROVIDER=openrouter\` + \`OPENROUTER_API_KEY=...\`
  - \`LLM_PROVIDER=ollama\` + \`OLLAMA_BASE_URL=http://your-hetzner-box:11434\`

For real decisions, reach out at /contact.`;

  const words = canned.split(/(\s+)/);
  for (const w of words) {
    yield { kind: "delta", text: w };
    await new Promise((r) => setTimeout(r, 8));
  }
  yield {
    kind: "done",
    inputTokens: 0,
    outputTokens: words.length,
    costUsd: 0,
    model: "stub-keyword-router",
    provider: "stub",
    finishReason: "stop",
  };
}

/**
 * Stub keyword router. Maps user messages to one of the curated bridge
 * tools based on regex matching. If no clear match, defaults to
 * `dharma_list_principles` (always a safe, useful response).
 */
function pickStubTool(userMessage: string): {
  name: string;
  args: Record<string, unknown>;
} {
  const lower = userMessage.toLowerCase();

  // Dharma / ethics
  if (/\b(ethic|dharma|karma|harm|ahimsa|consent|moral)\b/.test(lower)) {
    if (/check|boundary|action|deploy|push|commit/.test(lower)) {
      return {
        name: "dharma_check_boundaries",
        args: { action: { type: "user_request", source: userMessage.slice(0, 80) } },
      };
    }
    return { name: "dharma_list_principles", args: {} };
  }

  // Memory / archaeology
  if (/\b(memory|memories|archive|excavat|read|recall|find)\b/.test(lower)) {
    if (/recent|today|just|latest/.test(lower)) {
      return { name: "archaeology_recent_reads", args: { limit: 10 } };
    }
    return {
      name: "archaeology_search",
      args: { query: userMessage.slice(0, 60), limit: 5 },
    };
  }

  // Sessions
  if (/\b(session|handoff|context|where are we|current|state)\b/.test(lower)) {
    return { name: "session_get_context", args: {} };
  }

  // Zodiac
  if (/\b(zodiac|core|aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)\b/.test(lower)) {
    if (/consult|council|advice|wisdom|ask/.test(lower)) {
      return { name: "zodiac_consult_council", args: { query: userMessage.slice(0, 120) } };
    }
    return { name: "zodiac_list_cores", args: {} };
  }

  // Wisdom / I Ching
  if (/\b(iching|i ching|hexagram|divin|oracle|wisdom|guidance|advice)\b/.test(lower)) {
    return {
      name: "consult_iching",
      args: { question: userMessage.slice(0, 120), method: "coins" },
    };
  }

  // Predictions / forecasting
  if (/\b(predict|forecast|future|will |tomorrow|next week|outlook|prescience)\b/.test(lower)) {
    return { name: "gana_dipper", args: { task: "predict" } };
  }

  // Intelligence briefing
  if (/\b(briefing|daily|today|what.{0,5}new|insight|digest)\b/.test(lower)) {
    return { name: "gana_dipper", args: { task: "intelligence_briefing" } };
  }

  // Reasoning
  if (/\b(analy|reason|logic|pattern|why|how should|compare)\b/.test(lower)) {
    return {
      name: "apply_reasoning_methods",
      args: { question: userMessage.slice(0, 200) },
    };
  }

  // Meditation / pause
  if (/\b(pause|breath|still|meditat|calm|reflect)\b/.test(lower)) {
    return { name: "meditation_pause", args: { duration: 5 } };
  }

  // Time
  if (/\b(time|date|today|when|now|hour)\b/.test(lower)) {
    return { name: "get_system_time", args: {} };
  }

  // Metrics
  if (/\b(metric|stats|performance|benchmark)\b/.test(lower)) {
    return { name: "get_metrics_summary", args: {} };
  }

  // Default: useful safe fallback
  return { name: "dharma_list_principles", args: {} };
}
