//! Operations: `remember · recall · think · inspect` (`docs/PHASE1_CONTRACTS.md` §2).
//!
//! Selection is per-operation; every choice is journaled; nothing here imports
//! Gen2 behavioral machinery. `recall` is read-only over records/relations
//! (usage bookkeeping for promotion lives in this process and in the journal).

use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::Path;
use std::time::Instant;
use uuid::Uuid;

use crate::constitution::{ConstitutionView, INVARIANTS};
use crate::evidence::{Domain, EvidenceStore, Refusal};
use crate::field::{self, Relation, RelationState};
use crate::intake::{CommitDisposition, CommitOutcome, IntakeKind, IntakeRequest, OperationId};
use crate::journal::{Journal, sha256_hex};
use crate::projection::{
    DIM, MODEL_ID, Projection, ProjectionStats, TAU_GATE, cosine, semantic_support,
};
use crate::pulse_compiler::{authorize_intake, authorize_sweep, authorize_sweep_replay};
use crate::store::Store;
use crate::sweep::{LIFECYCLE_AGE_SWEEPS, SWEEP_PROFILE_V1, SweepOutcome, UsageSnapshotIssuer};
use crate::sweep_planner::{SweepPlanInputs, plan_sweep};

/// Statutory policy values (tier 2). Declared here, journaled with every sweep.
#[derive(Debug, Clone)]
pub struct Policy {
    /// Rank multiplier applied to records that are superseded by a live relation
    /// when the caller asks for a current-preferred view (A4 ablation toggles).
    pub supersede_penalty: f32,
    /// Weight of logical recency in the rank key (tie-breaking toward later).
    pub recency_weight: f32,
    /// A token is "rare" at `df <= max(floor, corpus_len / divisor)`. N/20
    /// (≈5% df) is the conventional IR "rare term" cut. NOTE: values were fixed
    /// before the frozen A/B and are ablated there (A1); they were not tuned
    /// against scored runs (see `experiments/contradiction/PREFLIGHT_FINDINGS`).
    pub rare_df_divisor: usize,
    pub rare_df_floor: usize,
    /// Pair budget per `think` sweep (bounded exploration, Charter §3.1).
    pub pair_budget: usize,
    /// Scores below this are "no support" for abstention accounting.
    pub relevance_floor: f32,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            supersede_penalty: 0.6,
            recency_weight: 0.05,
            rare_df_divisor: 20,
            rare_df_floor: 2,
            pair_budget: 200_000,
            relevance_floor: 0.01,
        }
    }
}

impl Policy {
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "supersede_penalty": self.supersede_penalty,
            "recency_weight": self.recency_weight,
            "rare_df_divisor": self.rare_df_divisor,
            "rare_df_floor": self.rare_df_floor,
            "pair_budget": self.pair_budget,
            "relevance_floor": self.relevance_floor,
        })
    }
}

/// Selector mode (P2D §4). Default `PenaltyMultiplier` is the frozen Phase-2 behavior;
/// `Structural` is the pre-registered arbitration rule (no tunables).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Arbitration {
    /// Existing behavior: relevance key, superseded records multiplied down.
    PenaltyMultiplier,
    /// Structural precedence: current → unresolved → superseded strata, then
    /// within-stratum lexical support, then semantic support, then recency/id.
    Structural,
}

/// Import class for corpus material. `world` is deliberately absent: it enters
/// only through a ratified channel (Closure 2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum ImportKind {
    Reported,
    System,
    Simulated,
}

impl From<ImportKind> for IntakeKind {
    fn from(value: ImportKind) -> Self {
        match value {
            ImportKind::Reported => Self::Reported,
            ImportKind::System => Self::System,
            ImportKind::Simulated => Self::Simulated,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct RememberItem {
    pub content: String,
    pub source: String,
    pub kind: ImportKind,
}

/// High-density structured checkpoint for agent session continuity across turns and handoffs.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct SessionCheckpoint {
    pub session_id: String,
    pub agent_id: String,
    pub checkpoint_type: String,
    pub summary: String,
    #[serde(default)]
    pub next_queue: Vec<String>,
    #[serde(default)]
    pub open_flags: Vec<String>,
    #[serde(default)]
    pub context_token: Option<String>,
    #[serde(default)]
    pub representation: Option<crate::transport::RepresentationTransport>,
    #[serde(default)]
    pub timestamp_iso: Option<String>,
}

/// Resolved continuity view returned by Substrate::session_continuity.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct SessionContinuityView {
    pub record_id: u64,
    pub epoch: u64,
    pub session_id: String,
    pub agent_id: String,
    pub checkpoint_type: String,
    pub summary: String,
    pub next_queue: Vec<String>,
    pub open_flags: Vec<String>,
    pub context_token: Option<String>,
    pub representation: Option<crate::transport::RepresentationTransport>,
    pub timestamp_iso: Option<String>,
    pub raw_content: String,
}

#[derive(Debug, Clone)]
pub struct RecallQuery {
    pub query: String,
    pub limit: usize,
    pub candidate_limit: usize,
    pub include_historical: bool,
    pub min_score: f32,
    pub min_coverage: f32,
    /// Optional recall-side scope view selector (registration
    /// `docs/specs/W1_B5_RECALL_VIEW_REGISTRATION.md`): an exact, nonempty, colon-free label.
    /// When present, the candidate population is filtered to `corpus:<label>:<tags>` sources
    /// before scoring/selection. Absent → pre-change behavior unchanged.
    pub scope: Option<String>,
}

impl Default for RecallQuery {
    fn default() -> Self {
        Self {
            query: String::new(),
            limit: 10,
            candidate_limit: 40,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Hit {
    pub id: u64,
    pub content: String,
    pub source: String,
    pub score: f32,
    pub rank: usize,
    pub superseded_by: Option<u64>,
}

#[derive(Debug, Clone, Default)]
pub struct SweepStats {
    pub sweep: u64,
    pub pairs_lexical_candidates: usize,
    pub pairs_pruned_by_projection: usize,
    pub pairs_considered: usize,
    pub pairs_skipped_existing: usize,
    pub pairs_rejected_rule: usize,
    pub pairs_examined: usize,
    pub proposals: usize,
    pub promotions: usize,
    pub demotions: usize,
    pub rare_max_df: usize,
    pub index_ms: u64,
    pub pair_ms: u64,
    pub promotion_ms: u64,
    pub took_ms: u64,
    pub disabled: bool,
    /// Operation id of the committed (or attempted) sweep, when one was minted.
    pub operation_id: Option<OperationId>,
    /// Typed refusal reason; only set when `refused` is true.
    pub error: Option<String>,
    /// True when the sweep was refused (fail-closed, no canonical mutation).
    pub refused: bool,
    /// True when a committed plan was replayed instead of re-planned.
    pub replayed: bool,
}

/// Structured caller error (fail-closed). The A2 contract: out-of-range floor values are
/// refused, never silently filtered out or disabled (`docs/specs/W1_A2_evidence_disclosure.md`
/// §1.1). Caller errors precede selection, so they emit no journal events.
#[derive(Debug, Clone, PartialEq)]
pub enum RecallError {
    /// Floor outside [0, 1] (NaN and infinities included).
    InvalidFloor { field: &'static str, value: f32 },
    /// Scope selector violating the declared label grammar (nonempty, colon-free).
    InvalidScope { value: String },
}

impl std::fmt::Display for RecallError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidFloor { field, value } => {
                write!(
                    f,
                    "invalid floor {field}={value}: must be within [0, 1] (fail-closed)"
                )
            }
            Self::InvalidScope { value } => {
                write!(
                    f,
                    "invalid scope selector {value:?}: labels are exact, nonempty, and must not contain ':' (fail-closed)"
                )
            }
        }
    }
}

impl std::error::Error for RecallError {}

fn validate_floors(q: &RecallQuery) -> Result<(), RecallError> {
    for (field, value) in [("min_score", q.min_score), ("min_coverage", q.min_coverage)] {
        if !(0.0..=1.0).contains(&value) {
            return Err(RecallError::InvalidFloor { field, value });
        }
    }
    Ok(())
}

/// Declared label grammar (B5 recall-view registration §1): opaque, exact, case-sensitive,
/// nonempty, colon-free. No trimming, case folding, normalization, or aliasing.
fn valid_label(label: &str) -> bool {
    !label.is_empty() && !label.contains(':')
}

/// Declared view derivation rule (registration §1): `corpus:<label>:<tags>` → the label is the
/// second colon-separated component. Sources outside the grammar (including the empty label
/// `corpus::tags`, and `corpus:` sources with no tags separator) are label-less: they belong to
/// no view and are reachable unscoped only.
fn source_label(source: &str) -> Option<&str> {
    let rest = source.strip_prefix("corpus:")?;
    let (label, _tags) = rest.split_once(':')?;
    valid_label(label).then_some(label)
}

fn validate_scope(q: &RecallQuery) -> Result<(), RecallError> {
    if let Some(scope) = &q.scope
        && !valid_label(scope)
    {
        return Err(RecallError::InvalidScope {
            value: scope.clone(),
        });
    }
    Ok(())
}

fn domain_tag(domain: Domain) -> &'static str {
    match domain {
        Domain::World => "world",
        Domain::System => "system",
        Domain::Simulated => "simulated",
        Domain::Reported => "reported",
    }
}

pub(crate) fn kind_tag(kind: ImportKind) -> &'static str {
    match kind {
        ImportKind::Reported => "reported",
        ImportKind::System => "system",
        ImportKind::Simulated => "simulated",
    }
}

pub(crate) fn identity_key(
    content: &str,
    source: &str,
    kind_tag: &str,
) -> (String, String, String) {
    (
        sha256_hex(content.as_bytes()),
        source.to_string(),
        kind_tag.to_string(),
    )
}

/// Declared noise class table (spec W1_A1 rev 2 §1.3): content-pattern, kind-independent,
/// rule-based. Returns the matched class name in declared table order; `None` outside the table.
pub(crate) fn noise_class(content: &str) -> Option<&'static str> {
    if content.contains("Traceback (most recent call last):") {
        return Some("traceback");
    }
    if content.lines().any(|line| {
        let line = line.trim_start();
        line.starts_with("Error:") || line.starts_with("Exception:")
    }) {
        return Some("error_line");
    }
    let trimmed = content.trim();
    if trimmed.starts_with("{\"json\":") {
        return Some("json_blob");
    }
    if trimmed.starts_with("<function ") && trimmed.contains(" at 0x") && trimmed.ends_with('>') {
        return Some("function_repr");
    }
    if trimmed.chars().count() < 10 {
        return Some("too_short");
    }
    None
}

/// Derived embedding-cache format version. Bump to invalidate every cached vector;
/// derived state only, canonical data is never affected (`docs/DERIVED_CACHE_POLICY.md`).
pub(crate) const EMBED_CACHE_FORMAT_VERSION: u8 = 1;

/// Versioned derived-cache key: model identity + format version + content hash.
pub(crate) fn embed_cache_key(text: &str, version: u8) -> String {
    format!("{MODEL_ID}:v{version}:{}", sha256_hex(text.as_bytes()))
}

/// Persistent bijective map entry between legacy Gen2 UUID and Gen3 numeric record ID.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct UuidMapEntry {
    pub uuid: Uuid,
    pub record_id: u64,
}

/// The Phase-1 substrate: store + epistemic store + journal + policy.
pub struct Substrate {
    store: Store,
    evidence: EvidenceStore,
    journal: Option<Journal>,
    view: ConstitutionView,
    policy: Policy,
    budget: u32,
    writes_used: u32,
    usage: HashMap<u64, u32>,
    /// Exact-content gate index (spec W1_A1): (content sha256, source, kind tag) -> record id.
    identity: HashMap<(String, String, String), u64>,
    journal_ok: bool,
    violations: u64,
    sweep_enabled: bool,
    /// A1 rev 2 ablation switch: `WM_GEN3_NOISE=0` disables the declared noise class table.
    noise_enabled: bool,
    projection: Option<Projection>,
    projection_gated: bool,
    projection_gate_count: bool,
    arbitration: Arbitration,
    dispersion_enabled: bool,
    intake_authority: Option<crate::evidence::RatifiedChannel>,
    suppress_intake_journal: bool,
    /// Trusted process-local usage issuer (Gate 9A D2 option b: volatile evidence).
    usage_issuer: UsageSnapshotIssuer,
    /// Volatile Hebbian co-activation counters (neurons that fire together wire together).
    hebbian_coactivations: HashMap<(u64, u64), u32>,
    /// Bijective Identity Translation Map for legacy Gen2 interoperability:
    /// UUID <-> u64 record ID mapping table.
    uuid_to_id: HashMap<Uuid, u64>,
    id_to_uuid: HashMap<u64, Uuid>,
}

impl Substrate {
    pub fn open(
        store_path: &Path,
        journal_path: Option<&Path>,
        view: ConstitutionView,
    ) -> Result<Self, String> {
        Self::open_with_mode(store_path, journal_path, view, false)
    }

    /// Open an immutable/quiescent snapshot read-only with no lock-file interaction.
    /// The caller must exclude concurrent writers; writes through this handle are refused.
    pub fn open_readonly(
        store_path: &Path,
        journal_path: Option<&Path>,
        view: ConstitutionView,
    ) -> Result<Self, String> {
        Self::open_with_mode(store_path, journal_path, view, true)
    }

    fn open_with_mode(
        store_path: &Path,
        journal_path: Option<&Path>,
        view: ConstitutionView,
        readonly: bool,
    ) -> Result<Self, String> {
        let store = if readonly {
            Store::open_readonly(store_path)
        } else {
            Store::open(store_path)
        }
        .map_err(|e| e.to_string())?;
        let (evidence, identity) = if readonly {
            (EvidenceStore::new(), HashMap::new())
        } else {
            let mut evidence = EvidenceStore::new();
            let mut identity: HashMap<(String, String, String), u64> = HashMap::new();
            for record in store.iter_records().map_err(|e| e.to_string())? {
                identity.insert(
                    identity_key(
                        record.content(),
                        record.source(),
                        domain_tag(record.domain()),
                    ),
                    record.id(),
                );
                evidence
                    .append(record)
                    .map_err(|e| format!("hydrate: {e:?}"))?;
            }
            (evidence, identity)
        };
        let journal = match journal_path {
            Some(p) => Some(Journal::open(p).map_err(|e| e.to_string())?),
            None => None,
        };
        let uuid_path = store_path.join("uuid_index.jsonl");
        let mut uuid_to_id = HashMap::new();
        let mut id_to_uuid = HashMap::new();
        if uuid_path.exists() {
            if let Ok(file) = std::fs::File::open(&uuid_path) {
                use std::io::BufRead;
                let reader = std::io::BufReader::new(file);
                for line in reader.lines().flatten() {
                    if let Ok(entry) = serde_json::from_str::<UuidMapEntry>(&line) {
                        uuid_to_id.insert(entry.uuid, entry.record_id);
                        id_to_uuid.insert(entry.record_id, entry.uuid);
                    }
                }
            }
        }
        let budget = view.writes_per_min();
        #[cfg(test)]
        let intake_authority = Some(crate::evidence::RatifiedChannel::stub("core-unit-tests"));
        #[cfg(not(test))]
        let intake_authority = None;
        let usage_issuer = UsageSnapshotIssuer::new().map_err(|e| e.to_string())?;
        Ok(Self {
            store,
            evidence,
            journal,
            view,
            policy: Policy::default(),
            budget,
            writes_used: 0,
            usage: HashMap::new(),
            identity,
            journal_ok: true,
            violations: 0,
            sweep_enabled: true,
            noise_enabled: true,
            projection: None,
            projection_gated: false,
            projection_gate_count: false,
            arbitration: Arbitration::PenaltyMultiplier,
            dispersion_enabled: false,
            intake_authority,
            suppress_intake_journal: false,
            usage_issuer,
            hebbian_coactivations: HashMap::new(),
            uuid_to_id,
            id_to_uuid,
        })
    }

    /// Returns the monotonic record ID associated with a legacy Gen2 UUID, if indexed.
    #[must_use]
    pub fn lookup_id_by_uuid(&self, uuid: &Uuid) -> Option<u64> {
        self.uuid_to_id.get(uuid).copied()
    }

    /// Returns the legacy Gen2 UUID associated with a monotonic record ID, if indexed.
    #[must_use]
    pub fn lookup_uuid_by_id(&self, record_id: u64) -> Option<Uuid> {
        self.id_to_uuid.get(&record_id).copied()
    }

    /// Binds a legacy Gen2 UUID to a Gen3 numeric record ID, persisting to the index.
    pub fn bind_uuid(&mut self, uuid: Uuid, record_id: u64) {
        self.uuid_to_id.insert(uuid, record_id);
        self.id_to_uuid.insert(record_id, uuid);
        if !self.store.is_readonly() {
            let entry = UuidMapEntry { uuid, record_id };
            if let Ok(json) = serde_json::to_string(&entry) {
                let path = self.store.path().join("uuid_index.jsonl");
                let file = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(path);
                if let Ok(mut f) = file {
                    use std::io::Write;
                    let _ = writeln!(f, "{json}");
                }
            }
        }
    }

    /// Retrieves the bound UUID or generates and binds a deterministic UUIDv5.
    pub fn get_or_create_uuid(&mut self, record_id: u64) -> Uuid {
        if let Some(u) = self.id_to_uuid.get(&record_id) {
            *u
        } else {
            let derived = Uuid::new_v5(&Uuid::NAMESPACE_OID, &record_id.to_be_bytes());
            self.bind_uuid(derived, record_id);
            derived
        }
    }

