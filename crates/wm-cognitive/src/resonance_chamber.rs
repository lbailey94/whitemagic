//! Resonance Chamber — Bounded scratchpads with temporal decay and harmonic merge thresholds.
//!
//! # Valkyrie's Cognitive Doctrine
//! Unbounded multiplexed scratchpads cause memory pollution and cognitive drift.
//! Unchecked intermediate reasoning tokens linger indefinitely, corrupting future
//! context windows and polluting long-term memory retrieval indices.
//!
//! Instead, scratchpads must operate as structured **Resonance Chambers**:
//! 1. **Temporal Signatures**: Strict TTL (time-to-live) bounds and epoch-based lifecycles.
//!    Thoughts naturally decay and auto-expire unless reinforced by sympathetic resonance.
//! 2. **Harmonic Merge Thresholds**: Only thoughts whose resonance and coherence exceed
//!    a rigorous harmonic threshold are synthesized into permanent memory galaxies
//!    (e.g., [`Galaxy::Valkyrie`], [`Galaxy::Dreams`], [`Galaxy::Citta`]).
//! 3. **Bounded Capacity**: Fixed ceiling preventing runaway buffer growth, with deterministic
//!    eviction of lowest-resonance substrate noise when capacity is reached.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::time::Duration;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use uuid::Uuid;
use wm_core::{Coordinate5D, Galaxy};
use wm_memory::{Memory, MemoryType, Tier};
use wm_workspace::Salience;

/// Error conditions arising within a [`ResonanceChamber`].
#[derive(Debug, Clone, Error, PartialEq, Eq)]
pub enum ChamberError {
    /// Chamber reached max capacity and overflow eviction is disabled.
    #[error("resonance chamber '{0}' capacity exhausted ({1} items)")]
    CapacityExhausted(String, usize),
    /// Thought identifier not found in active chamber.
    #[error("thought {0} not found in chamber '{1}'")]
    ThoughtNotFound(Uuid, String),
    /// Duplicate thought key attempted.
    #[error("thought with key '{0}' already exists in chamber '{1}'")]
    DuplicateKey(String, String),
    /// Thought has already expired and cannot be reinforced.
    #[error("thought {0} has expired")]
    ThoughtExpired(Uuid),
}

/// Temporal signature tracking the epoch and TTL constraints of a scratchpad thought.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TemporalSignature {
    /// Exact UTC timestamp when the thought entered the chamber.
    pub created_at: DateTime<Utc>,
    /// UTC timestamp of the most recent sympathetic resonance or reinforcement.
    pub last_resonated_at: DateTime<Utc>,
    /// Bounded time-to-live duration before automatic expiration.
    pub ttl: Duration,
    /// Originating chamber epoch counter.
    pub epoch_origin: u64,
    /// Maximum number of chamber epochs this thought can survive without being merged.
    pub max_epochs: u64,
}

impl TemporalSignature {
    /// Create a new temporal signature with specified TTL and epoch bounds.
    #[must_use]
    pub fn new(ttl: Duration, epoch_origin: u64, max_epochs: u64) -> Self {
        let now = Utc::now();
        Self {
            created_at: now,
            last_resonated_at: now,
            ttl,
            epoch_origin,
            max_epochs,
        }
    }

    /// Check if this thought has exceeded its TTL or maximum epoch boundary.
    #[must_use]
    pub fn is_expired(&self, now: DateTime<Utc>, current_epoch: u64) -> bool {
        let age_millis = (now - self.last_resonated_at).num_milliseconds();
        let ttl_millis = self.ttl.as_millis() as i64;
        let epoch_age = current_epoch.saturating_sub(self.epoch_origin);

        age_millis >= ttl_millis || epoch_age >= self.max_epochs
    }

    /// Compute elapsed time since creation.
    #[must_use]
    pub fn age(&self, now: DateTime<Utc>) -> Duration {
        let millis = (now - self.created_at).num_milliseconds().max(0) as u64;
        Duration::from_millis(millis)
    }

    /// Remaining time before TTL expiration, or zero if already expired.
    #[must_use]
    pub fn remaining_ttl(&self, now: DateTime<Utc>) -> Duration {
        let elapsed = (now - self.last_resonated_at).num_milliseconds().max(0) as u64;
        let ttl_ms = self.ttl.as_millis() as u64;
        Duration::from_millis(ttl_ms.saturating_sub(elapsed))
    }

