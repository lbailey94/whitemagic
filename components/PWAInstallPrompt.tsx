/**
 * PWA Install Prompt — "Add to Home Screen" handler
 *
 * Captures the beforeinstallprompt event and shows a custom install button.
 * Works on Chrome/Edge Android and desktop.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { Download, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    // Check if already installed
    if (window.matchMedia("(display-mode: standalone)").matches) {
      setInstalled(true);
      return;
    }

    // Listen for beforeinstallprompt
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      // Show prompt after 30 seconds or on 3rd visit
      const visitCount = parseInt(localStorage.getItem("wm_visit_count") || "0", 10);
      localStorage.setItem("wm_visit_count", String(visitCount + 1));

      if (visitCount >= 2) {
        setShowPrompt(true);
      } else {
        // Or show after 30 seconds
        setTimeout(() => setShowPrompt(true), 30000);
      }
    };

    window.addEventListener("beforeinstallprompt", handler);

    // Listen for app installed
    window.addEventListener("appinstalled", () => {
      setInstalled(true);
      setShowPrompt(false);
      setDeferredPrompt(null);
    });

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
    };
  }, []);

  const handleInstall = useCallback(async () => {
    if (!deferredPrompt) return;

    try {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;

      if (outcome === "accepted") {
        setInstalled(true);
        setShowPrompt(false);
      }
    } catch {
      // User dismissed or error
    }

    setDeferredPrompt(null);
  }, [deferredPrompt]);

  const handleDismiss = useCallback(() => {
    setShowPrompt(false);
    // Don't show again for 7 days
    localStorage.setItem("wm_install_dismissed", String(Date.now()));
  }, []);

  // Check if dismissed recently
  useEffect(() => {
    const dismissed = parseInt(localStorage.getItem("wm_install_dismissed") || "0", 10);
    if (dismissed && Date.now() - dismissed < 7 * 24 * 60 * 60 * 1000) {
      setShowPrompt(false);
    }
  }, []);

  if (installed || !showPrompt || !deferredPrompt) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-80 z-50">
      <div className="rounded-xl bg-gray-900 border border-purple-500/30 shadow-2xl shadow-purple-500/10 p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-600 flex items-center justify-center">
              <Download className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Install WhiteMagic</h3>
              <p className="text-xs text-gray-400">Add to home screen for offline access</p>
            </div>
          </div>
          <button
            onClick={handleDismiss}
            className="text-gray-500 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleInstall}
            className="flex-1 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium transition-colors"
          >
            Install
          </button>
          <button
            onClick={handleDismiss}
            className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
          >
            Later
          </button>
        </div>

        <div className="flex items-center gap-4 text-[10px] text-gray-500">
          <span>✓ Works offline</span>
          <span>✓ SQLite OPFS</span>
          <span>✓ ONNX embeddings</span>
        </div>
      </div>
    </div>
  );
}
