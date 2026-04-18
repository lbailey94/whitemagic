"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Send, Loader2, AlertCircle } from "lucide-react";
import type { ChatMessage, StreamChunk } from "@/lib/librarian/types";

function genSessionId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `sess-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

interface DisplayMessage extends ChatMessage {
  id: string;
  refusal?: { reason: string; message: string };
}

const INITIAL_GREETING: DisplayMessage = {
  id: "greet-0",
  role: "assistant",
  content:
    "Hi — I'm the Librarian for WhiteMagic Labs. I can help you understand what WhiteMagic is, what Lucas offers as a consultant, and where to find things on the site. Ask me anything within that scope.",
};

export function LibrarianChat() {
  const [messages, setMessages] = useState<DisplayMessage[]>([INITIAL_GREETING]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sessionId] = useState(genSessionId);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

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

    const priorForLLM: ChatMessage[] = [...messages, userMsg]
      .filter((m) => m.role !== "assistant" || m.content.length > 0)
      .map(({ role, content }) => ({ role, content }));

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/librarian/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: priorForLLM, sessionId }),
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
  }, [input, streaming, messages, sessionId]);

  return (
    <div className="flex h-[70vh] min-h-[520px] flex-col overflow-hidden rounded-2xl border border-border-light bg-surface">
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto p-5 md:p-6"
      >
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} streaming={streaming} />
        ))}
        {streaming && messages[messages.length - 1]?.content === "" && (
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
            placeholder="Ask the Librarian…"
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
          material. Conversations reset on page close.
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
      <div
        className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
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
