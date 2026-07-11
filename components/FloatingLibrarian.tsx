"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { MessageSquare, X, Minimize2 } from "lucide-react";
import { LibrarianChat } from "./LibrarianChat";

const STORAGE_KEY = "librarian-floating-v1";
const DISMISSED_KEY = "librarian-dismissed-v1";

/**
 * Site-wide floating Librarian bubble.
 *
 * Behavior:
 *   - Hidden on /librarian (full page there) and /admin (not for visitors).
 *   - Minimized by default: pill in bottom-right corner.
 *   - Click → expands to chat panel.
 *   - X button → dismisses for the browser session (sessionStorage).
 *   - Conversation persists across pages within the same session via
 *     the shared STORAGE_KEY handed to <LibrarianChat />.
 *   - Cmd/Ctrl+K toggles open/closed globally.
 */
export function FloatingLibrarian() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      setDismissed(
        window.sessionStorage.getItem(DISMISSED_KEY) === "1",
      );
    } catch {
      // ignore
    }
  }, []);

  // Cmd/Ctrl+K toggle.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
        // If the user invokes the shortcut, they're not actually dismissing.
        setDismissed(false);
        try {
          window.sessionStorage.removeItem(DISMISSED_KEY);
        } catch {
          // ignore
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const dismiss = () => {
    setDismissed(true);
    setOpen(false);
    try {
      window.sessionStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      // ignore
    }
  };

  // Never render on the dedicated chat page or the admin dashboard.
  if (!mounted) return null;
  if (pathname === "/librarian" || pathname?.startsWith("/admin")) return null;
  if (dismissed && !open) return null;

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="group fixed bottom-6 right-6 z-50 flex items-center gap-2.5 rounded-full border-2 border-lavender/50 bg-lavender px-5 py-3.5 text-base font-medium text-white shadow-xl shadow-lavender/30 transition hover:bg-lavender/90 hover:shadow-2xl hover:shadow-lavender/40 ring-4 ring-lavender/10 animate-pulse-slow"
          aria-label="Open Librarian"
        >
          <MessageSquare className="h-5 w-5" />
          <span>Ask the Librarian</span>
          <span className="hidden font-mono text-[11px] opacity-70 sm:inline">
            ⌘K
          </span>
        </button>
      )}

      {open && (
        <div data-no-scramble className="fixed bottom-6 right-6 z-50 flex w-[min(480px,calc(100vw-3rem))] flex-col rounded-2xl border border-border-light bg-bg shadow-2xl shadow-black/30">
          <div className="flex items-center justify-between border-b border-border-light bg-surface-alt px-4 py-2.5">
            <div className="flex items-center gap-2 text-sm font-medium text-ink">
              <MessageSquare className="h-3.5 w-3.5 text-lavender" />
              <span>Librarian</span>
              <span className="font-mono text-[10px] text-muted">
                (⌘K to toggle)
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded p-1 text-muted hover:bg-surface hover:text-fg"
                aria-label="Minimize"
              >
                <Minimize2 className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={dismiss}
                className="rounded p-1 text-muted hover:bg-surface hover:text-fg"
                aria-label="Dismiss for this session"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <div className="flex-1">
            <LibrarianChat
              heightClass="h-[560px]"
              storageKey={STORAGE_KEY}
              placeholder="Ask about services, pricing, timeline…"
            />
          </div>
        </div>
      )}
    </>
  );
}
