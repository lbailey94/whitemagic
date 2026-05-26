"use client";

import { useState, useEffect } from "react";
import { emitUnlock, subscribeDnaChange } from "@/store/neoStore";
import { AnimatedTriquetra } from "./AnimatedTriquetra";
import { NEOCodeInput } from "./NEOCodeInput";
import { MatrixRainControls } from "./MatrixRainControls";
import { GlimmerTracker } from "./GlimmerTracker";
import { TriquetraColorControls } from "./TriquetraColorControls";
import { GodSphere } from "./GodSphere";
import { LightningControls } from "./LightningControls";

function BreathingSilhouette({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 200"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={`triquetra-breathing text-lavender ${className || ""}`}
    >
      <g className="triquetra-spin">
        <circle cx="100" cy="76.9" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
        <circle cx="80" cy="111.55" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
        <circle cx="120" cy="111.55" r="40" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
        <circle cx="100" cy="100" r="2.5" fill="currentColor" opacity="0.15" />
      </g>
    </svg>
  );
}

export function Hero() {
  const [phase, setPhase] = useState<"breathing" | "spawned">("breathing");
  const [triKey, setTriKey] = useState(0);
  const [colorMode, setColorMode] = useState<"rainbow" | "fixed">("rainbow");
  const [rainbowSpeed, setRainbowSpeed] = useState(8);
  const [sat, setSat] = useState(85);
  const [lit, setLit] = useState(75);
  const [fixedHue, setFixedHue] = useState(270);
  const [, setDnaTick] = useState(0);

  // Atmospheric breathing: 2.4s of pulsing silhouette, then spawn
  useEffect(() => {
    const t = setTimeout(() => setPhase("spawned"), 2400);
    return () => clearTimeout(t);
  }, []);

  // Re-render triquetra when DNA state or colors change
  useEffect(() => {
    const unsub = subscribeDnaChange(() => setDnaTick((n) => n + 1));
    return unsub;
  }, []);

  const fixedColor =
    colorMode === "fixed" ? `hsl(${fixedHue}, ${sat}%, ${lit}%)` : undefined;

  const handleEpicenter = () => {
    emitUnlock("all");
  };

  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden border-b border-border-light">
      {/* Triquetra stage — breathing or spawned */}
      <div className="relative">
        {phase === "breathing" ? (
          <BreathingSilhouette className="h-[70vh] w-[70vh] max-w-[640px]" />
        ) : (
          <div
            onClick={() => setTriKey((k) => k + 1)}
            className="cursor-pointer transition-transform duration-300 hover:scale-[1.02] active:scale-[0.98]"
            title="Click to replay"
          >
            <AnimatedTriquetra
              key={triKey}
              rainbow={colorMode === "rainbow"}
              rainbowSpeed={rainbowSpeed}
              fixedColor={fixedColor}
              className="h-[70vh] w-[70vh] max-w-[640px] opacity-90"
            />
          </div>
        )}

        {/* GOD Knowledge Sphere overlay */}
        <GodSphere size={640} />

        {/* Epicenter click zone — invisible, triggers GOD */}
        <button
          onClick={handleEpicenter}
          className="absolute left-1/2 top-1/2 h-12 w-12 -translate-x-1/2 -translate-y-1/2 rounded-full bg-transparent"
          aria-label="Activate GOD mode"
          title="The still point"
        />
      </div>

      {/* Controls beneath */}
      <div className="z-10 flex flex-col items-center px-4 pb-12">
        <NEOCodeInput />
        <TriquetraColorControls
          mode={colorMode}
          onModeChange={setColorMode}
          rainbowSpeed={rainbowSpeed}
          onRainbowSpeedChange={setRainbowSpeed}
          sat={sat}
          onSatChange={setSat}
          lit={lit}
          onLitChange={setLit}
          fixedHue={fixedHue}
          onFixedHueChange={setFixedHue}
        />
        <MatrixRainControls />
        <LightningControls />
        <GlimmerTracker />
      </div>
    </section>
  );
}
