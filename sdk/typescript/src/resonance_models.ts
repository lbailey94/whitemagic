/**
 * Resonance Models — browser-side implementations of WhiteMagic's
 * resonance models, ported from Python to TypeScript for WASM/PWA use.
 *
 * Four models:
 * 1. MemoryDecayModel — Exponential decay with reinforcement
 * 2. PatternResonanceDetector — Same-frequency memory clustering
 * 3. ConstellationMerger — Auto-merge overlapping clusters
 * 4. GardenResonanceMatrix — Inter-garden harmony calculation
 *
 * These mirror the Python implementations in
 * core/whitemagic/core/resonance/resonance_models.py
 */

// ── Memory Decay Model ─────────────────────────────────────────────

export interface DecayParams {
  baseDecayRate: number;
  importanceProtection: number;
  reinforcementBoost: number;
  reinforcementDecay: number;
  minimumRetention: number;
  halfLifeBase: number;
}

export const DEFAULT_DECAY_PARAMS: DecayParams = {
  baseDecayRate: 0.02,
  importanceProtection: 0.5,
  reinforcementBoost: 0.3,
  reinforcementDecay: 0.9,
  minimumRetention: 0.05,
  halfLifeBase: 30.0,
};

export interface RetentionResult {
  retention: number;
  baseRetention: number;
  reinforcement: number;
  recallBonus: number;
  effectiveDecayRate: number;
  halfLifeDays: number;
  timeTo50PercentDays: number | null;
  status: "stable" | "decaying" | "critical";
}

export class MemoryDecayModel {
  private params: DecayParams;

  constructor(params?: Partial<DecayParams>) {
    this.params = { ...DEFAULT_DECAY_PARAMS, ...params };
  }

  predictRetention(opts: {
    importance?: number;
    ageDays?: number;
    accessCount?: number;
    recallCount?: number;
    lastAccessDaysAgo?: number;
    initialRetention?: number;
  }): RetentionResult {
    const p = this.params;
    const importance = opts.importance ?? 0.5;
    const ageDays = opts.ageDays ?? 0;
    const accessCount = opts.accessCount ?? 0;
    const recallCount = opts.recallCount ?? 0;
    const lastAccessDaysAgo = opts.lastAccessDaysAgo ?? 0;
    const initialRetention = opts.initialRetention ?? 1.0;

    const effectiveDecay = p.baseDecayRate * (1.0 - importance * p.importanceProtection);
    const baseRetention = initialRetention * Math.exp(-effectiveDecay * ageDays);

    let reinforcement = 0;
    if (accessCount > 0) {
      for (let i = 0; i < accessCount; i++) {
        reinforcement += p.reinforcementBoost * Math.pow(p.reinforcementDecay, i);
      }
      const recencyFactor = Math.exp(-0.1 * lastAccessDaysAgo);
      reinforcement *= recencyFactor;
    }

    const recallBonus = recallCount * 0.05 * Math.exp(-0.05 * lastAccessDaysAgo);

    let retention = Math.min(1.0, baseRetention + reinforcement + recallBonus);
    retention = Math.max(p.minimumRetention, retention);

    const halfLife = effectiveDecay > 0 ? Math.LN2 / effectiveDecay : Infinity;
    let timeToHalf: number | null;
    if (retention > 0.5) {
      timeToHalf = effectiveDecay > 0 ? Math.log(retention / 0.5) / effectiveDecay : null;
    } else {
      timeToHalf = 0;
    }

    const status: RetentionResult["status"] =
      retention > 0.7 ? "stable" : retention > 0.3 ? "decaying" : "critical";

    return {
      retention: round(retention, 6),
      baseRetention: round(baseRetention, 6),
      reinforcement: round(reinforcement, 6),
      recallBonus: round(recallBonus, 6),
      effectiveDecayRate: round(effectiveDecay, 6),
      halfLifeDays: round(halfLife, 2),
      timeTo50PercentDays: timeToHalf === Infinity || timeToHalf === null ? null : round(timeToHalf, 2),
      status,
    };
  }

  predictDecayCurve(opts: {
    importance?: number;
    accessCount?: number;
    days?: number;
    step?: number;
  }): { day: number; retention: number }[] {
    const { importance = 0.5, accessCount = 0, days = 365, step = 7 } = opts;
    const curve: { day: number; retention: number }[] = [];
    for (let d = 0; d <= days; d += step) {
      const result = this.predictRetention({
        importance,
        ageDays: d,
        accessCount,
        lastAccessDaysAgo: 0,
      });
      curve.push({ day: d, retention: result.retention });
    }
    return curve;
  }

