"use client";

import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(display-mode: standalone)").matches) {
      setInstalled(true);
      return;
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    const installedHandler = () => {
      setInstalled(true);
      setDeferredPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", handler);
    window.addEventListener("appinstalled", installedHandler);

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      window.removeEventListener("appinstalled", installedHandler);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    if (choice.outcome === "accepted") {
      setInstalled(true);
    }
    setDeferredPrompt(null);
  };

  if (installed || dismissed || !deferredPrompt) return null;

  return (
    <div className="z-20 fixed bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3 rounded-xl border border-lavender/40 bg-surface/95 px-4 py-3 backdrop-blur-md shadow-lg">
      <div className="flex flex-col">
        <p className="font-zh text-[10px] text-dim/60">安裝白術</p>
        <p className="font-mono text-[11px] text-fg">Install WhiteMagic</p>
      </div>
      <button
        onClick={handleInstall}
        className="rounded-lg bg-lavender px-4 py-1.5 font-mono text-[10px] uppercase tracking-wider text-white transition hover:bg-lavender/80"
      >
        Install
      </button>
      <button
        onClick={() => setDismissed(true)}
        className="font-mono text-[10px] text-dim/50 transition hover:text-dim"
      >
        ✕
      </button>
    </div>
  );
}
