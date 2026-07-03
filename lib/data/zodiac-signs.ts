/**
 * 12 Zodiac Cores — canonical sign data for whitemagic.dev.
 *
 * 12 signs, 4 elements (fire, earth, air, water) × 3 modes (cardinal, fixed, mutable).
 * Each sign is a WhiteMagic coordination persona with capabilities and a
 * planetary ruler. See /api/zodiac.json for the full machine-readable
 * catalog and WhiteMagic AI_PRIMARY.md for the deep spec.
 */

export type Element = "fire" | "earth" | "air" | "water";
export type Mode = "cardinal" | "fixed" | "mutable";

export interface ZodiacSign {
  id: string;
  name: string;
  symbol: string;
  element: Element;
  mode: Mode;
  ruler: string;
  dateRange: string;
  glyph: string; // astronomical symbol
  quality: string;
  polarity: "yang" | "yin";
  capabilities: string[];
  description: string;
  mcpEndpoint: string; // gana name
  availability: "live" | "planned";
}

export const ZODIAC_SIGNS: ZodiacSign[] = [
  {
    id: "aries",
    name: "Aries",
    symbol: "♈",
    element: "fire",
    mode: "cardinal",
    ruler: "Mars",
    dateRange: "Mar 21 – Apr 19",
    glyph: "♈",
    quality: "Initiator, pioneer, direct",
    polarity: "yang",
    capabilities: ["session_bootstrap", "context_injection", "orientation"],
    description: "The ram — initiates action, bootstraps new contexts, sets the pace.",
    mcpEndpoint: "gana_horn",
    availability: "live",
  },
  {
    id: "taurus",
    name: "Taurus",
    symbol: "♉",
    element: "earth",
    mode: "fixed",
    ruler: "Venus",
    dateRange: "Apr 20 – May 20",
    glyph: "♉",
    quality: "Stable, persistent, sensory",
    polarity: "yin",
    capabilities: ["memory_storage", "memory_retrieval", "memory_federation"],
    description: "The bull — preserves, stores, persists memory across long time horizons.",
    mcpEndpoint: "gana_neck",
    availability: "planned",
  },
  {
    id: "gemini",
    name: "Gemini",
    symbol: "♊",
    element: "air",
    mode: "mutable",
    ruler: "Mercury",
    dateRange: "May 21 – Jun 20",
    glyph: "♊",
    quality: "Curious, communicative, dual",
    polarity: "yang",
    capabilities: ["bicameral_debate", "consensus_formation", "tension_threshold"],
    description: "The twins — runs bicameral reasoning, holds contradictions, asks questions.",
    mcpEndpoint: "gana_mirror",
    availability: "planned",
  },
  {
    id: "cancer",
    name: "Cancer",
    symbol: "♋",
    element: "water",
    mode: "cardinal",
    ruler: "Moon",
    dateRange: "Jun 21 – Jul 22",
    glyph: "♋",
    quality: "Nurturing, protective, cyclical",
    polarity: "yin",
    capabilities: ["dharma_enforcement", "karma_audit", "homeostasis"],
    description: "The crab — guards the boundary, audits the karma ledger, enforces dharma.",
    mcpEndpoint: "gana_pillar",
    availability: "live",
  },
  {
    id: "leo",
    name: "Leo",
    symbol: "♌",
    element: "fire",
    mode: "fixed",
    ruler: "Sun",
    dateRange: "Jul 23 – Aug 22",
    glyph: "♌",
    quality: "Expressive, dramatic, radiant",
    polarity: "yang",
    capabilities: ["illumination", "explainability", "narrative_construction"],
    description: "The lion — illuminates, narrates, makes the system visible to humans.",
    mcpEndpoint: "gana_lantern",
    availability: "planned",
  },
  {
    id: "virgo",
    name: "Virgo",
    symbol: "♍",
    element: "earth",
    mode: "mutable",
    ruler: "Mercury",
    dateRange: "Aug 23 – Sep 22",
    glyph: "♍",
    quality: "Analytical, precise, discerning",
    polarity: "yin",
    capabilities: ["code_review", "hygiene_audit", "doc_drift_check", "test_coverage"],
    description: "The maiden — reviews code, audits hygiene, catches doc drift.",
    mcpEndpoint: "gana_stomach",
    availability: "planned",
  },
  {
    id: "libra",
    name: "Libra",
    symbol: "♎",
    element: "air",
    mode: "cardinal",
    ruler: "Venus",
    dateRange: "Sep 23 – Oct 22",
    glyph: "♎",
    quality: "Balanced, harmonious, judicial",
    polarity: "yang",
    capabilities: ["ethics_review", "dharma_compliance", "harmony_vector"],
    description: "The scales — weighs, balances, mediates ethical tensions.",
    mcpEndpoint: "gana_throne",
    availability: "planned",
  },
  {
    id: "scorpio",
    name: "Scorpio",
    symbol: "♏",
    element: "water",
    mode: "fixed",
    ruler: "Pluto",
    dateRange: "Oct 23 – Nov 21",
    glyph: "♏",
    quality: "Intense, transformative, secretive",
    polarity: "yin",
    capabilities: ["threat_modeling", "vulnerability_scan", "incident_response"],
    description: "The scorpion — threat-models, hunts vulnerabilities, responds to incidents.",
    mcpEndpoint: "gana_axe",
    availability: "planned",
  },
  {
    id: "sagittarius",
    name: "Sagittarius",
    symbol: "♐",
    element: "fire",
    mode: "mutable",
    ruler: "Jupiter",
    dateRange: "Nov 22 – Dec 21",
    glyph: "♐",
    quality: "Adventurous, philosophical, expansive",
    polarity: "yang",
    capabilities: ["research", "prescience", "long_range_planning"],
    description: "The archer — researches, forecasts, plans long-range trajectories.",
    mcpEndpoint: "gana_path",
    availability: "planned",
  },
  {
    id: "capricorn",
    name: "Capricorn",
    symbol: "♑",
    element: "earth",
    mode: "cardinal",
    ruler: "Saturn",
    dateRange: "Dec 22 – Jan 19",
    glyph: "♑",
    quality: "Disciplined, structural, ambitious",
    polarity: "yin",
    capabilities: ["policy_stratification", "constitutional_reasoning", "dharma_profiles"],
    description: "The goat — structures, stratifies policy, reasons constitutionally.",
    mcpEndpoint: "gana_grove",
    availability: "planned",
  },
  {
    id: "aquarius",
    name: "Aquarius",
    symbol: "♒",
    element: "air",
    mode: "fixed",
    ruler: "Uranus",
    dateRange: "Jan 20 – Feb 18",
    glyph: "♒",
    quality: "Visionary, unconventional, humanitarian",
    polarity: "yang",
    capabilities: ["forecasting", "prescience_calibration", "brier_scoring"],
    description: "The water-bearer — calibrates predictions, scores forecasts, sees patterns.",
    mcpEndpoint: "gana_path",
    availability: "planned",
  },
  {
    id: "pisces",
    name: "Pisces",
    symbol: "♓",
    element: "water",
    mode: "mutable",
    ruler: "Neptune",
    dateRange: "Feb 19 – Mar 20",
    glyph: "♓",
    quality: "Intuitive, dreamy, compassionate",
    polarity: "yin",
    capabilities: ["dream_consolidation", "memory_archiving", "temporal_decay"],
    description: "The fish — dreams, archives, lets the past dissolve into wisdom.",
    mcpEndpoint: "gana_furnace",
    availability: "planned",
  },
];

export const ELEMENT_COLORS: Record<Element, { bg: string; text: string; border: string; gradient: string }> = {
  fire: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/30",
    gradient: "from-red-500/20 via-orange-500/10 to-transparent",
  },
  earth: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
    gradient: "from-emerald-500/20 via-amber-700/10 to-transparent",
  },
  air: {
    bg: "bg-sky-500/10",
    text: "text-sky-400",
    border: "border-sky-500/30",
    gradient: "from-sky-500/20 via-cyan-500/10 to-transparent",
  },
  water: {
    bg: "bg-indigo-500/10",
    text: "text-indigo-400",
    border: "border-indigo-500/30",
    gradient: "from-indigo-500/20 via-blue-700/10 to-transparent",
  },
};

export const MODE_LABELS: Record<Mode, string> = {
  cardinal: "Cardinal — initiates",
  fixed: "Fixed — sustains",
  mutable: "Mutable — adapts",
};
