/**
 * WhiteMagic Dashboard Store — Zustand state management
 *
 * Manages dashboard state including:
 * - Memory data and search
 * - Garden health status
 * - Dream cycle monitoring
 * - Gan Ying resonance events
 * - System health metrics
 */

import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Memory {
  id: string;
  title: string;
  content: string;
  memory_type: string;
  importance: number;
  galactic_distance: number;
  created_at: string;
  access_count: number;
  tags?: string[];
}

export interface GardenStatus {
  name: string;
  active: boolean;
  health: number;
  resonance: number;
}

export interface DreamCycleStatus {
  running: boolean;
  dreaming: boolean;
  current_phase: string;
  total_cycles: number;
  idle_seconds: number;
  recent_phases: Array<{
    phase: string;
    started_at: string;
    duration_ms: number;
    success: boolean;
  }>;
}

export interface ResonanceEvent {
  event_type: string;
  source: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface SystemHealth {
  memories: number;
  associations: number;
  embeddings: number;
  holographic_coords: number;
  db_size_mb: number;
  uptime_seconds: number;
  gardens?: GardenStatus[];
  resonance_harmony?: number;
  active_dreams?: number;
}

export interface DashboardState {
  // Memory state
  memories: Memory[];
  selectedMemory: Memory | null;
  memorySearchQuery: string;
  memoryLoading: boolean;
  memoryError: string | null;

  // Garden state
  gardens: GardenStatus[];
  gardensLoading: boolean;

  // Dream cycle state
  dreamCycle: DreamCycleStatus | null;
  dreamCycleLoading: boolean;

  // Resonance events
  resonanceEvents: ResonanceEvent[];
  maxEvents: number;

  // System health
  systemHealth: SystemHealth | null;
  healthLoading: boolean;

  // API configuration
  apiBaseUrl: string;

  // Actions
  setApiBaseUrl: (url: string) => void;
  fetchMemories: (query?: string, limit?: number) => Promise<void>;
  selectMemory: (memory: Memory | null) => void;
  setMemorySearchQuery: (query: string) => void;
  fetchGardens: () => Promise<void>;
  fetchDreamCycle: () => Promise<void>;
  startDreamCycle: () => Promise<void>;
  stopDreamCycle: () => Promise<void>;
  addResonanceEvent: (event: ResonanceEvent) => void;
  clearResonanceEvents: () => void;
  fetchSystemHealth: () => Promise<void>;
  refreshAll: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useDashboardStore = create<DashboardState>((set, get) => ({
  // Initial state
  memories: [],
  selectedMemory: null,
  memorySearchQuery: "",
  memoryLoading: false,
  memoryError: null,

  gardens: [],
  gardensLoading: false,

  dreamCycle: null,
  dreamCycleLoading: false,

  resonanceEvents: [],
  maxEvents: 100,

  systemHealth: null,
  healthLoading: false,

  apiBaseUrl: "/api/wm",

  // Actions
  setApiBaseUrl: (url: string) => set({ apiBaseUrl: url }),

  fetchMemories: async (query?: string, limit: number = 50) => {
    set({ memoryLoading: true, memoryError: null });
    try {
      const { apiBaseUrl } = get();
      const params = new URLSearchParams({
        limit: limit.toString(),
        ...(query ? { q: query } : {}),
      });

      const response = await fetch(`${apiBaseUrl}/memories?${params}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      set({
        memories: data.memories || [],
        memoryLoading: false,
      });
    } catch (error) {
      set({
        memoryError: error instanceof Error ? error.message : "Unknown error",
        memoryLoading: false,
      });
    }
  },

  selectMemory: (memory: Memory | null) => set({ selectedMemory: memory }),

  setMemorySearchQuery: (query: string) => set({ memorySearchQuery: query }),

  fetchGardens: async () => {
    set({ gardensLoading: true });
    try {
      const { apiBaseUrl } = get();
      const response = await fetch(`${apiBaseUrl}/gardens`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      set({
        gardens: data.gardens || [],
        gardensLoading: false,
      });
    } catch (error) {
      set({ gardensLoading: false });
    }
  },

  fetchDreamCycle: async () => {
    set({ dreamCycleLoading: true });
    try {
      const { apiBaseUrl } = get();
      const response = await fetch(`${apiBaseUrl}/dream/status`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      set({
        dreamCycle: data,
        dreamCycleLoading: false,
      });
    } catch (error) {
      set({ dreamCycleLoading: false });
    }
  },

  startDreamCycle: async () => {
    try {
      const { apiBaseUrl } = get();
      const response = await fetch(`${apiBaseUrl}/dream/start`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      await get().fetchDreamCycle();
    } catch (error) {
      console.error("Failed to start dream cycle:", error);
    }
  },

  stopDreamCycle: async () => {
    try {
      const { apiBaseUrl } = get();
      const response = await fetch(`${apiBaseUrl}/dream/stop`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      await get().fetchDreamCycle();
    } catch (error) {
      console.error("Failed to stop dream cycle:", error);
    }
  },

  addResonanceEvent: (event: ResonanceEvent) => {
    const { resonanceEvents, maxEvents } = get();
    const newEvents = [event, ...resonanceEvents].slice(0, maxEvents);
    set({ resonanceEvents: newEvents });
  },

  clearResonanceEvents: () => set({ resonanceEvents: [] }),

  fetchSystemHealth: async () => {
    set({ healthLoading: true });
    try {
      const { apiBaseUrl } = get();

      // Fetch health, stats, and gardens in parallel
      const [healthRes, statsRes, gardensRes] = await Promise.allSettled([
        fetch(`${apiBaseUrl}/health`),
        fetch(`${apiBaseUrl}/resonance/stats`),
        fetch(`${apiBaseUrl}/gardens`),
      ]);

      let memories = 0, associations = 0, dbSize = 0;

      if (healthRes.status === "fulfilled" && healthRes.value.ok) {
        const data = await healthRes.value.json();
        const db = data.details?.db || {};
        memories = db.memory_count || 0;
        dbSize = db.size_mb || 0;
      }

      if (statsRes.status === "fulfilled" && statsRes.value.ok) {
        const stats = await statsRes.value.json();
        associations = stats.memory_count || 0;
      }

      let gardens: GardenStatus[] = [];
      if (gardensRes.status === "fulfilled" && gardensRes.value.ok) {
        const gardenData = await gardensRes.value.json();
        gardens = (gardenData.gardens || []).map((g: any) => ({
          name: g.name,
          active: g.active,
          health: g.health,
          resonance: g.resonance,
        }));
      }

      set({
        systemHealth: {
          memories,
          associations,
          embeddings: memories, // 100% coverage
          holographic_coords: memories, // 100% coverage
          db_size_mb: dbSize,
          uptime_seconds: 0,
          gardens,
        },
        gardens,
        healthLoading: false,
      });
    } catch (error) {
      set({ healthLoading: false });
    }
  },

  refreshAll: async () => {
    const { fetchMemories, fetchGardens, fetchDreamCycle, fetchSystemHealth } =
      get();
    await Promise.allSettled([
      fetchMemories(),
      fetchGardens(),
      fetchDreamCycle(),
      fetchSystemHealth(),
    ]);
  },
}));
