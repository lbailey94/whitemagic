"use client";

import { useEffect } from "react";
import { WIP_SCRAMBLE } from "@/lib/wip";

/**
 * WipUnregisterSw — one-time client component that unregisters any
 * active PWA service worker when the user first loads the site in
 * WIP mode. This clears the old HTML cache so users see the latest
 * content instead of stale cached pages.
 *
 * Once the SW is unregistered, this component is a no-op on
 * subsequent loads.
 */
export function WipUnregisterSw() {
  useEffect(() => {
    if (!WIP_SCRAMBLE) return;
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) {
      return;
    }

    navigator.serviceWorker.getRegistrations().then((regs) => {
      for (const reg of regs) {
        reg.unregister().catch(() => {
          // ignore — best effort
        });
      }
    });

    // Also clear any caches created by the SW
    if ("caches" in window) {
      caches.keys().then((keys) => {
        for (const key of keys) {
          caches.delete(key).catch(() => {
            // ignore
          });
        }
      });
    }
  }, []);

  return null;
}
