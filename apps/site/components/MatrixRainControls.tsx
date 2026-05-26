"use client";

import { useState, useEffect, useCallback } from "react";
import { neoStore, subscribeUnlock, emitDnaChange } from "@/store/neoStore";
import { NEO_CODES } from "@/hooks/useNEO";

type ParamKey = keyof typeof neoStore.matrixRain;

interface ControlDef {
  key: ParamKey;
  label: string;
  min: number;
  max: number;
  step: number;
}

const CONTROLS: ControlDef[] = [
  { key: "fps", label: "FPS", min: 5, max: 60, step: 1 },
  { key: "columnStride", label: "Density (stride)", min: 8, max: 40, step: 1 },
  { key: "trailSteps", label: "Trail length", min: 4, max: 36, step: 1 },
  { key: "dropStep", label: "Drop speed", min: 3, max: 30, step: 1 },
  { key: "glimmerChance", label: "Glimmer %", min: 0, max: 0.5, step: 0.005 },
  { key: "freezeChance", label: "Freeze %", min: 0, max: 0.1, step: 0.001 },
  { key: "charChangeInterval", label: "Char interval", min: 1, max: 16, step: 1 },
  { key: "lingerFrames", label: "Linger frames", min: 2, max: 20, step: 1 },
  { key: "morphSteps", label: "Morph steps", min: 0, max: 15, step: 1 },
];

export function MatrixRainControls() {
  const [visible, setVisible] = useState(false);
  const [, forceUpdate] = useState(0);

  // Listen for unlock events
  useEffect(() => {
    const unsub = subscribeUnlock((name) => {
      if (name === "rain" || name === "all") {
        setVisible(true);
      }
    });
    return unsub;
  }, []);

  const update = useCallback((key: ParamKey, value: number) => {
    neoStore.matrixRain[key] = value;
    forceUpdate((n) => n + 1);
  }, []);

  const toggleDna = useCallback(() => {
    neoStore.setDnaActive(!neoStore.dnaActive);
    emitDnaChange();
    forceUpdate((n) => n + 1);
  }, []);

  if (!visible) return null;

  const dnaUnlocked =
    neoStore.isPanelUnlocked("hue") || neoStore.isPanelUnlocked("all");

  return (
    <div className="neo-panel neo-panel-enter mt-6 rounded-xl border border-border bg-surface/90 p-4 shadow-lg backdrop-blur-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs font-bold uppercase tracking-widest text-lavender">
          NEO // Matrix Controls
        </span>
        <div className="flex gap-1">
          {NEO_CODES.map((c) => (
            <span
              key={c.code}
              className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
                neoStore.isPanelUnlocked(c.panel) ||
                (c.panel !== "all" && neoStore.isPanelUnlocked("all"))
                  ? "bg-lavender/20 text-lavender"
                  : "bg-border-light text-text-muted"
              }`}
            >
              {c.code}
            </span>
          ))}
        </div>
      </div>

      {/* DNA toggle */}
      {dnaUnlocked && (
        <div className="mb-3 flex items-center justify-between rounded-lg border border-border-light bg-border-light/20 px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
            Genetic Code
          </span>
          <button
            onClick={toggleDna}
            className={`relative h-5 w-9 rounded-full transition-colors ${
              neoStore.dnaActive ? "bg-lavender" : "bg-border-light"
            }`}
          >
            <span
              className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                neoStore.dnaActive ? "left-4.5 translate-x-0" : "left-0.5"
              }`}
              style={{ left: neoStore.dnaActive ? "18px" : "2px" }}
            />
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-4 gap-y-3">
        {CONTROLS.map((def) => (
          <div key={def.key} className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                {def.label}
              </label>
              <span className="font-mono text-[10px] text-lavender">
                {neoStore.matrixRain[def.key]}
              </span>
            </div>
            <input
              type="range"
              min={def.min}
              max={def.max}
              step={def.step}
              value={neoStore.matrixRain[def.key]}
              onChange={(e) => update(def.key, parseFloat(e.target.value))}
              className="h-1 w-full cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