    /// Reinforce the temporal signature, refreshing the `last_resonated_at` anchor.
    pub const fn touch(&mut self, now: DateTime<Utc>) {
        self.last_resonated_at = now;
    }

    /// Extend the TTL duration by a bonus increment.
    pub const fn extend_ttl(&mut self, bonus: Duration) {
        self.ttl = self.ttl.saturating_add(bonus);
    }
}

/// Harmonic resonance profile of an active scratchpad thought.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HarmonicProfile {
    /// Intrinsic clarity and internal consistency of the thought (0.0 to 1.0).
    pub coherence: f32,
    /// Sympathetic resonance with ambient context and surrounding thoughts (0.0 to 1.0).
    pub resonance: f32,
    /// Affective / cognitive valence (-1.0 to +1.0).
    pub valence: f32,
    /// Multiplicative salience score from global workspace (urgency, novelty, confidence).
    pub salience: Salience,
    /// Number of times sympathetic vibrations reinforced this thought.
    pub reinforcement_count: u32,
}

impl Default for HarmonicProfile {
    fn default() -> Self {
        Self {
            coherence: 0.5,
            resonance: 0.5,
            valence: 0.0,
            salience: Salience::new(0.5, 0.5, 0.8),
            reinforcement_count: 0,
        }
    }
}

impl HarmonicProfile {
    /// Construct a new harmonic profile.
    #[must_use]
    pub const fn new(coherence: f32, resonance: f32, valence: f32, salience: Salience) -> Self {
        Self {
            coherence: coherence.clamp(0.0, 1.0),
            resonance: resonance.clamp(0.0, 1.0),
            valence: valence.clamp(-1.0, 1.0),
            salience: salience.clamped(),
            reinforcement_count: 0,
        }
    }

    /// Unified harmonic composite score (0.0 to 1.0).
    ///
    /// Weights internal coherence (50%), sympathetic resonance (30%), and workspace
    /// salience composite (20%), modulated by a saturating reinforcement multiplier.
    #[must_use]
    pub fn composite_score(&self) -> f32 {
        let base =
            (self.coherence * 0.50) + (self.resonance * 0.30) + (self.salience.composite() * 0.20);
        let reinforcement_bonus = 1.0 + (0.05 * (self.reinforcement_count.min(6) as f32));
        (base * reinforcement_bonus).clamp(0.0, 1.0)
    }

    /// Apply temporal decay to coherence and resonance.
    pub fn apply_decay(&mut self, factor: f32) {
        let factor = factor.clamp(0.0, 1.0);
        self.coherence = (self.coherence * (1.0 - factor)).clamp(0.0, 1.0);
        self.resonance = (self.resonance * (1.0 - factor)).clamp(0.0, 1.0);
    }

    /// Reinforce thought coherence and resonance with a positive boost.
    pub fn reinforce(&mut self, boost: f32) {
        let b = boost.clamp(0.0, 1.0);
        self.coherence = (self.coherence + (b * 0.5)).clamp(0.0, 1.0);
        self.resonance = (self.resonance + b).clamp(0.0, 1.0);
        self.reinforcement_count = self.reinforcement_count.saturating_add(1);
    }
}

/// A structured, bounded thought residing within a [`ResonanceChamber`].
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChamberThought {
    /// Unique thought identity.
    pub id: Uuid,
    /// Human or semantic key label for indexing (e.g., "valkyrie.reflection.loop").
    pub key: String,
    /// Raw textual content of the scratchpad thought.
    pub content: String,
    /// Originating cognitive core or agent (e.g., "valkyrie", "citta", "autonomous").
    pub source: String,
    /// Intended destination galaxy if this thought reaches harmonic synthesis.
    pub target_galaxy: Galaxy,
    /// Category tags.
    pub tags: Vec<String>,
    /// Temporal constraints (TTL and epoch bounds).
    pub temporal: TemporalSignature,
    /// Resonance harmonics and coherence scoring.
    pub harmonics: HarmonicProfile,
    /// Optional arbitrary JSON payload for structured scratchpad artifacts.
    pub payload: serde_json::Value,
    /// Flag tracking whether this thought has been merged into long-term memory.
    pub synthesized: bool,
}

