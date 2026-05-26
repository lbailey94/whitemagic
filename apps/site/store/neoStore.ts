/**
 * NEO shared store — module-level mutable state for MatrixRain params,
 * glimmer events, and unlocked arcade panels.
 *
 * Canvas reads directly from this object each frame (no React re-renders).
 * UI panels write to it and re-render themselves.
 */

export interface MatrixRainParams {
  fps: number;
  columnStride: number;
  trailSteps: number;
  dropStep: number;
  glimmerChance: number;
  freezeChance: number;
  charChangeInterval: number;
  lingerFrames: number;
  morphSteps: number;
  [key: string]: number;
}

const TARGET_SENTENCE =
  "the prescience engine dreams in circuits of light and every glimmer is a thought that has not yet found its thinker and the garden grows in directions we have not yet learned to name and the tools wait patiently for hands that understand they were always meant to hold something larger than themselves and the matrix remembers what we have forgotten about the shape of becoming";

function loadRainEnabled(): boolean {
  if (typeof window === "undefined") return true;
  try {
    const v = window.localStorage.getItem("wm-rain-enabled");
    return v === null ? true : v === "true";
  } catch {
    return true;
  }
}

function saveRainEnabled(v: boolean) {
  try {
    window.localStorage.setItem("wm-rain-enabled", String(v));
  } catch {}
}

export const neoStore = {
  rainEnabled: loadRainEnabled(),

  matrixRain: {
    fps: 60,
    columnStride: 8,
    trailSteps: 36,
    dropStep: 6,
    glimmerChance: 0.15,
    freezeChance: 0.1,
    charChangeInterval: 1,
    lingerFrames: 20,
    morphSteps: 3,
  } as MatrixRainParams,

  dnaActive: false,
  dnaColors: [
    { hue: 330, sat: 80, lit: 75 }, // pink
    { hue: 140, sat: 70, lit: 70 }, // light green
    { hue: 200, sat: 80, lit: 75 }, // light blue
  ] as { hue: number; sat: number; lit: number }[],

  targetSentence: TARGET_SENTENCE,
  typedIndex: 0,

  unlockedPanels: new Set<string>(),

  unlockPanel(name: string) {
    this.unlockedPanels.add(name);
  },

  isPanelUnlocked(name: string) {
    return this.unlockedPanels.has(name);
  },

  recordGlimmer() {
    this.typedIndex++;
    if (this.typedIndex > this.targetSentence.length) {
      this.typedIndex = 1; // loop: reset but keep momentum with 1 char visible
    }
  },

  getTypedSentence() {
    return this.targetSentence.slice(0, this.typedIndex);
  },

  getRemainingSentence() {
    return this.targetSentence.slice(this.typedIndex);
  },

  setDnaActive(v: boolean) {
    this.dnaActive = v;
  },

  toggleRain() {
    this.rainEnabled = !this.rainEnabled;
    saveRainEnabled(this.rainEnabled);
    emitRainToggle();
  },

  lightning: {
    minHops: 6,
    maxHops: 12,
    frequencyMs: 1800,
    frequencyVariance: 2200,
  },
};

/** Subscribe callbacks for glimmer events (UI re-renders). */
let glimmerListeners: (() => void)[] = [];

export function subscribeGlimmer(cb: () => void) {
  glimmerListeners.push(cb);
  return () => {
    glimmerListeners = glimmerListeners.filter((l) => l !== cb);
  };
}

export function emitGlimmer() {
  neoStore.recordGlimmer();
  glimmerListeners.forEach((l) => l());
}

/** Subscribe callbacks for panel unlock events. */
let unlockListeners: ((name: string) => void)[] = [];

export function subscribeUnlock(cb: (name: string) => void) {
  unlockListeners.push(cb);
  return () => {
    unlockListeners = unlockListeners.filter((l) => l !== cb);
  };
}

export function emitUnlock(name: string) {
  neoStore.unlockPanel(name);
  unlockListeners.forEach((l) => l(name));
}

/** Subscribe callbacks for DNA state / color changes. */
let dnaChangeListeners: (() => void)[] = [];

export function subscribeDnaChange(cb: () => void) {
  dnaChangeListeners.push(cb);
  return () => {
    dnaChangeListeners = dnaChangeListeners.filter((l) => l !== cb);
  };
}

export function emitDnaChange() {
  dnaChangeListeners.forEach((l) => l());
}

/** Subscribe callbacks for rain enable/disable toggle. */
let rainToggleListeners: (() => void)[] = [];

export function subscribeRainToggle(cb: () => void) {
  rainToggleListeners.push(cb);
  return () => {
    rainToggleListeners = rainToggleListeners.filter((l) => l !== cb);
  };
}

export function emitRainToggle() {
  rainToggleListeners.forEach((l) => l());
}
