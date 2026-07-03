"use client";

import { useState, useEffect, useCallback } from "react";
import { neoStore, subscribeUnlock } from "@/store/neoStore";

type LightningKey = keyof typeof neoStore.lightning;

interface ControlDef {
  key: LightningKey;
  label: string;
  min: number;
  max: number;
  step: number;
}

const CONTROLS: ControlDef[] = [
  { key: "minHops", label: "Min hops", min: 2, max: 12, step: 1 },
  { key: "maxHops", label: "Max hops", min: 3, max: 20, step: 1 },
  { key: "frequencyMs", label: "Base freq (ms)", min: 500, max: 4000, step: 100 },
  { key: "frequencyVariance", label: "Variance (ms)", min: 0, max: 4000, step: 100 },
];

export function LightningControls() {
  const [visible, setVisible] = useState(false);
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const unsub = subscribeUnlock((name) => {
      if (name === "god" || name === "all") setVisible(true);
    });
    return unsub;
  }, []);

  const update = useCallback((key: LightningKey, value: number) => {
    neoStore.lightning[key] = value;
    forceUpdate((n) => n + 1);
  }, []);

  if (!visible) return null;

  return (
    <div className="neo-panel neo-panel-enter mt-4 max-w-xs rounded-xl border border-border bg-surface/90 p-4 shadow-lg backdrop-blur-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs font-bold uppercase tracking-widest text-lavender">
          GOD // Lightning
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {CONTROLS.map((def) => (
          <div key={def.key} className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                {def.label}
              </label>
              <span className="font-mono text-[10px] text-lavender">
                {neoStore.lightning[def.key]}
              </span>
            </div>
            <input
              type="range"
              min={def.min}
              max={def.max}
              step={def.step}
              value={neoStore.lightning[def.key]}
              onChange={(e) => update(def.key, parseFloat(e.target.value))}
              className="h-1 w-full cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
