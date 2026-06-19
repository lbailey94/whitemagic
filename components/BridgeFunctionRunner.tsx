"use client";

/**
 * BridgeFunctionRunner — interactive "Run" button for one bridge function.
 *
 * Calls POST /api/run-bridge-fn with the function's example_payload (or a
 * user-edited JSON payload) and renders the response inline. Lets visitors
 * exercise the bridge without leaving the catalog page.
 */

import { useState } from "react";
import type { BridgeFunction } from "@/lib/data/mcp-bridge";

type Status = "idle" | "running" | "ok" | "error";

interface Props {
  fn: BridgeFunction;
}

export default function BridgeFunctionRunner({ fn }: Props) {
  const [open, setOpen] = useState(false);
  const [payloadJson, setPayloadJson] = useState(
    JSON.stringify(fn.example_payload, null, 2),
  );
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setStatus("running");
    setError(null);
    setResult(null);
    let payload: Record<string, unknown> = {};
    try {
      payload = JSON.parse(payloadJson);
    } catch (e) {
      setStatus("error");
      setError(`invalid JSON: ${e instanceof Error ? e.message : String(e)}`);
      return;
    }
    try {
      const res = await fetch("/api/run-bridge-fn", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ function: fn.name, payload }),
      });
      const data = (await res.json()) as {
        ok: boolean;
        result?: unknown;
        error?: string;
      };
      if (data.ok) {
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

  function reset() {
    setStatus("idle");
    setResult(null);
    setError(null);
  }

  return (
    <div className="mt-3 pt-3 border-t border-fg/10 space-y-3 text-xs">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => {
            setOpen((v) => !v);
            if (open) reset();
          }}
          className="px-3 py-1.5 rounded border border-lavender/30 text-lavender hover:bg-lavender/10 transition font-mono"
        >
          {open ? "close runner" : "▶ run live"}
        </button>
        <span className="text-fg/40 font-mono">
          POST /api/run-bridge-fn
        </span>
      </div>

      {open && (
        <div className="space-y-3">
          <div>
            <div className="text-fg/40 mb-1">payload (edit to experiment)</div>
            <textarea
              value={payloadJson}
              onChange={(e) => setPayloadJson(e.target.value)}
              className="w-full rounded bg-black/40 p-3 font-mono text-fg/80 text-xs min-h-[80px]"
              spellCheck={false}
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={run}
              disabled={status === "running"}
              className="px-3 py-1.5 rounded bg-lavender/20 text-lavender hover:bg-lavender/30 disabled:opacity-50 transition font-mono"
            >
              {status === "running" ? "running…" : "execute"}
            </button>
            <button
              type="button"
              onClick={() => {
                setPayloadJson(JSON.stringify(fn.example_payload, null, 2));
                reset();
              }}
              className="px-3 py-1.5 rounded border border-fg/20 text-fg/60 hover:text-fg hover:border-fg/40 transition font-mono"
            >
              reset
            </button>
          </div>

          {status === "ok" && result !== null && (
            <div>
              <div className="text-emerald-400/80 mb-1 font-mono">↳ ok</div>
              <pre className="rounded bg-black/40 p-3 overflow-x-auto">
                <code className="text-fg/80 font-mono whitespace-pre-wrap break-all">
                  {JSON.stringify(result, null, 2)}
                </code>
              </pre>
            </div>
          )}

          {status === "error" && error && (
            <div>
              <div className="text-red-400/80 mb-1 font-mono">↳ error</div>
              <pre className="rounded bg-black/40 p-3 overflow-x-auto">
                <code className="text-red-300/80 font-mono whitespace-pre-wrap break-all">
                  {error}
                </code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