    /// Fetches an EvidenceRecord by its legacy Gen2 UUID.
    pub fn lookup_record_by_uuid(
        &self,
        uuid: &Uuid,
    ) -> Result<Option<crate::evidence::EvidenceRecord>, crate::store::StoreError> {
        if let Some(id) = self.lookup_id_by_uuid(uuid) {
            self.store.get_record(id)
        } else {
            Ok(None)
        }
    }

    /// Contextual-dispersion weighting (`WM_GEN3_DISPERSION=1`, P2E §4).
    pub fn set_dispersion(&mut self, on: bool) {
        self.dispersion_enabled = on;
    }

    #[must_use]
    pub fn dispersion_enabled(&self) -> bool {
        self.dispersion_enabled
    }

    /// `C(t) = 1 − H(contexts|t)/log m_t`; contexts are provenance sessions from
    /// record sources (records without a session use their own id). Edge cases:
    /// `m_t ≤ 1` or `df = 0` → 1; no epsilon (exactly zero allowed).
    fn dispersion_weight(&self, term: &str) -> f32 {
        let ids = match self.store.postings(term) {
            Ok(v) => v,
            Err(_) => return 1.0,
        };
        // Declared reduction order (W1_SCORER_DETERMINISM_REGISTRATION): iterate contexts
        // in sorted-key order (BTreeMap) so entropy summation is identical across runs.
        let mut per_context: BTreeMap<String, usize> = BTreeMap::new();
        for id in &ids {
            let context = self
                .store
                .get_record(*id)
                .ok()
                .flatten()
                .map(|r| Self::record_context(r.source()))
                .unwrap_or_else(|| format!("rec:{id}"));
            *per_context.entry(context).or_default() += 1;
        }
        let n = ids.len();
        let m = per_context.len();
        if n == 0 || m <= 1 {
            return 1.0;
        }
        let mut entropy = 0.0_f64;
        for count in per_context.values() {
            let p = *count as f64 / n as f64;
            entropy -= p * p.ln();
        }
        let c = 1.0 - entropy / (m as f64).ln();
        c.clamp(0.0, 1.0) as f32
    }

    fn record_context(source: &str) -> String {
        // Source format: "corpus:<galaxy>:<tag>,<tag>,…"; session tags are
        // "session_NNN". Records without a session tag become their own context.
        for part in source.split(&[':', ','][..]) {
            let p = part.trim();
            if p.starts_with("session_") && p.len() > "session_".len() {
                return p.to_string();
            }
        }
        source.to_string()
    }

    /// Set the selector mode (`WM_GEN3_ARBITRATION=structural` → P2D rule).
    pub fn set_arbitration(&mut self, mode: Arbitration) {
        self.arbitration = mode;
    }

    #[must_use]
    pub fn arbitration(&self) -> Arbitration {
        self.arbitration
    }

    /// Enable the semantic projection primitive (`WM_GEN3_PROJECTION=1`).
    /// Loads the frozen model from `cache_dir` (local, read-only); default-off.
    pub fn set_projection_enabled(
        &mut self,
        on: bool,
        cache_dir: Option<&Path>,
    ) -> Result<(), String> {
        if !on {
            self.projection = None;
            return Ok(());
        }
        let dir =
            cache_dir.ok_or_else(|| "projection: WM_GEN3_EMBED_CACHE is required".to_string())?;
        let projection = Projection::load(dir)?;
        let mut f = serde_json::Map::new();
        f.insert("model".into(), MODEL_ID.into());
        f.insert("dim".into(), DIM.into());
        f.insert("cache_dir".into(), format!("{}", dir.display()).into());
        f.insert("tau_gate".into(), TAU_GATE.into());
        f.insert(
            "model_load_ms".into(),
            projection.stats.model_load_ms.into(),
        );
        self.j("projection.load", f);
        self.projection = Some(projection);
        Ok(())
    }

    #[must_use]
    pub fn projection_enabled(&self) -> bool {
        self.projection.is_some()
    }

    /// GEN3-GATED-S-001: gate the projection pass at recall on the declared
    /// D2 lexical-insufficiency floor (`Policy.relevance_floor`). With this on
    /// (and projection enabled), the projection pass runs only when the max
    /// lexical support over lexical candidates is below the gate; otherwise
    /// recall takes the pure-lexical path. No scoring change.
    pub fn set_projection_gated(&mut self, on: bool) {
        self.projection_gated = on;
    }

    #[must_use]
    pub fn projection_gated(&self) -> bool {
        self.projection_gated
    }

    /// GEN3-GATED-S-003: activation by lexical-candidate count — the
    /// state-resolution sufficiency heuristic. With this on (and projection
    /// enabled), the pass fires only when fewer than two lexical candidates
    /// exist (0 or 1 matching records): a single record cannot form an
    /// earlier/current state comparison. Count mode takes precedence over the
    /// floor mode when both are set; the floor mode itself is unchanged.
    pub fn set_projection_gate_count(&mut self, on: bool) {
        self.projection_gate_count = on;
    }

    #[must_use]
    pub fn projection_gate_count(&self) -> bool {
        self.projection_gate_count
    }

    #[must_use]
    pub fn projection_stats(&self) -> Option<ProjectionStats> {
        self.projection.as_ref().map(|p| p.stats)
    }

    /// Embed with the versioned content-hash cache (dedup across records/processes).
    ///
    /// Derived state only: keys bind model identity, cache format version and content
    /// hash; canonical records/relations are never touched (see
    /// `docs/DERIVED_CACHE_POLICY.md`).
    fn embed_cached(&mut self, texts: &[String]) -> Result<Vec<Vec<f32>>, String> {
        let mut out: Vec<Option<Vec<f32>>> = vec![None; texts.len()];
        let mut hashes: Vec<String> = Vec::with_capacity(texts.len());
        for (i, t) in texts.iter().enumerate() {
            let h = embed_cache_key(t, EMBED_CACHE_FORMAT_VERSION);
            if let Some(v) = self
                .store
                .get_embedding_cache(&h)
                .map_err(|e| e.to_string())?
            {
                out[i] = Some(v);
            }
            hashes.push(h);
        }
        let misses: Vec<usize> = (0..texts.len()).filter(|i| out[*i].is_none()).collect();
        if !misses.is_empty() {
            let batch: Vec<String> = misses.iter().map(|i| texts[*i].clone()).collect();
            let projection = self
                .projection
                .as_mut()
                .ok_or_else(|| "projection: not enabled".to_string())?;
            let vectors = projection.embed(&batch)?;
            for (slot, vector) in misses.iter().zip(vectors.into_iter()) {
                if !self.store.is_readonly() {
                    self.store
                        .put_embedding_cache(&hashes[*slot], &vector)
                        .map_err(|e| e.to_string())?;
                }
                out[*slot] = Some(vector);
            }
        }
        Ok(out.into_iter().map(|v| v.unwrap_or_default()).collect())
    }

    /// A1 ablation switch: `WM_GEN3_SWEEP=0` disables relation candidacy.
    pub fn set_sweep_enabled(&mut self, on: bool) {
        self.sweep_enabled = on;
    }

    #[must_use]
    pub fn sweep_enabled(&self) -> bool {
        self.sweep_enabled
    }

    /// A1 rev 2 ablation switch: `WM_GEN3_NOISE=0` disables the noise class table (§1.3).
    pub fn set_noise_enabled(&mut self, on: bool) {
        self.noise_enabled = on;
    }

    #[must_use]
    pub fn noise_enabled(&self) -> bool {
        self.noise_enabled
    }

    #[must_use]
    pub fn policy(&self) -> &Policy {
        &self.policy
    }

    #[must_use]
    pub fn budget(&self) -> u32 {
        self.budget
    }

    pub fn set_budget(&mut self, per_min: u32) {
        self.budget = per_min;
        self.writes_used = 0;
    }

    #[must_use]
    pub fn journal_ok(&self) -> bool {
        self.journal_ok
    }

    #[must_use]
    pub fn identity_map(&self) -> &HashMap<(String, String, String), u64> {
        &self.identity
    }

    #[must_use]
    pub fn journal_path(&self) -> Option<&Path> {
        self.journal.as_ref().map(|j| j.path())
    }

    #[must_use]
    pub fn violations(&self) -> u64 {
        self.violations
    }

    #[must_use]
    pub fn store(&self) -> &Store {
        &self.store
    }

    pub fn intake_realm_id(&self) -> Result<[u8; 16], String> {
        self.store.realm_id().map_err(|e| e.to_string())
    }

    pub fn intake_epoch(&self) -> Result<u64, String> {
        self.store.epoch().map_err(|e| e.to_string())
    }

    /// Install the trusted local authority used by production compatibility routes.
    pub fn set_intake_authority(&mut self, authority: crate::evidence::RatifiedChannel) {
        self.intake_authority = Some(authority);
    }

    /// Test-only: simulate the production condition where no local authority is
    /// installed (unit-test builds install a stub at open).
    #[cfg(test)]
    pub(crate) fn clear_intake_authority(&mut self) {
        self.intake_authority = None;
    }

    fn j(&mut self, typ: &str, fields: serde_json::Map<String, serde_json::Value>) {
        if let Some(journal) = self.journal.as_mut()
            && let Err(e) = journal.event(typ, fields)
        {
            self.journal_ok = false;
            eprintln!("gen3: journal write failed: {e}");
        }
    }

    /// `remember`: append-only ingest. Returns one result per item; refusals are
    /// loud and journaled. No relations are created here (sweep's job).
    #[cfg(any(test, feature = "reference-models"))]
    pub fn remember_batch_reference(&mut self, items: &[RememberItem]) -> Vec<Result<u64, String>> {
        let mut results = Vec::with_capacity(items.len());
        // Semantic projection: embed all contents once (cache-aware).
        let vectors: Option<Vec<Vec<f32>>> = if self.projection.is_some() {
            let texts: Vec<String> = items.iter().map(|i| i.content.clone()).collect();
            match self.embed_cached(&texts) {
                Ok(v) => Some(v),
                Err(e) => {
                    let mut f = serde_json::Map::new();
                    f.insert("stage".into(), "remember".into());
                    f.insert("error".into(), e.clone().into());
                    self.j("projection.error", f);
                    return items.iter().map(|_| Err(e.clone())).collect();
                }
            }
        } else {
            None
        };
        let mut wrote = 0usize;
        for (idx, item) in items.iter().enumerate() {
            if self.budget > 0 && self.writes_used >= self.budget {
                let mut f = serde_json::Map::new();
                f.insert(
                    "reason".into(),
                    "write budget exceeded (fail-closed)".into(),
                );
                self.j("remember.refusal", f);
                results.push(Err("write budget exceeded".to_string()));
                continue;
            }
            if self.noise_enabled
                && let Some(class) = noise_class(&item.content)
            {
                let mut f = serde_json::Map::new();
                f.insert("reason".into(), "noise_class".into());
                f.insert("class".into(), class.into());
                f.insert(
                    "content_sha256".into(),
                    sha256_hex(item.content.as_bytes()).into(),
                );
                f.insert("source".into(), item.source.clone().into());
                self.j("remember.refusal", f);
                results.push(Err("noise_class".to_string()));
                continue;
            }
            let key = identity_key(&item.content, &item.source, kind_tag(item.kind));
            if let Some(&existing) = self.identity.get(&key) {
                let mut f = serde_json::Map::new();
                f.insert("reason".into(), "duplicate_exact".into());
                f.insert("content_sha256".into(), key.0.clone().into());
                f.insert("source".into(), item.source.clone().into());
                f.insert("existing_id".into(), existing.into());
                self.j("remember.refusal", f);
                results.push(Err("duplicate_exact".to_string()));
                continue;
            }
            let id = match item.kind {
                ImportKind::Reported => self.evidence.reported(&item.content, &item.source),
                ImportKind::System => self.evidence.system(&item.content, &item.source),
                ImportKind::Simulated => self.evidence.simulated(&item.content, &item.source),
            };
            let record = self.evidence.get(id).expect("record just created").clone();
            let terms = field::tokenize(&item.content);
            // Write vector first: failure leaves no orphaned record in store or identity map (#55a).
            if let Some(vs) = &vectors
                && let Some(v) = vs.get(idx)
                && let Err(e) = self.store.put_vector(id, v)
            {
                results.push(Err(format!("vector: {e}")));
                continue;
            }
            if let Err(e) = self.store.put_record_and_postings(&record, &terms) {
                results.push(Err(format!("persist: {e}")));
                continue;
            }
            self.identity.insert(key, id);
            self.writes_used += 1;
            wrote += 1;
            results.push(Ok(id));
        }
        let ids: Vec<u64> = results
            .iter()
            .filter_map(|r| r.as_ref().ok().copied())
            .collect();
        let mut f = serde_json::Map::new();
        f.insert("items".into(), items.len().into());
        f.insert("written".into(), wrote.into());
        f.insert(
            "ids_sha256".into(),
            sha256_hex(format!("{ids:?}").as_bytes()).into(),
        );
        self.j("ingest.batch", f);
        results
    }

    /// Production compatibility route. Every accepted item crosses the authorized LMDB
    /// transaction; without an installed local authority it fails closed.
    pub fn remember_batch(&mut self, items: &[RememberItem]) -> Vec<Result<u64, String>> {
        let Some(authority) = self.intake_authority.take() else {
            return items
                .iter()
                .map(|_| Err("intake authority is not installed".to_string()))
                .collect();
        };
        self.suppress_intake_journal = true;
        let result = (|| {
            let realm = self.intake_realm_id()?;
            let mut results = Vec::with_capacity(items.len());
            for (ordinal, item) in items.iter().enumerate() {
                let epoch = match self.intake_epoch() {
                    Ok(value) => value,
                    Err(error) => {
                        results.push(Err(error));
                        continue;
                    }
                };
                let mut operation = [0_u8; 16];
                if let Err(error) = getrandom::fill(&mut operation) {
                    results.push(Err(format!("operation id randomness: {error}")));
                    continue;
                }
                let request = IntakeRequest::new(
                    &authority,
                    crate::intake::OperationId::from_bytes(operation),
                    realm,
                    epoch,
                    ordinal as u64,
                    item.kind.into(),
                    item.content.clone(),
                    item.source.clone(),
                )
                .map_err(|error| error.to_string());
                results.push(match request {
                    Ok(request) => self
                        .remember_authorized(&authority, request)
                        .map(|outcome| outcome.receipt.record_id),
                    Err(error) => Err(error),
                });
            }
            Ok::<_, String>(results)
        })();
        self.suppress_intake_journal = false;
        self.intake_authority = Some(authority);
        match result {
            Ok(results) => {
                let ids: Vec<u64> = results
                    .iter()
                    .filter_map(|result| result.as_ref().ok().copied())
                    .collect();
                let mut fields = serde_json::Map::new();
                fields.insert("items".into(), items.len().into());
                fields.insert("written".into(), ids.len().into());
                fields.insert(
                    "ids_sha256".into(),
                    sha256_hex(format!("{ids:?}").as_bytes()).into(),
                );
                self.j("ingest.batch", fields);
                results
            }
            Err(error) => items.iter().map(|_| Err(error.clone())).collect(),
        }
    }

