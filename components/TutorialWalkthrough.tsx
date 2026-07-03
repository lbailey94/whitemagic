/**
 * Tutorial Galaxy Walkthrough — Guided Onboarding
 *
 * Highlights tutorial memories in sequence, showing users
 * how to navigate and use the WhiteMagic galaxy.
 */

"use client";

import { useEffect, useState, useCallback } from "react";

interface TutorialStep {
  step: number;
  title: string;
  content: string;
  zone: string;
  importance: number;
}

interface GalaxyStats {
  total_memories: number;
  with_coords: number;
  coord_coverage: number;
  zones: Array<{ name: string; count: number; avg_importance: number }>;
}

export function TutorialWalkthrough({
  apiUrl = "/api/wm",
  onComplete,
}: {
  apiUrl?: string;
  onComplete?: () => void;
}) {
  const [currentStep, setCurrentStep] = useState(0);
  const [tutorialSteps, setTutorialSteps] = useState<TutorialStep[]>([]);
  const [stats, setStats] = useState<GalaxyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [isComplete, setIsComplete] = useState(false);

  const loadTutorial = useCallback(async () => {
    try {
      // Fetch tutorial memories
      const res = await fetch(`${apiUrl}/memories?q=tutorial&limit=20`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const steps = data.memories
        .filter((m: any) => m.memory_type === "tutorial")
        .sort((a: any, b: any) => {
          const stepA = a.tags?.find((t: string) => t.startsWith("tutorial:"))?.split(":")[1] || 0;
          const stepB = b.tags?.find((t: string) => t.startsWith("tutorial:"))?.split(":")[1] || 0;
          return Number(stepA) - Number(stepB);
        })
        .map((m: any) => ({
          step: m.access_count || 0,
          title: m.title,
          content: m.content,
          zone: m.memory_type,
          importance: m.importance,
        }));

      setTutorialSteps(steps);

      // Fetch galaxy stats
      const statsRes = await fetch(`${apiUrl}/galaxy/stats`);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (e) {
      // Tutorial not seeded yet
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    loadTutorial();
  }, [loadTutorial]);

  const handleNext = () => {
    if (currentStep < tutorialSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      setIsComplete(true);
      onComplete?.();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  if (loading) {
    return (
      <div className="p-6 text-center text-gray-400 text-sm">
        Loading tutorial...
      </div>
    );
  }

  if (tutorialSteps.length === 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-400 text-sm mb-4">
          Tutorial galaxy not seeded yet.
        </p>
        <button
          onClick={loadTutorial}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg transition-colors"
        >
          Seed Tutorial
        </button>
      </div>
    );
  }

  const step = tutorialSteps[currentStep];
  const progress = ((currentStep + 1) / tutorialSteps.length) * 100;

  return (
    <div className="flex flex-col h-full">
      {/* Progress bar */}
      <div className="h-1 bg-gray-800">
        <div
          className="h-full bg-gradient-to-r from-purple-500 to-violet-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Step counter */}
      <div className="flex items-center justify-between p-3 border-b border-purple-500/20">
        <span className="text-xs text-gray-400">
          Step {currentStep + 1} of {tutorialSteps.length}
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">
          TUTORIAL
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-white mb-2">
          {step.title}
        </h3>
        <p className="text-xs text-gray-300 leading-relaxed">
          {step.content}
        </p>

        {/* Stats card */}
        {stats && currentStep === 0 && (
          <div className="mt-4 p-3 rounded-lg bg-black/30 border border-gray-700">
            <p className="text-xs text-gray-400 mb-2">Your Galaxy Stats</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-500">Memories:</span>
                <span className="text-white ml-1">{stats.total_memories}</span>
              </div>
              <div>
                <span className="text-gray-500">With coords:</span>
                <span className="text-white ml-1">{stats.with_coords}</span>
              </div>
              <div>
                <span className="text-gray-500">Coverage:</span>
                <span className="text-white ml-1">{stats.coord_coverage}%</span>
              </div>
              <div>
                <span className="text-gray-500">Zones:</span>
                <span className="text-white ml-1">{stats.zones.length}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between p-3 border-t border-purple-500/20">
        <button
          onClick={handlePrev}
          disabled={currentStep === 0}
          className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded transition-colors"
        >
          ← Previous
        </button>

        {/* Step dots */}
        <div className="flex gap-1">
          {tutorialSteps.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentStep(i)}
              className={`w-1.5 h-1.5 rounded-full transition-colors ${
                i === currentStep
                  ? "bg-purple-500"
                  : i < currentStep
                  ? "bg-purple-500/50"
                  : "bg-gray-600"
              }`}
            />
          ))}
        </div>

        <button
          onClick={handleNext}
          className="px-3 py-1.5 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors"
        >
          {isComplete ? "Done ✓" : "Next →"}
        </button>
      </div>

      {/* Completion */}
      {isComplete && (
        <div className="p-4 border-t border-green-500/20 bg-green-500/5">
          <p className="text-sm text-green-400 font-medium">
            🎉 Tutorial Complete!
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Your galaxy is ready. Start exploring and creating memories.
          </p>
        </div>
      )}
    </div>
  );
}
