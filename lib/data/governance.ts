import { Shield, GitCommit, Zap, Eye, Scale, Activity } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface Feature {
  icon: LucideIcon;
  title: string;
  desc: string;
}

export interface ComparisonRow {
  feature: string;
  wm: string;
  msft: string;
}

export const GOVERNANCE_FEATURES: Feature[] = [
  { icon: Scale, title: "Dharma Rules Engine", desc: "Declarative policy engine. Define what agents can and cannot do — tool allowlists, rate limits, ethical constraints, jurisdictional boundaries. Rules are versioned, auditable, and enforceable at runtime." },
  { icon: GitCommit, title: "Karma Ledger", desc: "Append-only, cryptographically verifiable audit trail. Every tool call, memory mutation, and agent decision is hashed into a Merkle chain. Declared-vs-actual side-effect tracking. Immutable provenance." },
  { icon: Zap, title: "8-Stage Dispatch Pipeline", desc: "Every tool call passes through authentication → authorization → rate limiting → circuit breaker → policy evaluation → karma check → execution → audit. No tool call bypasses governance." },
  { icon: Activity, title: "Circuit Breakers", desc: "Automatic tripwires for anomalous agent behavior. If an agent exceeds rate limits, attempts prohibited operations, or exhibits drift — the circuit opens. Graceful degradation, not catastrophic failure." },
  { icon: Eye, title: "Voice Audit", desc: "Every agent action is logged with chain-of-thought reasoning. Auditors can replay any decision, inspect the full context window, and verify governance rules were applied correctly." },
  { icon: Shield, title: "Bicameral Reasoner", desc: "Dual-path decision architecture. One path optimizes for speed and capability; the other evaluates ethical constraints and long-term consequences. Both must agree before high-stakes actions execute." },
];

export const COMPARISON_ROWS: ComparisonRow[] = [
  { feature: "Declarative policy engine", wm: "✅", msft: "✅" },
  { feature: "Append-only audit ledger", wm: "✅", msft: "✅" },
  { feature: "Multi-stage dispatch pipeline", wm: "8 stages", msft: "Pipeline" },
  { feature: "Circuit breakers", wm: "✅", msft: "✅" },
  { feature: "Cryptographic provenance (Merkle chain)", wm: "✅", msft: "—" },
  { feature: "Bicameral reasoning (dual-path)", wm: "✅", msft: "—" },
  { feature: "Voice audit with chain-of-thought", wm: "✅", msft: "—" },
  { feature: "28 Gana meta-tools (context compression)", wm: "✅", msft: "—" },
  { feature: "Agent trust scores", wm: "✅", msft: "Planned" },
  { feature: "Polyglot acceleration (7 languages)", wm: "✅", msft: ".NET only" },
  { feature: "Open source (MIT)", wm: "✅", msft: "MIT" },
  { feature: "First shipped", wm: "Feb 7, 2026", msft: "Mar 4, 2026" },
];

export const PIPELINE_STAGES = [
  "Authentication — Verify agent identity and session token",
  "Authorization — Check role against required permissions",
  "Rate Limiting — Enforce per-agent, per-tool, and global limits",
  "Circuit Breaker — Check if tripwires have been triggered",
  "Policy Evaluation — Run Dharma Rules Engine against proposed action",
  "Karma Check — Evaluate trust score and recent behavior history",
  "Execution — If all checks pass, execute the tool call",
  "Audit — Log full decision trail: inputs, reasoning, policy evaluations, outcome",
];
