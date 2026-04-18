/**
 * POST /api/librarian/chat
 *
 * Streaming chat endpoint for the Librarian. Pipeline:
 *   kill switch → dharma → rate limit → monthly budget → LLM → record spend
 *
 * Returns newline-delimited JSON (each line is a StreamChunk).
 */

import type { NextRequest } from "next/server";
import type { ChatMessage, ChatRequest, StreamChunk } from "@/lib/librarian/types";
import { checkDharma } from "@/lib/librarian/dharma";
import { checkRateLimit } from "@/lib/librarian/rate-limit";
import { getBudget, recordSpend } from "@/lib/librarian/budget";
import { streamLLM } from "@/lib/librarian/llm";
import { LIBRARIAN_CONFIG } from "@/lib/librarian/persona";
import { serializeCorpus } from "@/lib/librarian/corpus";

export const runtime = "nodejs"; // budget/rate-limit use fetch + KV; nodejs is safest for streams
export const dynamic = "force-dynamic";

function clientIp(req: NextRequest): string {
  // Vercel / Cloudflare forward the real IP here.
  const xff = req.headers.get("x-forwarded-for");
  if (xff) return xff.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "unknown";
}

function jsonLine(chunk: StreamChunk): string {
  return JSON.stringify(chunk) + "\n";
}

function refusalStream(chunk: StreamChunk): Response {
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(jsonLine(chunk)));
      controller.close();
    },
  });
  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "application/x-ndjson; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

export async function POST(req: NextRequest): Promise<Response> {
  // 1. Kill switch
  if (process.env.LIBRARIAN_DISABLED === "1") {
    return refusalStream({
      refusal: {
        reason: "kill_switch",
        message:
          "The Librarian is temporarily offline. Please reach Lucas directly at /contact.",
      },
    });
  }

  let body: ChatRequest;
  try {
    body = (await req.json()) as ChatRequest;
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  const messages = Array.isArray(body.messages) ? body.messages : [];
  if (messages.length === 0) {
    return new Response("Empty messages", { status: 400 });
  }
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  if (!lastUser) {
    return new Response("No user message", { status: 400 });
  }

  // 2. Dharma
  const dharma = checkDharma(lastUser.content);
  if (!dharma.allow) {
    return refusalStream({
      refusal: {
        reason: "dharma",
        message: dharma.message ?? "I can't help with that.",
      },
    });
  }

  // 3. Rate limit
  const ip = clientIp(req);
  const rl = await checkRateLimit(ip, body.sessionId);
  if (!rl.allow) {
    const scope = rl.scope ?? "ip_daily";
    const msg =
      scope === "ip_daily"
        ? "You've reached the daily message limit for your IP. Try again tomorrow, or reach Lucas at /contact."
        : "You've had a long conversation with me. Take a break and start fresh later, or reach Lucas at /contact.";
    return refusalStream({
      refusal: {
        reason: scope === "ip_daily" ? "rate_limit_ip" : "rate_limit_session",
        message: msg,
      },
    });
  }

  // 4. Monthly budget check
  const budget = await getBudget();
  if (budget.exceeded) {
    return refusalStream({
      refusal: {
        reason: "monthly_budget",
        message:
          "The Librarian has reached its monthly budget. It resets on the 1st of next month. Reach Lucas directly at /contact.",
      },
    });
  }

  // 5. Build LLM request
  const systemWithCorpus: ChatMessage = {
    role: "system",
    content: `${LIBRARIAN_CONFIG.systemPrompt}\n\n# Corpus\n\n${serializeCorpus()}`,
  };
  const llmMessages: ChatMessage[] = [systemWithCorpus, ...messages];

  // 6. Stream LLM → client
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        for await (const chunk of streamLLM({
          messages: llmMessages,
          maxTokens: LIBRARIAN_CONFIG.maxTokensPerResponse,
          temperature: LIBRARIAN_CONFIG.temperature,
        })) {
          controller.enqueue(encoder.encode(jsonLine(chunk)));
          if (chunk.done) {
            // Record spend after the stream completes. Fire and forget —
            // a failure here shouldn't fail the user's response.
            recordSpend(chunk.done.costUsd).catch((e) => {
              console.error("[librarian] recordSpend failed:", e);
            });
          }
        }
      } catch (e) {
        console.error("[librarian] stream error:", e);
        controller.enqueue(
          encoder.encode(
            jsonLine({
              refusal: {
                reason: "internal_error",
                message:
                  "Something went wrong on my end. Please try again, or reach Lucas at /contact.",
              },
            }),
          ),
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "application/x-ndjson; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