impl ChamberThought {
    /// Create a new chamber thought with default temporal bounds and harmonics.
    #[must_use]
    pub fn new(
        key: impl Into<String>,
        content: impl Into<String>,
        target_galaxy: Galaxy,
        coherence: f32,
    ) -> Self {
        let key_str = key.into();
        let content_str = content.into();
        Self {
            id: Uuid::new_v4(),
            key: key_str,
            content: content_str,
            source: "valkyrie".to_string(),
            target_galaxy,
            tags: vec!["scratchpad".to_string(), "resonance_chamber".to_string()],
            temporal: TemporalSignature::new(Duration::from_secs(300), 0, 5),
            harmonics: HarmonicProfile {
                coherence: coherence.clamp(0.0, 1.0),
                resonance: coherence.clamp(0.0, 1.0),
                valence: 0.0,
                salience: Salience::new(0.6, 0.7, 0.9),
                reinforcement_count: 0,
            },
            payload: serde_json::Value::Null,
            synthesized: false,
        }
    }

    /// Builder: attach custom TTL.
    #[must_use]
    pub const fn with_ttl(mut self, ttl: Duration) -> Self {
        self.temporal.ttl = ttl;
        self
    }

    /// Builder: attach epoch bounds.
    #[must_use]
    pub const fn with_epoch_bounds(mut self, origin: u64, max_epochs: u64) -> Self {
        self.temporal.epoch_origin = origin;
        self.temporal.max_epochs = max_epochs;
        self
    }

    /// Builder: specify originating source.
    #[must_use]
    pub fn with_source(mut self, source: impl Into<String>) -> Self {
        self.source = source.into();
        self
    }

    /// Builder: attach category tags.
    #[must_use]
    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self
    }

    /// Builder: attach custom salience.
    #[must_use]
    pub const fn with_salience(mut self, salience: Salience) -> Self {
        self.harmonics.salience = salience;
        self
    }

    /// Builder: attach structured payload.
    #[must_use]
    pub fn with_payload(mut self, payload: serde_json::Value) -> Self {
        self.payload = payload;
        self
    }

    /// Check if this thought is stale (either expired by TTL or epoch).
    #[must_use]
    pub fn is_stale(&self, now: DateTime<Utc>, current_epoch: u64) -> bool {
        self.temporal.is_expired(now, current_epoch) || self.harmonics.coherence <= 0.01
    }

    /// Calculate effective harmonic score at current moment.
    #[must_use]
    pub fn effective_harmonic_score(&self) -> f32 {
        self.harmonics.composite_score()
    }

    /// Synthesize this chamber thought into a permanent [`Memory`] record.
    ///
    /// Stamps the target galaxy (e.g. [`Galaxy::Valkyrie`] or [`Galaxy::Dreams`]),
    /// sets importance from the harmonic composite score, and assigns [`Tier::Working`].
    #[must_use]
    pub fn to_memory(&self) -> Memory {
        let importance = self.effective_harmonic_score();
        let mut mem =
            Memory::new(self.target_galaxy, self.content.clone()).with_importance(importance);

        let mut tags = self.tags.clone();
        if !tags.contains(&"synthesized".to_string()) {
            tags.push("synthesized".to_string());
        }
        if !tags.contains(&format!("source:{}", self.source)) {
            tags.push(format!("source:{}", self.source));
        }
        mem.metadata.tags = tags;
        mem.metadata.title = Some(self.key.clone());
        mem.metadata.memory_type = if self.target_galaxy == Galaxy::Valkyrie {
            MemoryType::Pattern
        } else if self.target_galaxy == Galaxy::Dreams {
            MemoryType::Hypothesis
        } else {
            MemoryType::ShortTerm
        };
        mem.metadata.tier = Tier::Working;
        mem.metadata.emotional_valence = self.harmonics.valence;
        mem.metadata.source.clone_from(&self.source);
        mem.metadata.coord5d = Coordinate5D::encode_with_context(&self.content, 0.6, importance);

        mem
    }
}

