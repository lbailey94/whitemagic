//! Effect Row System — Inspired by Koka's Effect Types
//!
//! Every tool declares what resources it reads, writes, invokes, and
//! whether it spawns external processes. This enables compile-time
//! effect safety via Rust traits and runtime governance via Dharma.

use serde::{Deserialize, Serialize};
use std::fmt;

/// A resource that a tool may read from or write to.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Resource {
    /// A specific LMDB galaxy database
    Galaxy(String),
    /// The karma ledger
    KarmaLedger,
    /// The Dharma rule engine
    DharmaRules,
    /// The Tantivy full-text index
    SearchIndex,
    /// The vector embedding store
    VectorStore,
    /// External network (HTTP, gRPC)
    Network,
    /// Local filesystem outside LMDB
    Filesystem,
    /// System process spawning
    Process,
    /// LLM inference (local or remote)
    Inference,
    /// User session state
    Session,
    /// The Gan Ying event bus (persisted to a JSONL log when enabled)
    EventBus,
}

/// A capability that a tool may invoke.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Capability {
    /// Memory read operations
    MemoryRead,
    /// Memory write operations
    MemoryWrite,
    /// Memory deletion
    MemoryDelete,
    /// Full-text search
    Search,
    /// Vector similarity search
    VectorSearch,
    /// Embedding generation
    Embed,
    /// LLM inference
    LlmInfer,
    /// Tool-to-tool delegation
    Delegate,
    /// External process execution
    Execute,
    /// Network request
    NetworkRequest,
    /// Dream cycle execution
    Dream,
    /// Consciousness update
    CittaUpdate,
}

/// Estimated resource cost for a tool call.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CostEstimate {
    /// Estimated CPU time in nanoseconds (0 = unknown)
    pub cpu_ns: u64,
    /// Estimated memory touched in bytes (0 = unknown)
    pub memory_bytes: u64,
    /// Estimated disk I/O in bytes (0 = unknown)
    pub disk_bytes: u64,
    /// Estimated network I/O in bytes (0 = unknown)
    pub network_bytes: u64,
    /// Whether this tool is expensive enough to skip in Alpha/Theta modes
    pub expensive: bool,
}

/// The effect row of a tool — what it does to the world.
///
/// Inspired by Koka's effect row system, this is checked at compile time
/// via Rust trait bounds and at runtime by the Dharma governance layer.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EffectRow {
    /// Resources this tool reads from
    pub reads: Vec<Resource>,
    /// Resources this tool writes to
    pub writes: Vec<Resource>,
    /// Capabilities this tool invokes
    pub invokes: Vec<Capability>,
    /// Whether this tool spawns external processes
    pub spawns: bool,
    /// Whether this tool is destructive (deletes/overwrites data).
    /// Destructive tools require explicit confirmation via `confirm: true` in args.
    pub destructive: bool,
    /// Estimated resource cost
    pub cost: CostEstimate,
}

impl EffectRow {
    /// Create an empty effect row (pure function)
    #[must_use]
    pub fn pure() -> Self {
        Self::default()
    }

    /// Create a read-only effect row
    #[must_use]
    pub fn read_only(resources: Vec<Resource>) -> Self {
        Self {
            reads: resources,
            writes: vec![],
            invokes: vec![],
            spawns: false,
            destructive: false,
            cost: CostEstimate::default(),
        }
    }

    /// Check if this effect row is compatible with a brain-wave state.
    ///
    /// In Alpha/Theta/Delta modes, expensive or write-heavy tools are
    /// filtered out to conserve resources.
    #[must_use]
    pub fn is_available_in(&self, brain_wave: crate::BrainWave) -> bool {
        use crate::BrainWave::{Alpha, Beta, Delta, Gamma, Theta};
        match brain_wave {
            Gamma => true,
            Beta => true,
            Alpha => !self.cost.expensive && self.writes.is_empty(),
            Theta => !self.cost.expensive && self.writes.is_empty() && !self.spawns,
            Delta => false, // Delta: no tools available, only wake on event
        }
    }

    /// Check if this effect row conflicts with another (for parallel execution)
    #[must_use]
    pub fn conflicts_with(&self, other: &Self) -> bool {
        // Write-write conflicts
        for w in &self.writes {
            if other.writes.contains(w) || other.reads.contains(w) {
                return true;
            }
        }
        for w in &other.writes {
            if self.reads.contains(w) {
                return true;
            }
        }
        // Both spawn processes — could overload
        if self.spawns && other.spawns {
            return true;
        }
        false
    }
}

