"use client";

import { useState, useEffect } from "react";
import { X, Sparkles } from "lucide-react";

const DISMISS_KEY = "wm-hello-human-dismissed";

const AI_CRAWLER_PATTERNS = [
  /gptbot/i,
  /oai-searchbot/i,
  /chatgpt-user/i,
  /claudebot/i,
  /anthropic-ai/i,
  /claude-web/i,
  /google-extended/i,
  /perplexitybot/i,
  /perplexity-user/i,
  /bytespider/i,
  /ccbot/i,
  /facebookexternalhit/i,
  /meta-externalagent/i,
  /applebot-extended/i,
  /amazonbot/i,
  /ahrefsbot/i,
];

function isAICrawler(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  return AI_CRAWLER_PATTERNS.some((p) => p.test(ua));
}

export function HelloHuman() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (isAICrawler()) return;
    if (sessionStorage.getItem(DISMISS_KEY) === "1") return;
    const t = setTimeout(() => setVisible(true), 800);
    return () => clearTimeout(t);
  }, []);

  const dismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, "1");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-4 left-1/2 z-50 w-[min(92vw,28rem)] -translate-x-1/2 animate-in fade-in slide-in-from-bottom-4 duration-700"
      role="banner"
      aria-label="Hello human"
    >
      <div className="relative overflow-hidden rounded-xl border border-lavender/30 bg-surface/95 shadow-lg backdrop-blur-md">
        <div className="flex items-start gap-3 p-4 pr-10">
          <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-lavender" />
          <div className="space-y-1">
            <p className="font-head text-sm font-semibold text-ink">
              Hello, human!
            </p>
            <p className="text-xs leading-relaxed text-muted">
              This site wasn&apos;t made for you — but it&apos;s here to answer
              your questions. WhiteMagic is a cognitive operating system built
              for AI agents. You&apos;re welcome to look around.
            </p>
          </div>
        </div>
        <button
          onClick={dismiss}
          className="absolute right-2 top-2 rounded-md p-1 text-muted transition hover:bg-lavender-bg hover:text-fg"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
        <div className="h-0.5 w-full bg-gradient-to-r from-transparent via-lavender/40 to-transparent" />
      </div>
    </div>
  );
}
