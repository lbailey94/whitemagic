//! Memory type — a single memory entry stored in LMDB.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use wm_core::{Coordinate5D, Galaxy, HolographicCoords};

/// Unique identifier for a memory.
pub type MemoryId = Uuid;

/// Classification of memory kind, inspired by cognitive science memory systems.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MemoryType {
    /// Temporary, easily displaced (working memory)
    ShortTerm,
    /// Stable, enduring knowledge
    #[default]
    LongTerm,
    /// Affectively charged (tied to emotions)
    Emotional,
    /// Sequential life-event story
    Narrative,
    /// Abstract representation / archetype
    Symbolic,
    /// Recognized regularity across experiences
    Pattern,
    /// Skill / how-to knowledge
    Procedural,
    /// Consciousness-cycle observation
    Citta,
    /// Imagined outcome / research hypothesis (Imagination Engine)
    Hypothesis,
}

impl MemoryType {
    /// All variants in canonical order.
    #[must_use]
    pub const fn all() -> &'static [Self] {
        &[
            Self::ShortTerm,
            Self::LongTerm,
            Self::Emotional,
            Self::Narrative,
            Self::Symbolic,
            Self::Pattern,
            Self::Procedural,
            Self::Citta,
            Self::Hypothesis,
        ]
    }

    /// String label for JSON / display.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ShortTerm => "short_term",
            Self::LongTerm => "long_term",
            Self::Emotional => "emotional",
            Self::Narrative => "narrative",
            Self::Symbolic => "symbolic",
            Self::Pattern => "pattern",
            Self::Procedural => "procedural",
            Self::Citta => "citta",
            Self::Hypothesis => "hypothesis",
        }
    }
}

/// Lifecycle tier (V8 S5, `MEMORY_TYPOLOGY_V8.md` §6) — how a memory is
/// *served* as it ages.
///
/// Distinct from [`MemoryType`] (what it *is* cognitively) and from the
/// typology class (`crate::typology` — which write-gate family it belongs
/// to). Fresh writes land in [`Tier::Working`]; the dream cycle is the
/// only tier-transition path (promotion on read, decay-out — §6).
/// Records written before S5 deserialize as [`Tier::Episodic`] (the warm
/// default recall surface — today's serving reality), never as something
/// they were never stamped.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Tier {
    /// Hot: current-session working set — briefing-served, decay-out first.
    Working,
    /// Warm: Tantivy-indexed, the default recall surface.
    #[default]
    Episodic,
    /// Warm knowledge: consolidated, promotion-eligible survivor.
    Semantic,
    /// Cold: sealed archive — explicit queries only.
    Archival,
}

impl Tier {
    /// String label for JSON / display.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Working => "working",
            Self::Episodic => "episodic",
            Self::Semantic => "semantic",
            Self::Archival => "archival",
        }
    }
}

/// Metadata for a memory entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryMetadata {
    /// Memory UUID
    pub id: MemoryId,
    /// Which galaxy this memory lives in
    pub galaxy: Galaxy,
    /// Content hash for deduplication
    pub content_hash: String,
    /// Tags for categorization
    pub tags: Vec<String>,
    /// Importance score (0.0 to 1.0)
    pub importance: f32,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    /// Last accessed timestamp
    pub accessed_at: DateTime<Utc>,
    /// Access count
    pub access_count: u64,
    /// Holographic coordinates
    pub coords: HolographicCoords,
    /// 5D holographic coordinate for spatial indexing
    #[serde(default = "default_coord5d")]
    pub coord5d: Coordinate5D,
    // ── Phase 6.1: Enriched fields ───────────────────────────────────
    /// Memory classification
    #[serde(default)]
    pub memory_type: MemoryType,
    /// Dynamic neural strength (0.0-1.0) — decays over time, boosts on recall
    #[serde(default = "default_neuro_score")]
    pub neuro_score: f32,
    /// Novelty score (0.0-1.0) — decays as info becomes familiar
    #[serde(default = "default_novelty_score")]
    pub novelty_score: f32,
    /// Emotional valence (-1.0 = negative, 1.0 = positive)
    #[serde(default)]
    pub emotional_valence: f32,
    /// Emotional weight / resonance (0.0-1.0)
    #[serde(default)]
    pub emotional_weight: f32,
    /// Hard protection from forgetting
    #[serde(default)]
    pub is_protected: bool,
    /// Exclude from MCP tool responses
    #[serde(default)]
    pub is_private: bool,
    /// Exclude from AI model context windows
    #[serde(default)]
    pub model_exclude: bool,
    /// Provenance: "user", "tool", "inferred", "web"
    #[serde(default = "default_source")]
    pub source: String,
    /// Trust score for source (0.0-1.0, defends against memory poisoning)
    #[serde(default = "default_source_trust")]
    pub source_trust: f32,
    /// Per-memory configurable decay half-life in days
    #[serde(default = "default_half_life_days")]
    pub half_life_days: f32,
    /// Recall count (independent from access_count)
    #[serde(default)]
    pub recall_count: u64,
    /// Version for multi-agent cache coherence
    #[serde(default = "default_version")]
    pub version: u64,
    /// Last writer identity
    #[serde(default = "default_agent_id")]
    pub agent_id: String,
    /// Human-readable title (envelope v2, S4). None = untitled; absent in
    /// old records deserializes as None, never as a fabricated value.
    #[serde(default)]
    pub title: Option<String>,
    /// Topic label for subject-scoped retrieval (envelope v2, S4)
    #[serde(default)]
    pub topic: Option<String>,
    /// Lifecycle tier (V8 S5) — stamped at creation, dream-cycle-only
    /// transitions. Pre-S5 rows default to [`Tier::Episodic`].
    #[serde(default)]
    pub tier: Tier,
    /// Typology class (V8 S5, `crate::typology`) — stamped at creation
    /// when confidently recognized. `None` = unstamped (pre-S5 row, or
    /// content the detector does not confidently recognize); never
    /// fabricated as a claim about the content.
    #[serde(default)]
    pub class: Option<crate::typology::MemoryClass>,
    /// Duplicate-write counter (V8 S5 dedup gate) — bumped instead of
    /// re-inserting identical content; importance decays with it.
    #[serde(default)]
    pub dup_count: u64,
    /// Lifecycle validity (V8 Slice B, D1+D2) — reuses
    /// [`wm_core::episodic::ValidityState`]; the dream cycle is the only
    /// transition path (see `validity_sweep`). Pre-Slice-B rows default to
    /// `Active`, so the recall surface is byte-identical until the
    /// `WM_VALIDITY_ENFORCE` knob turns on.
    #[serde(default)]
    pub validity: wm_core::episodic::ValidityState,
    /// Content-revision counter (V8 S11c) — how many times this memory's
    /// content has changed through `memory.update`. The per-entry chain
    /// itself lives in the store's `revisions` DBI (`memory.revisions`).
    #[serde(default)]
    pub revision_count: u32,
}