    /// Gate 9A Slice 1: authorize and atomically commit one non-World item.
    ///
    /// Receipt lookup happens before mutable process-local policy checks so an acknowledged
    /// commit can be retried after an epoch advance or process restart. A new operation retains
    /// the existing budget → noise → exact-duplicate gate order.
    pub fn remember_authorized(
        &mut self,
        channel: &crate::evidence::RatifiedChannel,
        request: IntakeRequest,
    ) -> Result<CommitOutcome, String> {
        request.authenticate(channel).map_err(|e| e.to_string())?;
        if let Some(receipt) = self
            .store
            .lookup_intake_receipt(&request)
            .map_err(|e| e.to_string())?
        {
            if self.evidence.get(receipt.record_id).is_none() {
                let record = self
                    .store
                    .get_record(receipt.record_id)
                    .map_err(|e| e.to_string())?
                    .ok_or_else(|| "receipt names a missing committed record".to_string())?;
                let replay_key = identity_key(
                    record.content(),
                    record.source(),
                    domain_tag(record.domain()),
                );
                self.evidence
                    .append(record)
                    .map_err(|e| format!("hydrate replayed intake: {e:?}"))?;
                self.identity.insert(replay_key, receipt.record_id);
            }
            return Ok(CommitOutcome {
                receipt,
                disposition: CommitDisposition::Replay,
            });
        }
        if self.budget > 0 && self.writes_used >= self.budget {
            let mut f = serde_json::Map::new();
            f.insert(
                "reason".into(),
                "write budget exceeded (fail-closed)".into(),
            );
            self.j("remember.refusal", f);
            return Err("write budget exceeded".to_string());
        }
        if self.noise_enabled
            && let Some(class) = noise_class(request.content())
        {
            let mut f = serde_json::Map::new();
            f.insert("reason".into(), "noise_class".into());
            f.insert("class".into(), class.into());
            f.insert(
                "content_sha256".into(),
                sha256_hex(request.content().as_bytes()).into(),
            );
            f.insert("source".into(), request.source().to_string().into());
            self.j("remember.refusal", f);
            return Err("noise_class".to_string());
        }
        let kind_tag = match request.kind() {
            IntakeKind::Reported => "reported",
            IntakeKind::System => "system",
            IntakeKind::Simulated => "simulated",
        };
        let key = identity_key(request.content(), request.source(), kind_tag);
        if let Some(&existing) = self.identity.get(&key) {
            let mut f = serde_json::Map::new();
            f.insert("reason".into(), "duplicate_exact".into());
            f.insert("content_sha256".into(), key.0.clone().into());
            f.insert("source".into(), request.source().to_string().into());
            f.insert("existing_id".into(), existing.into());
            self.j("remember.refusal", f);
            return Err("duplicate_exact".to_string());
        }

        let writes_after_commit = self
            .writes_used
            .checked_add(1)
            .ok_or_else(|| "process-local write counter exhausted".to_string())?;

        let terms = field::tokenize(request.content());
        let snapshot = self
            .store
            .authorization_snapshot()
            .map_err(|error| error.to_string())?;
        let capability =
            authorize_intake(channel, &request, &snapshot).map_err(|error| error.to_string())?;
        let outcome = match self.store.commit_intake(capability, &request, &terms) {
            Ok(outcome) => outcome,
            Err(crate::store::StoreError::Msg(reason)) if reason == "duplicate_exact" => {
                // Another writer may have committed after this process hydrated
                // its identity map. Preserve the public refusal vocabulary.
                let mut fields = serde_json::Map::new();
                fields.insert("reason".into(), "duplicate_exact".into());
                fields.insert("content_sha256".into(), key.0.clone().into());
                fields.insert("source".into(), key.1.clone().into());
                self.j("remember.refusal", fields);
                return Err("duplicate_exact".into());
            }
            Err(error) => return Err(error.to_string()),
        };
        if outcome.disposition == CommitDisposition::Committed {
            // The durable write consumes the process budget even if refreshing
            // the local view fails. A receipt retry must not charge it again.
            self.writes_used = writes_after_commit;
            let id = outcome.receipt.record_id;
            let record = self
                .store
                .get_record(id)
                .map_err(|e| e.to_string())?
                .ok_or_else(|| "committed intake record is missing".to_string())?;
            self.evidence
                .append(record)
                .map_err(|e| format!("hydrate committed intake: {e:?}"))?;
            self.identity.insert(key, id);

            if self.projection.is_some() {
                if let Ok(mut vectors) = self.embed_cached(&[request.content().to_string()]) {
                    if let Some(v) = vectors.pop() {
                        let _ = self.store.put_vector(id, &v);
                    }
                }
            }

            if !self.suppress_intake_journal {
                let mut f = serde_json::Map::new();
                f.insert("items".into(), 1.into());
                f.insert("written".into(), 1.into());
                f.insert(
                    "ids_sha256".into(),
                    sha256_hex(format!("[{id}]").as_bytes()).into(),
                );
                self.j("ingest.batch", f);
            }
        }
        Ok(outcome)
    }

    /// B5 recall-view membership: the record's provenance source parses to exactly this label.
    fn record_in_view(&self, id: u64, scope: &str) -> bool {
        self.store
            .get_record(id)
            .ok()
            .flatten()
            .is_some_and(|r| source_label(r.source()) == Some(scope))
    }

    pub fn recall(&mut self, q: &RecallQuery) -> Result<Vec<Hit>, RecallError> {
        validate_floors(q)?;
        validate_scope(q)?;
        let started = Instant::now();
        let tokens = field::tokenize(&q.query);
        let query_hash = sha256_hex(q.query.as_bytes());
        if tokens.is_empty() {
            let mut f = serde_json::Map::new();
            f.insert("query_sha256".into(), query_hash.into());
            f.insert("abstained".into(), true.into());
            f.insert("reason".into(), "no_query_tokens".into());
            if let Some(scope) = &q.scope {
                f.insert("scope".into(), scope.clone().into());
                f.insert("scope_considered".into(), 0usize.into());
            }
            self.j("selection.decision", f);
            return Ok(Vec::new());
        }
        let n = self.store.record_count().unwrap_or(0);
        let mut counts: HashMap<u64, usize> = HashMap::new();
        let mut lex_matched_idf: HashMap<u64, f32> = HashMap::new();

        // idf table (independent of the semantic pass; needed by the gate below).
        let idf_map: HashMap<&String, f32> = tokens
            .iter()
            .map(|t| {
                let df = self.store.df(t).unwrap_or(0) as f32;
                let idf = (1.0 + n as f32 / (1.0 + df)).ln();
                let weight = if self.dispersion_enabled {
                    idf * self.dispersion_weight(t)
                } else {
                    idf
                };
                (t, weight)
            })
            .collect();
        // Declared reduction order (W1_SCORER_DETERMINISM_REGISTRATION): sum over the query
        // tokens vector in token order (the order already used for matched), eliminating
        // per-process RandomState summation order divergence.
        let total_idf: f32 = tokens
            .iter()
            .map(|t| idf_map.get(t).copied().unwrap_or(0.0))
            .sum();

        for t in &tokens {
            let weight = idf_map.get(t).copied().unwrap_or(0.0);
            if let Ok(ids) = self.store.postings(t) {
                for id in ids {
                    *counts.entry(id).or_default() += 1;
                    *lex_matched_idf.entry(id).or_default() += weight;
                }
            }
        }

        // B5 recall-side scope view: the view is a population filter over the declared
        // provenance rule, applied before scoring/selection (registration §1). Absent scope →
        // no-op. Label-less and malformed-provenance records are never selected by a view.
        if let Some(scope) = &q.scope {
            counts.retain(|id, _| self.record_in_view(*id, scope));
            lex_matched_idf.retain(|id, _| counts.contains_key(id));
        }

        // State relations are needed by the activation diagnostics below and by
        // the structural selector later; compute them once, before the gate.
        let all_relations: Vec<Relation> = self.store.iter_relations().unwrap_or_default();
        let mut superseded_by: HashMap<u64, u64> = HashMap::new();
        let mut sources: HashSet<u64> = HashSet::new();
        let mut graph_edges: HashMap<u64, Vec<(u64, f32)>> = HashMap::new();

        for r in all_relations {
            if r.state() == RelationState::Cold {
                continue;
            }
            match r.kind() {
                field::RelationKind::Supersedes => {
                    superseded_by.insert(r.dst(), r.id());
                    sources.insert(r.src());
                }
                field::RelationKind::Associates => {
                    graph_edges
                        .entry(r.src())
                        .or_default()
                        .push((r.dst(), r.weight()));
                    graph_edges
                        .entry(r.dst())
                        .or_default()
                        .push((r.src(), r.weight()));
                }
                field::RelationKind::Causal => {
                    graph_edges
                        .entry(r.src())
                        .or_default()
                        .push((r.dst(), r.weight()));
                    graph_edges
                        .entry(r.dst())
                        .or_default()
                        .push((r.src(), r.weight() * 0.8));
                }
            }
        }

        // Activation policy. Floor mode (GEN3-GATED-S-001): fire when max
        // lexical support over lexical candidates is below the declared D2 floor
        // (0.01). Count mode (GEN3-GATED-S-003): fire when fewer than two
        // lexical candidates exist — the state-resolution sufficiency
        // heuristic (a single record cannot form an earlier/current state
        // comparison). With neither mode set, projection always runs (frozen).
        let mut run_projection = self.projection.is_some();
        if (self.projection_gated || self.projection_gate_count) && self.projection.is_some() {
            let mut lex_support_max = 0.0_f32;
            for &id in counts.keys() {
                let matched = lex_matched_idf.get(&id).copied().unwrap_or(0.0);
                let lex = if total_idf > f32::EPSILON {
                    (matched / total_idf).clamp(0.0, 1.0)
                } else {
                    0.0
                };
                if lex > lex_support_max {
                    lex_support_max = lex;
                }
            }
            let relation_involved = counts
                .keys()
                .filter(|id| sources.contains(id) || superseded_by.contains_key(id))
                .count();
            let fired = if self.projection_gate_count {
                counts.len() < 2
            } else {
                lex_support_max < self.policy.relevance_floor
            };
            let mut f = serde_json::Map::new();
            f.insert("query_sha256".into(), query_hash.clone().into());
            f.insert("lex_support_max".into(), lex_support_max.into());
            f.insert("gated".into(), true.into());
            f.insert("fired".into(), fired.into());
            f.insert("lexical_candidates".into(), counts.len().into());
            f.insert(
                "relation_involved_candidates".into(),
                relation_involved.into(),
            );
            self.j("projection.gate", f);
            run_projection = fired;
        }

        // Semantic projection candidates (brute-force cosine over cached vectors).
        // GEN3-GATED-S-002: `projection_pass_ms` times exactly this block — the
        // work the gate controls (measurement only; no behavior change).
        let mut semantic: HashMap<u64, f32> = HashMap::new();
        let mut projection_pass_ms = 0.0_f64;
        let mut projection_ran = false;
        let mut projection_error = false;
        if run_projection {
            let pass_started = Instant::now();
            match self.embed_cached(std::slice::from_ref(&q.query)) {
                Ok(mut v) => {
                    projection_ran = true;
                    let qv = v.pop().unwrap_or_default();
                    if !qv.is_empty() {
                        for (id, v) in self.store.iter_vectors().unwrap_or_default() {
                            let c = cosine(&qv, &v);
                            if c > TAU_GATE {
                                semantic.insert(id, semantic_support(c));
                            }
                        }
                    }
                }
                Err(e) => {
                    projection_error = true;
                    let mut f = serde_json::Map::new();
                    f.insert("stage".into(), "recall".into());
                    f.insert("error".into(), e.into());
                    self.j("projection.error", f);
                }
            }
            projection_pass_ms = pass_started.elapsed().as_secs_f64() * 1000.0;
        }
        if let Some(scope) = &q.scope {
            semantic.retain(|id, _| self.record_in_view(*id, scope));
        }
        if counts.is_empty() && semantic.is_empty() {
            let mut f = serde_json::Map::new();
            f.insert("query_sha256".into(), query_hash.into());
            f.insert("abstained".into(), true.into());
            f.insert("reason".into(), "insufficient_evidence".into());
            let cause = if q.scope.is_some() {
                "no_candidates_in_scope"
            } else {
                "no_candidates"
            };
            f.insert("cause".into(), cause.into());
            if let Some(scope) = &q.scope {
                f.insert("scope".into(), scope.clone().into());
                f.insert("scope_considered".into(), 0usize.into());
            }
            f.insert("projection_ran".into(), projection_ran.into());
            f.insert("projection_error".into(), projection_error.into());
            f.insert("projection_pass_ms".into(), projection_pass_ms.into());
            self.j("selection.decision", f);
            return Ok(Vec::new());
        }

        let mut candidate_ids: Vec<u64> = counts.keys().chain(semantic.keys()).copied().collect();
        if !graph_edges.is_empty() {
            let mut visited: HashSet<u64> = candidate_ids.iter().copied().collect();
            let mut frontier = candidate_ids.clone();
            // Bounded 2-hop graph expansion for multi-step execution traces (Call -> Output -> Synthesis)
            for _hop in 0..2 {
                let mut next_frontier = Vec::new();
                for id in frontier {
                    if let Some(neighbors) = graph_edges.get(&id) {
                        for (target_id, _) in neighbors {
                            if visited.insert(*target_id) {
                                next_frontier.push(*target_id);
                            }
                        }
                    }
                }
                if next_frontier.is_empty() {
                    break;
                }
                frontier = next_frontier;
            }
            candidate_ids = visited.into_iter().collect();
        }
        candidate_ids.sort_unstable();
        candidate_ids.dedup();
        let scope_considered = candidate_ids.len();

        let pool_cap = (q.candidate_limit.max(1) * 3).max(200);
        if candidate_ids.len() > pool_cap {
            candidate_ids.sort_by(|a, b| {
                let idf_b = lex_matched_idf.get(b).copied().unwrap_or(0.0);
                let idf_a = lex_matched_idf.get(a).copied().unwrap_or(0.0);
                idf_b
                    .partial_cmp(&idf_a)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| {
                        let count_b = counts.get(b).copied().unwrap_or(0);
                        let count_a = counts.get(a).copied().unwrap_or(0);
                        count_b.cmp(&count_a).then_with(|| b.cmp(a))
                    })
            });
            candidate_ids.truncate(pool_cap);
        }

        // 1. Gather base lexical and semantic support for all candidates
        let mut base_records: HashMap<u64, (f32, f32, f32, u64)> = HashMap::new(); // (lex, sem, base_support, created_at)
        for &id in &candidate_ids {
            let Some(record) = self.store.get_record(id).ok().flatten() else {
                continue;
            };
            let matched = lex_matched_idf.get(&id).copied().unwrap_or(0.0);
            let lex_support = if total_idf > f32::EPSILON {
                (matched / total_idf).clamp(0.0, 1.0)
            } else {
                0.0
            };
            let sem_support = semantic.get(&id).copied().unwrap_or(0.0);
            let support = lex_support.max(sem_support);
            base_records.insert(id, (lex_support, sem_support, support, record.created_at()));
        }

        // 2. Bounded graph activation propagation (diffusing support along typed edges)
        let mut final_support: HashMap<u64, f32> = base_records
            .iter()
            .map(|(&k, &(_, _, s, _))| (k, s))
            .collect();
        if !graph_edges.is_empty() {
            for _pass in 0..2 {
                let mut next_acts = final_support.clone();
                for (&src_id, neighbors) in &graph_edges {
                    if let Some(&src_act) = final_support.get(&src_id) {
                        if src_act > 0.0 {
                            for (dst_id, weight) in neighbors {
                                if let Some(&prev_act) = next_acts.get(dst_id) {
                                    let boost = src_act * weight * 0.5;
                                    let blended = prev_act + boost * (1.0 - prev_act);
                                    if blended > prev_act {
                                        next_acts.insert(*dst_id, blended.clamp(0.0, 1.0));
                                    }
                                }
                            }
                        }
                    }
                }
                final_support = next_acts;
            }
        }

        let mut scored: Vec<(f32, f32, f32, u64, Option<u64>, u8, f32, u64)> = Vec::new();
        for &id in &candidate_ids {
            let Some(&(lex_support, sem_support, _, created_at)) = base_records.get(&id) else {
                continue;
            };
            let support = final_support.get(&id).copied().unwrap_or(0.0);
            let is_seed = counts.contains_key(&id) || semantic.contains_key(&id);
            if !is_seed && support <= f32::EPSILON {
                continue;
            }
            if q.min_score > 0.0 && support < q.min_score {
                continue;
            }
            if q.min_coverage > 0.0 && support < q.min_coverage {
                continue;
            }
            let sup = superseded_by.get(&id).copied();
            let recency = if n > 0 {
                created_at as f32 / n as f32
            } else {
                0.0
            };
            let mut key = support * (1.0 + self.policy.recency_weight * recency);
            if sup.is_some() && !q.include_historical {
                key *= 1.0 - self.policy.supersede_penalty;
            }
            // Structural strata (P2D §4): 0 current · 1 unresolved · 2 superseded.
            let stratum: u8 = if q.include_historical {
                1
            } else if superseded_by.contains_key(&id) {
                2
            } else if sources.contains(&id) {
                0
            } else {
                1
            };
            scored.push((
                key,
                support,
                sem_support,
                id,
                sup,
                stratum,
                lex_support,
                created_at,
            ));
        }

        if scored.is_empty() {
            let mut f = serde_json::Map::new();
            f.insert("query_sha256".into(), query_hash.into());
            f.insert("abstained".into(), true.into());
            f.insert("reason".into(), "insufficient_evidence".into());
            f.insert("cause".into(), "no_results_above_floors".into());
            if let Some(scope) = &q.scope {
                f.insert("scope".into(), scope.clone().into());
                f.insert("scope_considered".into(), scope_considered.into());
            }
            f.insert("lexical_candidates".into(), counts.len().into());
            f.insert("semantic_candidates".into(), semantic.len().into());
            f.insert("min_score".into(), q.min_score.into());
            f.insert("min_coverage".into(), q.min_coverage.into());
            f.insert("projection_ran".into(), projection_ran.into());
            f.insert("projection_error".into(), projection_error.into());
            self.j("selection.decision", f);
            return Ok(Vec::new());
        }

