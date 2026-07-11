"use client";

import { useState, useEffect, useCallback } from "react";
import { neoStore, subscribeUnlock, emitDnaChange } from "@/store/neoStore";

export function TriquetraColorControls({
  mode,
  onModeChange,
  rainbowSpeed,
  onRainbowSpeedChange,
  sat,
  onSatChange,
  lit,
  onLitChange,
  fixedHue,
  onFixedHueChange,
}: {
  mode: "rainbow" | "fixed";
  onModeChange: (m: "rainbow" | "fixed") => void;
  rainbowSpeed: number;
  onRainbowSpeedChange: (v: number) => void;
  sat: number;
  onSatChange: (v: number) => void;
  lit: number;
  onLitChange: (v: number) => void;
  fixedHue: number;
  onFixedHueChange: (v: number) => void;
}) {
  const [visible, setVisible] = useState(false);
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const unsub = subscribeUnlock((name) => {
      if (name === "hue" || name === "all") setVisible(true);
    });
    return unsub;
  }, []);

  const updateDnaColor = useCallback((idx: number, key: "hue" | "sat" | "lit", value: number) => {
    neoStore.dnaColors[idx][key] = value;
    emitDnaChange();
    forceUpdate((n) => n + 1);
  }, []);

  if (!visible) return null;

  const dnaLabels = ["C1", "C2", "C3"];

  return (
    <div className="neo-panel neo-panel-enter mt-4 max-w-xs rounded-xl border border-border bg-surface/90 p-4 shadow-lg backdrop-blur-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs font-bold uppercase tracking-widest text-lavender">
          DNA // Hue Shift
        </span>
      </div>

      {/* Mode toggle */}
      <div className="mb-3 flex gap-1 rounded-lg border border-border-light p-0.5">
        {(["rainbow", "fixed"] as const).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            className={`flex-1 rounded-md px-2 py-1 font-mono text-[10px] uppercase tracking-wide transition-colors ${
              mode === m
                ? "bg-lavender/15 text-lavender"
                : "text-text-muted hover:text-ink"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {mode === "rainbow" ? (
        <>
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                Cycle speed (s)
              </label>
              <span className="font-mono text-[10px] text-lavender">
                {rainbowSpeed}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={20}
              step={0.5}
              value={rainbowSpeed}
              onChange={(e) => onRainbowSpeedChange(parseFloat(e.target.value))}
              className="h-1 w-full cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
            />
          </div>
          <div className="mt-2 flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                Saturation
              </label>
              <span className="font-mono text-[10px] text-lavender">
                {sat}%
              </span>
            </div>
            <input
              type="range"
              min={20}
              max={100}
              step={1}
              value={sat}
              onChange={(e) => onSatChange(parseFloat(e.target.value))}
              className="h-1 w-full cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
            />
          </div>
          <div className="mt-2 flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                Lightness
              </label>
              <span className="font-mono text-[10px] text-lavender">
                {lit}%
              </span>
            </div>
            <input
              type="range"
              min={40}
              max={90}
              step={1}
              value={lit}
              onChange={(e) => onLitChange(parseFloat(e.target.value))}
              className="h-1 w-full cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
            />
          </div>
        </>
      ) : (
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <label className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
              Hue
            </label>
            <span className="font-mono text-[10px] text-lavender">
              {fixedHue}°
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={360}
            step={1}
            value={fixedHue}
            onChange={(e) => onFixedHueChange(parseFloat(e.target.value))}
            className="h-1 w-full cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
          />
          {/* Hue preview bar */}
          <div
            className="mt-1 h-1.5 w-full rounded-full"
            style={{
              background: `linear-gradient(90deg, hsl(0,${sat}%,${lit}%), hsl(60,${sat}%,${lit}%), hsl(120,${sat}%,${lit}%), hsl(180,${sat}%,${lit}%), hsl(240,${sat}%,${lit}%), hsl(300,${sat}%,${lit}%), hsl(360,${sat}%,${lit}%))`,
            }}
          />
        </div>
      )}

      {/* DNA Circle Colors — individual triquetra circle hues */}
      <div className="mt-4 border-t border-border-light pt-3">
        <span className="mb-2 block font-mono text-[10px] uppercase tracking-wide text-text-muted">
          Genetic Circles
        </span>
        <div className="flex flex-col gap-2">
          {neoStore.dnaColors.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <div
                className="h-3 w-3 shrink-0 rounded-full"
                style={{
                  background: `hsl(${c.hue}, ${c.sat}%, ${c.lit}%)`,
                }}
              />
              <span className="w-5 font-mono text-[9px] text-text-muted">{dnaLabels[i]}</span>
              <input
                type="range"
                min={0}
                max={360}
                step={1}
                value={c.hue}
                onChange={(e) => updateDnaColor(i, "hue", parseFloat(e.target.value))}
                className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
              />
              <span className="w-8 text-right font-mono text-[9px] text-lavender">{c.hue}°</span>
            </div>
          ))}
        </div>
        <div className="mt-2 flex items-center gap-2">
          <span className="w-5 font-mono text-[9px] text-text-muted">Sat</span>
          <input
            type="range"
            min={20}
            max={100}
            step={1}
            value={neoStore.dnaColors[0].sat}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              neoStore.dnaColors.forEach((_, i) => updateDnaColor(i, "sat", v));
            }}
            className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
          />
          <span className="w-8 text-right font-mono text-[9px] text-lavender">{neoStore.dnaColors[0].sat}%</span>
        </div>
        <div className="mt-1 flex items-center gap-2">
          <span className="w-5 font-mono text-[9px] text-text-muted">Lit</span>
          <input
            type="range"
            min={40}
            max={90}
            step={1}
            value={neoStore.dnaColors[0].lit}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              neoStore.dnaColors.forEach((_, i) => updateDnaColor(i, "lit", v));
            }}
            className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-border-light accent-lavender"
          />
          <span className="w-8 text-right font-mono text-[9px] text-lavender">{neoStore.dnaColors[0].lit}%</span>
        </div>
      </div>
    </div>
  );
}