const fn default_coord5d() -> Coordinate5D {
    Coordinate5D::new(0.5, 0.5, 0.5, 0.5, 0.5)
}

const fn default_neuro_score() -> f32 {
    0.5
}

const fn default_novelty_score() -> f32 {
    1.0
}

fn default_source() -> String {
    // Unstamped writes claim nothing. "user" as a default was an
    // attribution lie: agent-authored session turns and machine outputs
    // all claimed user provenance because Memory::new defaulted there
    // (sessions-galaxy archaeology finding, 2026-08-29). Write paths that
    // know authorship stamp explicitly — memory.create, the session tools.
    "unattributed".to_string()
}

const fn default_source_trust() -> f32 {
    // Below tool-neutral (0.7): unstamped content must not outrank any
    // attributed class under trust weighting. Heritage records are
    // unaffected — their stored JSON carries whatever was stamped at
    // write time.
    0.5
}

/// Validity enforcement knob (V8 Slice B, D1+D2).
///
/// Off by default: returns true only when `WM_VALIDITY_ENFORCE=1` (exact
/// match — anything else, including unset, stays off). While off, the
/// validity predicate is identically true and the recall surface is
/// byte-identical with or without validity stamps (the S8 doctrine).
#[must_use]
pub fn validity_enforced() -> bool {
    matches!(std::env::var("WM_VALIDITY_ENFORCE"), Ok(v) if v == "1")
}

/// Retrieval trust factor (V8.1, evidence-gated via `WM_TRUST_WEIGHT`).
///
/// Semantics per the master plan: user-confirmed (trust 1.0) ranks up,
/// tool-ingested neutral (0.7) is unchanged, low trust ranks down. `weight`
/// scales the whole effect — 0.0 (the default) disables weighting entirely.
/// Bounded: with weight 1.0 the factor spans 0.3..1.3.
// Deterministic scorer: `mul_add` would change float rounding and with it
// the ranking — the same deliberate `suboptimal_flops` allow class the
// deterministic scorer documents (AGENTS.md).
#[allow(clippy::suboptimal_flops)]
#[must_use]
pub fn trust_weighted_score(score: f32, source_trust: f32, weight: f32) -> f32 {
    let factor = 1.0 + weight * (source_trust.clamp(0.0, 1.0) - 0.7);
    score * factor.max(0.0)
}

const fn default_half_life_days() -> f32 {
    30.0
}

const fn default_version() -> u64 {
    1
}

fn default_agent_id() -> String {
    "system".to_string()
}

/// A complete memory entry: metadata + content.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Memory {
    /// Metadata
    pub metadata: MemoryMetadata,
    /// Content (text, JSON, or binary encoded as base64)
    pub content: String,
    /// Optional embedding vector (stored separately in Embeddings galaxy)
    pub embedding: Option<Vec<f32>>,
}