/// Candidate thought that has met the harmonic merge threshold and is ready for synthesis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HarmonicMergeCandidate {
    /// Thought UUID.
    pub thought_id: Uuid,
    /// Thought key.
    pub key: String,
    /// Harmonic score at time of qualification.
    pub harmonic_score: f32,
    /// Target galaxy destination.
    pub target_galaxy: Galaxy,
    /// Prepared permanent memory ready for insertion into LMDB.
    pub memory: Memory,
}

/// Configuration parameters governing a [`ResonanceChamber`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResonanceChamberConfig {
    /// Maximum concurrent thoughts allowed in this chamber (bounds memory footprint).
    pub max_capacity: usize,
    /// Default TTL duration for newly deposited thoughts.
    pub default_ttl: Duration,
    /// Maximum epochs a thought can survive before auto-expiring.
    pub max_epoch_survival: u64,
    /// Minimum harmonic score required to qualify for permanent merge into the target galaxy.
    pub harmonic_merge_threshold: f32,
    /// Linear or geometric decay factor applied per epoch (0.0 to 1.0).
    pub epoch_decay_rate: f32,
    /// Minimum coherence floor below which a thought is discarded as noise.
    pub min_coherence_floor: f32,
    /// Default destination galaxy when not explicitly specified.
    pub default_target_galaxy: Galaxy,
    /// Whether to automatically evict the lowest-resonance thought when capacity is exhausted.
    pub auto_evict_on_overflow: bool,
}

impl Default for ResonanceChamberConfig {
    fn default() -> Self {
        Self {
            max_capacity: 128,
            default_ttl: Duration::from_secs(300), // 5 minutes nominal scratchpad horizon
            max_epoch_survival: 5,
            harmonic_merge_threshold: 0.70, // Only highly coherent thoughts graduate
            epoch_decay_rate: 0.08,         // 8% harmonic decay per epoch
            min_coherence_floor: 0.05,      // Discard background thermal chatter
            default_target_galaxy: Galaxy::Valkyrie,
            auto_evict_on_overflow: true,
        }
    }
}

/// Telemetry and lifecycle statistics for a [`ResonanceChamber`].
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ChamberStats {
    /// Total thoughts deposited since inception.
    pub total_deposited: u64,
    /// Total thoughts auto-expired due to TTL or epoch lapse.
    pub total_expired: u64,
    /// Total thoughts graduated via harmonic merge.
    pub total_merged: u64,
    /// Total thoughts evicted due to capacity overflow.
    pub total_evicted: u64,
    /// Total sympathetic reinforcements applied.
    pub total_reinforcements: u64,
    /// Current chamber epoch counter.
    pub current_epoch: u64,
    /// Number of thoughts currently active in the chamber.
    pub active_thoughts: usize,
}

/// Summary report emitted after an epoch advancement cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EpochAdvancementReport {
    /// The new chamber epoch.
    pub epoch: u64,
    /// Total thoughts processed.
    pub thoughts_evaluated: usize,
    /// Identifiers of stale thoughts that auto-expired during this epoch sweep.
    pub expired_ids: Vec<Uuid>,
    /// Remaining thoughts in the chamber.
    pub remaining_count: usize,
    /// Average harmonic score among remaining thoughts.
    pub avg_harmonic_score: f32,
}

/// Bounded Resonance-Chamber Scratchpad subsystem.
///
/// Prevents memory pollution and cognitive drift by constraining scratchpad reasoning
/// within temporal bounds and harmonic merge filters.
pub struct ResonanceChamber {
    /// Human-readable chamber identifier (e.g., "valkyrie-scratchpad").
    name: String,
    /// Chamber configuration.
    config: ResonanceChamberConfig,
    /// Map of active thoughts keyed by thought UUID.
    thoughts: HashMap<Uuid, ChamberThought>,
    /// Secondary index from semantic key to thought UUID.
    key_index: HashMap<String, Uuid>,
    /// Current epoch counter.
    current_epoch: u64,
    /// Chamber cumulative metrics.
    stats: ChamberStats,
}

// Deliberate compact Debug: prints identity + live cardinalities, not the
// full thought/key maps (which would flood logs at chamber scale).
#[allow(clippy::missing_fields_in_debug)]
impl std::fmt::Debug for ResonanceChamber {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ResonanceChamber")
            .field("name", &self.name)
            .field("current_epoch", &self.current_epoch)
            .field("active_count", &self.thoughts.len())
            .field("max_capacity", &self.config.max_capacity)
            .field(
                "harmonic_merge_threshold",
                &self.config.harmonic_merge_threshold,
            )
            .finish()
    }
}