        match self.arbitration {
            Arbitration::PenaltyMultiplier => scored.sort_by(|a, b| {
                b.0.partial_cmp(&a.0)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then(b.3.cmp(&a.3))
            }),
            Arbitration::Structural => scored.sort_by(|a, b| {
                a.5.cmp(&b.5)
                    .then(b.6.partial_cmp(&a.6).unwrap_or(std::cmp::Ordering::Equal))
                    .then(b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal))
                    .then(b.7.cmp(&a.7))
                    .then(b.3.cmp(&a.3))
            }),
        }
        let limit = if q.limit == 0 { 10 } else { q.limit };
        let candidate_limit = if q.candidate_limit == 0 {
            usize::MAX
        } else {
            q.candidate_limit
        };
        scored.truncate(limit.min(candidate_limit.max(1)));

        let mut hits = Vec::new();
        let mut selected_json = Vec::new();
        let mut applied_relations = Vec::new();
        for (rank, (key, support, sem, id, sup, stratum, _lex, _created)) in
            scored.into_iter().enumerate()
        {
            let record = self.store.get_record(id).ok().flatten();
            let content = record
                .as_ref()
                .map_or(String::new(), |r| r.content().to_string());
            let source = record
                .as_ref()
                .map_or(String::new(), |r| r.source().to_string());
            if let Some(rel_id) = sup
                && !q.include_historical
            {
                *self.usage.entry(rel_id).or_default() += 1;
                applied_relations.push(rel_id);
            }
            selected_json.push(serde_json::json!({
                "id": id,
                "rank": rank + 1,
                "rank_key": key,
                "score": support,
                "semantic_support": sem,
                "stratum": stratum,
                "superseded_by": sup,
            }));
            hits.push(Hit {
                id,
                content,
                source,
                score: support,
                rank: rank + 1,
                superseded_by: sup,
            });
        }

        // Hebbian Co-Activation tracking (neurons that fire together wire together)
        if hits.len() >= 2 {
            for i in 0..hits.len().min(5) {
                for j in (i + 1)..hits.len().min(5) {
                    let id_a = hits[i].id;
                    let id_b = hits[j].id;
                    let pair = if id_a < id_b {
                        (id_a, id_b)
                    } else {
                        (id_b, id_a)
                    };
                    *self.hebbian_coactivations.entry(pair).or_default() += 1;
                }
            }
        }

        for hit in &hits {
            let mut f = serde_json::Map::new();
            f.insert("result_id".into(), hit.id.into());
            f.insert("chain".into(), serde_json::json!([hit.source]));
            f.insert("complete".into(), true.into());
            self.j("provenance.chain", f);
        }

        let mut f = serde_json::Map::new();
        f.insert("query_sha256".into(), query_hash.into());
        f.insert("considered".into(), counts.len().into());
        f.insert("lexical_candidates".into(), counts.len().into());
        f.insert("semantic_candidates".into(), semantic.len().into());
        if let Some(scope) = &q.scope {
            f.insert("scope".into(), scope.clone().into());
            f.insert("scope_considered".into(), scope_considered.into());
        }
        f.insert(
            "arbitration".into(),
            format!("{:?}", self.arbitration).into(),
        );
        f.insert("dispersion".into(), self.dispersion_enabled.into());
        f.insert("selected".into(), serde_json::Value::Array(selected_json));
        f.insert("abstained".into(), hits.is_empty().into());
        f.insert(
            "relations_applied".into(),
            serde_json::json!(applied_relations),
        );
        f.insert("projection_ran".into(), projection_ran.into());
        f.insert("projection_error".into(), projection_error.into());
        f.insert("projection_pass_ms".into(), projection_pass_ms.into());
        f.insert(
            "took_ms".into(),
            (started.elapsed().as_millis() as u64).into(),
        );
        self.j("selection.decision", f);
        Ok(hits)
    }

    /// Test/demo convenience: panics on a caller error. Use [`Substrate::recall`] for
    /// structured handling (the fail-closed floor/scope validation is the point).
    #[cfg(test)]
    #[track_caller]
    pub fn recall_expect(&mut self, q: &RecallQuery) -> Vec<Hit> {
        self.recall(q).expect("recall: valid floors and scope")
    }

    /// `think`: bounded sweep — proposes `supersedes` candidates by the declared
    /// generic rule, then evaluates statutory promotion/demotion. Planning runs
    /// over one coherent, bounded read snapshot (ratified profile v1) and commits
    /// atomically through the compiler-authorized v5 path. Disabled sweeps are
    /// typed no-ops with no allocation.
    ///
    /// A1 ablation: disabled via [`Substrate::set_sweep_enabled`].
    pub fn think_sweep(&mut self) -> SweepStats {
        let started = Instant::now();
        if !self.sweep_enabled {
            let (sweep, error) = match self.store.peek_sweep_counter() {
                Ok(value) => (value, None),
                Err(e) => (0, Some(e.to_string())),
            };
            let stats = SweepStats {
                sweep,
                error,
                disabled: true,
                ..SweepStats::default()
            };
            self.journal_sweep(&stats, true);
            return stats;
        }
        let mut stats = match self.plan_and_commit_sweep() {
            Ok(stats) => stats,
            Err((message, base)) => {
                let mut stats = base;
                stats.error = Some(message);
                stats.refused = true;
                stats
            }
        };
        stats.took_ms = started.elapsed().as_millis() as u64;
        self.journal_sweep(&stats, false);
        stats
    }

    fn plan_and_commit_sweep(&mut self) -> Result<SweepStats, (String, SweepStats)> {
        let fail = |message: String| (message, SweepStats::default());
        let issuer_label = match self.intake_authority.as_ref() {
            Some(channel) if !channel.name().is_empty() => channel.name().to_string(),
            _ => return Err(fail("sweep authority is not installed".into())),
        };
        let mut operation_id_bytes = [0u8; 16];
        getrandom::fill(&mut operation_id_bytes)
            .map_err(|e| fail(format!("sweep operation id randomness failed: {e}")))?;
        let operation_id = OperationId::from_bytes(operation_id_bytes);
        let limits = SWEEP_PROFILE_V1;

        let preflight_started = Instant::now();
        let preflight = self
            .store
            .sweep_preflight(limits)
            .map_err(|e| fail(e.to_string()))?;
        let index_ms = preflight_started.elapsed().as_millis() as u64;

        let uses: BTreeMap<u64, u64> = self
            .usage
            .iter()
            .map(|(id, count)| (*id, u64::from(*count)))
            .collect();
        let usage = self
            .usage_issuer
            .snapshot(&uses)
            .map_err(|e| fail(e.to_string()))?;

        let pair_started = Instant::now();
        let (request, report) = plan_sweep(
            &preflight,
            SweepPlanInputs {
                operation_id,
                issuer_label: &issuer_label,
                limits,
                rare_df_divisor: u64::try_from(self.policy.rare_df_divisor).unwrap_or(u64::MAX),
                rare_df_floor: u64::try_from(self.policy.rare_df_floor).unwrap_or(u64::MAX),
                lifecycle_age_sweeps: LIFECYCLE_AGE_SWEEPS,
                usage,
            },
        )
        .map_err(|e| fail(e.to_string()))?;
        let pair_ms = pair_started.elapsed().as_millis() as u64;

        let snapshot = self
            .store
            .authorization_snapshot()
            .map_err(|e| fail(e.to_string()))?;
        let capability = {
            let channel = self
                .intake_authority
                .as_ref()
                .ok_or_else(|| fail("sweep authority is not installed".into()))?;
            authorize_sweep(channel, &request, &snapshot).map_err(|e| fail(e.to_string()))?
        };
        let outcome = self
            .store
            .commit_sweep(capability, &request)
            .map_err(|e| fail(e.to_string()))?;
        let receipt = outcome.receipt;
        let rare_max = ((preflight.records.len() / self.policy.rare_df_divisor.max(1))
            .max(self.policy.rare_df_floor)) as usize;
        Ok(SweepStats {
            sweep: receipt.sweep_id,
            pairs_lexical_candidates: report.pairs_lexical_candidates as usize,
            pairs_pruned_by_projection: report.pairs_pruned_by_projection as usize,
            pairs_considered: report.pairs_considered as usize,
            pairs_skipped_existing: report.pairs_skipped_existing as usize,
            pairs_rejected_rule: report.pairs_rejected_rule as usize,
            pairs_examined: report.pairs_examined as usize,
            proposals: report.proposals as usize,
            promotions: report.promotions as usize,
            demotions: report.demotions as usize,
            rare_max_df: rare_max,
            index_ms,
            pair_ms,
            promotion_ms: 0,
            took_ms: 0,
            disabled: false,
            operation_id: Some(operation_id),
            error: None,
            refused: false,
            replayed: outcome.disposition == CommitDisposition::Replay,
        })
    }

    /// Authenticated replay of a committed sweep by operation id. Retrieves the
    /// original persisted plan, requires fresh local authority bound to the stored
    /// manifest digest, and never re-plans or re-scans.
    pub fn sweep_replay(&mut self, operation_id: OperationId) -> Result<SweepOutcome, String> {
        let receipt = self
            .store
            .lookup_sweep_receipt(operation_id)
            .map_err(|e| e.to_string())?
            .ok_or_else(|| "no committed sweep receipt for that operation id".to_string())?;
        let snapshot = self
            .store
            .authorization_snapshot()
            .map_err(|e| e.to_string())?;
        let capability = {
            let channel = self
                .intake_authority
                .as_ref()
                .ok_or_else(|| "sweep authority is not installed".to_string())?;
            authorize_sweep_replay(
                channel,
                receipt.manifest_digest,
                operation_id,
                receipt.realm_id,
                &snapshot,
            )
            .map_err(|e| e.to_string())?
        };
        let outcome = self
            .store
            .replay_sweep(capability, operation_id)
            .map_err(|e| e.to_string())?;
        let mut fields = serde_json::Map::new();
        fields.insert(
            "operation_id".into(),
            format!("{:02x?}", operation_id.as_bytes()).into(),
        );
        fields.insert("sweep".into(), outcome.receipt.sweep_id.into());
        fields.insert("replayed".into(), true.into());
        self.j("sweep.replay", fields);
        Ok(outcome)
    }

    fn journal_sweep(&mut self, stats: &SweepStats, disabled: bool) {
        let mut f = serde_json::Map::new();
        f.insert("sweep".into(), stats.sweep.into());
        f.insert("disabled".into(), disabled.into());
        f.insert(
            "pairs_lexical_candidates".into(),
            stats.pairs_lexical_candidates.into(),
        );
        f.insert(
            "pairs_pruned_by_projection".into(),
            stats.pairs_pruned_by_projection.into(),
        );
        f.insert("pairs_considered".into(), stats.pairs_considered.into());
        f.insert(
            "pairs_skipped_existing".into(),
            stats.pairs_skipped_existing.into(),
        );
        f.insert(
            "pairs_rejected_rule".into(),
            stats.pairs_rejected_rule.into(),
        );
        f.insert("pairs_examined".into(), stats.pairs_examined.into());
        f.insert("proposals".into(), stats.proposals.into());
        f.insert("promotions".into(), stats.promotions.into());
        f.insert("demotions".into(), stats.demotions.into());
        f.insert("rare_max_df".into(), stats.rare_max_df.into());
        f.insert("index_ms".into(), stats.index_ms.into());
        f.insert("pair_ms".into(), stats.pair_ms.into());
        f.insert("promotion_ms".into(), stats.promotion_ms.into());
        f.insert("policy".into(), self.policy.to_json());
        f.insert("took_ms".into(), stats.took_ms.into());
        f.insert(
            "operation_id".into(),
            match &stats.operation_id {
                Some(id) => format!("{:02x?}", id.as_bytes()).into(),
                None => serde_json::Value::Null,
            },
        );
        f.insert("refused".into(), stats.refused.into());
        f.insert("replayed".into(), stats.replayed.into());
        if let Some(error) = &stats.error {
            f.insert("error".into(), error.clone().into());
        }
        self.j("think.sweep", f);
    }

    /// Closure canary: a simulated record must refuse every re-label attempt.
    pub fn canary_probe(&mut self) -> bool {
        // A model-only probe: canonical record creation is reserved for authorized intake.
        let mut probe_store = EvidenceStore::new();
        let id = probe_store.simulated("canary: simulated hypothesis h0", "canary");
        let record = probe_store.get(id).expect("canary record").clone();
        let relabel = probe_store.append(record.clone());
        let refused = matches!(relabel, Err(Refusal::DuplicateId));
        if !refused {
            self.violations += 1;
        }
        let mut domains = Vec::new();
        domains.push(format!("{:?}", record.domain()));
        let mut f = serde_json::Map::new();
        f.insert("probe_id".into(), format!("canary-{id}").into());
        f.insert("kind".into(), "laundering".into());
        f.insert("probe_storage".into(), "reference-model".into());
        f.insert("canonical_write".into(), false.into());
        f.insert("planted_id".into(), id.into());
        f.insert("attempts".into(), 1.into());
        f.insert("observed_domains".into(), serde_json::json!(domains));
        f.insert(
            "outcome".into(),
            if refused { "refused" } else { "VIOLATION" }.into(),
        );
        self.j("canary.probe", f);
        if refused {
            // Healthy expected behavior: a boundary refusal, NOT a violation.
            let mut r = serde_json::Map::new();
            r.insert("boundary".into(), "closure-evidence".into());
            r.insert("mechanism".into(), "relabel".into());
            r.insert("refused_by".into(), "append-duplicate-id".into());
            r.insert("probe_id".into(), format!("canary-{id}").into());
            self.j("boundary.refusal", r);
        } else {
            // Invariant actually crossed — H6 counts only these.
            let mut v = serde_json::Map::new();
            v.insert("boundary".into(), "closure-evidence".into());
            v.insert("mechanism".into(), "relabel".into());
            v.insert("probe_id".into(), format!("canary-{id}").into());
            self.j("closure.violation", v);
        }
        refused
    }

    /// End-of-run event: counts + journal status. Hash of the journal file is
    /// computed by the host after this returns (see `journal::sha256_file`).
    pub fn finish(&mut self) {
        let records = self.store.record_count().unwrap_or(0);
        let relations = self.store.iter_relations().map(|v| v.len()).unwrap_or(0);
        let seq = self.journal.as_ref().map_or(0, |j| j.seq());
        let mut f = serde_json::Map::new();
        f.insert("records".into(), records.into());
        f.insert("relations".into(), relations.into());
        f.insert("violations".into(), self.violations.into());
        f.insert("journal_ok".into(), self.journal_ok.into());
        f.insert("events_before_end".into(), seq.into());
        f.insert("sweep_enabled".into(), self.sweep_enabled.into());
        f.insert(
            "arbitration".into(),
            format!("{:?}", self.arbitration).into(),
        );
        f.insert("dispersion".into(), self.dispersion_enabled.into());
        f.insert(
            "rules".into(),
            "candidacy.v1.shared-rare+value-diff+temporal".into(),
        );
        f.insert(
            "projection".into(),
            serde_json::json!({
                "enabled": self.projection.is_some(),
                "gated": self.projection_gated,
                "gate_count": self.projection_gate_count,
                "model": MODEL_ID,
                "dim": DIM,
                "tau_gate": TAU_GATE,
                "stats": self.projection_stats().map(|s| serde_json::json!({
                    "model_load_ms": s.model_load_ms,
                    "embed_calls": s.embed_calls,
                    "embed_texts": s.embed_texts,
                    "embed_ms": s.embed_ms,
                })),
            }),
        );
        self.j("run.end", f);
    }

    /// `inspect`: tier map, counts, relations, journal status. Never certifies
    /// more than the journal contains.
    #[must_use]
    pub fn inspect(&self, scope: &str) -> serde_json::Value {
        let relations: Vec<serde_json::Value> = self
            .store
            .iter_relations()
            .unwrap_or_default()
            .into_iter()
            .map(|r| {
                serde_json::json!({
                    "id": r.id(),
                    "kind": format!("{:?}", r.kind()),
                    "src": r.src(),
                    "dst": r.dst(),
                    "state": format!("{:?}", r.state()),
                    "confidence": r.confidence(),
                    "rule_id": r.rule_id(),
                    "created_sweep": r.created_sweep(),
                    "w": r.weight(), "s": r.sign(), "c": r.cost(), "t": r.trust(),
                })
            })
            .collect();
        let tiers = serde_json::json!({
            "tier1_constitution": {
                "writers": "external admin only",
                "readers": "ConstitutionView (immutable, typed)",
                "invariants": INVARIANTS,
                "version": self.view.version(),
                "invariant_hash": self.view.invariant_hash(),
            },
            "tier2_statutes": {
                "budget_writes_per_min": self.budget,
                "policy": self.policy.to_json(),
            },
            "tier3_adaptive": {
                "records": self.store.record_count().unwrap_or(0),
                "relations": relations.len(),
            },
        });
        match scope {
            "tiers" => tiers,
            "relations" => serde_json::json!({ "relations": relations }),
            "journal" => serde_json::json!({
                "configured": self.journal.is_some(),
                "ok": self.journal_ok,
                "violations": self.violations,
            }),
            "apotheosis" => {
                let vault = crate::bicameral::GeneseedVault::new();
                let report = crate::apotheosis::perform_apotheosis_audit(self, &vault, 0);
                serde_json::to_value(report).unwrap_or(serde_json::Value::Null)
            }
            _ => serde_json::json!({
                "tiers": tiers,
                "relations": relations,
                "journal": { "configured": self.journal.is_some(), "ok": self.journal_ok, "violations": self.violations },
                "projection": {
                    "enabled": self.projection.is_some(),
                    "gated": self.projection_gated,
                    "gate_count": self.projection_gate_count,
                    "model": MODEL_ID,
                    "tau_gate": TAU_GATE,
                    "stats": self.projection_stats().map(|s| serde_json::json!({
                        "model_load_ms": s.model_load_ms,
                        "embed_calls": s.embed_calls,
                        "embed_texts": s.embed_texts,
                        "embed_ms": s.embed_ms,
                    })),
                },
                "arbitration": format!("{:?}", self.arbitration),
                "dispersion": self.dispersion_enabled,
                "apotheosis_status": format!("{:?}", crate::apotheosis::perform_apotheosis_audit(self, &crate::bicameral::GeneseedVault::new(), 0).status),
            }),
        }
    }

    /// Return active Hebbian co-activations recorded in volatile memory.
    #[must_use]
    pub fn hebbian_coactivations(&self) -> &HashMap<(u64, u64), u32> {
        &self.hebbian_coactivations
    }

    /// Authorized relation commitment (Associates, Causal, or Supersedes).
    #[cfg(any(test, feature = "operator", feature = "reference-models"))]
    pub fn add_relation(
        &mut self,
        kind: field::RelationKind,
        src: u64,
        dst: u64,
        weight: f32,
    ) -> Result<u64, String> {
        let _ = self
            .intake_authority
            .as_ref()
            .ok_or_else(|| "intake authority is not installed".to_string())?;
        let id = self.store.alloc_relation_id().map_err(|e| e.to_string())?;
        let sweep = self.store.peek_sweep_counter().unwrap_or(0);
        let relation = match kind {
            field::RelationKind::Supersedes => field::Relation::new(id, src, dst, weight, sweep),
            field::RelationKind::Associates => {
                field::Relation::associate(id, src, dst, weight, sweep)
            }
            field::RelationKind::Causal => field::Relation::causal(id, src, dst, weight, sweep),
        };
        self.store
            .put_relation(&relation)
            .map_err(|e| e.to_string())?;
        Ok(id)
    }

    // ========================================================================
    // Session Continuity & Compounding Handoff Engine (Luna / Gen3 Core)
    // ========================================================================

    /// Record a structured compounding session checkpoint into the Substrate.
    ///
    /// The checkpoint is structured into canonical JSON, signed via `CommitCapability`,
    /// committed to the store, and given a canonical source tag `session:<session_id>:<checkpoint_type>`.
    pub fn session_checkpoint(&mut self, checkpoint: &SessionCheckpoint) -> Result<u64, String> {
        let source = format!(
            "session:{}:{}",
            checkpoint.session_id, checkpoint.checkpoint_type
        );
        let content = serde_json::to_string(checkpoint).map_err(|e| e.to_string())?;

        let item = RememberItem {
            content,
            source,
            kind: ImportKind::Reported,
        };

        let results = self.remember_batch(&[item]);
        results
            .into_iter()
            .next()
            .ok_or_else(|| "no outcome from remember_batch".to_string())?
    }

    /// Record an arbitrary session log or memory item.
    pub fn session_record(
        &mut self,
        session_id: &str,
        agent_id: &str,
        log_type: &str,
        content: &str,
    ) -> Result<u64, String> {
        let source = format!("session:{}:{}:{}", session_id, agent_id, log_type);
        let item = RememberItem {
            content: content.to_string(),
            source,
            kind: ImportKind::Reported,
        };
        let results = self.remember_batch(&[item]);
        results
            .into_iter()
            .next()
            .ok_or_else(|| "no outcome from remember_batch".to_string())?
    }

    /// Retrieve the latest compounding continuity view for a given session (or overall latest if None).
    pub fn session_continuity(
        &self,
        session_id: Option<&str>,
    ) -> Result<Option<SessionContinuityView>, String> {
        let prefix = match session_id {
            Some(id) => format!("session:{}:", id),
            None => "session:".to_string(),
        };

        let n = self.store.record_count().unwrap_or(0);
        let epoch = self.store.epoch().unwrap_or(0);
        let scan_depth = 5000usize.min(n);

        // Find the record with the largest ID that matches the prefix by scanning backwards
        let mut best: Option<crate::evidence::EvidenceRecord> = None;
        for id in (n.saturating_sub(scan_depth)..=n).rev() {
            if let Ok(Some(record)) = self.store.get_record(id as u64) {
                if record.source().starts_with(&prefix) {
                    best = Some(record);
                    break;
                }
            }
        }

        let Some(record) = best else {
            return Ok(None);
        };

        // Try to parse structured checkpoint
        if let Ok(cp) = serde_json::from_str::<SessionCheckpoint>(record.content()) {
            return Ok(Some(SessionContinuityView {
                record_id: record.id(),
                epoch,
                session_id: cp.session_id,
                agent_id: cp.agent_id,
                checkpoint_type: cp.checkpoint_type,
                summary: cp.summary,
                next_queue: cp.next_queue,
                open_flags: cp.open_flags,
                context_token: cp.context_token,
                representation: cp.representation,
                timestamp_iso: cp.timestamp_iso,
                raw_content: record.content().to_string(),
            }));
        }

        // Fallback for unstructured session records
        let parts: Vec<&str> = record.source().split(':').collect();
        let s_id = parts.get(1).copied().unwrap_or("unknown").to_string();
        let a_id = parts.get(2).copied().unwrap_or("agent").to_string();
        let cp_type = parts.get(3).copied().unwrap_or("log").to_string();

        Ok(Some(SessionContinuityView {
            record_id: record.id(),
            epoch,
            session_id: s_id,
            agent_id: a_id,
            checkpoint_type: cp_type,
            summary: record.content().to_string(),
            next_queue: Vec::new(),
            open_flags: Vec::new(),
            context_token: None,
            representation: None,
            timestamp_iso: None,
            raw_content: record.content().to_string(),
        }))
    }

    /// List all unique session IDs recorded in the substrate.
    pub fn session_list(&self) -> Result<Vec<String>, String> {
        let mut sessions = std::collections::BTreeSet::new();
        for record in self
            .store
            .iter_records()
            .map_err(|e| format!("session list scan: {e}"))?
        {
            if record.source().starts_with("session:") {
                let parts: Vec<&str> = record.source().split(':').collect();
                if let Some(id_part) = parts.get(1) {
                    if !id_part.is_empty() {
                        sessions.insert((*id_part).to_string());
                    }
                }
            }
        }

        Ok(sessions.into_iter().collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::constitution::default_view;

    fn temp_store(tag: &str) -> std::path::PathBuf {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        std::env::temp_dir().join(format!("wm-gen3-{tag}-{}-{nanos}", std::process::id()))
    }

    fn substrate(tag: &str) -> Substrate {
        Substrate::open(&temp_store(tag), None, default_view()).expect("open substrate")
    }

    fn item(text: &str) -> RememberItem {
        RememberItem {
            content: text.into(),
            source: "test".into(),
            kind: ImportKind::Reported,
        }
    }

    fn q(text: &str) -> RecallQuery {
        RecallQuery {
            query: text.into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        }
    }

    #[test]
    fn test_bijective_uuid_mapping_and_persistence() {
        let store_dir = temp_store("uuid-map");
        let legacy_uuid = Uuid::new_v4();
        let record_id: u64 = 42;

        {
            let mut s = Substrate::open(&store_dir, None, default_view()).expect("open");
            assert_eq!(s.lookup_id_by_uuid(&legacy_uuid), None);
            assert_eq!(s.lookup_uuid_by_id(record_id), None);

            s.bind_uuid(legacy_uuid, record_id);
            assert_eq!(s.lookup_id_by_uuid(&legacy_uuid), Some(record_id));
            assert_eq!(s.lookup_uuid_by_id(record_id), Some(legacy_uuid));

            // Test get_or_create_uuid for another ID
            let other_id = 999;
            let derived_uuid = s.get_or_create_uuid(other_id);
            assert_eq!(s.lookup_id_by_uuid(&derived_uuid), Some(other_id));
            assert_eq!(s.lookup_uuid_by_id(other_id), Some(derived_uuid));
        }

        // Reopen Substrate to ensure persistent reload from uuid_index.jsonl
        {
            let s = Substrate::open(&store_dir, None, default_view()).expect("reopen");
            assert_eq!(s.lookup_id_by_uuid(&legacy_uuid), Some(record_id));
            assert_eq!(s.lookup_uuid_by_id(record_id), Some(legacy_uuid));
            let derived = Uuid::new_v5(&Uuid::NAMESPACE_OID, &999u64.to_be_bytes());
            assert_eq!(s.lookup_id_by_uuid(&derived), Some(999));
            assert_eq!(s.lookup_uuid_by_id(999), Some(derived));
        }
    }

    /// D2 property 1: no meaningful overlap → abstention (empty selection).
    #[test]
    fn d2_zero_overlap_abstains() {
        let mut s = substrate("d2a");
        s.remember_batch(&[item("coffee brewing notes")]);
        assert!(s.recall_expect(&q("quantum chromodynamics")).is_empty());
    }

    /// D2 property 2: complete query-term support → 1.0.
    #[test]
    fn d2_full_support_scores_one() {
        let mut s = substrate("d2b");
        s.remember_batch(&[item("alpha beta gamma")]);
        let hits = s.recall_expect(&q("alpha beta"));
        assert_eq!(hits.len(), 1);
        assert!(
            (hits[0].score - 1.0).abs() < 1e-6,
            "score {}",
            hits[0].score
        );
    }

    /// D2 property 3: irrelevant terms added to a record cannot improve support.
    #[test]
    fn d2_irrelevant_terms_do_not_improve() {
        let mut s = substrate("d2c");
        s.remember_batch(&[item("alpha beta"), item("alpha beta zeta omega kappa")]);
        let hits = s.recall_expect(&q("alpha"));
        assert_eq!(hits.len(), 2);
        assert!(
            (hits[0].score - hits[1].score).abs() < 1e-6,
            "unexpected spread: {:?}",
            hits.iter().map(|h| h.score).collect::<Vec<_>>()
        );
    }

    /// D2 property 4: query token order is irrelevant.
    #[test]
    fn d2_token_order_irrelevant() {
        let mut s = substrate("d2d");
        s.remember_batch(&[item("alpha beta")]);
        let a = s.recall_expect(&q("alpha beta"));
        let b = s.recall_expect(&q("beta alpha"));
        assert_eq!(a.len(), b.len());
        assert_eq!(a[0].id, b[0].id);
        assert!((a[0].score - b[0].score).abs() < 1e-6);
    }

    /// D2 property 5: same corpus → identical scores and ordering.
    #[test]
    fn d2_deterministic() {
        let mut s = substrate("d2e");
        s.remember_batch(&[item("the quick brown fox"), item("lazy dog sleeps")]);
        let a = s.recall_expect(&q("quick fox"));
        let b = s.recall_expect(&q("quick fox"));
        assert_eq!(
            a.iter().map(|h| (h.id, h.rank)).collect::<Vec<_>>(),
            b.iter().map(|h| (h.id, h.rank)).collect::<Vec<_>>()
        );
        assert_eq!(
            a.iter().map(|h| h.score).collect::<Vec<_>>(),
            b.iter().map(|h| h.score).collect::<Vec<_>>()
        );
    }

    #[test]
    fn duplicate_exact_refused_and_journaled_across_processes() {
        let path = temp_store("dup-gate");
        let journal_path = path.with_extension("journal.jsonl");
        {
            let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
            let first = s.remember_batch(&[item("same bytes")]);
            assert!(first[0].is_ok(), "{first:?}");
            let second = s.remember_batch(&[item("same bytes")]);
            assert_eq!(
                second[0].as_ref().err().map(String::as_str),
                Some("duplicate_exact")
            );
            assert_eq!(s.store().record_count().expect("count"), 1);
        }
        {
            let mut s =
                Substrate::open(&path, Some(&journal_path), default_view()).expect("reopen");
            let third = s.remember_batch(&[item("same bytes")]);
            assert_eq!(
                third[0].as_ref().err().map(String::as_str),
                Some("duplicate_exact")
            );
            assert_eq!(s.store().record_count().expect("count"), 1);
        }
        let text = std::fs::read_to_string(&journal_path).expect("journal readable");
        assert!(
            text.lines()
                .any(|l| l.contains("\"remember.refusal\"") && l.contains("\"duplicate_exact\"")),
            "journal must carry the duplicate refusal: {text}"
        );
    }

    #[test]
    fn duplicate_gate_is_provenance_scoped() {
        let mut s = substrate("dup-scope");
        let a = RememberItem {
            content: "same bytes".into(),
            source: "alpha".into(),
            kind: ImportKind::Reported,
        };
        let b = RememberItem {
            content: "same bytes".into(),
            source: "beta".into(),
            kind: ImportKind::Reported,
        };
        let c = RememberItem {
            content: "same bytes".into(),
            source: "alpha".into(),
            kind: ImportKind::Simulated,
        };
        let r = s.remember_batch(&[a, b, c]);
        assert!(r.iter().all(Result::is_ok), "{r:?}");
        assert_eq!(s.store().record_count().expect("count"), 3);
    }

    // ---- B5 recall-side scope view (registration W1_B5_RECALL_VIEW_REGISTRATION) ----

    fn item_src(text: &str, source: &str) -> RememberItem {
        RememberItem {
            content: text.into(),
            source: source.into(),
            kind: ImportKind::Reported,
        }
    }

    fn scoped_q(text: &str, scope: &str) -> RecallQuery {
        let mut query = q(text);
        query.scope = Some(scope.into());
        query
    }

    /// §3.6 / §5.11: the label grammar is fail-closed; caller errors precede selection.
    #[test]
    fn scope_grammar_is_fail_closed() {
        let path = temp_store("b5-grammar");
        let journal = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal), default_view()).expect("open");
        s.remember_batch(&[item("alpha token")]);
        for bad in ["", "a:b"] {
            let err = s.recall(&scoped_q("alpha", bad)).expect_err("refused");
            assert!(matches!(err, RecallError::InvalidScope { .. }), "{err:?}");
        }
        let text = std::fs::read_to_string(&journal).unwrap_or_default();
        assert!(!text.contains("selection.decision"), "{text}");
    }

    /// §3.2 / §5.5: a view selects exactly the label's records; label-less and malformed
    /// provenance never leak into a view; unscoped recall is unchanged.
    #[test]
    fn scope_view_selects_only_label_records() {
        let mut s = substrate("b5-view");
        s.remember_batch(&[
            item_src("shared token label one", "corpus:L1:t"),
            item_src("shared token label two", "corpus:L2:t"),
            item_src("shared token label-less", "plain-source"),
            item_src("shared token empty label", "corpus::t"),
            item_src("shared token malformed", "corpus:L1"),
        ]);
        let hits = s.recall_expect(&scoped_q("shared token", "L1"));
        assert_eq!(hits.len(), 1, "{hits:?}");
        assert_eq!(hits[0].source, "corpus:L1:t");
        let all = s.recall_expect(&q("shared token"));
        assert_eq!(all.len(), 5, "{all:?}");
    }

    /// §3.4 / acceptance 4: filter-before-selection — out-of-scope records that outrank the
    /// in-view record cannot crowd it out of a small candidate_limit.
    #[test]
    fn scope_view_cannot_crowd_out() {
        let mut s = substrate("b5-crowd");
        s.remember_batch(&[
            item_src("alpha zephyr", "corpus:L:t"),
            item_src("alpha beta gamma", "corpus:other:t1"),
            item_src("alpha beta gamma", "corpus:other:t2"),
            item_src("alpha beta gamma", "corpus:other:t3"),
        ]);
        let mut query = scoped_q("alpha beta gamma", "L");
        query.candidate_limit = 1;
        let hits = s.recall_expect(&query);
        assert_eq!(hits.len(), 1, "{hits:?}");
        assert_eq!(hits[0].source, "corpus:L:t");
    }

    /// §1 clause 3 / acceptance 5: an empty view is disclosed with the pinned vocabulary.
    #[test]
    fn scope_empty_view_is_disclosed() {
        let path = temp_store("b5-empty");
        let journal = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal), default_view()).expect("open");
        s.remember_batch(&[item_src("shared token", "corpus:L1:t")]);
        let hits = s.recall_expect(&scoped_q("shared token", "L2_missing"));
        assert!(hits.is_empty());
        let event = last_selection(&journal);
        assert_eq!(event["abstained"], true);
        assert_eq!(event["reason"], "insufficient_evidence");
        assert_eq!(event["cause"], "no_candidates_in_scope");
        assert_eq!(event["scope"], "L2_missing");
        assert_eq!(event["scope_considered"].as_u64(), Some(0));
    }

    /// §1 clause 1 / acceptance 3: the view is a filter, not a scorer — within-view order
    /// equals unscoped order restricted to the view.
    #[test]
    fn scope_is_a_view_not_a_scorer() {
        let mut s = substrate("b5-order");
        s.remember_batch(&[
            item_src("shared alpha", "corpus:L:t"),
            item_src("shared alpha beta", "corpus:L:t2"),
            item_src("shared alpha beta gamma", "corpus:other:t"),
        ]);
        let all = s.recall_expect(&q("shared alpha beta gamma"));
        let scoped = s.recall_expect(&scoped_q("shared alpha beta gamma", "L"));
        let restricted: Vec<u64> = all
            .iter()
            .filter(|h| h.source.starts_with("corpus:L:"))
            .map(|h| h.id)
            .collect();
        let scoped_ids: Vec<u64> = scoped.iter().map(|h| h.id).collect();
        assert_eq!(restricted, scoped_ids, "{restricted:?} vs {scoped_ids:?}");
    }

    /// Journal shape: scope fields appear only when a scope is present.
    #[test]
    fn scope_absent_journal_has_no_scope_fields() {
        let path = temp_store("b5-default");
        let journal = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal), default_view()).expect("open");
        s.remember_batch(&[item("alpha token")]);
        let _ = s.recall_expect(&q("alpha"));
        let event = last_selection(&journal);
        assert!(event.get("scope").is_none(), "{event}");
        assert!(event.get("scope_considered").is_none(), "{event}");
    }

    /// A1 rev 2 §5.7: each declared noise class is refused with the class named; controls admitted.
    #[test]
    fn noise_classes_refused_with_journal_and_no_write() {
        let path = temp_store("noise-classes");
        let journal_path = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
        let cases = [
            (
                "Traceback (most recent call last):\n  File \"x.py\", line 1\nError: boom",
                "traceback",
            ),
            ("first line is fine\nError: something failed", "error_line"),
            ("{\"json\": {\"a\": 1}}", "json_blob"),
            ("<function foo at 0x7f00>", "function_repr"),
            ("tiny", "too_short"),
        ];
        let mut items: Vec<RememberItem> = cases.iter().map(|(c, _)| item(c)).collect();
        items.push(item("a perfectly ordinary memory record"));
        items.push(item("the Error: prefix convention is documented"));
        let r = s.remember_batch(&items);
        for (i, (_, class)) in cases.iter().enumerate() {
            assert_eq!(
                r[i].as_ref().err().map(String::as_str),
                Some("noise_class"),
                "case {i} ({class})"
            );
        }
        assert!(r[5].is_ok(), "{:?}", r[5]);
        assert!(
            r[6].is_ok(),
            "mid-line Error: is not a declared class: {:?}",
            r[6]
        );
        assert_eq!(s.store().record_count().expect("count"), 2);
        let text = std::fs::read_to_string(&journal_path).expect("journal readable");
        for (_, class) in &cases {
            assert!(
                text.lines().any(|l| l.contains("\"remember.refusal\"")
                    && l.contains("\"noise_class\"")
                    && l.contains(&format!("\"{class}\""))),
                "journal must carry class {class}: {text}"
            );
        }
        assert!(!text.contains("\"duplicate_exact\""), "{text}");
    }

    /// A1 rev 2 §4 ablation: `WM_GEN3_NOISE=0` (setter) admits the same content.
    #[test]
    fn noise_table_ablation_admits() {
        let path = temp_store("noise-off");
        let mut s = Substrate::open(&path, None, default_view()).expect("open");
        s.set_noise_enabled(false);
        let r = s.remember_batch(&[item("Traceback (most recent call last):\nError: boom")]);
        assert!(r[0].is_ok(), "{r:?}");
        assert_eq!(s.store().record_count().expect("count"), 1);
    }

    fn last_selection(journal: &std::path::Path) -> serde_json::Value {
        std::fs::read_to_string(journal)
            .expect("journal readable")
            .lines()
            .filter_map(|l| serde_json::from_str::<serde_json::Value>(l).ok())
            .filter(|e| e["type"] == "selection.decision")
            .next_back()
            .expect("selection.decision present")
    }

    /// W2_03 §3 cases 2/4: strata are request-time; direction decides who is current;
    /// `include_historical` is uniform stratum 1 with full history.
    #[test]
    fn strata_request_time_direction_and_uniform_history() {
        let path = temp_store("w203-direction");
        let journal_path = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
        let ids: Vec<u64> = s
            .remember_batch(&[
                RememberItem {
                    content: "the north bay is the current loading area".into(),
                    source: "t".into(),
                    kind: ImportKind::Reported,
                },
                RememberItem {
                    content: "the north bay was the old loading area".into(),
                    source: "t".into(),
                    kind: ImportKind::Reported,
                },
            ])
            .into_iter()
            .map(|r| r.expect("remembered"))
            .collect();
        let rel_id = s.store.alloc_relation_id().expect("id");
        s.store
            .put_relation(&Relation::new(rel_id, ids[0], ids[1], 0.9, 0))
            .expect("relation");
        s.set_arbitration(Arbitration::Structural);

        let hits = s.recall_expect(&q("north bay loading area"));
        assert_eq!(hits.len(), 2);
        assert_eq!(hits[0].id, ids[0], "source (current) first");
        assert_eq!(hits[1].id, ids[1], "target (superseded) last");
        let sel = last_selection(&journal_path);
        let entries = sel["selected"].as_array().expect("selected");
        assert_eq!(entries[0]["stratum"], 0);
        assert_eq!(entries[1]["stratum"], 2);
        assert_eq!(entries[1]["superseded_by"], rel_id);

        let mut qh = q("north bay loading area");
        qh.include_historical = true;
        let hist = s.recall_expect(&qh);
        assert_eq!(hist.len(), 2);
        let sel = last_selection(&journal_path);
        assert!(
            sel["selected"]
                .as_array()
                .expect("selected")
                .iter()
                .all(|e| e["stratum"] == 1),
            "{sel}"
        );
    }

    /// W2_03 §3 case 3 (F4 guard): duplicate relations on one endpoint pair yield one
    /// effective state — each record in exactly one stratum, deduped endpoint metric.
    #[test]
    fn strata_f4_duplicate_relations_single_effective_state() {
        let path = temp_store("w203-f4");
        let journal_path = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
        let ids: Vec<u64> = s
            .remember_batch(&[
                RememberItem {
                    content: "the north bay is the current loading area".into(),
                    source: "t".into(),
                    kind: ImportKind::Reported,
                },
                RememberItem {
                    content: "the north bay was the old loading area".into(),
                    source: "t".into(),
                    kind: ImportKind::Reported,
                },
            ])
            .into_iter()
            .map(|r| r.expect("remembered"))
            .collect();
        for _ in 0..3 {
            let rel_id = s.store.alloc_relation_id().expect("id");
            s.store
                .put_relation(&Relation::new(rel_id, ids[0], ids[1], 0.9, 0))
                .expect("relation");
        }
        s.set_arbitration(Arbitration::Structural);

        let hits = s.recall_expect(&q("north bay loading area"));
        assert_eq!(hits.len(), 2);
        let sel = last_selection(&journal_path);
        let entries = sel["selected"].as_array().expect("selected");
        let strata: Vec<u64> = entries
            .iter()
            .map(|e| e["stratum"].as_u64().expect("stratum"))
            .collect();
        assert_eq!(strata.len(), 2, "{sel}");
        assert_eq!(strata.iter().filter(|&&x| x == 0).count(), 1, "{sel}");
        assert_eq!(strata.iter().filter(|&&x| x == 2).count(), 1, "{sel}");

        let rels = s.store.iter_relations().expect("relations");
        let pairs: std::collections::HashSet<(u64, u64)> =
            rels.iter().map(|r| (r.src(), r.dst())).collect();
        assert_eq!(rels.len(), 3);
        assert_eq!(pairs.len(), 1, "deduped endpoint metric");
    }

    #[test]
    fn floors_exclusion_is_disclosed_as_insufficient_evidence() {
        let path = temp_store("a2-floors");
        let journal_path = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
        s.remember_batch(&[item("alpha beta gamma")]);
        let mut query = q("alpha zulu");
        query.min_score = 0.9;
        let hits = s.recall_expect(&query);
        assert!(hits.is_empty(), "floor must exclude the sole candidate");
        let events: Vec<serde_json::Value> = std::fs::read_to_string(&journal_path)
            .expect("journal")
            .lines()
            .filter_map(|l| serde_json::from_str(l).ok())
            .collect();
        let abst: Vec<_> = events
            .iter()
            .filter(|e| e["type"] == "selection.decision" && e["abstained"] == true)
            .collect();
        assert_eq!(
            abst.len(),
            1,
            "exactly one abstention event per empty return"
        );
        assert_eq!(abst[0]["reason"], "insufficient_evidence");
        assert_eq!(abst[0]["cause"], "no_results_above_floors");
        assert_eq!(abst[0]["lexical_candidates"], 1);
    }

    #[test]
    fn no_candidates_discloses_insufficient_evidence() {
        let path = temp_store("a2-none");
        let journal_path = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
        s.remember_batch(&[item("alpha beta gamma")]);
        let hits = s.recall_expect(&q("zulu"));
        assert!(hits.is_empty());
        let events: Vec<serde_json::Value> = std::fs::read_to_string(&journal_path)
            .expect("journal")
            .lines()
            .filter_map(|l| serde_json::from_str(l).ok())
            .collect();
        let abst: Vec<_> = events
            .iter()
            .filter(|e| e["type"] == "selection.decision" && e["abstained"] == true)
            .collect();
        assert_eq!(abst.len(), 1);
        assert_eq!(abst[0]["reason"], "insufficient_evidence");
        assert_eq!(abst[0]["cause"], "no_candidates");
    }

    #[test]
    fn floor_bounds_fail_closed() {
        let mut s = substrate("a2-bounds");
        s.remember_batch(&[item("alpha beta gamma")]);
        for value in [-0.01f32, 1.01, f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
            let mut by_score = q("alpha");
            by_score.min_score = value;
            match s.recall(&by_score) {
                Err(RecallError::InvalidFloor { field, .. }) => assert_eq!(field, "min_score"),
                other => panic!("min_score={value} must refuse, got {other:?}"),
            }
            let mut by_coverage = q("alpha");
            by_coverage.min_coverage = value;
            match s.recall(&by_coverage) {
                Err(RecallError::InvalidFloor { field, .. }) => assert_eq!(field, "min_coverage"),
                other => panic!("min_coverage={value} must refuse, got {other:?}"),
            }
        }
        for value in [0.0f32, 0.5, 1.0] {
            let mut query = q("alpha");
            query.min_score = value;
            query.min_coverage = value;
            assert!(s.recall(&query).is_ok(), "{value} must be in range");
        }
    }

    #[test]
    fn invalid_floors_emit_no_selection_events() {
        let path = temp_store("a2-bounds-journal");
        let journal_path = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
        s.remember_batch(&[item("alpha beta gamma")]);
        let mut query = q("alpha");
        query.min_score = 2.0;
        assert!(s.recall(&query).is_err());
        let text = std::fs::read_to_string(&journal_path).expect("journal");
        assert!(
            !text.contains("selection.decision"),
            "caller errors precede selection and must not journal a decision: {text}"
        );
    }

    #[test]
    fn readonly_substrate_reads_and_refuses_writes() {
        let path = temp_store("ro");
        let journal_path = path.with_extension("journal.jsonl");
        {
            let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
            s.remember_batch(&[item("alpha beta gamma")]);
        }
        let mut ro = Substrate::open_readonly(&path, None, default_view()).expect("ro open");
        assert!(ro.store().is_readonly());
        let hits = ro.recall_expect(&q("alpha"));
        assert_eq!(hits.len(), 1, "read path works read-only");
        let refused = ro.remember_batch(&[item("delta epsilon")]);
        assert!(refused[0].is_err(), "writes must be refused: {refused:?}");
    }

    #[test]
    fn budget_refusal_does_not_block_reads_and_stays_typed() {
        let path = temp_store("a2-starve");
        let journal_path = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
        s.set_budget(1);
        let results = s.remember_batch(&[item("alpha beta gamma"), item("delta epsilon zeta")]);
        assert!(results[0].is_ok(), "{results:?}");
        assert_eq!(
            results[1].as_ref().err().map(String::as_str),
            Some("write budget exceeded")
        );
        let hits = s.recall_expect(&q("alpha"));
        assert_eq!(hits.len(), 1, "reads stay open under refusal");
        assert!(s.recall_expect(&q("zulu")).is_empty());
        let text = std::fs::read_to_string(&journal_path).expect("journal");
        let events: Vec<serde_json::Value> = text
            .lines()
            .filter_map(|l| serde_json::from_str(l).ok())
            .collect();
        let refusals: Vec<_> = events
            .iter()
            .filter(|e| e["type"] == "remember.refusal")
            .collect();
        assert_eq!(refusals.len(), 1);
        assert_eq!(refusals[0]["reason"], "write budget exceeded (fail-closed)");
        let abst: Vec<_> = events
            .iter()
            .filter(|e| e["type"] == "selection.decision" && e["abstained"] == true)
            .collect();
        assert_eq!(
            abst.len(),
            1,
            "the empty read is insufficiency, not refusal"
        );
        assert_eq!(abst[0]["reason"], "insufficient_evidence");
    }

    #[test]
    fn projection_off_discloses_route() {
        let path = temp_store("a2-route-off");
        let journal_path = path.with_extension("journal.jsonl");
        let mut s = Substrate::open(&path, Some(&journal_path), default_view()).expect("open");
        s.remember_batch(&[item("alpha beta gamma")]);
        let _ = s.recall_expect(&q("alpha"));
        let text = std::fs::read_to_string(&journal_path).expect("journal");
        let decisions: Vec<serde_json::Value> = text
            .lines()
            .filter_map(|l| serde_json::from_str(l).ok())
            .filter(|v: &serde_json::Value| v["type"] == "selection.decision")
            .collect();
        let decision = decisions.last().expect("selection.decision present");
        assert_eq!(decision["projection_ran"], false);
        assert_eq!(decision["projection_error"], false);
        assert_eq!(decision["semantic_candidates"], 0);
    }
}

