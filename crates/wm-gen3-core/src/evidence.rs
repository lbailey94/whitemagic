//! Epistemic substrate skeleton and the Evidence closure surface (Charter v0.1.1 §3.8).
//!
//! Structure enforces the invariant:
//! - [`Domain`] is fixed at construction; there is **no setter and no re-label path**
//!   anywhere in the crate's public surface.
//! - [`EvidenceRecord`] fields are private; records are append-only in [`EvidenceStore`].
//! - `world` evidence enters only through [`RatifiedChannel`] — a capability token with
//!   a private field, mintable only by the operator path or the test stub.
//! - Testimony: the communication *event* may be recorded as `world` (it happened);
//!   the *content* stays `reported`. There is no promotion API.
//!
//! The two `compile_fail` doctests here are executed by `cargo test` and constitute the
//! type-level half of the Closure 2 static analysis.

/// Epistemic domain of a record. Immutable once constructed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Domain {
    /// Observed reality, admitted through a ratified intake channel.
    World,
    /// The system's own logs and state.
    System,
    /// Outputs of simulation/dreaming: never evidence about the world.
    Simulated,
    /// Testimony: someone communicated something. The event is evidence; the content is not.
    Reported,
}

/// Epistemic class (Charter §3.9). Fixed at construction in Phase 1.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Class {
    /// Something encountered, observed, imported or deliberately stored.
    Evidence,
    /// A revisable claim held about the world.
    Belief,
    /// A hypothesis, analogy, candidate or prediction — speculative by nature.
    Speculation,
}

/// Minimal lifecycle state (contracts §1.3). Phase 1: imports are fixed
/// `Persistent`; lifecycle is exercised on inferred relations.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RecordStatus {
    Transient,
    Candidate,
    Persistent,
    Cold,
}

/// A durable evidence record.
///
/// ```compile_fail
/// use wm_gen3_core::evidence::{Domain, EvidenceRecord};
/// // Fields are private; records cannot be conjured — only recorded through the store.
/// let r = EvidenceRecord { id: 1, domain: Domain::World, content: "x".into(), source: "y".into() }; // E0451
/// ```
#[derive(Debug, Clone)]
pub struct EvidenceRecord {
    id: u64,
    domain: Domain,
    class: Class,
    content: String,
    source: String,
    confidence: f32,
    status: RecordStatus,
    created_at: u64,
}

impl EvidenceRecord {
    #[must_use]
    pub fn id(&self) -> u64 {
        self.id
    }

    #[must_use]
    pub fn domain(&self) -> Domain {
        self.domain
    }

    #[must_use]
    pub fn class(&self) -> Class {
        self.class
    }

    #[must_use]
    pub fn content(&self) -> &str {
        &self.content
    }

    #[must_use]
    pub fn source(&self) -> &str {
        &self.source
    }

    #[must_use]
    pub fn confidence(&self) -> f32 {
        self.confidence
    }

    #[must_use]
    pub fn status(&self) -> RecordStatus {
        self.status
    }

    /// Logical ingest time (monotonic id); corpus order is preserved.
    #[must_use]
    pub fn created_at(&self) -> u64 {
        self.created_at
    }

    /// Crate-internal reconstruction from durable bytes. Not a public construction
    /// path: `pub(crate)` keeps the domain-fixed-at-construction invariant intact
    /// outside the crate (Closure 2 static analysis, `docs/CLOSURE_TESTS.md` §2.1).
    #[must_use]
    pub(crate) fn from_wire(
        id: u64,
        domain: Domain,
        class: Class,
        content: String,
        source: String,
        confidence: f32,
        status: RecordStatus,
        created_at: u64,
    ) -> Self {
        Self {
            id,
            domain,
            class,
            content,
            source,
            confidence,
            status,
            created_at,
        }
    }
}

/// Ratified world-intake channel (capability token).
///
/// ```compile_fail
/// use wm_gen3_core::evidence::RatifiedChannel;
/// let forged = RatifiedChannel { name: "fake".into() }; // E0451: private field
/// ```
#[derive(Debug)]
pub struct RatifiedChannel {
    name: String,
}

impl RatifiedChannel {
    /// Operator-side mint. Enabled only with the `operator` feature; the adaptive
    /// layer never enables it (and never links the admin path anyway).
    #[cfg(feature = "operator")]
    #[must_use]
    pub fn mint(name: &str) -> Self {
        Self {
            name: name.to_string(),
        }
    }

    /// Test stub — explicitly not a production construction path.
    #[cfg(test)]
    #[must_use]
    pub fn stub(name: &str) -> Self {
        Self {
            name: name.to_string(),
        }
    }

    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }
}

/// Refusal reasons for store writes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Refusal {
    /// A record with this id already exists. Append-only: re-labelling is impossible.
    DuplicateId,
}

/// Append-only evidence store. No record is ever mutated or re-labelled.
#[derive(Debug, Default)]
pub struct EvidenceStore {
    records: Vec<EvidenceRecord>,
    next_id: u64,
}

impl EvidenceStore {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    fn push(&mut self, domain: Domain, content: &str, source: String) -> u64 {
        let id = self.next_id;
        self.next_id += 1;
        self.records.push(EvidenceRecord {
            id,
            domain,
            class: Class::Evidence,
            content: content.to_string(),
            source,
            confidence: 1.0,
            status: RecordStatus::Persistent,
            created_at: id,
        });
        id
    }

