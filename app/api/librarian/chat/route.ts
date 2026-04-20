/**
 * POST /api/librarian/chat — streaming chat with tool execution loop.
 *
 * Pipeline:
 *   kill switch → dharma(user msg) → rate limit → monthly budget
 *   → loop up to MAX_ITERS:
 *       streamLLM → if tool_calls: execute, feed back, continue
 *                 → else: done, flush
 *   → record spend + karma
 *
 * Output: newline-delimited JSON chunks (StreamChunk format).
 */

import type { NextRequest } from "next/server";
import type { ChatMessage, ChatRequest, StreamChunk } from "@/lib/librarian/types";
import { checkDharma } from "@/lib/librarian/dharma";
import { checkRateLimit } from "@/lib/librarian/rate-limit";
import { getBudget, recordSpend } from "@/lib/librarian/budget";
import { streamLLM, type PendingToolCall } from "@/lib/librarian/llm";
import { LIBRARIAN_CONFIG } from "@/lib/librarian/persona";
import { serializeCorpus } from "@/lib/librarian/corpus";
import { TOOL_SCHEMAS, executeTool } from "@/lib/librarian/tools";
import { recordKarma } from "@/lib/librarian/karma";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_TOOL_ITERATIONS = 3;

function clientIp(req: NextRequest): string {
  const xff = req.headers.get("x-forwarded-for");
  if (xff) return xff.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "unknown";
}

function jsonLine(chunk: StreamChunk): Uint8Array {
  return new TextEncoder().encode(JSON.stringify(chunk) + "\n");
}

function refusalStream(chunk: StreamChunk): Response {
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(jsonLine(chunk));
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

  // 2. Dharma on last user message
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

  // 4. Monthly budget
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

  // 5. Build system prompt with corpus + optional page context
  const contextLine = body.pageContext?.path
    ? `\n\n# Visitor context\nThe visitor is currently on \`${body.pageContext.path}\`${body.pageContext.title ? ` (page: "${body.pageContext.title}")` : ""}. When relevant, tailor your answer to what they're likely looking at.`
    : "";
  const systemMsg: ChatMessage = {
    role: "system",
    content: `${LIBRARIAN_CONFIG.systemPrompt}\n\n# Corpus\n\n${serializeCorpus()}${contextLine}`,
  };
  // Conversation state for the tool loop — starts with system + user turns.
  const conversation: ChatMessage[] = [systemMsg, ...messages];

  const toolCtx = {
    sessionId: body.sessionId,
    pageContext: body.pageContext,
    ip,
  };

  // 6. Stream with tool-execution loop
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let totalCost = 0;
      let totalInputTokens = 0;
      let totalOutputTokens = 0;
      let lastModel = "";

      try {
        for (let iter = 0; iter < MAX_TOOL_ITERATIONS + 1; iter++) {
          const pendingToolCalls: PendingToolCall[] = [];
          let finishedWithTools = false;

          for await (const chunk of streamLLM({
            messages: conversation,
            maxTokens: LIBRARIAN_CONFIG.maxTokensPerResponse,
            temperature: LIBRARIAN_CONFIG.temperature,
            tools: iter < MAX_TOOL_ITERATIONS ? TOOL_SCHEMAS : undefined,
          })) {
            if (chunk.kind === "delta") {
              controller.enqueue(jsonLine({ delta: chunk.text }));
            } else if (chunk.kind === "tool_calls") {
              pendingToolCalls.push(...chunk.calls);
              finishedWithTools = true;
            } else if (chunk.kind === "error") {
              controller.enqueue(
                jsonLine({
                  refusal: {
                    reason: "internal_error",
                    message: chunk.message,
                  },
                }),
              );
              controller.close();
              return;
            } else if (chunk.kind === "done") {
              totalInputTokens += chunk.inputTokens;
              totalOutputTokens += chunk.outputTokens;
              totalCost += chunk.costUsd;
              lastModel = chunk.model;
            }
          }

          if (!finishedWithTools || pendingToolCalls.length === 0) {
            break; // natural end — LLM produced a final answer
          }

          // Execute tools, emit chunks, and append to conversation.
          const assistantToolMsg: ChatMessage = {
            role: "assistant",
            content: "",
          };
          // Attach tool_calls payload for the provider on the next turn.
          (
            assistantToolMsg as unknown as {
              tool_calls: unknown[];
            }
          ).tool_calls = pendingToolCalls.map((c) => ({
            id: c.id,
            type: "function",
            function: { name: c.name, arguments: c.arguments },
          }));
          conversation.push(assistantToolMsg);

          for (const call of pendingToolCalls) {
            let parsedArgs: Record<string, unknown> = {};
            try {
              parsedArgs = call.arguments ? JSON.parse(call.arguments) : {};
            } catch {
              parsedArgs = {};
            }
            const argsPreview = JSON.stringify(parsedArgs).slice(0, 120);

            controller.enqueue(
              jsonLine({
                tool_call: {
                  id: call.id,
                  name: call.name,
                  argsPreview,
                },
              }),
            );

            const t0 = Date.now();
            const result = await executeTool(call.name, parsedArgs, toolCtx);
            const durationMs = Date.now() - t0;

            controller.enqueue(
              jsonLine({
                tool_result: {
                  callId: call.id,
                  name: call.name,
                  result,
                },
              }),
            );

            // Append tool result as a "tool" role message for the LLM's next turn.
            const toolMsg = {
              role: "tool" as const,
              content: JSON.stringify(result),
              tool_call_id: call.id,
            };
            conversation.push(toolMsg as unknown as ChatMessage);

            // Record karma (fire-and-forget)
            recordKarma({
              tool: call.name,
              argsPreview,
              resultKind: result.kind,
              durationMs,
              dharmaOk: true,
              sessionId: body.sessionId,
            }).catch((e) =>
              console.error("[librarian] recordKarma failed:", e),
            );
          }
          // Loop continues — LLM gets the tool results and can produce
          // its final natural-language answer (or more tool calls).
        }

        // Emit final done chunk
        controller.enqueue(
          jsonLine({
            done: {
              inputTokens: totalInputTokens,
              outputTokens: totalOutputTokens,
              costUsd: totalCost,
              model: lastModel,
            },
          }),
        );

        if (totalCost > 0) {
          recordSpend(totalCost).catch((e) =>
            console.error("[librarian] recordSpend failed:", e),
          );
        }
      } catch (e) {
        console.error("[librarian] stream error:", e);
        controller.enqueue(
          jsonLine({
            refusal: {
              reason: "internal_error",
              message:
                "Something went wrong on my end. Please try again, or reach Lucas at /contact.",
            },
          }),
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
