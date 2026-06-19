"use client";

/**
 * ZodiacCoreActivator — interactive "Activate" button for one zodiac core.
 *
 * Calls POST /api/run-bridge-fn with { function: "zodiac_activate_core",
 * payload: { core_name, context: { question } } } and renders the
 * returned wisdom inline. Visitors can ask the core a question and see
 * the activation result with transformation_applied and resonance.
 */

import { useState } from "react";
import type { ZodiacSign } from "@/lib/data/zodiac-signs";

interface Props {
  sign: ZodiacSign;
}

type Status = "idle" | "running" | "ok" | "error";

export default function ZodiacCoreActivator({ sign }: Props) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function activate() {
    setStatus("running");
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/run-bridge-fn", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          function: "zodiac_activate_core",
          payload: {
            core_name: sign.id,
            context: question.trim() ? { question: question.trim() } : {},
          },
        }),
      });
      const data = (await res.json()) as {
        ok: boolean;
        result?: Record<string, unknown>;
        error?: string;
      };
      if (data.ok && data.result) {
        setStatus("ok");
        setResult(data.result);
      } else {
        setStatus("error");
        setError(data.error ?? `HTTP ${res.status}`);
      }
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => {
          setOpen((v) => !v);
          if (open) {
            setStatus("idle");
            setResult(null);
            setError(null);
          }
        }}
        className="px-3 py-1.5 rounded border border-lavender/30 text-lavender hover:bg-lavender/10 transition font-mono text-xs"
      >
        {open ? "close" : "✶ activate core"}
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          <div>
            <div className="text-fg/40 mb-1 text-xs">
              ask {sign.name} a question (optional)
            </div>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How do I begin?"
              className="w-full rounded bg-black/40 p-2 text-fg/90 text-sm border border-fg/10 focus:border-lavender/40 outline-none"
            />
          </div>

          <button
            type="button"
            onClick={activate}
            disabled={status === "running"}
            className="px-3 py-1.5 rounded bg-lavender/20 text-lavender hover:bg-lavender/30 disabled:opacity-50 transition font-mono text-xs"
          >
            {status === "running" ? "activating…" : "execute activation"}
          </button>

          {status === "ok" && result && (
            <div className="space-y-2 text-xs">
              <div className="flex flex-wrap gap-3 text-fg/50 font-mono">
                <span>
                  <span className="text-fg/30">core:</span>{" "}
                  <span className="text-lavender">{String(result.core)}</span>
                </span>
                <span>
                  <span className="text-fg/30">element:</span>{" "}
                  {String(result.element)}
                </span>
                <span>
                  <span className="text-fg/30">mode:</span>{" "}
                  {String(result.mode)}
                </span>
                <span>
                  <span className="text-fg/30">ruler:</span>{" "}
                  {String(result.ruler)}
                </span>
                {typeof result.resonance === "number" && (
                  <span>
                    <span className="text-fg/30">resonance:</span>{" "}
                    <span className="text-emerald-400">
                      {result.resonance.toFixed(2)}
                    </span>
                  </span>
                )}
                {typeof result.transformation_applied === "string" && (
                  <span>
                    <span className="text-fg/30">transformation:</span>{" "}
                    <code className="text-fg/70">
                      {result.transformation_applied as string}
                    </code>
                  </span>
                )}
                {typeof result.availability === "string" && (
                  <span>
                    <span className="text-fg/30">availability:</span>{" "}
                    <span
                      className={
                        result.availability === "live"
                          ? "text-emerald-400"
                          : "text-amber-400"
                      }
                    >
                      {result.availability}
                    </span>
                  </span>
                )}
              </div>
              {typeof result.wisdom === "string" && (
                <div className="rounded border border-lavender/20 bg-lavender/5 p-3 italic text-fg/80">
                  &ldquo;{result.wisdom as string}&rdquo;
                </div>
              )}
              {typeof result.question_acknowledged === "string" && (
                <div className="text-fg/40 font-mono text-[10px]">
                  question acknowledged: &ldquo;{result.question_acknowledged}&rdquo;
                </div>
              )}
            </div>
          )}

          {status === "error" && error && (
            <div className="rounded bg-red-500/10 border border-red-500/30 p-3 text-red-300 text-xs font-mono">
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
