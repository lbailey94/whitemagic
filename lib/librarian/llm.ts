/**
 * LLM client for the Librarian.
 *
 * Backend: OpenRouter (https://openrouter.ai). One API key, many models.
 * Streams Server-Sent Events; we transcode to our own StreamChunk format.
 *
 * When OPENROUTER_API_KEY is not set, the client runs in MOCK MODE and
 * streams a canned response. This lets the full site run in dev without
 * burning any budget, and lets CI/preview deployments work without keys.
 */

import type { ChatMessage, StreamChunk } from "./types";

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";

// Pricing as of April 2026 for cost estimation. Update when OpenRouter
// adjusts — these drive the budget tracker.
const MODEL_PRICING: Record<
  string,
  { inputPer1M: number; outputPer1M: number }
> = {
  "anthropic/claude-sonnet-4.5": { inputPer1M: 3.0, outputPer1M: 15.0 },
  "openai/gpt-4o": { inputPer1M: 2.5, outputPer1M: 10.0 },
  "mistralai/mistral-large": { inputPer1M: 2.0, outputPer1M: 6.0 },
};

export const DEFAULT_MODEL = "anthropic/claude-sonnet-4.5";

export interface LLMStreamOptions {
  model?: string;
  messages: ChatMessage[];
  maxTokens: number;
  temperature: number;
}

/**
 * Stream LLM output. Yields incremental StreamChunks.
 */
export async function* streamLLM(
  opts: LLMStreamOptions,
): AsyncGenerator<StreamChunk> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = opts.model ?? DEFAULT_MODEL;

  if (!apiKey) {
    yield* mockStream(opts.messages, model);
    return;
  }

  const res = await fetch(OPENROUTER_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://whitemagic.dev",
      "X-Title": "WhiteMagic Librarian",
    },
    body: JSON.stringify({
      model,
      messages: opts.messages,
      max_tokens: opts.maxTokens,
      temperature: opts.temperature,
      stream: true,
      usage: { include: true },
    }),
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "(no body)");
    yield {
      refusal: {
        reason: "internal_error",
        message: `Librarian upstream error (${res.status}): ${text.slice(0, 200)}`,
      },
    };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let inputTokens = 0;
  let outputTokens = 0;

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
          const delta = json?.choices?.[0]?.delta?.content;
          if (typeof delta === "string" && delta.length > 0) {
            yield { delta };
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

  const pricing = MODEL_PRICING[model];
  const costUsd = pricing
    ? (inputTokens * pricing.inputPer1M +
        outputTokens * pricing.outputPer1M) /
      1_000_000
    : 0;

  yield { done: { inputTokens, outputTokens, costUsd, model } };
}

/**
 * Mock stream for dev / no-API-key mode. Chunks a canned response.
 */
async function* mockStream(
  messages: ChatMessage[],
  model: string,
): AsyncGenerator<StreamChunk> {
  const last = messages[messages.length - 1]?.content ?? "";
  const canned = `(Mock Librarian — OPENROUTER_API_KEY not configured.)

You asked: "${last.slice(0, 140)}${last.length > 140 ? "..." : ""}"

I'd normally answer by drawing on the WhiteMagic site corpus (services, pricing, timeline, open-source components). Once Lucas sets OPENROUTER_API_KEY in the Vercel environment, I'll start answering for real — with source citations to specific pages.

For now: the site itself is your best source. Try /services for what's offered, /pricing for tiers, or /timeline for the technical history.

If this is a real decision point for you, ask Lucas directly at /contact.`;

  const words = canned.split(/(\s+)/);
  for (const w of words) {
    yield { delta: w };
    await new Promise((r) => setTimeout(r, 15));
  }
  yield {
    done: {
      inputTokens: 0,
      outputTokens: words.length,
      costUsd: 0,
      model: `${model} (mock)`,
    },
  };
}