impl Memory {
    /// Create a new memory in the given galaxy.
    #[must_use]
    pub fn new(galaxy: Galaxy, content: String) -> Self {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let content_hash = content_hash(&content);
        let coord5d = Coordinate5D::encode_with_context(&content, 0.5, 0.5);
        Self {
            metadata: MemoryMetadata {
                id,
                galaxy,
                content_hash,
                tags: vec![],
                importance: 0.5,
                created_at: now,
                accessed_at: now,
                access_count: 0,
                coords: HolographicCoords::new(galaxy, now.timestamp() as u64),
                coord5d,
                memory_type: MemoryType::default(),
                neuro_score: default_neuro_score(),
                novelty_score: default_novelty_score(),
                emotional_valence: 0.0,
                emotional_weight: 0.0,
                is_protected: false,
                is_private: false,
                model_exclude: false,
                source: default_source(),
                source_trust: default_source_trust(),
                half_life_days: default_half_life_days(),
                recall_count: 0,
                version: default_version(),
                agent_id: default_agent_id(),
                title: None,
                topic: None,
                tier: Tier::Working,
                class: crate::typology::detect_class(&content, &[]),
                dup_count: 0,
                validity: wm_core::episodic::ValidityState::default(),
                revision_count: 0,
            },
            content,
            embedding: None,
        }
    }

    /// Set tags on this memory.
    #[must_use]
    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.metadata.tags = tags;
        self
    }

    /// Set importance score (0.0 to 1.0).
    #[must_use]
    pub const fn with_importance(mut self, importance: f32) -> Self {
        self.metadata.importance = importance.clamp(0.0, 1.0);
        self.metadata.coord5d.v = self.metadata.importance;
        self
    }

    /// Set memory type.
    #[must_use]
    pub const fn with_memory_type(mut self, memory_type: MemoryType) -> Self {
        self.metadata.memory_type = memory_type;
        self
    }

    /// Set emotional valence (-1.0 to 1.0) and weight (0.0 to 1.0).
    #[must_use]
    pub const fn with_emotional_valence(mut self, valence: f32, weight: f32) -> Self {
        self.metadata.emotional_valence = valence.clamp(-1.0, 1.0);
        self.metadata.emotional_weight = weight.clamp(0.0, 1.0);
        self
    }

    /// Mark this memory as protected from forgetting.
    #[must_use]
    pub const fn with_protection(mut self, protected: bool) -> Self {
        self.metadata.is_protected = protected;
        self
    }

    /// Set provenance source and trust score.
    #[must_use]
    pub fn with_source(mut self, source: String, trust: f32) -> Self {
        self.metadata.source = source;
        self.metadata.source_trust = trust.clamp(0.0, 1.0);
        self
    }

    /// Set per-memory decay half-life in days.
    #[must_use]
    pub const fn with_half_life_days(mut self, days: f32) -> Self {
        self.metadata.half_life_days = days.max(1.0);
        self
    }

    /// Set initial neuro_score (0.0 to 1.0).
    #[must_use]
    pub const fn with_neuro_score(mut self, score: f32) -> Self {
        self.metadata.neuro_score = score.clamp(0.0, 1.0);
        self
    }

    /// Set initial novelty_score (0.0 to 1.0).
    #[must_use]
    pub const fn with_novelty_score(mut self, score: f32) -> Self {
        self.metadata.novelty_score = score.clamp(0.0, 1.0);
        self
    }

    /// Set privacy flags.
    #[must_use]
    pub const fn with_privacy(mut self, is_private: bool, model_exclude: bool) -> Self {
        self.metadata.is_private = is_private;
        self.metadata.model_exclude = model_exclude;
        self
    }

    /// Transition the serving tier (`MEMORY_TYPOLOGY_V8.md` §6).
    ///
    /// The dream cycle is the ONLY legitimate caller — tier moves are a
    /// sleep-time lifecycle decision, never a request-path one (no tool
    /// accepts a tier argument; `memory.update` whitelists its fields).
    /// Legal moves:
    /// - `Working → Episodic` — age-out of the current-session working set
    /// - `Episodic → Semantic` — consolidation promotion
    /// - `Working | Episodic | Semantic → Archival` — decay-out
    /// - `Archival → Episodic` — promotion on read (warm re-serving)
    ///
    /// Anything else — demotion out of a consolidated or sealed state,
    /// skipping ahead on the ladder — is refused. One move per call: the
    /// dream cycle paces the ladder one step per cycle.
    pub fn transition_tier(&mut self, to: Tier) -> Result<(), wm_core::CoreError> {
        let legal = matches!(
            (self.metadata.tier, to),
            (Tier::Working, Tier::Episodic | Tier::Archival)
                | (Tier::Episodic, Tier::Semantic | Tier::Archival)
                | (Tier::Semantic, Tier::Archival)
                | (Tier::Archival, Tier::Episodic)
        );
        if !legal {
            return Err(wm_core::CoreError::InvalidArgs(format!(
                "illegal tier transition {} -> {} (dream-cycle ladder: one step forward, \
                 decay-out to archival, or archival promotion on read)",
                self.metadata.tier.as_str(),
                to.as_str()
            )));
        }
        self.metadata.tier = to;
        Ok(())
    }

    /// Transition the lifecycle validity (V8 Slice B, D1+D2).
    ///
    /// The dream cycle's `validity_sweep` is the ONLY legitimate caller —
    /// validity moves are a sleep-time lifecycle decision, never a
    /// request-path one (no tool accepts a validity argument).
    /// Legality is exactly [`wm_core::episodic::ValidityState::transition`];
    /// this wrapper only supplies the record id so callers cannot
    /// fabricate a mismatched identity.
    pub fn transition_validity(
        &mut self,
        transition: wm_core::episodic::MemoryTransition,
    ) -> Result<(), wm_core::episodic::ValidityTransitionError> {
        let id = self.metadata.id;
        self.metadata.validity.transition(id, transition)
    }

    /// Set agent identity and version.
    #[must_use]
    pub fn with_agent(mut self, agent_id: String, version: u64) -> Self {
        self.metadata.agent_id = agent_id;
        self.metadata.version = version;
        self
    }

    /// Attach an embedding vector.
    #[must_use]
    pub fn with_embedding(mut self, embedding: Vec<f32>) -> Self {
        self.embedding = Some(embedding);
        self
    }

    /// Record an access (updates `accessed_at` and increments `access_count`).
    pub fn record_access(&mut self) {
        self.metadata.accessed_at = Utc::now();
        self.metadata.access_count += 1;
    }

    /// Record a recall — Hebbian-style strengthening of `neuro_score`.
    ///
    /// Boosts `neuro_score` by `0.05 * (1.0 - current_neuro_score)` (diminishing
    /// returns), increments `recall_count`, updates `accessed_at`, and decays
    /// `novelty_score` (familiarity reduces novelty).
    pub fn recall(&mut self) {
        let now = Utc::now();
        self.metadata.accessed_at = now;
        self.metadata.access_count += 1;
        self.metadata.recall_count += 1;

        // Hebbian boost: diminishing returns as neuro_score approaches 1.0
        let boost = 0.05 * (1.0 - self.metadata.neuro_score);
        self.metadata.neuro_score = (self.metadata.neuro_score + boost).clamp(0.0, 1.0);

        // Novelty decays with each recall (familiarity effect)
        self.metadata.novelty_score = (self.metadata.novelty_score * 0.9).clamp(0.0, 1.0);
    }

    /// Apply exponential decay to `neuro_score` based on time since last access
    /// and the memory's `half_life_days`.
    ///
    /// `neuro_score *= 0.5 ^ (days_since_access / half_life_days)`
    /// Protected memories are exempt from decay.
    pub fn decay(&mut self, now: DateTime<Utc>) {
        if self.metadata.is_protected {
            return;
        }
        let days_since = ((now - self.metadata.accessed_at).num_seconds() as f32) / 86_400.0;
        if days_since <= 0.0 {
            return;
        }
        let half_life = self.metadata.half_life_days.max(1.0);
        let factor = 0.5_f32.powf(days_since / half_life);
        self.metadata.neuro_score = (self.metadata.neuro_score * factor).clamp(0.0, 1.0);
    }

    /// Decay importance by a given factor (used by mindful forgetting).
    pub fn decay_importance(&mut self, factor: f32) {
        if self.metadata.is_protected {
            return;
        }
        self.metadata.importance = (self.metadata.importance * factor).clamp(0.0, 1.0);
    }

    /// Whether this memory should be forgotten (importance below threshold).
    /// Protected memories are never forgotten.
    #[must_use]
    pub fn should_forget(&self, threshold: f32) -> bool {
        !self.metadata.is_protected && self.metadata.importance < threshold
    }
}

