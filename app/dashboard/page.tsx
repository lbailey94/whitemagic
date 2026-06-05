/**
 * WhiteMagic Dashboard — Main Dashboard Page
 *
 * PWA-enabled dashboard for monitoring and interacting with the WhiteMagic
 * agent governance and metacognition substrate. Displays:
 * - Memory graph visualization
 * - Wu Xing elemental balance
 * - Gan Ying resonance monitor
 * - Dream cycle status
 * - System health metrics
 */

"use client";

import { useEffect, useState } from "react";
import { useDashboardStore } from "@/store/dashboardStore";
import { WuXingWheel } from "@/components/dashboard/WuXingWheel";
import { GanYingMonitor } from "@/components/dashboard/GanYingMonitor";
import { MemoryGraph } from "@/components/dashboard/MemoryGraph";
import { TutorialWalkthrough } from "@/components/TutorialWalkthrough";
import { MemoryBrowser } from "@/components/MemoryBrowser";

export default function DashboardPage() {
  const {
    memories,
    fetchMemories,
    fetchGardens,
    fetchDreamCycle,
    fetchSystemHealth,
    dreamCycle,
    systemHealth,
    selectedMemory,
    memoryLoading,
    gardens,
  } = useDashboardStore();

  const [activeTab, setActiveTab] = useState<"overview" | "memory" | "resonance" | "dream" | "tutorial">(
    "overview"
  );

  // Load data on mount
  useEffect(() => {
    fetchMemories(undefined, 100);
    fetchGardens();
    fetchDreamCycle();
    fetchSystemHealth();
  }, [fetchMemories, fetchGardens, fetchDreamCycle, fetchSystemHealth]);

  const tabs = [
    { id: "overview" as const, label: "Overview" },
    { id: "memory" as const, label: "Memory" },
    { id: "resonance" as const, label: "Resonance" },
    { id: "dream" as const, label: "Dream" },
    { id: "tutorial" as const, label: "Tutorial" },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Header */}
      <header className="border-b border-purple-500/20 bg-black/40 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">WM</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold">WhiteMagic Dashboard</h1>
                <p className="text-xs text-gray-400">
                  v22.2.0 — Cognitive Operating System
                </p>
              </div>
            </div>

            {/* System health badge */}
            {systemHealth && (
              <div className="hidden md:flex items-center gap-4 text-xs text-gray-400">
                <span>
                  <span className="text-white">{systemHealth.memories.toLocaleString()}</span>{" "}
                  memories
                </span>
                <span>
                  <span className="text-white">{systemHealth.associations.toLocaleString()}</span>{" "}
                  associations
                </span>
                <span>
                  <span className="text-white">{systemHealth.db_size_mb.toFixed(1)}</span> MB
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Tab navigation */}
      <nav className="border-b border-purple-500/10 bg-black/20">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-purple-500 text-white"
                    : "border-transparent text-gray-400 hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Wu Xing Wheel */}
            <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
              <h2 className="text-sm font-medium text-white mb-4">
                Wu Xing Elemental Balance
              </h2>
              <WuXingWheel size={280} gardens={gardens as any} />
            </div>

            {/* Memory Graph */}
            <div className="lg:col-span-2 bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
              <h2 className="text-sm font-medium text-white mb-4">
                Memory Graph
              </h2>
              {memoryLoading ? (
                <div className="flex items-center justify-center h-[400px] text-gray-500">
                  Loading memories...
                </div>
              ) : (
                <MemoryGraph width={700} height={400} maxNodes={80} />
              )}
            </div>

            {/* System Stats */}
            <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
              <h2 className="text-sm font-medium text-white mb-4">
                System Statistics
              </h2>
              {systemHealth ? (
                <div className="space-y-3">
                  <StatRow label="Memories" value={systemHealth.memories.toLocaleString()} />
                  <StatRow label="Associations" value={systemHealth.associations.toLocaleString()} />
                  <StatRow label="Embeddings" value={systemHealth.embeddings.toLocaleString()} />
                  <StatRow label="Holo Coords" value={systemHealth.holographic_coords.toLocaleString()} />
                  <StatRow label="DB Size" value={`${systemHealth.db_size_mb.toFixed(1)} MB`} />
                </div>
              ) : (
                <div className="text-gray-500 text-sm">Loading...</div>
              )}
            </div>

            {/* Dream Cycle Status */}
            <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
              <h2 className="text-sm font-medium text-white mb-4">
                Dream Cycle
              </h2>
              {dreamCycle ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        dreamCycle.running ? "bg-green-500 animate-pulse" : "bg-gray-500"
                      }`}
                    />
                    <span className="text-sm">
                      {dreamCycle.running ? "Running" : "Stopped"}
                    </span>
                  </div>
                  <StatRow label="Phase" value={dreamCycle.current_phase || "N/A"} />
                  <StatRow label="Cycles" value={dreamCycle.total_cycles.toString()} />
                  <StatRow label="Idle" value={`${Math.round(dreamCycle.idle_seconds)}s`} />
                </div>
              ) : (
                <div className="text-gray-500 text-sm">Loading...</div>
              )}
            </div>

            {/* Gan Ying Monitor */}
            <div className="lg:col-span-1 bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20">
              <GanYingMonitor height={300} useRealTime />
            </div>
          </div>
        )}

        {activeTab === "memory" && (
          <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20">
            <MemoryBrowser height={600} />
          </div>
        )}

        {activeTab === "resonance" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20">
              <GanYingMonitor height={600} maxEvents={100} useRealTime />
            </div>
            <div className="space-y-6">
              <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
                <h2 className="text-sm font-medium text-white mb-4">
                  Wu Xing Resonance
                </h2>
                <WuXingWheel size={280} gardens={gardens as any} />
              </div>

              {/* Garden Harmony */}
              <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
                <h2 className="text-sm font-medium text-white mb-4">
                  Garden Harmony
                </h2>
                {systemHealth?.gardens && systemHealth.gardens.length > 0 ? (
                  <div className="space-y-2">
                    {systemHealth.gardens.slice(0, 6).map((garden) => (
                      <div key={garden.name} className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">{garden.name.replace("_garden", "")}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-purple-500 rounded-full"
                              style={{ width: `${garden.resonance * 100}%` }}
                            />
                          </div>
                          <span className="text-white font-mono w-8 text-right">
                            {garden.resonance.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 text-sm">Loading...</div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "dream" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
              <h2 className="text-sm font-medium text-white mb-4">
                Dream Cycle Control
              </h2>
              {dreamCycle && (
                <DreamCycleControls dreamCycle={dreamCycle} />
              )}
            </div>
            <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
              <h2 className="text-sm font-medium text-white mb-4">
                Recent Dream Phases
              </h2>
              {dreamCycle?.recent_phases && dreamCycle.recent_phases.length > 0 ? (
                <div className="space-y-2">
                  {dreamCycle.recent_phases.map((phase, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg bg-black/30 border border-gray-700"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-white">
                          {phase.phase}
                        </span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded ${
                            phase.success
                              ? "bg-green-500/20 text-green-400"
                              : "bg-red-500/20 text-red-400"
                          }`}
                        >
                          {phase.success ? "OK" : "ERR"}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {phase.started_at} • {phase.duration_ms.toFixed(0)}ms
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500 text-sm">No dream phases recorded</div>
              )}
            </div>
          </div>
        )}

        {activeTab === "tutorial" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Tutorial walkthrough */}
            <div className="lg:col-span-2 bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20">
              <TutorialWalkthrough />
            </div>

            {/* Quick actions */}
            <div className="space-y-6">
              <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
                <h2 className="text-sm font-medium text-white mb-4">
                  Quick Actions
                </h2>
                <div className="space-y-2">
                  <QuickAction
                    label="Create Memory"
                    desc="Store your first memory"
                    href="/dashboard"
                  />
                  <QuickAction
                    label="Live Galaxy"
                    desc="Explore 5D holographic space"
                    href="/galaxy"
                  />
                  <QuickAction
                    label="Knowledge Sphere"
                    desc="Browse CODEX nodes"
                    href="/sphere"
                  />
                  <QuickAction
                    label="Research Library"
                    desc="340+ research files"
                    href="/library"
                  />
                </div>
              </div>

              {/* Galaxy stats */}
              <div className="bg-black/30 backdrop-blur-sm rounded-xl border border-purple-500/20 p-4">
                <h2 className="text-sm font-medium text-white mb-4">
                  Galaxy Stats
                </h2>
                {systemHealth ? (
                  <div className="space-y-2">
                    <StatRow label="Memories" value={systemHealth.memories.toLocaleString()} />
                    <StatRow label="Associations" value={systemHealth.associations.toLocaleString()} />
                    <StatRow label="Embeddings" value={systemHealth.embeddings.toLocaleString()} />
                    <StatRow label="Holo Coords" value={systemHealth.holographic_coords.toLocaleString()} />
                    <StatRow label="DB Size" value={`${systemHealth.db_size_mb.toFixed(1)} MB`} />
                  </div>
                ) : (
                  <div className="text-gray-500 text-sm">Loading...</div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="text-white font-mono">{value}</span>
    </div>
  );
}