  calculateReinforcementSchedule(opts: {
    importance?: number;
    targetRetention?: number;
  }): { timeToDropBelowTargetDays: number | null; recommendedIntervalsDays: number[] } {
    const p = this.params;
    const importance = opts.importance ?? 0.5;
    const targetRetention = opts.targetRetention ?? 0.8;

    const effectiveDecay = p.baseDecayRate * (1.0 - importance * p.importanceProtection);
    const timeToDrop = effectiveDecay > 0 ? Math.log(1.0 / targetRetention) / effectiveDecay : Infinity;

    const intervals: number[] = [];
    let currentInterval = Math.max(1, Math.floor(timeToDrop * 0.8));
    for (let i = 0; i < 5; i++) {
      intervals.push(currentInterval);
      currentInterval = Math.floor(currentInterval * (1.0 + importance * 0.5));
    }

    return {
      timeToDropBelowTargetDays: timeToDrop === Infinity ? null : round(timeToDrop, 2),
      recommendedIntervalsDays: intervals,
    };
  }
}

// ── Pattern Resonance Detector ──────────────────────────────────────

export interface ResonantCluster {
  clusterId: number;
  memberIds: (string | number)[];
  centerFrequency: number;
  frequencySpread: number;
  coherence: number;
  avgImportance: number;
  avgDamping: number;
  garden: string;
  size: number;
}

export class PatternResonanceDetector {
  private frequencyTolerance: number;

  constructor(frequencyTolerance: number = 0.15) {
    this.frequencyTolerance = frequencyTolerance;
  }

  findResonantPatterns(
    memories: Array<{
      id: string | number;
      resonance?: { frequency?: number; damping?: number; garden?: string };
      importance?: number;
    }>,
    minClusterSize: number = 2,
  ): { clusters: ResonantCluster[]; totalClusters: number; memoriesAnalyzed: number } {
    const resonant: Array<{
      id: string | number;
      frequency: number;
      damping: number;
      importance: number;
      garden: string;
    }> = [];

    for (const mem of memories) {
      const freq = mem.resonance?.frequency;
      if (freq !== undefined) {
        resonant.push({
          id: mem.id,
          frequency: freq,
          damping: mem.resonance?.damping ?? 0.1,
          importance: mem.importance ?? 0.5,
          garden: mem.resonance?.garden ?? "core_garden",
        });
      }
    }

    if (resonant.length === 0) {
      return { clusters: [], totalClusters: 0, memoriesAnalyzed: memories.length };
    }

    resonant.sort((a, b) => a.frequency - b.frequency);

    const clusters: typeof resonant[] = [];
    let currentCluster = [resonant[0]];

    for (let i = 1; i < resonant.length; i++) {
      const mem = resonant[i];
      const centerFreq = currentCluster.reduce((s, m) => s + m.frequency, 0) / currentCluster.length;
      if (Math.abs(mem.frequency - centerFreq) <= this.frequencyTolerance) {
        currentCluster.push(mem);
      } else {
        if (currentCluster.length >= minClusterSize) clusters.push(currentCluster);
        currentCluster = [mem];
      }
    }
    if (currentCluster.length >= minClusterSize) clusters.push(currentCluster);

    const resultClusters: ResonantCluster[] = clusters.map((cluster, i) => {
      const freqs = cluster.map((m) => m.frequency);
      const centerFreq = freqs.reduce((s, f) => s + f, 0) / freqs.length;
      const spread = Math.max(...freqs) - Math.min(...freqs);
      const coherence = Math.max(0, 1.0 - spread / (2 * this.frequencyTolerance));
      const gardens = cluster.map((m) => m.garden);
      const dominantGarden = mostFrequent(gardens);

      return {
        clusterId: i,
        memberIds: cluster.map((m) => m.id),
        centerFrequency: round(centerFreq, 4),
        frequencySpread: round(spread, 4),
        coherence: round(coherence, 4),
        avgImportance: round(cluster.reduce((s, m) => s + m.importance, 0) / cluster.length, 4),
        avgDamping: round(cluster.reduce((s, m) => s + m.damping, 0) / cluster.length, 4),
        garden: dominantGarden,
        size: cluster.length,
      };
    });

    return {
      clusters: resultClusters,
      totalClusters: resultClusters.length,
      memoriesAnalyzed: memories.length,
    };
  }
}

// ── Constellation Merger ────────────────────────────────────────────

export interface Constellation {
  id: string;
  centroid: number[];
  radius: number;
  memberIds: (string | number)[];
  coherence: number;
}

export class ConstellationMerger {
  private overlapThreshold: number;

  constructor(overlapThreshold: number = 0.3) {
    this.overlapThreshold = overlapThreshold;
  }

