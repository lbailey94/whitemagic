"use client";

import { useEffect } from "react";
import { WIP_SCRAMBLE } from "@/lib/wip";

/**
 * WipUnregisterSw — one-time client component that unregisters any
 * active PWA service worker when the user first loads the site in
 * WIP mode. This clears the old HTML cache so users see the latest
 * content instead of stale cached pages.
 *
 * Belt-and-suspenders for the sw.js shim. If the shim didn't fire
 * (e.g., browser hasn't checked for a new SW yet), this component
 * catches it on the client side and forces a reload.
 */
export function WipUnregisterSw() {
  useEffect(() => {
    if (!WIP_SCRAMBLE) return;
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) {
      return;
    }

    let needsReload = false;

    navigator.serviceWorker.getRegistrations().then((regs) => {
      if (regs.length > 0) needsReload = true;
      for (const reg of regs) {
        reg.unregister().catch(() => {});
      }
    });

    if ("caches" in window) {
      caches.keys().then((keys) => {
        if (keys.length > 0) needsReload = true;
        for (const key of keys) {
          caches.delete(key).catch(() => {});
        }
        if (needsReload) {
          // Force a reload after caches are cleared, once
          setTimeout(() => {
            window.location.reload();
          }, 500);
        }
      });
    }
  }, []);

  return null;
}