function QuickAction({ label, desc, href }: { label: string; desc: string; href: string }) {
  return (
    <a
      href={href}
      className="block p-3 rounded-lg border border-gray-700 hover:border-purple-500/50 hover:bg-purple-500/5 transition-colors"
    >
      <span className="text-sm font-medium text-white">{label}</span>
      <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
    </a>
  );
}

function DreamCycleControls({
  dreamCycle,
}: {
  dreamCycle: { running: boolean; dreaming: boolean };
}) {
  const { startDreamCycle, stopDreamCycle, fetchDreamCycle } =
    useDashboardStore();

  const handleStart = async () => {
    await startDreamCycle();
    await fetchDreamCycle();
  };

  const handleStop = async () => {
    await stopDreamCycle();
    await fetchDreamCycle();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div
          className={`w-3 h-3 rounded-full ${
            dreamCycle.running ? "bg-green-500 animate-pulse" : "bg-gray-500"
          }`}
        />
        <span className="text-sm">
          {dreamCycle.running ? "Dream Cycle Active" : "Dream Cycle Stopped"}
        </span>
      </div>

      <div className="flex gap-2">
        {!dreamCycle.running ? (
          <button
            onClick={handleStart}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg transition-colors"
          >
            Start Dreaming
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors"
          >
            Stop Dreaming
          </button>
        )}
      </div>
    </div>
  );
}
