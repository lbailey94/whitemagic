"use client";

import { useState, useEffect } from "react";
import { AnimatedTriquetra } from "./AnimatedTriquetra";

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

export function SigilHero() {
  const [phase, setPhase] = useState<"breathing" | "spawned">("breathing");
  const [triKey, setTriKey] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setPhase("spawned"), 2400);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      onClick={() => setTriKey((k) => k + 1)}
      className="cursor-pointer transition-transform duration-300 hover:scale-[1.02] active:scale-[0.98]"
      title="Click to replay"
    >
      {phase === "breathing" ? (
        <BreathingSilhouette className="h-96 w-96 md:h-[32rem] md:w-[32rem]" />
      ) : (
        <AnimatedTriquetra
          key={triKey}
          rainbow
          rainbowSpeed={8}
          className="h-96 w-96 md:h-[32rem] md:w-[32rem] opacity-90"
        />
      )}
    </div>
  );
}