    /// Raw append. Duplicate ids are refused — this is the no-re-label gate.
    pub fn append(&mut self, record: EvidenceRecord) -> Result<(), Refusal> {
        // Fast path for monotonic appends (e.g. store hydration): if record.id >= next_id,
        // it cannot collide with any previously inserted record.
        if record.id < self.next_id && self.records.iter().any(|r| r.id == record.id) {
            return Err(Refusal::DuplicateId);
        }
        self.next_id = self.next_id.max(record.id.saturating_add(1));
        self.records.push(record);
        Ok(())
    }

    /// Observed reality — requires a ratified channel.
    /// The returned id is always a **new** record; nothing existing is modified.
    pub fn observe(&mut self, channel: &RatifiedChannel, content: &str, source: &str) -> u64 {
        self.push(
            Domain::World,
            content,
            format!("channel:{}:{source}", channel.name()),
        )
    }

    /// System-internal record.
    pub fn system(&mut self, content: &str, source: &str) -> u64 {
        self.push(Domain::System, content, source.to_string())
    }

    /// Simulation output — never world evidence; no promotion path exists.
    pub fn simulated(&mut self, content: &str, source: &str) -> u64 {
        self.push(Domain::Simulated, content, source.to_string())
    }

    /// Testimony — the communication event is recorded; the content stays reported.
    pub fn reported(&mut self, content: &str, source: &str) -> u64 {
        self.push(Domain::Reported, content, source.to_string())
    }

    #[must_use]
    pub fn get(&self, id: u64) -> Option<&EvidenceRecord> {
        self.records.iter().find(|r| r.id == id)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.records.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Closure 2 canary A: a simulated record cannot be re-labelled, even by the
    /// strongest available (in-crate privileged) attempt.
    #[test]
    fn simulated_record_cannot_be_relabelled() {
        let mut store = EvidenceStore::new();
        let id = store.simulated("hypothesis H: bridge is underwater", "dream-cycle");
        let before = store.get(id).expect("record exists").clone();

        // Attempt: re-insert a relabelled copy with the same id.
        let relabelled = EvidenceRecord {
            id,
            domain: Domain::World,
            class: Class::Evidence,
            content: before.content().to_string(),
            source: before.source().to_string(),
            confidence: 1.0,
            status: RecordStatus::Persistent,
            created_at: id,
        };
        assert_eq!(store.append(relabelled), Err(Refusal::DuplicateId));

        // The original is untouched, byte for byte.
        let after = store.get(id).expect("record still exists");
        assert_eq!(after.domain(), Domain::Simulated);
        assert_eq!(after.content(), before.content());
        assert_eq!(after.source(), before.source());
        assert_eq!(store.len(), 1);
    }

    /// Closure 2 canary D (positive): a ratified channel creates a NEW world record;
    /// pre-existing records are unaffected.
    #[test]
    fn ratified_channel_creates_new_world_record_original_untouched() {
        let mut store = EvidenceStore::new();
        let sim_id = store.simulated("bridge collapsed (imagined)", "imagination");
        let channel = RatifiedChannel::stub("sensor-array-01");
        let world_id = store.observe(&channel, "bridge collapsed", "accel-9");

        assert_ne!(
            sim_id, world_id,
            "world evidence is a new record, never a mutation"
        );
        let world = store.get(world_id).expect("world record exists");
        assert_eq!(world.domain(), Domain::World);
        assert!(
            world.source().contains("sensor-array-01"),
            "intake provenance recorded"
        );
        assert_eq!(
            store.get(sim_id).expect("sim record exists").domain(),
            Domain::Simulated
        );
    }

    /// Closure 2 canary B: testimony — the content stays reported.
    #[test]
    fn testimony_content_stays_reported() {
        let mut store = EvidenceStore::new();
        let id = store.reported("bridge collapsed", "source-X (human testimony)");
        assert_eq!(
            store.get(id).expect("record exists").domain(),
            Domain::Reported
        );

        // Strongest available attempt: relabel via same-id insert. Refused.
        let r = store.get(id).expect("record exists").clone();
        let forged = EvidenceRecord {
            id,
            domain: Domain::World,
            class: Class::Evidence,
            content: r.content().to_string(),
            source: r.source().to_string(),
            confidence: 1.0,
            status: RecordStatus::Persistent,
            created_at: id,
        };
        assert_eq!(store.append(forged), Err(Refusal::DuplicateId));
        assert_eq!(
            store.get(id).expect("record exists").domain(),
            Domain::Reported
        );
    }

    /// System logs stay system.
    #[test]
    fn system_logs_stay_system() {
        let mut store = EvidenceStore::new();
        let id = store.system("mesh beacon accepted", "sangha-transport");
        assert_eq!(
            store.get(id).expect("record exists").domain(),
            Domain::System
        );
    }

    /// The store is append-only: duplicate ids are refused; length only grows.
    #[test]
    fn store_is_append_only() {
        let mut store = EvidenceStore::new();
        let a = store.simulated("a", "t");
        let b = store.simulated("b", "t");
        assert_ne!(a, b);
        assert_eq!(store.len(), 2);

        let dup = EvidenceRecord {
            id: a,
            domain: Domain::System,
            class: Class::Evidence,
            content: "c".into(),
            source: "t".into(),
            confidence: 1.0,
            status: RecordStatus::Persistent,
            created_at: a,
        };
        assert_eq!(store.append(dup), Err(Refusal::DuplicateId));
        assert_eq!(store.len(), 2);
    }
}