  mergeOverlapping(constellations: Constellation[]): {
    merged: Constellation[];
    mergeCount: number;
  } {
    if (constellations.length === 0) return { merged: [], mergeCount: 0 };

    const merged: Constellation[] = [];
    const used = new Set<number>();

    for (let i = 0; i < constellations.length; i++) {
      if (used.has(i)) continue;
      let current = { ...constellations[i], memberIds: [...constellations[i].memberIds] };

      for (let j = i + 1; j < constellations.length; j++) {
        if (used.has(j)) continue;
        const other = constellations[j];
        const overlap = this.calculateOverlap(current, other);
        if (overlap >= this.overlapThreshold) {
          current = this.mergeTwo(current, other);
          used.add(j);
        }
      }
      merged.push(current);
    }

    return { merged, mergeCount: constellations.length - merged.length };
  }

  private calculateOverlap(a: Constellation, b: Constellation): number {
    if (a.centroid.length !== b.centroid.length) return 0;
    const dist = euclideanDistance(a.centroid, b.centroid);
    const sumRadii = a.radius + b.radius;
    if (dist >= sumRadii) return 0;
    if (dist === 0) return 1.0;
    // Overlap coefficient: 1 - dist/sumRadii
    return 1.0 - dist / sumRadii;
  }

  private mergeTwo(a: Constellation, b: Constellation): Constellation {
    const totalMembers = a.memberIds.length + b.memberIds.length;
    const wA = a.memberIds.length / totalMembers;
    const wB = b.memberIds.length / totalMembers;
    const centroid = a.centroid.map((v, i) => v * wA + b.centroid[i] * wB);
    return {
      id: `${a.id}+${b.id}`,
      centroid,
      radius: Math.max(a.radius, b.radius),
      memberIds: [...a.memberIds, ...b.memberIds],
      coherence: (a.coherence + b.coherence) / 2,
    };
  }
}

// ── Garden Resonance Matrix ─────────────────────────────────────────

export interface GardenInfo {
  name: string;
  memoryCount: number;
  avgImportance: number;
  avgResonance: number;
  dominantFrequency: number;
}

export class GardenResonanceMatrix {
  calculateInterGardenHarmony(gardens: GardenInfo[]): {
    matrix: number[][];
    gardenNames: string[];
    overallHarmony: number;
    strongestPair: [string, string] | null;
    weakestPair: [string, string] | null;
  } {
    const n = gardens.length;
    const matrix: number[][] = Array(n).fill(null).map(() => Array(n).fill(0));
    const names = gardens.map((g) => g.name);

    for (let i = 0; i < n; i++) {
      matrix[i][i] = 1.0;
      for (let j = i + 1; j < n; j++) {
        const harmony = this.pairwiseHarmony(gardens[i], gardens[j]);
        matrix[i][j] = harmony;
        matrix[j][i] = harmony;
      }
    }

    let overallHarmony = 0;
    let pairCount = 0;
    let maxHarmony = -1;
    let minHarmony = 2;
    let strongestPair: [string, string] | null = null;
    let weakestPair: [string, string] | null = null;

    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        overallHarmony += matrix[i][j];
        pairCount++;
        if (matrix[i][j] > maxHarmony) {
          maxHarmony = matrix[i][j];
          strongestPair = [names[i], names[j]];
        }
        if (matrix[i][j] < minHarmony) {
          minHarmony = matrix[i][j];
          weakestPair = [names[i], names[j]];
        }
      }
    }

    return {
      matrix,
      gardenNames: names,
      overallHarmony: pairCount > 0 ? round(overallHarmony / pairCount, 4) : 1.0,
      strongestPair,
      weakestPair,
    };
  }

  private pairwiseHarmony(a: GardenInfo, b: GardenInfo): number {
    // Frequency alignment: closer frequencies = higher harmony
    const freqDiff = Math.abs(a.dominantFrequency - b.dominantFrequency);
    const freqHarmony = Math.exp(-freqDiff);

    // Importance alignment: similar importance levels = higher harmony
    const impDiff = Math.abs(a.avgImportance - b.avgImportance);
    const impHarmony = 1.0 - impDiff;

    // Size balance: similar-sized gardens resonate better
    const sizeRatio = Math.min(a.memoryCount, b.memoryCount) / Math.max(a.memoryCount, b.memoryCount, 1);
    const sizeHarmony = sizeRatio;

    // Weighted combination
    const harmony = 0.4 * freqHarmony + 0.3 * impHarmony + 0.3 * sizeHarmony;
    return round(Math.max(0, Math.min(1, harmony)), 4);
  }
}

// ── Utility functions ───────────────────────────────────────────────

function round(value: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}

function euclideanDistance(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) {
    const d = a[i] - b[i];
    sum += d * d;
  }
  return Math.sqrt(sum);
}

function mostFrequent<T>(arr: T[]): T {
  const counts = new Map<T, number>();
  for (const item of arr) {
    counts.set(item, (counts.get(item) ?? 0) + 1);
  }
  let maxCount = 0;
  let result: T = arr[0];
  for (const [item, count] of counts) {
    if (count > maxCount) {
      maxCount = count;
      result = item;
    }
  }
  return result;
}
