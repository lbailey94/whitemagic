/**
 * LLM client for the Librarian — now with tool-calling.
 *
 * Backend: OpenRouter (OpenAI-compatible). One round-trip per call; the
 * API route orchestrates multi-turn tool loops by calling streamLLM again
 * with updated messages.
 *
 * Stream protocol:
 *   This function yields LlmChunk values. The route transcodes to the
 *   public StreamChunk format after executing any tool calls.
 */

import type { ChatMessage } from "./types";

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";

// Pricing for cost estimation — update when OpenRouter adjusts.
const MODEL_PRICING: Record<
  string,
  { inputPer1M: number; outputPer1M: number }
> = {
  "anthropic/claude-sonnet-4.5": { inputPer1M: 3.0, outputPer1M: 15.0 },
  "openai/gpt-4o": { inputPer1M: 2.5, outputPer1M: 10.0 },
  "mistralai/mistral-large": { inputPer1M: 2.0, outputPer1M: 6.0 },
};

export const DEFAULT_MODEL = "anthropic/claude-sonnet-4.5";

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
      finishReason: string | null;
    }
  | { kind: "error"; message: string };

export interface LLMStreamOptions {
  model?: string;
  messages: ChatMessage[];
  maxTokens: number;
  temperature: number;
  tools?: unknown[]; // OpenAI-compatible tool schemas; see tools.ts TOOL_SCHEMAS
}

/**
 * Stream one LLM round-trip. Yields text deltas, then exactly one of:
 *   - tool_calls (LLM wants to invoke tools; route must execute + loop)
 *   - done (final response; no more tools)
 */
export async function* streamLLM(
  opts: LLMStreamOptions,
): AsyncGenerator<LlmChunk> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = opts.model ?? DEFAULT_MODEL;

  if (!apiKey) {
    yield* mockStream(opts.messages, model, !!opts.tools);
    return;
  }

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

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let inputTokens = 0;
  let outputTokens = 0;
  let finishReason: string | null = null;
  // Accumulator for streamed tool calls keyed by index.
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

          // Tool-call deltas (OpenAI format: streamed incrementally per index)
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

  // Emit accumulated tool calls (if any) before done.
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
    finishReason,
  };
}

/**
 * Mock stream for dev / no-API-key mode.
 *
 * In non-tool mode: streams a canned text response.
 * In tool mode: emits a fake tool_call for get_service_detail so the UI
 * can be exercised end-to-end without a real LLM.
 */
async function* mockStream(
  messages: ChatMessage[],
  model: string,
  toolsAvailable: boolean,
): AsyncGenerator<LlmChunk> {
  const last = messages[messages.length - 1]?.content ?? "";

  // If tools are available AND this is the first LLM round (no prior tool
  // messages in the conversation), fake a tool call. On subsequent rounds
  // (after tool results come back), fall through to a canned text response
  // so the mock doesn't loop forever.
  const alreadyToolLooped = messages.some(
    (m) => (m as unknown as { role: string }).role === "tool",
  );

  if (toolsAvailable && !alreadyToolLooped && last.length > 0) {
    // Heuristic: guess which tool the user probably wants so the mock feels
    // semi-realistic during development.
    const lower = last.toLowerCase();
    let name = "get_service_detail";
    let args: Record<string, unknown> = {};
    if (/pric|cost|tier|office hours|architecture review/i.test(lower)) {
      name = "get_pricing_tier";
    } else if (/timeline|when|ship|release|v\d/i.test(lower)) {
      name = "search_timeline";
      args = { query: last.slice(0, 60) };
    } else if (/dharma|karma|harmony|gana|gnosis|circuit/i.test(lower)) {
      name = "get_platform_capability";
      args = { search: last.slice(0, 60) };
    }
    yield {
      kind: "tool_calls",
      calls: [
        {
          id: `mock_call_${Date.now()}`,
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
      model: `${model} (mock)`,
      finishReason: "tool_calls",
    };
    return;
  }

  const canned = `(Mock Librarian — OPENROUTER_API_KEY not configured.)

You asked: "${last.slice(0, 140)}${last.length > 140 ? "..." : ""}"

Once the API key is set in the Vercel environment, I'll answer for real. In the meantime, try /services for consulting tracks, /pricing for tiers, or /timeline for the technical history.

If this is a real decision point, reach out directly at /contact.`;

  const words = canned.split(/(\s+)/);
  for (const w of words) {
    yield { kind: "delta", text: w };
    await new Promise((r) => setTimeout(r, 10));
  }
  yield {
    kind: "done",
    inputTokens: 0,
    outputTokens: words.length,
    costUsd: 0,
    model: `${model} (mock)`,
    finishReason: "stop",
  };
}