impl fmt::Display for EffectRow {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "reads:{}, writes:{}, invokes:{}, spawns:{}",
            self.reads.len(),
            self.writes.len(),
            self.invokes.len(),
            self.spawns
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pure_effect_has_no_side_effects() {
        let e = EffectRow::pure();
        assert!(e.reads.is_empty());
        assert!(e.writes.is_empty());
        assert!(!e.spawns);
    }

    #[test]
    fn effect_conflict_detection() {
        let writer = EffectRow {
            writes: vec![Resource::Galaxy("citta".into())],
            ..Default::default()
        };
        let reader = EffectRow {
            reads: vec![Resource::Galaxy("citta".into())],
            ..Default::default()
        };
        assert!(writer.conflicts_with(&reader));
        assert!(reader.conflicts_with(&writer));

        let other_reader = EffectRow {
            reads: vec![Resource::Galaxy("codex".into())],
            ..Default::default()
        };
        assert!(!reader.conflicts_with(&other_reader));
    }

    #[test]
    fn brain_wave_filtering() {
        use crate::BrainWave::*;
        let expensive = EffectRow {
            cost: CostEstimate {
                expensive: true,
                ..Default::default()
            },
            ..Default::default()
        };
        assert!(expensive.is_available_in(Gamma));
        assert!(!expensive.is_available_in(Alpha));
        assert!(!expensive.is_available_in(Delta));
    }

    // ── Property-based tests (proptest) ─────────────────────────────

    use crate::BrainWave;
    use proptest::prelude::*;

    fn arb_resource() -> impl Strategy<Value = Resource> {
        prop_oneof![
            Just(Resource::Galaxy("codex".into())),
            Just(Resource::Galaxy("citta".into())),
            Just(Resource::Filesystem),
            Just(Resource::Network),
            Just(Resource::Process),
        ]
    }

    fn arb_effect_row() -> impl Strategy<Value = EffectRow> {
        (
            proptest::collection::vec(arb_resource(), 0..6),
            proptest::collection::vec(arb_resource(), 0..6),
            any::<bool>(),
            any::<bool>(),
        )
            .prop_map(|(reads, writes, spawns, expensive)| EffectRow {
                reads,
                writes,
                spawns,
                cost: CostEstimate {
                    expensive,
                    ..Default::default()
                },
                ..Default::default()
            })
    }

    proptest! {
        /// Delta must always return false (no tools available in Delta).
        #[test]
        fn delta_blocks_all(effects in arb_effect_row()) {
            prop_assert!(!effects.is_available_in(BrainWave::Delta));
        }

        /// Gamma must always return true (all tools available in Gamma).
        #[test]
        fn gamma_allows_all(effects in arb_effect_row()) {
            prop_assert!(effects.is_available_in(BrainWave::Gamma));
        }

        /// Beta must always return true (all tools available in Beta).
        #[test]
        fn beta_allows_all(effects in arb_effect_row()) {
            prop_assert!(effects.is_available_in(BrainWave::Beta));
        }

        /// Alpha blocks writes and expensive tools.
        #[test]
        fn alpha_blocks_writes_and_expensive(effects in arb_effect_row()) {
            let result = effects.is_available_in(BrainWave::Alpha);
            if !effects.writes.is_empty() || effects.cost.expensive {
                prop_assert!(!result, "Alpha should block writes/expensive: {effects}");
            } else {
                prop_assert!(result, "Alpha should allow pure reads: {effects}");
            }
        }

        /// Theta blocks writes, spawns, and expensive tools.
        #[test]
        fn theta_blocks_writes_spawns_expensive(effects in arb_effect_row()) {
            let result = effects.is_available_in(BrainWave::Theta);
            if !effects.writes.is_empty() || effects.cost.expensive || effects.spawns {
                prop_assert!(!result, "Theta should block: {effects}");
            } else {
                prop_assert!(result, "Theta should allow pure reads: {effects}");
            }
        }

        /// conflicts_with is symmetric: a.conflicts_with(b) == b.conflicts_with(a).
        #[test]
        fn conflicts_symmetric(a in arb_effect_row(), b in arb_effect_row()) {
            let ab = a.conflicts_with(&b);
            let ba = b.conflicts_with(&a);
            prop_assert_eq!(ab, ba, "conflicts_with must be symmetric");
        }

        /// conflicts_with is reflexive for effect rows with writes or spawns.
        #[test]
        fn conflicts_self_with_writes_or_spawns(effects in arb_effect_row()) {
            let self_conflict = effects.conflicts_with(&effects);
            if !effects.writes.is_empty() || effects.spawns {
                prop_assert!(self_conflict, "effect row with writes/spawns should conflict with itself");
            } else {
                prop_assert!(!self_conflict, "pure effect row should not conflict with itself");
            }
        }
    }
}