impl ResonanceChamber {
    /// Create a new resonance chamber with custom configuration.
    #[must_use]
    pub fn new(name: impl Into<String>, config: ResonanceChamberConfig) -> Self {
        Self {
            name: name.into(),
            config,
            thoughts: HashMap::new(),
            key_index: HashMap::new(),
            current_epoch: 0,
            stats: ChamberStats::default(),
        }
    }

    /// Create a new resonance chamber with default configuration.
    #[must_use]
    pub fn with_default_config(name: impl Into<String>) -> Self {
        Self::new(name, ResonanceChamberConfig::default())
    }

    /// Name of this resonance chamber.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Chamber configuration reference.
    #[must_use]
    pub const fn config(&self) -> &ResonanceChamberConfig {
        &self.config
    }

    /// Current chamber epoch.
    #[must_use]
    pub const fn current_epoch(&self) -> u64 {
        self.current_epoch
    }

    /// Number of active thoughts currently retained in the chamber.
    #[must_use]
    pub fn len(&self) -> usize {
        self.thoughts.len()
    }

    /// Whether the chamber contains no thoughts.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.thoughts.is_empty()
    }

    /// Maximum capacity of the chamber.
    #[must_use]
    pub const fn capacity(&self) -> usize {
        self.config.max_capacity
    }

    /// Current telemetry statistics.
    #[must_use]
    pub fn stats(&self) -> ChamberStats {
        let mut s = self.stats.clone();
        s.current_epoch = self.current_epoch;
        s.active_thoughts = self.thoughts.len();
        s
    }

    /// Deposit an explicitly constructed thought into the resonance chamber.
    ///
    /// If capacity is exceeded and `auto_evict_on_overflow` is enabled, the thought
    /// with the lowest harmonic score is automatically evicted.
    pub fn deposit(&mut self, mut thought: ChamberThought) -> Result<Uuid, ChamberError> {
        let now = Utc::now();
        // Purge any stale thoughts first to reclaim space naturally
        self.purge_stale(now);

        // Check if key already exists; if so, replace/reinforce existing
        if let Some(&existing_id) = self.key_index.get(&thought.key) {
            if let Some(existing) = self.thoughts.get_mut(&existing_id) {
                existing.content = thought.content;
                existing.harmonics.reinforce(thought.harmonics.coherence);
                existing.temporal.touch(now);
                self.stats.total_reinforcements = self.stats.total_reinforcements.saturating_add(1);
                return Ok(existing_id);
            }
        }

        // Check capacity bounds
        if self.thoughts.len() >= self.config.max_capacity {
            if self.config.auto_evict_on_overflow {
                self.evict_lowest_resonance();
            } else {
                return Err(ChamberError::CapacityExhausted(
                    self.name.clone(),
                    self.config.max_capacity,
                ));
            }
        }

        thought.temporal.epoch_origin = self.current_epoch;
        thought.temporal.max_epochs = self.config.max_epoch_survival;
        let id = thought.id;
        let key = thought.key.clone();

        self.key_index.insert(key, id);
        self.thoughts.insert(id, thought);
        self.stats.total_deposited = self.stats.total_deposited.saturating_add(1);

        Ok(id)
    }

    /// Deposit a scratchpad thought using convenient primitive values.
    pub fn deposit_thought(
        &mut self,
        key: &str,
        content: &str,
        coherence: f32,
        target_galaxy: Galaxy,
    ) -> Result<Uuid, ChamberError> {
        let thought = ChamberThought::new(key, content, target_galaxy, coherence)
            .with_ttl(self.config.default_ttl);
        self.deposit(thought)
    }

    /// Deposit a thought targeting the default galaxy ([`Galaxy::Valkyrie`]).
    pub fn deposit_simple(
        &mut self,
        key: &str,
        content: &str,
        coherence: f32,
    ) -> Result<Uuid, ChamberError> {
        self.deposit_thought(key, content, coherence, self.config.default_target_galaxy)
    }

    /// Retrieve an immutable reference to a thought by UUID.
    #[must_use]
    pub fn get(&self, id: &Uuid) -> Option<&ChamberThought> {
        self.thoughts.get(id)
    }

    /// Retrieve an immutable reference to a thought by semantic key.
    #[must_use]
    pub fn get_by_key(&self, key: &str) -> Option<&ChamberThought> {
        self.key_index.get(key).and_then(|id| self.thoughts.get(id))
    }

    /// Retrieve a mutable reference to a thought by UUID.
    pub fn get_mut(&mut self, id: &Uuid) -> Option<&mut ChamberThought> {
        self.thoughts.get_mut(id)
    }

    /// Sympathetically reinforce an existing thought, boosting its coherence and refreshing its TTL.
    pub fn reinforce(&mut self, id: &Uuid, boost: f32) -> Result<f32, ChamberError> {
        let now = Utc::now();
        let thought = self
            .thoughts
            .get_mut(id)
            .ok_or_else(|| ChamberError::ThoughtNotFound(*id, self.name.clone()))?;

        if thought.is_stale(now, self.current_epoch) {
            return Err(ChamberError::ThoughtExpired(*id));
        }

        thought.harmonics.reinforce(boost);
        thought.temporal.touch(now);
        self.stats.total_reinforcements = self.stats.total_reinforcements.saturating_add(1);

        Ok(thought.effective_harmonic_score())
    }

    /// Advance the chamber by one epoch, decaying all thoughts and auto-expiring stale ones.
    pub fn advance_epoch(&mut self) -> EpochAdvancementReport {
        self.current_epoch = self.current_epoch.saturating_add(1);
        let decay = self.config.epoch_decay_rate;
        let now = Utc::now();

        // Apply temporal decay to all thoughts
        for thought in self.thoughts.values_mut() {
            thought.harmonics.apply_decay(decay);
        }

        let evaluated = self.thoughts.len();
        // Purge expired thoughts
        let expired = self.purge_stale(now);
        let expired_ids: Vec<Uuid> = expired.into_iter().map(|t| t.id).collect();

        let avg_score = if self.thoughts.is_empty() {
            0.0
        } else {
            let sum: f32 = self
                .thoughts
                .values()
                .map(ChamberThought::effective_harmonic_score)
                .sum();
            sum / (self.thoughts.len() as f32)
        };

        EpochAdvancementReport {
            epoch: self.current_epoch,
            thoughts_evaluated: evaluated,
            expired_ids,
            remaining_count: self.thoughts.len(),
            avg_harmonic_score: avg_score,
        }
    }

    /// Automatically purge stale thoughts whose TTL has elapsed, epoch bound exceeded,
    /// or whose coherence has dropped below the chamber noise floor.
    pub fn purge_stale(&mut self, now: DateTime<Utc>) -> Vec<ChamberThought> {
        let floor = self.config.min_coherence_floor;
        let current_epoch = self.current_epoch;

        let mut stale_ids = Vec::new();
        for (id, thought) in &self.thoughts {
            if thought.is_stale(now, current_epoch) || thought.harmonics.coherence < floor {
                stale_ids.push(*id);
            }
        }

        let mut purged = Vec::with_capacity(stale_ids.len());
        for id in stale_ids {
            if let Some(thought) = self.thoughts.remove(&id) {
                self.key_index.remove(&thought.key);
                self.stats.total_expired = self.stats.total_expired.saturating_add(1);
                purged.push(thought);
            }
        }

        purged
    }

    /// Scan active thoughts and identify all candidates that exceed the harmonic merge threshold.
    #[must_use]
    pub fn evaluate_harmonic_merges(&self) -> Vec<HarmonicMergeCandidate> {
        let threshold = self.config.harmonic_merge_threshold;
        let now = Utc::now();

        self.thoughts
            .values()
            .filter(|t| !t.synthesized && !t.is_stale(now, self.current_epoch))
            .filter_map(|t| {
                let score = t.effective_harmonic_score();
                if score >= threshold {
                    Some(HarmonicMergeCandidate {
                        thought_id: t.id,
                        key: t.key.clone(),
                        harmonic_score: score,
                        target_galaxy: t.target_galaxy,
                        memory: t.to_memory(),
                    })
                } else {
                    None
                }
            })
            .collect()
    }

    /// Extract all thoughts qualifying for harmonic merge and mark them as synthesized.
    ///
    /// This prevents duplicate graduation while preserving the thought in the chamber
    /// until its temporal bounds naturally clear it.
    pub fn extract_harmonized(&mut self) -> Vec<HarmonicMergeCandidate> {
        let candidates = self.evaluate_harmonic_merges();
        for candidate in &candidates {
            if let Some(t) = self.thoughts.get_mut(&candidate.thought_id) {
                t.synthesized = true;
                self.stats.total_merged = self.stats.total_merged.saturating_add(1);
            }
        }
        candidates
    }

    /// Evict the active thought with the lowest harmonic composite score.
    pub fn evict_lowest_resonance(&mut self) -> Option<ChamberThought> {
        if self.thoughts.is_empty() {
            return None;
        }

        let mut lowest_id = None;
        let mut lowest_score = f32::MAX;

        for (id, thought) in &self.thoughts {
            let score = thought.effective_harmonic_score();
            if score < lowest_score {
                lowest_score = score;
                lowest_id = Some(*id);
            }
        }

        if let Some(id) = lowest_id {
            if let Some(thought) = self.thoughts.remove(&id) {
                self.key_index.remove(&thought.key);
                self.stats.total_evicted = self.stats.total_evicted.saturating_add(1);
                return Some(thought);
            }
        }

        None
    }

    /// Compute collective chamber resonance across all active thoughts.
    #[must_use]
    pub fn collective_resonance(&self) -> f32 {
        if self.thoughts.is_empty() {
            return 0.0;
        }
        let sum: f32 = self
            .thoughts
            .values()
            .map(ChamberThought::effective_harmonic_score)
            .sum();
        sum / (self.thoughts.len() as f32)
    }

    /// Return an iterator over all active thoughts.
    pub fn active_thoughts(&self) -> impl Iterator<Item = &ChamberThought> {
        self.thoughts.values()
    }

    /// Clear all thoughts from the chamber.
    pub fn clear(&mut self) {
        self.thoughts.clear();
        self.key_index.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_temporal_signature_bounded_lifetime_and_auto_expiration() {
        let mut chamber = ResonanceChamber::new(
            "test-temporal",
            ResonanceChamberConfig {
                default_ttl: Duration::from_millis(50),
                max_epoch_survival: 3,
                ..Default::default()
            },
        );

        let id = chamber
            .deposit_simple("test.stale", "Temporary hypothesis", 0.6)
            .expect("deposit should succeed");

        assert_eq!(chamber.len(), 1);
        assert!(chamber.get(&id).is_some());

        // Sleep past the 50ms TTL
        std::thread::sleep(Duration::from_millis(60));

        let now = Utc::now();
        let purged = chamber.purge_stale(now);
        assert_eq!(
            purged.len(),
            1,
            "stale thought must auto-expire on TTL lapse"
        );
        assert_eq!(purged[0].id, id);
        assert_eq!(
            chamber.len(),
            0,
            "chamber must be empty after purging stale thoughts"
        );
        assert!(chamber.get(&id).is_none());
    }

    #[test]
    fn test_epoch_bound_expiration() {
        let mut chamber = ResonanceChamber::new(
            "test-epochs",
            ResonanceChamberConfig {
                default_ttl: Duration::from_secs(3600), // Long TTL
                max_epoch_survival: 2,                  // Only survive 2 epochs
                ..Default::default()
            },
        );

        let id = chamber
            .deposit_simple("epoch.test", "Epoch bound hypothesis", 0.6)
            .unwrap();

        assert_eq!(chamber.len(), 1);

        // Advance 1st epoch
        let r1 = chamber.advance_epoch();
        assert_eq!(r1.epoch, 1);
        assert_eq!(r1.expired_ids.len(), 0);
        assert_eq!(chamber.len(), 1);

        // Advance 2nd epoch -> reaches max_epoch_survival (2) and auto-expires
        let r2 = chamber.advance_epoch();
        assert_eq!(r2.epoch, 2);
        assert_eq!(
            r2.expired_ids.len(),
            1,
            "thought must auto-expire after 2 epochs"
        );
        assert_eq!(r2.expired_ids[0], id);
        assert_eq!(chamber.len(), 0);
    }

    #[test]
    fn test_harmonic_merge_threshold_and_target_galaxies() {
        let mut chamber = ResonanceChamber::new(
            "test-harmonic-merge",
            ResonanceChamberConfig {
                harmonic_merge_threshold: 0.75, // Strict threshold
                ..Default::default()
            },
        );

        // 1. Thought below threshold (coherence 0.50 -> harmonic score ~0.49)
        let low_id = chamber
            .deposit_thought("low.res", "Uncertain fragment", 0.50, Galaxy::Codex)
            .unwrap();

        // 2. High-resonance Valkyrie thought (coherence 0.95 -> harmonic score > 0.85)
        let valk_id = chamber
            .deposit_thought(
                "valkyrie.insight",
                "Valkyrie architectural reflection on bounded resonance chambers",
                0.95,
                Galaxy::Valkyrie,
            )
            .unwrap();

        // 3. High-resonance Dreams thought (coherence 0.90)
        let dream_id = chamber
            .deposit_thought(
                "dream.synthesis",
                "Subconscious pattern alignment hypothesis",
                0.90,
                Galaxy::Dreams,
            )
            .unwrap();

        // Evaluate candidates
        let candidates = chamber.extract_harmonized();

        // Only high-coherence thoughts should be extracted
        assert_eq!(
            candidates.len(),
            2,
            "only high resonance thoughts qualify for harmonic merge"
        );

        let valk_candidate = candidates.iter().find(|c| c.thought_id == valk_id).unwrap();
        assert_eq!(valk_candidate.target_galaxy, Galaxy::Valkyrie);
        assert_eq!(valk_candidate.memory.metadata.galaxy, Galaxy::Valkyrie);
        assert_eq!(
            valk_candidate.memory.metadata.memory_type,
            MemoryType::Pattern
        );
        assert!(valk_candidate.harmonic_score >= 0.75);

        let dream_candidate = candidates
            .iter()
            .find(|c| c.thought_id == dream_id)
            .unwrap();
        assert_eq!(dream_candidate.target_galaxy, Galaxy::Dreams);
        assert_eq!(dream_candidate.memory.metadata.galaxy, Galaxy::Dreams);
        assert_eq!(
            dream_candidate.memory.metadata.memory_type,
            MemoryType::Hypothesis
        );
        assert!(dream_candidate.harmonic_score >= 0.75);

        // Low resonance thought was not merged
        assert!(candidates.iter().all(|c| c.thought_id != low_id));
        let low_thought = chamber.get(&low_id).unwrap();
        assert!(!low_thought.synthesized);
    }

    #[test]
    fn test_capacity_overflow_evicts_lowest_resonance() {
        let mut chamber = ResonanceChamber::new(
            "test-capacity",
            ResonanceChamberConfig {
                max_capacity: 2,
                auto_evict_on_overflow: true,
                ..Default::default()
            },
        );

        let id_low = chamber.deposit_simple("t1", "Low coherence", 0.20).unwrap();
        let _id_med = chamber
            .deposit_simple("t2", "Medium coherence", 0.60)
            .unwrap();
        assert_eq!(chamber.len(), 2);

        // Adding 3rd should evict t1 (lowest coherence 0.20)
        let id_high = chamber
            .deposit_simple("t3", "High coherence", 0.95)
            .unwrap();
        assert_eq!(chamber.len(), 2);
        assert!(
            chamber.get(&id_low).is_none(),
            "lowest resonance thought must be evicted on overflow"
        );
        assert!(chamber.get(&id_high).is_some());
    }

    #[test]
    fn test_reinforcement_boosts_harmonic_score() {
        let mut chamber = ResonanceChamber::with_default_config("test-reinforce");
        let id = chamber.deposit_simple("t1", "Initial idea", 0.60).unwrap();
        let initial_score = chamber.get(&id).unwrap().effective_harmonic_score();

        let boosted_score = chamber.reinforce(&id, 0.40).unwrap();
        assert!(
            boosted_score > initial_score,
            "reinforcement must increase harmonic score"
        );
        assert_eq!(chamber.get(&id).unwrap().harmonics.reinforcement_count, 1);
    }
}
