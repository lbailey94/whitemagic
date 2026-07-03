"use client";

import { useState } from "react";
import { Send, Check, AlertCircle } from "lucide-react";

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "ok"; reference: string }
  | { kind: "error"; message: string };

export function ContactForm() {
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState("");
  const [summary, setSummary] = useState("");
  const [website, setWebsite] = useState(""); // honeypot
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (status.kind === "submitting") return;
    setStatus({ kind: "submitting" });
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, topic, summary, website }),
      });
      const data = (await res.json().catch(() => ({}))) as {
        ok?: boolean;
        reference?: string;
        error?: string;
      };
      if (!res.ok || !data.ok || !data.reference) {
        setStatus({
          kind: "error",
          message: data.error ?? `Request failed (${res.status}).`,
        });
        return;
      }
      setStatus({ kind: "ok", reference: data.reference });
      setEmail("");
      setTopic("");
      setSummary("");
    } catch (err) {
      setStatus({
        kind: "error",
        message: (err as Error).message ?? "Network error.",
      });
    }
  }

  if (status.kind === "ok") {
    return (
      <div className="rounded-2xl border border-emerald-300/40 bg-emerald-50/40 p-6 dark:bg-emerald-950/20">
        <div className="mb-2 flex items-center gap-2 text-emerald-800 dark:text-emerald-200">
          <Check className="h-5 w-5" />
          <span className="font-head text-lg font-semibold">Message received.</span>
        </div>
        <p className="text-sm text-muted">
          Reference:{" "}
          <span className="font-mono text-xs">{status.reference}</span>. I
          will reply within two business days. If you&apos;d like to book a
          slot in the meantime, see{" "}
          <a href="/pricing" className="text-lavender underline">
            pricing
          </a>
          .
        </p>
      </div>
    );
  }

  const submitting = status.kind === "submitting";

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-4 rounded-2xl border border-border bg-surface p-6"
      noValidate
    >
      {/* Honeypot — invisible to humans, filled by bots */}
      <div aria-hidden="true" className="absolute left-[-9999px] top-auto">
        <label>
          Website
          <input
            type="text"
            tabIndex={-1}
            autoComplete="off"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
          />
        </label>
      </div>

      <div>
        <label
          htmlFor="contact-email"
          className="mb-1 block font-mono text-xs uppercase tracking-wider text-muted"
        >
          Email
        </label>
        <input
          id="contact-email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-border bg-surface-alt px-3 py-2 text-sm text-ink outline-none transition focus:border-lavender"
          placeholder="you@company.com"
        />
      </div>

      <div>
        <label
          htmlFor="contact-topic"
          className="mb-1 block font-mono text-xs uppercase tracking-wider text-muted"
        >
          Topic
        </label>
        <input
          id="contact-topic"
          type="text"
          required
          minLength={3}
          maxLength={200}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="w-full rounded-lg border border-border bg-surface-alt px-3 py-2 text-sm text-ink outline-none transition focus:border-lavender"
          placeholder="Architecture review for a fintech MCP deployment"
        />
      </div>

      <div>
        <label
          htmlFor="contact-summary"
          className="mb-1 block font-mono text-xs uppercase tracking-wider text-muted"
        >
          What are you working on?
        </label>
        <textarea
          id="contact-summary"
          required
          minLength={10}
          maxLength={2000}
          rows={6}
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          className="w-full rounded-lg border border-border bg-surface-alt px-3 py-2 text-sm text-ink outline-none transition focus:border-lavender"
          placeholder="Short description of the problem or the question. Regulated industry, team size, current stack, constraints — whatever helps me respond usefully."
        />
        <p className="mt-1 font-mono text-[10px] text-muted">
          {summary.length}/2000
        </p>
      </div>

      {status.kind === "error" && (
        <div className="flex items-start gap-2 rounded-lg border border-red-300/40 bg-red-50/40 p-3 text-sm text-red-800 dark:bg-red-950/20 dark:text-red-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{status.message}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="inline-flex items-center gap-2 rounded-lg bg-lavender px-4 py-2 text-sm font-medium text-white transition hover:bg-lavender-dark disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Send className="h-4 w-4" />
        {submitting ? "Sending…" : "Send message"}
      </button>
      <p className="font-mono text-[10px] text-muted">
        Stored in WhiteMagic&apos;s Karma ledger; no tracking cookies; no third
        parties.
      </p>
    </form>
  );
}