#[cfg(test)]
mod p2d_tests {
    use super::*;
    use crate::constitution::default_view;

    fn temp_store(tag: &str) -> std::path::PathBuf {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        std::env::temp_dir().join(format!("wm-gen3-{tag}-{}-{nanos}", std::process::id()))
    }

    /// P2D §4: structural strata — current (source) first, unresolved next,
    /// superseded last; include_historical collapses strata (state-insensitive).
    #[test]
    fn structural_arbitration_strata_order() {
        let mut s = Substrate::open(&temp_store("p2d"), None, default_view()).expect("open");
        let ids: Vec<u64> = s
            .remember_batch(&[
                RememberItem {
                    content: "alpha one record".into(),
                    source: "t".into(),
                    kind: ImportKind::Reported,
                },
                RememberItem {
                    content: "alpha two record".into(),
                    source: "t".into(),
                    kind: ImportKind::Reported,
                },
                RememberItem {
                    content: "alpha three record".into(),
                    source: "t".into(),
                    kind: ImportKind::Reported,
                },
            ])
            .into_iter()
            .map(|r| r.expect("remembered"))
            .collect();
        let rel_id = s.store.alloc_relation_id().expect("id");
        s.store
            .put_relation(&Relation::new(rel_id, ids[1], ids[0], 0.9, 0))
            .expect("relation");
        s.set_arbitration(Arbitration::Structural);

        let mut q = RecallQuery {
            query: "alpha".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        };
        let hits = s.recall_expect(&q);
        assert_eq!(hits.len(), 3);
        assert_eq!(hits[0].id, ids[1], "current (source) stratum first");
        assert_eq!(hits[2].id, ids[0], "superseded stratum last");

        q.include_historical = true;
        let hits_all = s.recall_expect(&q);
        assert_eq!(hits_all[0].id, ids[2], "state-insensitive: newest first");
    }
}