/// Compute SHA-256 content hash, returned as hex string.
#[must_use]
pub fn content_hash(content: &str) -> String {
    use sha2::{Digest, Sha256};
    let hasher = Sha256::digest(content.as_bytes());
    format!("{hasher:x}")
}

/// Encode an f32 embedding vector as raw bytes for LMDB storage.
#[must_use]
pub fn encode_embedding(embedding: &[f32]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(embedding.len() * 4);
    for &v in embedding {
        bytes.extend_from_slice(&v.to_le_bytes());
    }
    bytes
}

/// Decode raw bytes back into an f32 embedding vector.
#[must_use]
pub fn decode_embedding(bytes: &[u8]) -> Vec<f32> {
    bytes
        .chunks_exact(4)
        .map(|chunk| f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::MemoryStore;
    use chrono::Duration;
    use wm_core::Galaxy;

    // ── V8.1 trust scoring ─────────────────────────────────────────────

    #[test]
    fn trust_weighted_score_semantics() {
        // Weight 0 = off: score passes through untouched.
        assert!((trust_weighted_score(2.0, 1.0, 0.0) - 2.0).abs() < 1e-5);
        assert!((trust_weighted_score(2.0, 0.0, 0.0) - 2.0).abs() < 1e-5);

        // Neutral point: tool-ingested (0.7) is unchanged at any weight.
        for w in [0.0f32, 0.15, 0.5, 1.0] {
            assert!((trust_weighted_score(3.0, 0.7, w) - 3.0).abs() < 1e-5);
        }

        // User-confirmed ranks up, unverified ranks down, proportionally.
        assert!(trust_weighted_score(1.0, 1.0, 0.5) > 1.0);
        assert!(trust_weighted_score(1.0, 0.2, 0.5) < 1.0);
        assert!((trust_weighted_score(1.0, 1.0, 0.5) - 1.15).abs() < 1e-5);
        assert!((trust_weighted_score(1.0, 0.0, 0.5) - 0.65).abs() < 1e-5);

        // Weight 1.0 spans 0.3..1.3; clamped inputs stay in [0,1].
        assert!((trust_weighted_score(2.0, 0.0, 1.0) - 0.6).abs() < 1e-5);
        assert!((trust_weighted_score(2.0, 5.0, 1.0) - 2.6).abs() < 1e-5);
        assert!((trust_weighted_score(2.0, -1.0, 1.0) - 0.6).abs() < 1e-5);
    }

    // ── MemoryType enum tests ──────────────────────────────────────────

    #[test]
    fn memory_type_default_is_long_term() {
        assert_eq!(MemoryType::default(), MemoryType::LongTerm);
    }

    #[test]
    fn memory_type_all_has_9_variants() {
        assert_eq!(MemoryType::all().len(), 9);
    }

    #[test]
    fn memory_type_as_str_roundtrip() {
        for &mt in MemoryType::all() {
            let s = mt.as_str();
            let json = serde_json::to_string(&mt).unwrap();
            // serde uses snake_case rename
            let expected = format!("\"{s}\"");
            assert_eq!(json, expected);
        }
    }

    #[test]
    fn memory_type_serde_roundtrip() {
        for &mt in MemoryType::all() {
            let json = serde_json::to_string(&mt).unwrap();
            let back: MemoryType = serde_json::from_str(&json).unwrap();
            assert_eq!(mt, back);
        }
    }

    // ── Enriched field defaults ────────────────────────────────────────

    #[test]
    fn new_memory_has_enriched_defaults() {
        let mem = Memory::new(Galaxy::Codex, "test".into());
        let m = &mem.metadata;

        assert_eq!(m.memory_type, MemoryType::LongTerm);
        assert!((m.neuro_score - 0.5).abs() < f32::EPSILON);
        assert!((m.novelty_score - 1.0).abs() < f32::EPSILON);
        assert!((m.emotional_valence).abs() < f32::EPSILON);
        assert!((m.emotional_weight).abs() < f32::EPSILON);
        assert!(!m.is_protected);
        assert!(!m.is_private);
        assert!(!m.model_exclude);
        assert_eq!(m.source, "unattributed");
        assert!((m.source_trust - 0.5).abs() < f32::EPSILON);
        assert!((m.half_life_days - 30.0).abs() < f32::EPSILON);
        assert_eq!(m.recall_count, 0);
        assert_eq!(m.version, 1);
        assert_eq!(m.agent_id, "system");
    }

    // ── Validity states (V8 Slice B, D1+D2) ─────────────────────────────

    #[test]
    fn new_memory_validity_defaults_active() {
        let mem = Memory::new(Galaxy::Codex, "test".into());
        assert_eq!(
            mem.metadata.validity,
            wm_core::episodic::ValidityState::Active
        );
        assert!(mem.metadata.validity.is_current());
    }

    #[test]
    fn legacy_metadata_without_validity_deserializes_active() {
        // Pre-Slice-B rows carry no `validity` key — serde default must be
        // Active so old stores read byte-identical.
        let mem = Memory::new(Galaxy::Codex, "test".into());
        let mut json = serde_json::to_value(&mem.metadata).unwrap();
        json.as_object_mut().unwrap().remove("validity");
        let back: MemoryMetadata = serde_json::from_value(json).unwrap();
        assert_eq!(back.validity, wm_core::episodic::ValidityState::Active);
    }

    #[test]
    fn transition_validity_supersede_roundtrip() {
        let mut mem = Memory::new(Galaxy::Codex, "old claim".into());
        let replacement = uuid::Uuid::new_v4();
        mem.transition_validity(wm_core::episodic::MemoryTransition::Supersede { replacement })
            .unwrap();
        assert_eq!(
            mem.metadata.validity,
            wm_core::episodic::ValidityState::Superseded { by: replacement }
        );
        assert!(!mem.metadata.validity.is_current());
        assert!(mem.metadata.validity.is_historical());
    }

    #[test]
    fn transition_validity_refuses_self_supersession() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        let own = mem.metadata.id;
        let err = mem
            .transition_validity(wm_core::episodic::MemoryTransition::Supersede {
                replacement: own,
            })
            .unwrap_err();
        assert_eq!(
            err,
            wm_core::episodic::ValidityTransitionError::SelfSupersession
        );
        assert!(mem.metadata.validity.is_current());
    }

    #[test]
    fn transition_validity_erased_is_terminal() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        mem.transition_validity(wm_core::episodic::MemoryTransition::Erase)
            .unwrap();
        assert_eq!(
            mem.metadata.validity,
            wm_core::episodic::ValidityState::Erased
        );
        let err = mem
            .transition_validity(wm_core::episodic::MemoryTransition::Archive)
            .unwrap_err();
        assert_eq!(err, wm_core::episodic::ValidityTransitionError::Erased);
    }

    #[test]
    fn validity_enforced_defaults_off() {
        // Load-bearing for the S8 byte-identical doctrine: unless a session
        // deliberately opts in via WM_VALIDITY_ENFORCE=1, enforcement is off.
        // (Env mutation is `unsafe` under edition-2024 `forbid(unsafe)`, so
        // the ON case is covered by inspection + the benchmark gate, not here.)
        assert!(!validity_enforced());
    }

    // ── recall() Hebbian dynamics ──────────────────────────────────────

    #[test]
    fn recall_boosts_neuro_score() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        let initial = mem.metadata.neuro_score;
        mem.recall();
        assert!(mem.metadata.neuro_score > initial);
        assert_eq!(mem.metadata.recall_count, 1);
        assert_eq!(mem.metadata.access_count, 1);
    }

    #[test]
    fn recall_has_diminishing_returns() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        mem.metadata.neuro_score = 0.9;

        mem.recall();
        let boost_high = 0.05 * (1.0 - 0.9); // 0.005
        assert!((mem.metadata.neuro_score - (0.9 + boost_high)).abs() < 1e-5);

        // Now from a lower starting point
        let mut mem2 = Memory::new(Galaxy::Codex, "test".into());
        mem2.metadata.neuro_score = 0.1;
        mem2.recall();
        let boost_low = 0.05 * (1.0 - 0.1); // 0.045
        assert!((mem2.metadata.neuro_score - (0.1 + boost_low)).abs() < 1e-5);
    }

    #[test]
    fn recall_decays_novelty() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        let initial_novelty = mem.metadata.novelty_score;
        mem.recall();
        assert!(mem.metadata.novelty_score < initial_novelty);
        assert!((initial_novelty.mul_add(-0.9, mem.metadata.novelty_score)).abs() < 1e-5);
    }

    #[test]
    fn recall_neuro_score_caps_at_1() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        mem.metadata.neuro_score = 0.99;
        for _ in 0..100 {
            mem.recall();
        }
        // Asymptotic approach to 1.0 — should be very close but not exact
        assert!(mem.metadata.neuro_score > 0.999);
        assert!(mem.metadata.neuro_score <= 1.0);
    }

    // ── decay() exponential dynamics ───────────────────────────────────

    #[test]
    fn decay_reduces_neuro_score_over_time() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        mem.metadata.neuro_score = 1.0;
        mem.metadata.half_life_days = 30.0;

        // Simulate 30 days since last access = one half-life
        mem.metadata.accessed_at = Utc::now() - Duration::days(30);
        mem.decay(Utc::now());

        // After one half-life, neuro_score should be ~0.5
        assert!((mem.metadata.neuro_score - 0.5).abs() < 0.01);
    }

    #[test]
    fn decay_zero_time_is_noop() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        let score = mem.metadata.neuro_score;
        mem.decay(Utc::now());
        assert!((mem.metadata.neuro_score - score).abs() < f32::EPSILON);
    }

    #[test]
    fn decay_respects_is_protected() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        mem.metadata.neuro_score = 1.0;
        mem.metadata.is_protected = true;
        mem.metadata.accessed_at = Utc::now() - Duration::days(365);
        mem.decay(Utc::now());
        assert!((mem.metadata.neuro_score - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn decay_uses_per_memory_half_life() {
        let mut mem_short = Memory::new(Galaxy::Codex, "short".into());
        mem_short.metadata.neuro_score = 1.0;
        mem_short.metadata.half_life_days = 7.0;
        mem_short.metadata.accessed_at = Utc::now() - Duration::days(7);

        let mut mem_long = Memory::new(Galaxy::Codex, "long".into());
        mem_long.metadata.neuro_score = 1.0;
        mem_long.metadata.half_life_days = 90.0;
        mem_long.metadata.accessed_at = Utc::now() - Duration::days(7);

        mem_short.decay(Utc::now());
        mem_long.decay(Utc::now());

        // Short half-life should have decayed more
        assert!(mem_short.metadata.neuro_score < mem_long.metadata.neuro_score);
    }

    // ── Protection logic ───────────────────────────────────────────────

    #[test]
    fn should_forget_respects_protection() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        mem.metadata.importance = 0.01;
        mem.metadata.is_protected = true;
        assert!(!mem.should_forget(0.1));
    }

    #[test]
    fn decay_importance_respects_protection() {
        let mut mem = Memory::new(Galaxy::Codex, "test".into());
        mem.metadata.importance = 0.5;
        mem.metadata.is_protected = true;
        mem.decay_importance(0.5);
        assert!((mem.metadata.importance - 0.5).abs() < f32::EPSILON);
    }

    // ── Builder methods ────────────────────────────────────────────────

    #[test]
    fn with_memory_type_builder() {
        let mem = Memory::new(Galaxy::Codex, "test".into()).with_memory_type(MemoryType::Emotional);
        assert_eq!(mem.metadata.memory_type, MemoryType::Emotional);
    }

    #[test]
    fn with_emotional_valence_clamps() {
        let mem = Memory::new(Galaxy::Codex, "test".into()).with_emotional_valence(2.0, 2.0);
        assert!((mem.metadata.emotional_valence - 1.0).abs() < f32::EPSILON);
        assert!((mem.metadata.emotional_weight - 1.0).abs() < f32::EPSILON);

        let mem2 = Memory::new(Galaxy::Codex, "test".into()).with_emotional_valence(-2.0, -1.0);
        assert!((mem2.metadata.emotional_valence - (-1.0)).abs() < f32::EPSILON);
        assert!((mem2.metadata.emotional_weight).abs() < f32::EPSILON);
    }

    #[test]
    fn with_protection_builder() {
        let mem = Memory::new(Galaxy::Codex, "test".into()).with_protection(true);
        assert!(mem.metadata.is_protected);
    }

    #[test]
    fn with_source_builder() {
        let mem = Memory::new(Galaxy::Codex, "test".into()).with_source("web".into(), 0.5);
        assert_eq!(mem.metadata.source, "web");
        assert!((mem.metadata.source_trust - 0.5).abs() < f32::EPSILON);
    }

    #[test]
    fn with_half_life_days_clamps_to_min_1() {
        let mem = Memory::new(Galaxy::Codex, "test".into()).with_half_life_days(0.1);
        assert!((mem.metadata.half_life_days - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn with_neuro_score_clamps() {
        let mem = Memory::new(Galaxy::Codex, "test".into()).with_neuro_score(1.5);
        assert!((mem.metadata.neuro_score - 1.0).abs() < f32::EPSILON);

        let mem2 = Memory::new(Galaxy::Codex, "test".into()).with_neuro_score(-0.5);
        assert!((mem2.metadata.neuro_score).abs() < f32::EPSILON);
    }

    #[test]
    fn with_novelty_score_clamps() {
        let mem = Memory::new(Galaxy::Codex, "test".into()).with_novelty_score(2.0);
        assert!((mem.metadata.novelty_score - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn with_privacy_builder() {
        let mem = Memory::new(Galaxy::Codex, "secret".into()).with_privacy(true, true);
        assert!(mem.metadata.is_private);
        assert!(mem.metadata.model_exclude);
    }

    #[test]
    fn with_agent_builder() {
        let mem = Memory::new(Galaxy::Codex, "test".into()).with_agent("agent-007".into(), 42);
        assert_eq!(mem.metadata.agent_id, "agent-007");
        assert_eq!(mem.metadata.version, 42);
    }

    // ── Serde backward compatibility ───────────────────────────────────

    #[test]
    fn serde_backward_compat_missing_enriched_fields() {
        // Simulate an old-format memory (pre-6.1) serialized without enriched fields.
        // serde defaults should fill them in.
        let old_json = serde_json::json!({
            "metadata": {
                "id": uuid::Uuid::new_v4().to_string(),
                "galaxy": "Codex",
                "content_hash": "abc123",
                "tags": [],
                "importance": 0.5,
                "created_at": "2025-01-01T00:00:00Z",
                "accessed_at": "2025-01-01T00:00:00Z",
                "access_count": 0,
                "coords": {
                    "galaxy": 2,
                    "sector": 0,
                    "radial": 0.5,
                    "angular": 0.0,
                    "temporal": 0,
                    "consciousness": 0.5
                }
            },
            "content": "old memory",
            "embedding": null
        });

        let mem: Memory = serde_json::from_value(old_json).unwrap();
        assert_eq!(mem.metadata.memory_type, MemoryType::LongTerm);
        assert!((mem.metadata.neuro_score - 0.5).abs() < f32::EPSILON);
        assert!((mem.metadata.novelty_score - 1.0).abs() < f32::EPSILON);
        assert!(!mem.metadata.is_protected);
        // Heritage JSON missing the source fields deserializes as
        // UNATTRIBUTED — absent stamps claim nothing; they must not
        // materialize as a user claim.
        assert_eq!(mem.metadata.source, "unattributed");
        assert!((mem.metadata.source_trust - 0.5).abs() < f32::EPSILON);
        assert!((mem.metadata.half_life_days - 30.0).abs() < f32::EPSILON);
        assert_eq!(mem.metadata.recall_count, 0);
        assert_eq!(mem.metadata.version, 1);
        assert_eq!(mem.metadata.agent_id, "system");
        // Envelope-v2 fields (S4): absent in old records → None, never
        // fabricated.
        assert_eq!(mem.metadata.title, None);
        assert_eq!(mem.metadata.topic, None);
        // S5 tier/class/dup fields: old records are warm-served (episodic)
        // and unstamped as to class — never fabricated.
        assert_eq!(mem.metadata.tier, Tier::Episodic);
        assert_eq!(mem.metadata.class, None);
        assert_eq!(mem.metadata.dup_count, 0);
    }

    #[test]
    fn fresh_memory_stamps_working_tier_and_detected_class() {
        // Friction template content is telemetry by construction.
        let friction = Memory::new(
            Galaxy::Codex,
            "## Auto-logged Friction: Tool dispatch error\n\nbody".into(),
        );
        assert_eq!(friction.metadata.tier, Tier::Working);
        assert_eq!(
            friction.metadata.class,
            Some(crate::typology::MemoryClass::Telemetry)
        );
        // Ordinary prose is not confidently recognized → unstamped.
        let plain = Memory::new(Galaxy::Codex, "a normal thought about kumquats".into());
        assert_eq!(plain.metadata.tier, Tier::Working);
        assert_eq!(plain.metadata.class, None);
    }

    #[test]
    fn tier_transition_ladder_is_enforced() {
        // Legal ladder: forward one step, decay-out to archival, and the
        // archival promotion-on-read. Every other move is refused.
        let mut m = Memory::new(Galaxy::Codex, "tier ladder".into());
        assert_eq!(m.metadata.tier, Tier::Working);

        m.transition_tier(Tier::Episodic).unwrap();
        assert_eq!(m.metadata.tier, Tier::Episodic);
        m.transition_tier(Tier::Semantic).unwrap();
        assert_eq!(m.metadata.tier, Tier::Semantic);
        m.transition_tier(Tier::Archival).unwrap();
        assert_eq!(m.metadata.tier, Tier::Archival);
        m.transition_tier(Tier::Episodic).unwrap();
        assert_eq!(m.metadata.tier, Tier::Episodic);

        // Decay-out is legal from any warm tier.
        m.transition_tier(Tier::Archival).unwrap();
        // No demotion out of a consolidated or sealed state, no skipping.
        for (from, to) in [
            (Tier::Semantic, Tier::Episodic),
            (Tier::Semantic, Tier::Working),
            (Tier::Archival, Tier::Working),
            (Tier::Archival, Tier::Semantic),
            (Tier::Working, Tier::Semantic),
        ] {
            let mut mem = Memory::new(Galaxy::Codex, "illegal move probe".into());
            mem.metadata.tier = from;
            let err = mem.transition_tier(to).unwrap_err();
            assert!(
                err.to_string().contains("illegal tier transition"),
                "{from:?} -> {to:?} must be refused, got: {err}"
            );
            assert_eq!(mem.metadata.tier, from, "refused move must not mutate");
        }
    }

    #[test]
    fn msgpack_roundtrip_preserves_enriched_fields() {
        let mem = Memory::new(Galaxy::Codex, "test".into())
            .with_memory_type(MemoryType::Emotional)
            .with_emotional_valence(0.8, 0.6)
            .with_protection(true)
            .with_source("tool".into(), 0.7)
            .with_half_life_days(14.0)
            .with_neuro_score(0.75)
            .with_novelty_score(0.3)
            .with_privacy(true, false)
            .with_agent("agent-x".into(), 5);

        let bytes = rmp_serde::to_vec(&mem).unwrap();
        let back: Memory = rmp_serde::from_slice(&bytes).unwrap();

        assert_eq!(back.metadata.memory_type, MemoryType::Emotional);
        assert!((back.metadata.neuro_score - 0.75).abs() < 1e-5);
        assert!((back.metadata.novelty_score - 0.3).abs() < 1e-5);
        assert!((back.metadata.emotional_valence - 0.8).abs() < 1e-5);
        assert!((back.metadata.emotional_weight - 0.6).abs() < 1e-5);
        assert!(back.metadata.is_protected);
        assert!(back.metadata.is_private);
        assert!(!back.metadata.model_exclude);
        assert_eq!(back.metadata.source, "tool");
        assert!((back.metadata.source_trust - 0.7).abs() < 1e-5);
        assert!((back.metadata.half_life_days - 14.0).abs() < 1e-5);
        assert_eq!(back.metadata.agent_id, "agent-x");
        assert_eq!(back.metadata.version, 5);
    }

    // ── LMDB store roundtrip with enriched fields ──────────────────────

    #[test]
    fn lmdb_roundtrip_preserves_enriched_fields() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem = Memory::new(Galaxy::Codex, "enriched".into())
            .with_memory_type(MemoryType::Pattern)
            .with_emotional_valence(-0.5, 0.8)
            .with_protection(true)
            .with_source("inferred".into(), 0.3)
            .with_half_life_days(7.0)
            .with_neuro_score(0.9)
            .with_novelty_score(0.2)
            .with_agent("test-agent".into(), 3);

        let id = mem.metadata.id;
        store.put(Galaxy::Codex, &mem).unwrap();

        let back = store.get(Galaxy::Codex, id).unwrap().unwrap();
        assert_eq!(back.metadata.memory_type, MemoryType::Pattern);
        assert!((back.metadata.neuro_score - 0.9).abs() < 1e-5);
        assert!((back.metadata.emotional_valence - (-0.5)).abs() < 1e-5);
        assert!(back.metadata.is_protected);
        assert_eq!(back.metadata.source, "inferred");
        assert!((back.metadata.source_trust - 0.3).abs() < 1e-5);
        assert!((back.metadata.half_life_days - 7.0).abs() < 1e-5);
        assert_eq!(back.metadata.agent_id, "test-agent");
        assert_eq!(back.metadata.version, 3);
    }
}
