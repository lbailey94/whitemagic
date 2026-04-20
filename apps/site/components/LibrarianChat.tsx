"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname } from "next/navigation";
import { Send, Loader2, AlertCircle, Wrench } from "lucide-react";
import type { ChatMessage, StreamChunk } from "@/lib/librarian/types";
import { ToolResultCard } from "./librarian/ToolCards";

function genSessionId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `sess-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

type ToolCardData = { callId: string; name: string; result: unknown };
type ToolCallIndicator = { callId: string; name: string; argsPreview: string };

interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  refusal?: { reason: string; message: string };
  toolCalls?: ToolCallIndicator[]; // tools the LLM called during this turn
  toolResults?: ToolCardData[]; // results rendered as cards
}

const INITIAL_GREETING: DisplayMessage = {
  id: "greet-0",
  role: "assistant",
  content:
    "Hi — I'm the Librarian for WhiteMagic Labs. Ask me about services, pricing, the timeline, or how a specific capability works — I can pull the details inline. For anything I can't answer, I'll point you at Lucas.",
};

export interface LibrarianChatProps {
  /** Optional height class override. Defaults to full-page embed sizing. */
  heightClass?: string;
  /** Persist conversation to sessionStorage under this key. */
  storageKey?: string;
  /** Initial placeholder text. */
  placeholder?: string;
}

export function LibrarianChat({
  heightClass = "h-[70vh] min-h-[520px]",
  storageKey,
  placeholder = "Ask the Librarian…",
}: LibrarianChatProps) {
  const pathname = usePathname();
  const [messages, setMessages] = useState<DisplayMessage[]>(() =>
    loadFromStorage(storageKey) ?? [INITIAL_GREETING],
  );
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sessionId] = useState(genSessionId);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Persist to sessionStorage (debounced via effect).
  useEffect(() => {
    if (!storageKey || typeof window === "undefined") return;
    try {
      window.sessionStorage.setItem(storageKey, JSON.stringify(messages));
    } catch {
      // ignore quota / private-mode errors
    }
  }, [messages, storageKey]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, streaming]);

  const send = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || streaming) return;

    const userMsg: DisplayMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    const assistantMsg: DisplayMessage = {
      id: `a-${Date.now()}`,
      role: "assistant",
      content: "",
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setStreaming(true);

    // Build conversation history for the LLM — role/content only (DisplayMessage
    // has extra UI fields we don't send). Skip the greeting and empty assistant
    // placeholders.
    const priorForLLM: ChatMessage[] = [...messages, userMsg]
      .filter((m) => m.id !== "greet-0" && m.content.length > 0)
      .map(({ role, content }) => ({ role, content }));

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/librarian/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: priorForLLM,
          sessionId,
          pageContext: { path: pathname ?? "/" },
        }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`Librarian returned ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          let chunk: StreamChunk;
          try {
            chunk = JSON.parse(line) as StreamChunk;
          } catch {
            continue;
          }
          if (chunk.refusal) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      content: chunk.refusal!.message,
                      refusal: chunk.refusal,
                    }
                  : m,
              ),
            );
          } else if (chunk.delta) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: m.content + chunk.delta }
                  : m,
              ),
            );
          } else if (chunk.tool_call) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      toolCalls: [
                        ...(m.toolCalls ?? []),
                        {
                          callId: chunk.tool_call!.id,
                          name: chunk.tool_call!.name,
                          argsPreview: chunk.tool_call!.argsPreview,
                        },
                      ],
                    }
                  : m,
              ),
            );
          } else if (chunk.tool_result) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      toolResults: [
                        ...(m.toolResults ?? []),
                        {
                          callId: chunk.tool_result!.callId,
                          name: chunk.tool_result!.name,
                          result: chunk.tool_result!.result,
                        },
                      ],
                    }
                  : m,
              ),
            );
          }
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id
            ? {
                ...m,
                content:
                  "Something went wrong on my end. Please try again, or reach Lucas at /contact.",
                refusal: {
                  reason: "internal_error",
                  message: "client error",
                },
              }
            : m,
        ),
      );
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, streaming, messages, sessionId, pathname]);

  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i].id;
    }
    return null;
  }, [messages]);

  return (
    <div
      className={`flex ${heightClass} flex-col overflow-hidden rounded-2xl border border-border-light bg-surface`}
    >
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto p-5 md:p-6"
      >
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            streaming={streaming && m.id === lastAssistantId}
          />
        ))}
        {streaming &&
          messages[messages.length - 1]?.role === "assistant" &&
          messages[messages.length - 1]?.content === "" &&
          !(messages[messages.length - 1]?.toolCalls?.length) && (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>Thinking…</span>
            </div>
          )}
      </div>

      <form
        className="border-t border-border-light bg-surface-alt p-4"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            placeholder={placeholder}
            rows={2}
            disabled={streaming}
            className="flex-1 resize-none rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg placeholder:text-muted focus:border-lavender focus:outline-none focus:ring-1 focus:ring-lavender disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="btn-primary h-[62px] shrink-0 px-4"
            aria-label="Send"
          >
            {streaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
        <p className="mt-2 text-xs text-muted">
          Scope: public site + open-source components. Not for private Lucas
          material. Conversations reset when you close this tab.
        </p>
      </form>
    </div>
  );
}

function MessageBubble({
  message,
  streaming,
}: {
  message: DisplayMessage;
  streaming: boolean;
}) {
  const isUser = message.role === "user";
  const isRefusal = !!message.refusal;
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={isUser ? "max-w-[85%]" : "w-full max-w-[92%]"}>
        <div
          className={`rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-lavender text-white"
              : isRefusal
                ? "border border-amber-300/50 bg-amber-50/40 text-fg dark:bg-amber-950/20"
                : "bg-surface-alt text-fg"
          }`}
        >
          {isRefusal && (
            <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-amber-700 dark:text-amber-300">
              <AlertCircle className="h-3.5 w-3.5" />
              <span>{refusalLabel(message.refusal!.reason)}</span>
            </div>
          )}
          {/* Tool-call indicators appear before the assistant text */}
          {!isUser &&
            message.toolCalls?.map((tc) => (
              <ToolCallIndicatorPill key={tc.callId} name={tc.name} />
            ))}
          <div className="whitespace-pre-wrap">
            {message.content}
            {!isUser &&
              !isRefusal &&
              streaming &&
              message.content.length > 0 && (
                <span className="ml-0.5 inline-block h-3.5 w-1 animate-pulse bg-current align-middle" />
              )}
          </div>
        </div>
        {/* Tool-result cards render after the bubble, outside it, full width */}
        {!isUser &&
          message.toolResults?.map((tr) => (
            <div key={tr.callId} className="mt-1">
              <ToolResultCard
                result={tr.result as { kind: string; data: unknown } | null}
              />
            </div>
          ))}
      </div>
    </div>
  );
}

function ToolCallIndicatorPill({ name }: { name: string }) {
  return (
    <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-lavender/30 bg-lavender/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-lavender">
      <Wrench className="h-2.5 w-2.5" />
      <span>{name}</span>
    </div>
  );
}

function refusalLabel(reason: string): string {
  switch (reason) {
    case "dharma":
      return "Out of scope";
    case "rate_limit_ip":
      return "Daily limit reached";
    case "rate_limit_session":
      return "Session limit reached";
    case "monthly_budget":
      return "Monthly budget reached";
    case "kill_switch":
      return "Librarian offline";
    default:
      return "Notice";
  }
}

function loadFromStorage(key: string | undefined): DisplayMessage[] | null {
  if (!key || typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length === 0) return null;
    return parsed as DisplayMessage[];
  } catch {
    return null;
  }
}