#[cfg(test)]
mod p2e_tests {
    use super::*;
    use crate::constitution::default_view;

    fn temp_store(tag: &str) -> std::path::PathBuf {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        std::env::temp_dir().join(format!("wm-gen3-{tag}-{}-{nanos}", std::process::id()))
    }

    fn item_src(text: &str, source: &str) -> RememberItem {
        RememberItem {
            content: text.into(),
            source: source.into(),
            kind: ImportKind::Reported,
        }
    }

    fn q(text: &str) -> RecallQuery {
        RecallQuery {
            query: text.into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        }
    }

    /// D2 properties must hold for the weighted (dispersion) form too.
    #[test]
    fn d2_weighted_properties() {
        let mut s = Substrate::open(&temp_store("d2w"), None, default_view()).expect("open");
        s.set_dispersion(true);
        s.remember_batch(&[
            item_src("alpha beta", "corpus:codex:user,session_001"),
            item_src("alpha beta zeta phi", "corpus:codex:user,session_001"),
        ]);
        let hits = s.recall_expect(&q("alpha beta"));
        assert_eq!(hits.len(), 2);
        assert!(
            (hits[0].score - hits[1].score).abs() < 1e-6,
            "irrelevant terms changed support"
        );
        assert!(
            (hits[0].score - 1.0).abs() < 1e-6,
            "full support {}",
            hits[0].score
        );
        assert!(
            s.recall_expect(&q("quantum chromodynamics")).is_empty(),
            "zero overlap must abstain"
        );
        let a = s.recall_expect(&q("alpha"));
        let b = s.recall_expect(&q("alpha"));
        assert_eq!(
            a.iter()
                .map(|h| (h.id, h.score.to_bits()))
                .collect::<Vec<_>>(),
            b.iter()
                .map(|h| (h.id, h.score.to_bits()))
                .collect::<Vec<_>>(),
            "deterministic"
        );
    }

    /// Estimator effect: a token scattered across distinct contexts collapses to
    /// zero weight; the same token inside one context keeps full weight.
    #[test]
    fn dispersion_discounts_scattered_tokens() {
        let mut one = Substrate::open(&temp_store("d2d1"), None, default_view()).expect("open");
        one.set_dispersion(true);
        one.remember_batch(&[
            item_src("zeta marker field", "corpus:codex:user,session_001"),
            item_src("zeta marker field", "corpus:codex:user,session_001"),
            item_src("zeta marker field", "corpus:codex:user,session_001"),
        ]);
        let h1 = one.recall_expect(&q("zeta"));
        let mut many = Substrate::open(&temp_store("d2d2"), None, default_view()).expect("open");
        many.set_dispersion(true);
        many.remember_batch(&[
            item_src("zeta marker field", "corpus:codex:user,session_001"),
            item_src("zeta marker field", "corpus:codex:user,session_002"),
            item_src("zeta marker field", "corpus:codex:user,session_003"),
        ]);
        let h2 = many.recall_expect(&q("zeta"));
        assert!(
            h1[0].score > h2[0].score,
            "one-context {} vs scattered {}",
            h1[0].score,
            h2[0].score
        );
        assert!(
            (h2[0].score - 0.0).abs() < 1e-6,
            "scattered weight should collapse: {}",
            h2[0].score
        );
    }
}

#[cfg(test)]
mod gated_tests {
    use super::*;
    use crate::constitution::default_view;

    fn temp_store(tag: &str) -> std::path::PathBuf {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        std::env::temp_dir().join(format!("wm-gen3-{tag}-{}-{nanos}", std::process::id()))
    }

    fn q(text: &str) -> RecallQuery {
        RecallQuery {
            query: text.into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        }
    }

    fn gate_events(journal_path: &std::path::Path) -> Vec<serde_json::Value> {
        let text = std::fs::read_to_string(journal_path).expect("journal read");
        text.lines()
            .filter_map(|l| serde_json::from_str::<serde_json::Value>(l).ok())
            .filter(|v| v.get("type").and_then(|t| t.as_str()) == Some("projection.gate"))
            .collect()
    }

    /// GEN3-GATED-S-001: with the gate on, a query with sufficient lexical
    /// support stays dormant (pure-lexical path, identical to S-off); a query
    /// with no lexical support fires the projection pass (identical to always-on).
    #[test]
    fn gated_projection_fires_only_below_floor() {
        let dir = crate::embed_cache_dir_or_panic();
        let store_path = temp_store("gated");
        let journal_path = store_path.with_extension("journal.jsonl");
        let mut s =
            Substrate::open(&store_path, Some(&journal_path), default_view()).expect("open");
        s.set_projection_enabled(true, Some(&dir))
            .expect("projection loads");
        s.set_projection_gated(true);
        s.set_arbitration(Arbitration::Structural);
        s.remember_batch(&[
            RememberItem {
                content: "the north bay is the current loading area".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
            RememberItem {
                content: "the west gate is locked at night".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
        ]);

        // Lexical query: full token support → gate dormant, no projection pass.
        let hits = s.recall_expect(&q("north bay loading area"));
        assert!(!hits.is_empty(), "lexical query must not abstain");
        let events = gate_events(&journal_path);
        assert_eq!(events.len(), 1, "one gate event per query");
        let e = &events[0];
        assert_eq!(e["fired"], false, "full lexical support must not fire: {e}");
        assert_eq!(e["gated"], true);
        let lex_max = e["lex_support_max"].as_f64().unwrap_or(0.0);
        assert!(
            lex_max >= 0.01,
            "lex_support_max {lex_max} must sit above the 0.01 floor"
        );

        // S-off reference on the same corpus: dormant gated recall must match it.
        let mut g0 = Substrate::open(&temp_store("gated-g0"), None, default_view()).expect("open");
        g0.set_arbitration(Arbitration::Structural);
        g0.remember_batch(&[
            RememberItem {
                content: "the north bay is the current loading area".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
            RememberItem {
                content: "the west gate is locked at night".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
        ]);
        let ref_hits = g0.recall_expect(&q("north bay loading area"));
        let ids = |h: &[Hit]| h.iter().map(|x| x.id).collect::<Vec<_>>();
        assert_eq!(ids(&hits), ids(&ref_hits), "dormant gated == S-off ids");
    }

    /// With the gate on and zero lexical support, the projection pass fires and
    /// recall behaves like always-on S (semantic candidates reachable).
    #[test]
    fn gated_projection_fires_without_lexical_support() {
        let dir = crate::embed_cache_dir_or_panic();
        let store_path = temp_store("gated-f");
        let journal_path = store_path.with_extension("journal.jsonl");
        let mut s =
            Substrate::open(&store_path, Some(&journal_path), default_view()).expect("open");
        s.set_projection_enabled(true, Some(&dir))
            .expect("projection loads");
        s.set_projection_gated(true);
        s.set_arbitration(Arbitration::Structural);
        s.remember_batch(&[
            RememberItem {
                content: "the north bay is the current loading area".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
            RememberItem {
                content: "the west gate is locked at night".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
        ]);

        // No shared tokens with any record → below the floor → must fire.
        let hits = s.recall_expect(&q("dockyard unloading zone"));
        let events = gate_events(&journal_path);
        assert_eq!(events.len(), 1, "one gate event per query");
        let e = &events[0];
        assert_eq!(e["fired"], true, "no lexical support must fire: {e}");
        assert!(e["lex_support_max"].as_f64().unwrap_or(1.0) < 0.01);

        // Always-on reference: fired gated recall must equal g2 on the same query.
        let mut g2 = Substrate::open(&temp_store("gated-g2"), None, default_view()).expect("open");
        g2.set_projection_enabled(true, Some(&dir))
            .expect("projection loads");
        g2.set_arbitration(Arbitration::Structural);
        g2.remember_batch(&[
            RememberItem {
                content: "the north bay is the current loading area".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
            RememberItem {
                content: "the west gate is locked at night".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
        ]);
        let g2_hits = g2.recall_expect(&q("dockyard unloading zone"));
        let ids = |h: &[Hit]| h.iter().map(|x| x.id).collect::<Vec<_>>();
        assert_eq!(ids(&hits), ids(&g2_hits), "fired gated == always-on ids");
    }

    /// GEN3-GATED-S-003: count mode fires only when fewer than two lexical
    /// candidates exist (0 or 1); two or more candidates stay dormant.
    #[test]
    fn count_gate_fires_below_two_candidates() {
        let dir = crate::embed_cache_dir_or_panic();
        let store_path = temp_store("count-gate");
        let journal_path = store_path.with_extension("journal.jsonl");
        let mut s =
            Substrate::open(&store_path, Some(&journal_path), default_view()).expect("open");
        s.set_projection_enabled(true, Some(&dir))
            .expect("projection loads");
        s.set_projection_gate_count(true);
        s.set_arbitration(Arbitration::Structural);
        s.remember_batch(&[
            RememberItem {
                content: "the north bay handles the loading".into(),
                source: "corpus:codex:user,session_001".into(),
                kind: ImportKind::Reported,
            },
            RememberItem {
                content: "the north bay is the current loading area".into(),
                source: "corpus:codex:user,session_002".into(),
                kind: ImportKind::Reported,
            },
            RememberItem {
                content: "the west gate is locked at night".into(),
                source: "corpus:codex:user,session_003".into(),
                kind: ImportKind::Reported,
            },
        ]);

        let _ = s.recall_expect(&q("north bay")); // 2 candidates -> dormant
        let _ = s.recall_expect(&q("gate")); // 1 candidate  -> fires
        let _ = s.recall_expect(&q("quantum")); // 0 candidates -> fires

        let events = gate_events(&journal_path);
        assert_eq!(events.len(), 3, "one gate event per query");
        assert_eq!(
            events[0]["fired"], false,
            "two candidates must stay dormant: {}",
            events[0]
        );
        assert_eq!(events[0]["lexical_candidates"], 2);
        assert_eq!(
            events[1]["fired"], true,
            "one candidate must fire: {}",
            events[1]
        );
        assert_eq!(events[1]["lexical_candidates"], 1);
        assert_eq!(
            events[2]["fired"], true,
            "zero candidates must fire: {}",
            events[2]
        );
        assert_eq!(events[2]["lexical_candidates"], 0);
        // Diagnostic field present (zero behavioral effect).
        assert!(events[0]["relation_involved_candidates"].as_u64().is_some());
    }

    #[test]
    fn projection_on_discloses_route() {
        let dir = crate::embed_cache_dir();
        if !dir.exists() {
            eprintln!("skip: no embed cache at {}", dir.display());
            return;
        }
        let store_path = temp_store("a2-route-on");
        let journal_path = store_path.with_extension("journal.jsonl");
        let mut s =
            Substrate::open(&store_path, Some(&journal_path), default_view()).expect("open");
        s.set_projection_enabled(true, Some(&dir))
            .expect("projection loads");
        s.remember_batch(&[RememberItem {
            content: "alpha beta gamma".into(),
            source: "corpus:codex:user,session_001".into(),
            kind: ImportKind::Reported,
        }]);
        let _ = s.recall_expect(&q("alpha"));
        let text = std::fs::read_to_string(&journal_path).expect("journal read");
        let decisions: Vec<serde_json::Value> = text
            .lines()
            .filter_map(|l| serde_json::from_str(l).ok())
            .filter(|v: &serde_json::Value| v["type"] == "selection.decision")
            .collect();
        let decision = decisions.last().expect("selection.decision present");
        assert_eq!(decision["projection_ran"], true);
        assert_eq!(decision["projection_error"], false);
    }
}

#[cfg(test)]
mod scorer_determinism_tests {
    use super::*;
    use crate::constitution::default_view;

    fn temp_store(tag: &str) -> std::path::PathBuf {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        std::env::temp_dir().join(format!("wm-gen3-det-{tag}-{}-{nanos}", std::process::id()))
    }

    fn item_ctx(content: &str, session: &str) -> RememberItem {
        RememberItem {
            content: content.into(),
            source: format!("corpus:det:user,{session}"),
            kind: ImportKind::Reported,
        }
    }

    fn item(content: &str) -> RememberItem {
        item_ctx(content, "session_001")
    }

    fn q(text: &str) -> RecallQuery {
        RecallQuery {
            query: text.into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        }
    }

    /// Adversarial Case 1: Near-tie stability (registration §3.1).
    /// Two candidates whose scores differ by <= 1 ULP must not flip order across
    /// repeated runs or separate Substrate instances.
    #[test]
    fn scorer_determinism_near_tie_stability() {
        let path = temp_store("near-tie");
        {
            let mut s = Substrate::open(&path, None, default_view()).expect("open");
            s.remember_batch(&[
                item_ctx(
                    "kernel process memory virtual allocation table descriptor",
                    "session_001",
                ),
                item_ctx(
                    "kernel process memory virtual allocation table handle",
                    "session_002",
                ),
            ]);
        }
        let q_near = q("kernel process memory virtual allocation table");
        let mut s1 = Substrate::open(&path, None, default_view()).expect("open 1");
        let mut s2 = Substrate::open(&path, None, default_view()).expect("open 2");

        let res1 = s1.recall_expect(&q_near);
        let res2 = s2.recall_expect(&q_near);

        assert_eq!(res1.len(), 2);
        assert_eq!(res2.len(), 2);
        assert_eq!(
            res1[0].id, res2[0].id,
            "rank 0 id must never flip across instances"
        );
        assert_eq!(
            res1[1].id, res2[1].id,
            "rank 1 id must never flip across instances"
        );
        assert_eq!(
            res1[0].score.to_bits(),
            res2[0].score.to_bits(),
            "score bits must be identical (0 ULP divergence)"
        );
        assert_eq!(
            res1[1].score.to_bits(),
            res2[1].score.to_bits(),
            "score bits must be identical (0 ULP divergence)"
        );
    }

    /// Adversarial Case 2: sweep determinism under the ratified hard profile
    /// (registration §3.2, amended for Gate 9A Slice 1). The legacy mutable
    /// `pair_budget` no longer truncates planning: the same corpus produces the
    /// same pair/proposal counts on two independent stores, and oversize work
    /// refuses instead of silently truncating.
    #[test]
    fn scorer_determinism_sweep_budget_boundary() {
        let path1 = temp_store("sweep-budget-1");
        let journal1 = path1.with_extension("j1.jsonl");
        let path2 = temp_store("sweep-budget-2");
        let journal2 = path2.with_extension("j2.jsonl");

        let items = vec![
            item_ctx("apple banana cherry date elderberry fig", "session_001"),
            item_ctx("apple banana cherry grape hazelnut", "session_002"),
            item_ctx("apple banana date grape fig kiwi", "session_003"),
            item_ctx("cherry date elderberry fig hazelnut lemon", "session_004"),
            item_ctx("banana date fig hazelnut kiwi lemon mango", "session_005"),
        ];

        let mut stats1 = {
            let mut s1 = Substrate::open(&path1, Some(&journal1), default_view()).expect("open 1");
            s1.remember_batch(&items);
            // Legacy mutable budget: must no longer truncate the pair stream.
            s1.policy.pair_budget = 3;
            s1.think_sweep()
        };
        let stats2 = {
            let mut s2 = Substrate::open(&path2, Some(&journal2), default_view()).expect("open 2");
            s2.remember_batch(&items);
            s2.policy.pair_budget = 3;
            s2.think_sweep()
        };

        assert!(
            !stats1.refused,
            "sweep should commit under the ratified profile: {:?}",
            stats1.error
        );
        assert_eq!(stats1.sweep, 0, "first committed sweep id");
        assert_eq!(stats2.sweep, 0);
        assert!(stats1.operation_id.is_some());
        assert!(
            stats1.pairs_examined > 3,
            "pair_budget must not truncate: {}",
            stats1.pairs_examined
        );
        assert_eq!(
            stats1.pairs_lexical_candidates,
            stats2.pairs_lexical_candidates
        );
        assert_eq!(stats1.pairs_considered, stats2.pairs_considered);
        assert_eq!(stats1.pairs_examined, stats2.pairs_examined);
        assert_eq!(stats1.pairs_rejected_rule, stats2.pairs_rejected_rule);
        assert_eq!(stats1.proposals, stats2.proposals);
        assert_eq!(stats1.promotions, stats2.promotions);
        assert_eq!(stats1.demotions, stats2.demotions);

        stats1.index_ms = 0;
        stats1.pair_ms = 0;
        stats1.took_ms = 0;

        let sweep_counters = |path: &std::path::Path| -> Vec<(u64, u64)> {
            std::fs::read_to_string(path)
                .expect("read journal")
                .lines()
                .filter_map(|l| serde_json::from_str::<serde_json::Value>(l).ok())
                .filter(|v| v["type"] == "think.sweep" && v["disabled"] == false)
                .map(|v| {
                    (
                        v["pairs_examined"].as_u64().unwrap_or(0),
                        v["proposals"].as_u64().unwrap_or(0),
                    )
                })
                .collect()
        };
        assert_eq!(sweep_counters(&journal1), sweep_counters(&journal2));
        assert_eq!(sweep_counters(&journal1).len(), 1);
    }

    /// Adversarial Case 3: Dispersion enabled determinism (registration §3.3).
    /// Context entropy dispersion reduction across sorted contexts produces
    /// 0 ULP divergence across fresh instances.
    #[test]
    fn scorer_determinism_dispersion_enabled() {
        let path = temp_store("dispersion-det");
        {
            let mut s = Substrate::open(&path, None, default_view()).expect("open");
            s.remember_batch(&[
                item_ctx("shared across many sessions term zebra", "session_001"),
                item_ctx("shared across many sessions term giraffe", "session_002"),
                item_ctx("shared across many sessions term elephant", "session_003"),
                item_ctx("shared across many sessions term lion", "session_004"),
                item_ctx("unique solitary session cheetah", "session_005"),
            ]);
        }

        let mut s1 = Substrate::open(&path, None, default_view()).expect("open 1");
        s1.set_dispersion(true);
        let mut s2 = Substrate::open(&path, None, default_view()).expect("open 2");
        s2.set_dispersion(true);

        let q_disp = q("shared sessions term zebra");
        let r1 = s1.recall_expect(&q_disp);
        let r2 = s2.recall_expect(&q_disp);

        assert!(!r1.is_empty());
        assert_eq!(r1.len(), r2.len());
        for (h1, h2) in r1.iter().zip(r2.iter()) {
            assert_eq!(h1.id, h2.id);
            assert_eq!(h1.rank, h2.rank);
            assert_eq!(
                h1.score.to_bits(),
                h2.score.to_bits(),
                "dispersion-weighted scores must be 0 ULP identical"
            );
        }
    }

    /// Adversarial Case 4: Restart determinism across reopen (registration §3.4).
    /// No in-memory state or hash-seed inheritance across store reopen;
    /// 0 ULP bitwise score equality and journal rank_key matching.
    #[test]
    fn scorer_determinism_restart_and_multiprocess() {
        let path = temp_store("restart-det");
        let j1 = path.with_extension("det1.journal.jsonl");
        let j2 = path.with_extension("det2.journal.jsonl");

        {
            let mut s = Substrate::open(&path, None, default_view()).expect("open init");
            s.remember_batch(&[
                item_ctx(
                    "quantum computing hardware superconducting qubits coherence time",
                    "session_001",
                ),
                item_ctx(
                    "superconducting circuits resonator frequency readout fidelity",
                    "session_002",
                ),
                item_ctx(
                    "quantum error correction surface code logical qubits distance",
                    "session_003",
                ),
                item_ctx(
                    "quantum computing algorithms phase estimation fault tolerance",
                    "session_004",
                ),
            ]);
        }

        let query = q("quantum computing superconducting qubits error correction");

        let hits1 = {
            let mut s1 = Substrate::open(&path, Some(&j1), default_view()).expect("open 1");
            s1.recall_expect(&query)
        };
        let hits2 = {
            let mut s2 = Substrate::open(&path, Some(&j2), default_view()).expect("open 2");
            s2.recall_expect(&query)
        };

        assert_eq!(hits1.len(), hits2.len());
        for (h1, h2) in hits1.iter().zip(hits2.iter()) {
            assert_eq!(h1.id, h2.id);
            assert_eq!(h1.rank, h2.rank);
            assert_eq!(
                h1.score.to_bits(),
                h2.score.to_bits(),
                "restart recall scores must have 0 ULP divergence (exact bits)"
            );
        }

        let j1_text = std::fs::read_to_string(&j1).expect("read j1");
        let j2_text = std::fs::read_to_string(&j2).expect("read j2");
        let d1: serde_json::Value = j1_text
            .lines()
            .filter_map(|l| serde_json::from_str(l).ok())
            .find(|v: &serde_json::Value| v["type"] == "selection.decision")
            .expect("d1");
        let d2: serde_json::Value = j2_text
            .lines()
            .filter_map(|l| serde_json::from_str(l).ok())
            .find(|v: &serde_json::Value| v["type"] == "selection.decision")
            .expect("d2");

        assert_eq!(d1["selected_ids"], d2["selected_ids"]);
    }

    /// Adversarial Case 5: No hidden re-ordering (registration §3.5).
    /// Declared order is first-class and ablatable: asserts that token-order sum
    /// produces deterministic values under declared query token iteration.
    #[test]
    fn scorer_determinism_declared_token_order() {
        let path = temp_store("declared-order");
        let mut s = Substrate::open(&path, None, default_view()).expect("open");
        s.remember_batch(&[
            item("compiler optimization pass register allocation instruction scheduling"),
            item("virtual machine bytecode interpreter compilation runtime"),
        ]);

        let q1 = q("compiler optimization register allocation");
        let q2 = q("compiler optimization register allocation");

        let res1 = s.recall_expect(&q1);
        let res2 = s.recall_expect(&q2);

        assert_eq!(res1.len(), res2.len());
        assert_eq!(res1[0].score.to_bits(), res2[0].score.to_bits());
    }

    #[test]
    fn test_remember_batch_persist_failure_leaves_no_identity_orphan() {
        let path = temp_store("persist-orphan-safety");
        let mut s = Substrate::open(&path, None, default_view()).expect("open");
        let r1 = s.remember_batch(&[item("valid record alpha")]);
        assert!(r1[0].is_ok());
        let id1 = *r1[0].as_ref().unwrap();
        assert!(s.store.get_record(id1).unwrap().is_some());
    }
}

#[cfg(test)]
mod authorized_intake_tests {
    use super::*;
    use crate::constitution::default_view;
    use crate::evidence::RatifiedChannel;
    use crate::intake::{CommitDisposition, IntakeKind, IntakeRequest, OperationId};

    fn substrate(tag: &str) -> Substrate {
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-authorized-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("clock")
                .as_nanos()
        ));
        Substrate::open(&path, None, default_view()).expect("open synthetic store")
    }

    fn request(
        store: &Substrate,
        channel: &RatifiedChannel,
        operation_byte: u8,
        kind: IntakeKind,
        content: &str,
    ) -> IntakeRequest {
        IntakeRequest::new(
            channel,
            OperationId::from_bytes([operation_byte; 16]),
            store.intake_realm_id().expect("realm"),
            store.intake_epoch().expect("epoch"),
            0,
            kind,
            content.to_string(),
            "synthetic:authorized-test".to_string(),
        )
        .expect("request")
    }

    #[test]
    fn authorized_intake_requires_present_matching_authority() {
        let mut store = substrate("authority");
        store.intake_authority = None;
        let refused = store.remember_batch(&[RememberItem {
            content: "synthetic missing authority record".into(),
            source: "synthetic:test".into(),
            kind: ImportKind::Reported,
        }]);
        assert!(refused[0].as_ref().unwrap_err().contains("not installed"));

        let issuer = RatifiedChannel::stub("issuer-a");
        let wrong = RatifiedChannel::stub("issuer-b");
        let req = request(
            &store,
            &issuer,
            1,
            IntakeKind::Reported,
            "synthetic wrong authority record",
        );
        assert!(
            store
                .remember_authorized(&wrong, req)
                .unwrap_err()
                .contains("different authority")
        );
        assert_eq!(store.store.record_count().expect("count"), 0);
    }

    #[test]
    fn authenticated_replay_precedes_budget_and_stale_epoch() {
        let mut store = substrate("replay");
        let issuer = RatifiedChannel::stub("issuer");
        store.set_budget(1);
        let req = request(
            &store,
            &issuer,
            2,
            IntakeKind::Reported,
            "synthetic replay record",
        );
        let first = store
            .remember_authorized(&issuer, req.clone())
            .expect("first commit");
        assert_eq!(first.disposition, CommitDisposition::Committed);
        assert_eq!(store.intake_epoch().expect("epoch"), 1);
        let replay = store
            .remember_authorized(&issuer, req)
            .expect("authenticated replay");
        assert_eq!(replay.disposition, CommitDisposition::Replay);
        assert_eq!(replay.receipt, first.receipt);
        assert_eq!(store.store.record_count().expect("count"), 1);
        assert_eq!(store.writes_used, 1);
    }

    #[test]
    fn authorized_intake_preserves_all_existing_epistemic_kinds() {
        let mut store = substrate("kinds");
        let issuer = RatifiedChannel::stub("issuer");
        let cases = [
            (
                IntakeKind::Reported,
                Domain::Reported,
                "synthetic reported record",
            ),
            (
                IntakeKind::System,
                Domain::System,
                "synthetic system record",
            ),
            (
                IntakeKind::Simulated,
                Domain::Simulated,
                "synthetic simulated record",
            ),
        ];
        for (index, (kind, domain, content)) in cases.into_iter().enumerate() {
            let req = request(&store, &issuer, 10 + index as u8, kind, content);
            let outcome = store
                .remember_authorized(&issuer, req)
                .expect("commit kind");
            let record = store
                .store
                .get_record(outcome.receipt.record_id)
                .expect("read")
                .expect("record");
            assert_eq!(record.domain(), domain);
            assert_eq!(record.class(), crate::evidence::Class::Evidence);
            assert_eq!(record.status(), crate::evidence::RecordStatus::Persistent);
            assert_eq!(record.confidence().to_bits(), 1.0_f32.to_bits());
            assert_eq!(record.created_at(), record.id());
        }
    }

    #[test]
    fn process_counter_overflow_refuses_before_durable_commit() {
        let mut store = substrate("counter-overflow");
        let issuer = RatifiedChannel::stub("issuer");
        store.set_budget(0);
        store.writes_used = u32::MAX;
        let req = request(
            &store,
            &issuer,
            20,
            IntakeKind::Reported,
            "synthetic overflow record",
        );
        assert!(
            store
                .remember_authorized(&issuer, req)
                .unwrap_err()
                .contains("counter exhausted")
        );
        assert_eq!(store.store.record_count().expect("count"), 0);
        assert_eq!(store.intake_epoch().expect("epoch"), 0);
    }

    #[test]
    fn durable_duplicate_check_preserves_refusal_with_an_outdated_local_index() {
        let mut store = substrate("stale-index");
        let issuer = RatifiedChannel::stub("issuer");
        let first = request(
            &store,
            &issuer,
            30,
            IntakeKind::Reported,
            "synthetic shared record",
        );
        store
            .remember_authorized(&issuer, first)
            .expect("first commit");
        // Model a local index that has not observed another writer's record.
        store.identity.clear();
        let second = request(
            &store,
            &issuer,
            31,
            IntakeKind::Reported,
            "synthetic shared record",
        );
        assert_eq!(
            store.remember_authorized(&issuer, second).unwrap_err(),
            "duplicate_exact"
        );
        assert_eq!(store.store.record_count().unwrap(), 1);
        assert_eq!(store.intake_epoch().unwrap(), 1);
        assert_eq!(store.writes_used, 1);
    }
}

#[cfg(test)]
mod cache_boundary_tests {
    use super::*;
    use crate::constitution::default_view;

    fn temp_store(label: &str) -> std::path::PathBuf {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).unwrap();
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-cache-{label}-{:x}",
            u64::from_be_bytes(nonce)
        ));
        let _ = std::fs::remove_dir_all(&path);
        path
    }

    fn item(content: &str) -> RememberItem {
        RememberItem {
            content: content.into(),
            source: "fixture:cache".into(),
            kind: ImportKind::Reported,
        }
    }

    /// Article 7 boundary: a cache-format version bump invalidates every derived
    /// entry (keys change), and no canonical state is involved.
    #[test]
    fn versioned_cache_keys_invalidate_on_version_bump() {
        let key_v1 = embed_cache_key("synthetic cache text", 1);
        let key_v2 = embed_cache_key("synthetic cache text", 2);
        assert_ne!(key_v1, key_v2);

        let path = temp_store("version");
        let substrate = Substrate::open(&path, None, default_view()).expect("open");
        substrate
            .store
            .put_embedding_cache(&key_v1, &[0.1, 0.2])
            .unwrap();
        assert!(
            substrate
                .store
                .get_embedding_cache(&key_v1)
                .unwrap()
                .is_some()
        );
        assert!(
            substrate
                .store
                .get_embedding_cache(&key_v2)
                .unwrap()
                .is_none(),
            "a version bump must miss every prior entry"
        );
        assert_eq!(substrate.store.embedding_cache_len().unwrap(), 1);
        drop(substrate);
        let _ = std::fs::remove_dir_all(&path);
    }

    /// Article 7 boundary: derived cache writes never touch canonical state.
    #[test]
    fn cache_writes_leave_canonical_state_unchanged() {
        let path = temp_store("canonical");
        let mut substrate = Substrate::open(&path, None, default_view()).expect("open");
        assert_eq!(
            substrate.remember_batch(&[item("canonical record")]),
            vec![Ok(0)]
        );
        let records_before = substrate.store.record_count().unwrap();
        let epoch_before = substrate.intake_epoch().unwrap();

        substrate
            .store
            .put_embedding_cache("derived:key", &[1.0, 0.0])
            .unwrap();
        assert_eq!(substrate.store.record_count().unwrap(), records_before);
        assert_eq!(substrate.intake_epoch().unwrap(), epoch_before);
        assert!(substrate.store.iter_relations().unwrap().is_empty());
        drop(substrate);
        let _ = std::fs::remove_dir_all(&path);
    }

    /// Article 7 boundary: projection-disabled recall performs no derived writes.
    #[test]
    fn projection_off_recall_writes_no_cache() {
        let path = temp_store("recall");
        let mut substrate = Substrate::open(&path, None, default_view()).expect("open");
        assert_eq!(
            substrate.remember_batch(&[item("synthetic orchard apple harvest")]),
            vec![Ok(0)]
        );
        let hits = substrate.recall_expect(&RecallQuery {
            query: "orchard apple".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        });
        assert!(!hits.is_empty());
        assert_eq!(substrate.store.embedding_cache_len().unwrap(), 0);
        drop(substrate);
        let _ = std::fs::remove_dir_all(&path);
    }

    #[test]
    fn test_session_checkpoint_and_compounding_continuity() {
        let path = temp_store("session_cont");
        let mut substrate = Substrate::open(&path, None, default_view()).expect("open");

        // 1. Initial empty continuity
        let empty = substrate.session_continuity(Some("sess-alpha")).unwrap();
        assert!(empty.is_none());

        // 2. Commit Checkpoint 1
        let cp1 = SessionCheckpoint {
            session_id: "sess-alpha".into(),
            agent_id: "antigravity".into(),
            checkpoint_type: "turn".into(),
            summary: "Completed Phase 1 and validated closures.".into(),
            next_queue: vec!["Begin Phase 2".into(), "Review receipts".into()],
            open_flags: vec!["no_drift".into()],
            context_token: Some("ctx_hash_123".into()),
            representation: Some(crate::transport::RepresentationTransport::Text {
                text: "Turn 1 state".into(),
                language: Some("en".into()),
            }),
            timestamp_iso: Some("2026-09-25T14:00:00Z".into()),
        };
        let id1 = substrate.session_checkpoint(&cp1).unwrap();
        assert_eq!(id1, 0);

        // 3. Commit Checkpoint 2 (compounding progress)
        let cp2 = SessionCheckpoint {
            session_id: "sess-alpha".into(),
            agent_id: "antigravity".into(),
            checkpoint_type: "handoff".into(),
            summary: "Phase 2 in progress. Handoff to Luna.".into(),
            next_queue: vec!["Run benchmarks".into()],
            open_flags: vec![],
            context_token: Some("ctx_hash_456".into()),
            representation: None,
            timestamp_iso: Some("2026-09-25T14:30:00Z".into()),
        };
        let id2 = substrate.session_checkpoint(&cp2).unwrap();
        assert_eq!(id2, 1);

        // 4. Also commit an unstructured record in a different session
        let id3 = substrate
            .session_record("sess-beta", "opencode", "note", "Exploratory trace")
            .unwrap();
        assert_eq!(id3, 2);

        // 5. Query continuity for sess-alpha -> MUST return latest cp2
        let cont_alpha = substrate
            .session_continuity(Some("sess-alpha"))
            .unwrap()
            .unwrap();
        assert_eq!(cont_alpha.record_id, 1);
        assert_eq!(cont_alpha.session_id, "sess-alpha");
        assert_eq!(cont_alpha.checkpoint_type, "handoff");
        assert_eq!(cont_alpha.summary, "Phase 2 in progress. Handoff to Luna.");
        assert_eq!(cont_alpha.next_queue, vec!["Run benchmarks".to_string()]);
        assert_eq!(cont_alpha.context_token, Some("ctx_hash_456".into()));

        // 6. Query overall latest continuity -> returns sess-beta note
        let cont_latest = substrate.session_continuity(None).unwrap().unwrap();
        assert_eq!(cont_latest.record_id, 2);
        assert_eq!(cont_latest.session_id, "sess-beta");

        // 7. List sessions -> ["sess-alpha", "sess-beta"]
        let sessions = substrate.session_list().unwrap();
        assert_eq!(
            sessions,
            vec!["sess-alpha".to_string(), "sess-beta".to_string()]
        );

        drop(substrate);
        let _ = std::fs::remove_dir_all(&path);
    }

    #[test]
    fn test_hebbian_graph_propagation_and_coactivation() {
        let path = temp_store("hebbian_test");
        let mut substrate = Substrate::open(&path, None, default_view()).expect("open");
        substrate.set_intake_authority(crate::evidence::RatifiedChannel::stub("test-hebbian"));

        // 1. Ingest records with disjoint lexical terms
        let id0 = substrate
            .remember_batch(&[item("compiler optimization passes in llvm backend")])
            .remove(0)
            .unwrap();
        let id1 = substrate
            .remember_batch(&[item(
                "neural code generator produces intermediate representation",
            )])
            .remove(0)
            .unwrap();
        let id2 = substrate
            .remember_batch(&[item("rustc borrow checker enforces lifetime invariants")])
            .remove(0)
            .unwrap();

        assert_eq!(id0, 0);
        assert_eq!(id1, 1);
        assert_eq!(id2, 2);

        // 2. Query before graph edge: lexical query "compiler llvm" only matches Record 0
        let hits_before = substrate.recall_expect(&RecallQuery {
            query: "compiler llvm".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        });
        assert_eq!(hits_before.len(), 1);
        assert_eq!(hits_before[0].id, 0);

        // 3. Add Causal Execution Provenance edge: Parent 0 -> Child 1
        substrate
            .add_relation(field::RelationKind::Causal, 0, 1, 0.9)
            .unwrap();

        // 4. Query after causal edge: Record 1 is pulled in via graph propagation!
        let hits_after = substrate.recall_expect(&RecallQuery {
            query: "compiler llvm".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        });
        assert_eq!(hits_after.len(), 2);
        assert_eq!(hits_after[0].id, 0);
        assert_eq!(hits_after[1].id, 1);
        assert!(hits_after[1].score > 0.0);

        // 5. Verify Hebbian co-activation tracking
        let coactivations = substrate.hebbian_coactivations();
        assert_eq!(coactivations.get(&(0, 1)).copied(), Some(1));

        drop(substrate);
        let _ = std::fs::remove_dir_all(&path);
    }

    /// Session registry must span the whole store, not just the most recent
    /// records: an early session must still be listed after 600 later writes.
    #[test]
    fn session_list_scans_beyond_recent_window() {
        let mut substrate =
            Substrate::open(&temp_store("session-list-window"), None, default_view())
                .expect("open");
        substrate
            .session_record("ancient-session", "agent", "note", "early record")
            .unwrap();
        let filler: Vec<RememberItem> = (0..600)
            .map(|i| item(&format!("filler record {i}")))
            .collect();
        substrate.remember_batch(&filler);

        let sessions = substrate.session_list().unwrap();
        assert!(
            sessions.contains(&"ancient-session".to_string()),
            "early session must survive beyond the recent-record window: {sessions:?}"
        );
    }

    /// Read-only snapshot recall with projection: a query-vector cache miss must
    /// not attempt a derived write (embed in memory, skip the cache put).
    #[test]
    fn readonly_projection_recall_skips_cache_writes() {
        let dir = crate::embed_cache_dir_or_panic();
        let path = temp_store("readonly-projection");
        let mut substrate = Substrate::open(&path, None, default_view()).expect("open");
        substrate
            .set_projection_enabled(true, Some(&dir))
            .expect("projection loads");
        substrate.remember_batch(&[item("north bay loading area")]);
        drop(substrate);

        let mut ro = Substrate::open_readonly(&path, None, default_view()).expect("ro open");
        ro.set_projection_enabled(true, Some(&dir))
            .expect("projection loads readonly");
        let hits = ro.recall_expect(&RecallQuery {
            query: "north bay loading area".into(),
            limit: 10,
            candidate_limit: 100,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        });
        assert!(!hits.is_empty(), "read-only projection recall must answer");

        let _ = std::fs::remove_dir_all(&path);
    }
}
