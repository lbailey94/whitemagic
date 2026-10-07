//! Durable store (LMDB): records, relations, postings, counters.
//!
//! Storage is infrastructure — the dependency manifest allows the same LMDB
//! crate family as the control for storage-physics parity. No Gen2 behavior is
//! imported: postings are built from this crate's own generic tokenizer.
//!
//! Domain values travel as opaque wire bytes and are reconstructed only through
//! the crate-internal `EvidenceRecord::from_wire` — there is no public
//! construction or re-label path (Closure 2).

use std::borrow::Cow;
#[cfg(test)]
use std::cell::Cell;
use std::collections::{HashMap, HashSet};
use std::fmt;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use lmdb::{Cursor, Database, Transaction};
use zeroize::Zeroizing;

use crate::at_rest::{
    self, AtRestConfig, AtRestError, AtRestState, AtRestStatus, MigrationLedger, RECORD_SCOPE,
};
use crate::capability::CommitCapability;
use crate::evidence::{Class, Domain, EvidenceRecord, RecordStatus};
use crate::field::{Relation, RelationKind, RelationState};
use crate::intake::{
    COMMIT_RECEIPT_VERSION, CommitDisposition, CommitOutcome, CommitReceipt,
    FEASIBILITY_CAPABILITY_CLASS, INTAKE_SCOPE, IntakeError, IntakeKind, IntakeRequest,
    OperationId, REMEMBER_OPERATION_KIND, STORE_FORMAT_VERSION,
};
use crate::pulse_compiler::AuthorizationSnapshot;
use crate::sweep::{
    CommitReceiptEnvelopeV5, MAX_WIRE_RECORD_OVERHEAD, SWEEP_OPERATION_KIND, SWEEP_RECEIPT_VERSION,
    SWEEP_SCOPE, SweepEffect, SweepError, SweepLimits, SweepObserved, SweepOutcome, SweepReceipt,
    SweepRequest, decode_receipt_envelope, decode_validated_plan, encode_receipt_envelope,
    outcomes_digest, sweep_authority_digest,
};
use crate::sweep_planner::SweepPreflightData;
use sha2::{Digest, Sha256};

const DB_RECORDS: &str = "records";
const DB_RELATIONS: &str = "relations";
const DB_POSTINGS: &str = "postings";
const DB_EMBEDDINGS: &str = "embeddings";
const DB_EMBED_CACHE: &str = "embed_cache";
const DB_NULLIFIERS: &str = "nullifiers";
const DB_RECEIPTS: &str = "receipts";
const META_INITIALIZING: &[u8] = b"__init__";
const META_FORMAT_VERSION: &[u8] = b"__ver__";
const META_REALM_ID: &[u8] = b"__rlm__";
const META_EPOCH: &[u8] = b"__epc__";
const META_NEXT_RECORD: &[u8] = b"__nrid_";
const META_NEXT_RELATION: &str = "next_relation_id";
const META_SWEEP: &str = "sweep";
/// Monotonic relation-write stamp: bumped in the same transaction as every
/// relation write. The recall adjacency cache uses it as a cross-process
/// change signal (lmdb 0.8 exposes no `Env::info()`/`last_txnid`).
const META_RELATION_VIEW: &[u8] = b"__rvw__";
/// Postings-index tokenizer/format marker used by the duplicate-probe fast path.
const META_IDENTITY_INDEX: &[u8] = b"__iidx__";

/// Unforgeable-to-ops witness that a snapshot came from the authoritative Store.
/// The tuple field is private: only this module can construct it.
pub(crate) struct StoreAuthoritySeal(());

#[derive(Debug)]
pub enum StoreError {
    Lmdb(lmdb::Error),
    Encode(rmp_serde::encode::Error),
    Decode(rmp_serde::decode::Error),
    Msg(String),
    Io(std::io::Error),
    IncompatibleFormat,
    UnsupportedFutureVersion,
    CorruptVersionHeader,
    InterruptedInitialization,
    CounterOverflow { key: String },
    Intake(IntakeError),
    Sweep(SweepError),
    AtRest(AtRestError),
}

impl fmt::Display for StoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            StoreError::Lmdb(e) => write!(f, "lmdb: {e}"),
            StoreError::Encode(e) => write!(f, "encode: {e}"),
            StoreError::Decode(e) => write!(f, "decode: {e}"),
            StoreError::Msg(m) => write!(f, "store: {m}"),
            StoreError::Io(e) => write!(f, "io: {e}"),
            StoreError::IncompatibleFormat => write!(f, "incompatible store format"),
            StoreError::UnsupportedFutureVersion => write!(f, "unsupported future store format"),
            StoreError::CorruptVersionHeader => write!(f, "corrupt store format header"),
            StoreError::InterruptedInitialization => write!(f, "interrupted store initialization"),
            StoreError::CounterOverflow { key } => write!(f, "counter overflow: {key}"),
            StoreError::Intake(e) => write!(f, "intake: {e}"),
            StoreError::Sweep(e) => write!(f, "sweep: {e}"),
            StoreError::AtRest(e) => write!(f, "at-rest: {e}"),
        }
    }
}

impl std::error::Error for StoreError {}

impl From<lmdb::Error> for StoreError {
    fn from(e: lmdb::Error) -> Self {
        StoreError::Lmdb(e)
    }
}
impl From<std::io::Error> for StoreError {
    fn from(e: std::io::Error) -> Self {
        StoreError::Io(e)
    }
}
impl From<rmp_serde::encode::Error> for StoreError {
    fn from(e: rmp_serde::encode::Error) -> Self {
        StoreError::Encode(e)
    }
}
impl From<rmp_serde::decode::Error> for StoreError {
    fn from(e: rmp_serde::decode::Error) -> Self {
        StoreError::Decode(e)
    }
}
impl From<IntakeError> for StoreError {
    fn from(e: IntakeError) -> Self {
        Self::Intake(e)
    }
}
impl From<SweepError> for StoreError {
    fn from(e: SweepError) -> Self {
        Self::Sweep(e)
    }
}
impl From<AtRestError> for StoreError {
    fn from(e: AtRestError) -> Self {
        Self::AtRest(e)
    }
}

#[derive(serde::Serialize, serde::Deserialize)]
struct WireRecord {
    id: u64,
    domain: u8,
    class: u8,
    content: String,
    source: String,
    confidence: f32,
    status: u8,
    created_at: u64,
}

fn domain_to_u8(d: Domain) -> u8 {
    match d {
        Domain::World => 0,
        Domain::System => 1,
        Domain::Simulated => 2,
        Domain::Reported => 3,
    }
}
fn domain_from_u8(v: u8) -> Result<Domain, StoreError> {
    match v {
        0 => Ok(Domain::World),
        1 => Ok(Domain::System),
        2 => Ok(Domain::Simulated),
        3 => Ok(Domain::Reported),
        other => Err(StoreError::Msg(format!("invalid wire domain tag: {other}"))),
    }
}
fn class_to_u8(c: Class) -> u8 {
    match c {
        Class::Evidence => 0,
        Class::Belief => 1,
        Class::Speculation => 2,
    }
}
fn class_from_u8(v: u8) -> Result<Class, StoreError> {
    match v {
        0 => Ok(Class::Evidence),
        1 => Ok(Class::Belief),
        2 => Ok(Class::Speculation),
        other => Err(StoreError::Msg(format!("invalid wire class tag: {other}"))),
    }
}
fn status_to_u8(s: RecordStatus) -> u8 {
    match s {
        RecordStatus::Transient => 0,
        RecordStatus::Candidate => 1,
        RecordStatus::Persistent => 2,
        RecordStatus::Cold => 3,
    }
}
fn status_from_u8(v: u8) -> Result<RecordStatus, StoreError> {
    match v {
        0 => Ok(RecordStatus::Transient),
        1 => Ok(RecordStatus::Candidate),
        2 => Ok(RecordStatus::Persistent),
        3 => Ok(RecordStatus::Cold),
        other => Err(StoreError::Msg(format!("invalid wire status tag: {other}"))),
    }
}

/// Durable store handle. Not thread-safe by design: one writer per store.
///
/// Canonical writes are crate-internal and capability-gated
/// ([`crate::store::Store::commit_intake`], [`crate::store::Store::commit_sweep`]);
/// there is no public raw writer (Evil Gana attempt 2).
///
/// ```compile_fail
/// // Evil Gana attempt 2 (executable): no public raw mutation method exists.
/// use wm_gen3_core::store::Store;
/// fn raw_write(store: &Store) { store.put_relation(); }
/// ```
pub struct Store {
    env: lmdb::Environment,
    path: PathBuf,
    records: Database,
    relations: Database,
    postings: Database,
    embeddings: Database,
    embed_cache: Database,
    nullifiers: Database,
    receipts: Database,
    default: Database,
    readonly: bool,
    /// Unlocked at-rest keyring state (mode B/C writable opens only).
    at_rest: Option<AtRestState>,
    /// Keyring DBI handle (present iff [`Self::at_rest`] is).
    keyring: Option<Database>,
    /// Lazily derived relation adjacency for recall, tagged with the relation
    /// stamp it was built from. Process-local only (never persisted); rebuilt
    /// when the store's relation stamp moves (same-handle writes invalidate,
    /// other processes' writes are observed through the stamp).
    cached_relations_view: Mutex<Option<(u64, Arc<RelationsView>)>>,
    #[cfg(test)]
    fail_after_stage: Cell<Option<u8>>,
    /// Structural debug counter: stored-record decodes performed by this handle.
    #[cfg(test)]
    decode_count: Cell<u64>,
}

/// Derived in-memory relation adjacency consumed by recall (supersedes pairs,
/// support sources, and weighted graph edges). Rebuilt lazily and dropped on
/// relation writes; equality with the recall-side full scan is a test invariant.
#[derive(Debug, Default)]
pub(crate) struct RelationsView {
    pub(crate) superseded_by: HashMap<u64, u64>,
    pub(crate) sources: HashSet<u64>,
    pub(crate) graph_edges: HashMap<u64, Vec<(u64, f32)>>,
}

impl RelationsView {
    /// Exact old full-scan derivation: cold relations skipped, supersedes pairs
    /// keyed by destination (id order, later wins), associates/causal edges
    /// expanded both ways (causal reverse weighted ×0.8).
    fn derive(relations: &[Relation]) -> Self {
        let mut view = Self::default();
        for r in relations {
            if r.state() == RelationState::Cold {
                continue;
            }
            match r.kind() {
                RelationKind::Supersedes => {
                    view.superseded_by.insert(r.dst(), r.id());
                    view.sources.insert(r.src());
                }
                RelationKind::Associates => {
                    view.graph_edges
                        .entry(r.src())
                        .or_default()
                        .push((r.dst(), r.weight()));
                    view.graph_edges
                        .entry(r.dst())
                        .or_default()
                        .push((r.src(), r.weight()));
                }
                RelationKind::Causal => {
                    view.graph_edges
                        .entry(r.src())
                        .or_default()
                        .push((r.dst(), r.weight()));
                    view.graph_edges
                        .entry(r.dst())
                        .or_default()
                        .push((r.src(), r.weight() * 0.8));
                }
            }
        }
        view
    }
}

/// Growth metrics for the LMDB environment backing a store: on-disk data
/// bytes, the configured map ceiling, and the used fraction. Additive,
/// read-only snapshot for the growth ledger written by `Substrate::finish`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct StoreMapStats {
    pub data_bytes: u64,
    pub map_bytes: u64,
    pub used_fraction: f64,
}

/// Outcome of a bounded seal-on-rewrite migration pass (Q39 slice B).
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct AtRestMigrationReport {
    /// Whether the pass counted without writing anything.
    pub dry_run: bool,
    /// Records scanned in the `records` keyspace.
    pub scanned: u64,
    /// Plaintext records sealed by this pass.
    pub sealed: u64,
    /// Records that already carried the WMEN envelope.
    pub already_sealed: u64,
    /// Values skipped as undecodable non-records or non-8-byte keys.
    pub skipped: u64,
    /// Whether the keyspace is now fully scanned (ledger `done`).
    pub done: bool,
}

fn bytes_u64(v: u64) -> [u8; 8] {
    v.to_be_bytes()
}

fn record_key_id(key: &[u8]) -> Result<u64, StoreError> {
    key.try_into()
        .map(u64::from_be_bytes)
        .map_err(|_| StoreError::Msg(format!("record key is {} bytes, expected 8", key.len())))
}

fn decode_record(bytes: &[u8]) -> Result<EvidenceRecord, StoreError> {
    let w: WireRecord = rmp_serde::from_slice(bytes)?;
    Ok(EvidenceRecord::from_wire(
        w.id,
        domain_from_u8(w.domain)?,
        class_from_u8(w.class)?,
        w.content,
        w.source,
        w.confidence,
        status_from_u8(w.status)?,
        w.created_at,
    ))
}

fn configured_map_size() -> usize {
    if let Ok(gb_str) = std::env::var("WM_MAP_SIZE_GB") {
        if let Ok(gb) = gb_str.parse::<usize>() {
            return gb << 30;
        }
    }
    // Default 16 GiB (up from 1 GiB), providing ample virtual headroom on 64-bit platforms
    16 << 30
}

impl Store {
    /// Open with the environment's at-rest configuration
    /// ([`AtRestConfig::from_env`]: `WM_AT_REST_MODE`, default `off`).
    pub fn open(path: &Path) -> Result<Self, StoreError> {
        Self::open_with_at_rest(path, &AtRestConfig::from_env()?)
    }

    /// Open with an explicit at-rest configuration (`off` | `keyfile` |
    /// `passphrase`). `off` is a provable no-op: no keyring DBI, no key file,
    /// records byte-identical to the pre-at-rest codec.
    pub fn open_with_at_rest(path: &Path, config: &AtRestConfig) -> Result<Self, StoreError> {
        let fresh = match std::fs::read_dir(path) {
            Ok(mut entries) => entries.next().is_none(),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                std::fs::create_dir_all(path)?;
                true
            }
            Err(e) => return Err(e.into()),
        };
        if !fresh {
            // Inspection is read-only before a normal handle is ever opened.  In
            // particular, an unknown legacy environment cannot acquire new DBIs.
            Self::inspect_existing(path)?;
        }
        let mut builder = lmdb::Environment::new();
        builder.set_max_dbs(16).set_map_size(configured_map_size());
        let env = builder.open_with_permissions(path, 0o600)?;
        if fresh {
            Self::initialize_fresh(&env)?;
        }
        let mut store = Self::from_env(env, path, false)?;
        store.install_at_rest(config)?;
        Ok(store)
    }

    /// Snapshot-readonly open (`MDB_RDONLY | MDB_NOLOCK`, the 9.1.8 inspection pattern):
    /// no lock-file interaction; callers must use a quiescent immutable snapshot.
    pub fn open_readonly(path: &Path) -> Result<Self, StoreError> {
        let mut builder = lmdb::Environment::new();
        builder
            .set_max_dbs(16)
            .set_map_size(configured_map_size())
            .set_flags(lmdb::EnvironmentFlags::READ_ONLY | lmdb::EnvironmentFlags::NO_LOCK);
        let env = builder.open_with_permissions(path, 0o600)?;
        Self::from_env(env, path, true)
    }

    fn inspect_existing(path: &Path) -> Result<(), StoreError> {
        let mut builder = lmdb::Environment::new();
        builder
            .set_max_dbs(16)
            .set_map_size(configured_map_size())
            .set_flags(lmdb::EnvironmentFlags::READ_ONLY);
        let env = builder.open_with_permissions(path, 0o600)?;
        Self::validate_header(&env)
    }

    fn initialize_fresh(env: &lmdb::Environment) -> Result<(), StoreError> {
        let default = env.open_db(None)?;
        {
            let mut txn = env.begin_rw_txn()?;
            // Freshness must be rechecked while holding LMDB's single writer lock.
            let has_entries = {
                let mut cursor = txn.open_ro_cursor(default)?;
                cursor.iter().next().is_some()
            };
            if has_entries {
                return Err(StoreError::InterruptedInitialization);
            }
            txn.put(
                default,
                &META_INITIALIZING,
                &[1],
                lmdb::WriteFlags::NO_OVERWRITE,
            )?;
            txn.commit()?;
        }
        // lmdb 0.8 makes transaction-local DB creation unsafe. These safe calls
        // deliberately leave an interruption-detectable state; Slice 1 never resumes it.
        for name in [
            DB_RECORDS,
            DB_RELATIONS,
            DB_POSTINGS,
            DB_EMBEDDINGS,
            DB_EMBED_CACHE,
            DB_NULLIFIERS,
            DB_RECEIPTS,
        ] {
            env.create_db(Some(name), lmdb::DatabaseFlags::empty())?;
        }
        let mut realm = [0u8; 16];
        getrandom::fill(&mut realm)
            .map_err(|e| StoreError::Msg(format!("realm randomness: {e}")))?;
        let mut txn = env.begin_rw_txn()?;
        if txn.get(default, &META_INITIALIZING) != Ok(&[1][..]) {
            return Err(StoreError::InterruptedInitialization);
        }
        txn.put(
            default,
            &META_REALM_ID,
            &realm,
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        txn.put(
            default,
            &META_EPOCH,
            &bytes_u64(0),
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        txn.put(
            default,
            &META_NEXT_RECORD,
            &bytes_u64(0),
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        txn.put(
            default,
            &META_NEXT_RELATION,
            &bytes_u64(0),
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        txn.put(
            default,
            &META_SWEEP,
            &bytes_u64(0),
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        txn.put(
            default,
            &META_FORMAT_VERSION,
            &STORE_FORMAT_VERSION.to_be_bytes(),
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        txn.del(default, &META_INITIALIZING, None)?;
        txn.commit()?;
        Ok(())
    }

    fn validate_header(env: &lmdb::Environment) -> Result<(), StoreError> {
        let default = env.open_db(None)?;
        let txn = env.begin_ro_txn()?;
        match txn.get(default, &META_INITIALIZING) {
            Ok(_) => return Err(StoreError::InterruptedInitialization),
            Err(lmdb::Error::NotFound) => {}
            Err(e) => return Err(e.into()),
        }
        let version = match txn.get(default, &META_FORMAT_VERSION) {
            Ok(bytes) if bytes.len() == 4 => u32::from_be_bytes(
                bytes
                    .try_into()
                    .map_err(|_| StoreError::CorruptVersionHeader)?,
            ),
            Ok(_) => return Err(StoreError::CorruptVersionHeader),
            Err(lmdb::Error::NotFound) => return Err(StoreError::IncompatibleFormat),
            Err(e) => return Err(e.into()),
        };
        if version < STORE_FORMAT_VERSION {
            return Err(StoreError::IncompatibleFormat);
        }
        if version > STORE_FORMAT_VERSION {
            return Err(StoreError::UnsupportedFutureVersion);
        }
        match txn.get(default, &META_REALM_ID) {
            Ok(v) if v.len() == 16 => {}
            _ => return Err(StoreError::CorruptVersionHeader),
        }
        for key in [
            META_EPOCH,
            META_NEXT_RECORD,
            META_NEXT_RELATION.as_bytes(),
            META_SWEEP.as_bytes(),
        ] {
            match txn.get(default, &key) {
                Ok(v) if v.len() == 8 => {}
                _ => return Err(StoreError::CorruptVersionHeader),
            }
        }
        drop(txn);
        for name in [
            DB_RECORDS,
            DB_RELATIONS,
            DB_POSTINGS,
            DB_EMBEDDINGS,
            DB_EMBED_CACHE,
            DB_NULLIFIERS,
            DB_RECEIPTS,
        ] {
            env.open_db(Some(name))
                .map_err(|_| StoreError::InterruptedInitialization)?;
        }
        Ok(())
    }

    fn from_env(env: lmdb::Environment, path: &Path, readonly: bool) -> Result<Self, StoreError> {
        Self::validate_header(&env)?;
        // Handles are opened once, outside any transaction: `open_db` starts an
        // internal read transaction and must not run while another txn on this
        // thread is live (MDB_BAD_RSLOT).
        let records = env.open_db(Some(DB_RECORDS))?;
        let relations = env.open_db(Some(DB_RELATIONS))?;
        let postings = env.open_db(Some(DB_POSTINGS))?;
        let embeddings = env.open_db(Some(DB_EMBEDDINGS))?;
        let embed_cache = env.open_db(Some(DB_EMBED_CACHE))?;
        let nullifiers = env.open_db(Some(DB_NULLIFIERS))?;
        let receipts = env.open_db(Some(DB_RECEIPTS))?;
        let default = env.open_db(None)?;
        Ok(Self {
            env,
            path: path.to_path_buf(),
            records,
            relations,
            postings,
            embeddings,
            embed_cache,
            nullifiers,
            receipts,
            default,
            readonly,
            at_rest: None,
            keyring: None,
            cached_relations_view: Mutex::new(None),
            #[cfg(test)]
            fail_after_stage: Cell::new(None),
            #[cfg(test)]
            decode_count: Cell::new(0),
        })
    }

    /// Wire the at-rest keyring into this store (writable opens only).
    ///
    /// `off` + absent keyring is a no-op; `off` + present keyring refuses
    /// (split-brain guard); B/C initialize on first use and unlock on later
    /// opens. Read-only handles never call this: they disclose status via
    /// [`Self::at_rest_status`] without resolving the root key.
    fn install_at_rest(&mut self, config: &AtRestConfig) -> Result<(), StoreError> {
        let (keyring, state) = at_rest::open_at_rest(&self.env, &self.path, config)?;
        self.keyring = keyring;
        self.at_rest = state;
        Ok(())
    }

    /// Unlocked at-rest state, when this writable open resolved the keyring.
    #[must_use]
    pub const fn at_rest_state(&self) -> Option<&AtRestState> {
        self.at_rest.as_ref()
    }

    /// Read-only at-rest disclosure (meta + counts, never the key bytes).
    /// Works on read-only inspection handles too.
    #[must_use]
    pub fn at_rest_status(&self) -> AtRestStatus {
        if let Some(state) = &self.at_rest {
            return AtRestStatus::Present(state.status());
        }
        match at_rest::open_keyring_optional(&self.env) {
            Ok(Some(db)) => at_rest::read_status(&self.env, db, &self.path),
            Ok(None) => AtRestStatus::Absent,
            Err(e) => AtRestStatus::Malformed {
                reason: e.to_string(),
            },
        }
    }

    /// Read the `migration:v1` ledger from the keyring DBI, when present.
    pub fn at_rest_migration_ledger(&self) -> Result<Option<MigrationLedger>, StoreError> {
        match at_rest::open_keyring_optional(&self.env)? {
            Some(db) => Ok(Some(at_rest::read_migration_ledger(&self.env, db)?)),
            None => Ok(None),
        }
    }

    /// DEK sealing this store's record bodies, when mode B/C is unlocked.
    fn record_dek(&self) -> Option<&[u8; at_rest::AT_REST_KEY_LEN]> {
        self.at_rest
            .as_ref()
            .and_then(|state| state.galaxy_dek(RECORD_SCOPE))
    }

    /// Encode a record body for storage: the plaintext wire bytes unchanged
    /// in `off` mode, sealed under the record-scope DEK otherwise.
    fn encode_stored_record<'a>(
        &self,
        id: u64,
        version: u64,
        plaintext: &'a [u8],
    ) -> Result<Cow<'a, [u8]>, StoreError> {
        match self.record_dek() {
            None => Ok(Cow::Borrowed(plaintext)),
            Some(dek) => at_rest::seal_record(
                plaintext,
                dek,
                RECORD_SCOPE,
                &at_rest::record_identity(id),
                version,
            )
            .map(Cow::Owned)
            .map_err(|e| StoreError::AtRest(AtRestError::msg(e))),
        }
    }

    /// Open a stored record body's plaintext bytes (sealed values fail closed
    /// without their key).
    fn open_stored_record(&self, id: u64, stored: &[u8]) -> Result<Zeroizing<Vec<u8>>, StoreError> {
        if !at_rest::is_sealed_record(stored) {
            return Ok(Zeroizing::new(stored.to_vec()));
        }
        let Some(dek) = self.record_dek() else {
            return Err(StoreError::AtRest(AtRestError::msg(format!(
                "sealed record {id} but no at-rest key is loaded — open the store with its \
                 WM_AT_REST_MODE/key source (a sealed value without its key fails closed)"
            ))));
        };
        at_rest::open_record(stored, dek, RECORD_SCOPE, &at_rest::record_identity(id))
            .map_err(|e| StoreError::AtRest(AtRestError::msg(format!("at-rest open failed: {e}"))))
    }

    /// Decode a stored record value: sealed values open under the record-scope
    /// DEK (failing closed without one), plaintext values follow the legacy
    /// wire codec.
    fn decode_stored_record(&self, id: u64, stored: &[u8]) -> Result<EvidenceRecord, StoreError> {
        #[cfg(test)]
        self.decode_count
            .set(self.decode_count.get().saturating_add(1));
        if at_rest::is_sealed_record(stored) {
            let opened = self.open_stored_record(id, stored)?;
            decode_record(&opened)
        } else {
            decode_record(stored)
        }
    }

    /// Seal-on-rewrite migration for pre-existing plaintext records (Q39
    /// slice B). Scans the `records` keyspace, sealing every plaintext body
    /// under the record-scope DEK in bounded batches and journaling progress
    /// in the `migration:v1` ledger row.
    ///
    /// Idempotent: already-sealed values are skipped, a completed pass
    /// (`done`) short-circuits without touching the ledger, and a crash
    /// between a batch commit and the ledger write only repeats bounded
    /// work. `dry_run` counts without writing records or ledger.
    pub fn migrate_at_rest_records(
        &self,
        batch_size: usize,
        dry_run: bool,
    ) -> Result<AtRestMigrationReport, StoreError> {
        self.ensure_writable()?;
        if self.at_rest.is_none() {
            return Err(StoreError::AtRest(AtRestError::msg(
                "at-rest migration requires an unlocked mode B/C store",
            )));
        }
        let keyring = self.keyring.ok_or_else(|| {
            StoreError::AtRest(AtRestError::msg("at-rest keyring DBI is not open"))
        })?;
        let mut report = AtRestMigrationReport {
            dry_run,
            ..Default::default()
        };
        let mut ledger = at_rest::read_migration_ledger(&self.env, keyring)?;
        if ledger
            .galaxies
            .get(RECORD_SCOPE)
            .is_some_and(|state| state.done)
        {
            report.done = true;
            return Ok(report);
        }

        // Pass 1: collect ids of unsealed records (bounded memory — values
        // are re-read per batch below).
        let mut pending: Vec<u64> = Vec::new();
        {
            let txn = self.env.begin_ro_txn()?;
            let mut cursor = txn.open_ro_cursor(self.records)?;
            for (key, value) in cursor.iter() {
                report.scanned += 1;
                if at_rest::is_sealed_record(value) {
                    report.already_sealed += 1;
                    continue;
                }
                match record_key_id(key) {
                    Ok(id) => pending.push(id),
                    Err(_) => report.skipped += 1,
                }
            }
        }
        report.sealed = pending.len() as u64;
        if dry_run {
            report.done = pending.is_empty();
            return Ok(report);
        }

        let prior = ledger
            .galaxies
            .get(RECORD_SCOPE)
            .map_or(0, |state| state.encrypted);
        let mut sealed_total = prior;
        let mut sealed_now: u64 = 0;
        for chunk in pending.chunks(batch_size.max(1)) {
            let mut txn = self.env.begin_rw_txn()?;
            for id in chunk {
                let value = match txn.get(self.records, &bytes_u64(*id)) {
                    Ok(value) => value.to_vec(),
                    Err(lmdb::Error::NotFound) => continue,
                    Err(e) => return Err(e.into()),
                };
                if at_rest::is_sealed_record(&value) {
                    continue;
                }
                let record = match decode_record(&value) {
                    Ok(record) => record,
                    Err(_) => {
                        report.skipped += 1;
                        continue;
                    }
                };
                let sealed = self.encode_stored_record(*id, record.created_at(), &value)?;
                txn.put(
                    self.records,
                    &bytes_u64(*id),
                    &sealed,
                    lmdb::WriteFlags::empty(),
                )?;
                sealed_now += 1;
            }
            txn.commit()?;
            sealed_total = prior + sealed_now;
            ledger.galaxies.insert(
                RECORD_SCOPE.to_string(),
                at_rest::MigrationGalaxyState {
                    encrypted: sealed_total,
                    cursor_hex: chunk
                        .last()
                        .map_or_else(String::new, |id| at_rest::hex_encode(&bytes_u64(*id))),
                    done: false,
                },
            );
            ledger.updated_at = chrono::Utc::now().to_rfc3339();
            at_rest::write_migration_ledger(&self.env, keyring, &ledger)?;
        }

        if let Some(state) = ledger.galaxies.get_mut(RECORD_SCOPE) {
            state.done = true;
            state.encrypted = sealed_total;
        } else {
            ledger.galaxies.insert(
                RECORD_SCOPE.to_string(),
                at_rest::MigrationGalaxyState {
                    encrypted: sealed_total,
                    cursor_hex: String::new(),
                    done: true,
                },
            );
        }
        ledger.updated_at = chrono::Utc::now().to_rfc3339();
        at_rest::write_migration_ledger(&self.env, keyring, &ledger)?;
        report.sealed = sealed_now;
        report.done = true;
        Ok(report)
    }

    #[must_use]
    pub fn is_readonly(&self) -> bool {
        self.readonly
    }

    pub fn realm_id(&self) -> Result<[u8; 16], StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let bytes = txn
            .get(self.default, &META_REALM_ID)
            .map_err(|_| StoreError::CorruptVersionHeader)?;
        bytes
            .try_into()
            .map_err(|_| StoreError::CorruptVersionHeader)
    }

    pub fn epoch(&self) -> Result<u64, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let bytes = txn
            .get(self.default, &META_EPOCH)
            .map_err(|_| StoreError::CorruptVersionHeader)?;
        Ok(u64::from_be_bytes(
            bytes
                .try_into()
                .map_err(|_| StoreError::CorruptVersionHeader)?,
        ))
    }

    /// Read the authority-relevant state together, with a private Store witness.
    pub(crate) fn authorization_snapshot(&self) -> Result<AuthorizationSnapshot, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let realm_id: [u8; 16] = txn
            .get(self.default, &META_REALM_ID)
            .map_err(|_| StoreError::CorruptVersionHeader)?
            .try_into()
            .map_err(|_| StoreError::CorruptVersionHeader)?;
        let epoch = u64::from_be_bytes(
            txn.get(self.default, &META_EPOCH)
                .map_err(|_| StoreError::CorruptVersionHeader)?
                .try_into()
                .map_err(|_| StoreError::CorruptVersionHeader)?,
        );
        Ok(AuthorizationSnapshot::from_store(
            realm_id,
            epoch,
            StoreAuthoritySeal(()),
        ))
    }

    pub(crate) fn lookup_intake_receipt(
        &self,
        request: &IntakeRequest,
    ) -> Result<Option<CommitReceipt>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let operation_id = request.operation_id();
        let key = operation_id.as_bytes();
        let receipt_bytes = match txn.get(self.receipts, key) {
            Ok(bytes) => bytes,
            Err(lmdb::Error::NotFound) => {
                match txn.get(self.nullifiers, key) {
                    Ok(_) => return Err(IntakeError::CorruptCommitState.into()),
                    Err(lmdb::Error::NotFound) => {}
                    Err(e) => return Err(e.into()),
                }
                return Ok(None);
            }
            Err(e) => return Err(e.into()),
        };
        let envelope =
            decode_receipt_envelope(receipt_bytes).map_err(|_| IntakeError::CorruptCommitState)?;
        let receipt = match envelope {
            CommitReceiptEnvelopeV5::IntakeV2(receipt) => receipt,
            CommitReceiptEnvelopeV5::SweepV1(_) => {
                return Err(SweepError::CrossKindConflict.into());
            }
        };
        let nullifier = txn
            .get(self.nullifiers, key)
            .map_err(|_| IntakeError::CorruptCommitState)?;
        if nullifier != receipt.manifest_digest || receipt.operation_id != request.operation_id() {
            return Err(IntakeError::CorruptCommitState.into());
        }
        self.validate_receipt_state(&txn, &receipt)?;
        if receipt.realm_id != *request.realm_id()
            || receipt.manifest_digest != request.digest()
            || receipt.authority != *request.authority()
        {
            return Err(IntakeError::IdempotencyConflict.into());
        }
        Ok(Some(receipt))
    }

    pub(crate) fn commit_intake(
        &self,
        capability: CommitCapability,
        request: &IntakeRequest,
        terms: &[String],
    ) -> Result<CommitOutcome, StoreError> {
        self.ensure_writable()?;
        if !request.authority().is_canonical() {
            return Err(IntakeError::InvalidAuthorityLabel.into());
        }
        let derived_terms = crate::field::tokenize(request.content());
        if derived_terms != terms {
            return Err(StoreError::Msg(
                "postings do not match bound intake payload".into(),
            ));
        }
        let digest = request.digest();
        let authority_digest = request.authority().digest();
        if capability.authorized_digest() != digest {
            return Err(IntakeError::UnauthorizedCapability { field: "digest" }.into());
        }
        if capability.scope() != INTAKE_SCOPE {
            return Err(IntakeError::UnauthorizedCapability { field: "scope" }.into());
        }
        if capability.feasibility_operation_id() != Some(request.operation_id()) {
            return Err(IntakeError::UnauthorizedCapability {
                field: "operation_id",
            }
            .into());
        }
        if capability.feasibility_realm_id() != Some(*request.realm_id()) {
            return Err(IntakeError::UnauthorizedCapability { field: "realm_id" }.into());
        }
        if capability.feasibility_expected_epoch() != Some(request.expected_epoch()) {
            return Err(IntakeError::UnauthorizedCapability {
                field: "expected_epoch",
            }
            .into());
        }
        if capability.feasibility_authority_digest() != Some(authority_digest) {
            return Err(IntakeError::UnauthorizedCapability {
                field: "authority_digest",
            }
            .into());
        }
        if capability.feasibility_operation_kind() != Some(REMEMBER_OPERATION_KIND) {
            return Err(IntakeError::UnauthorizedCapability {
                field: "operation_kind",
            }
            .into());
        }
        let operation_id = request.operation_id();
        let key = operation_id.as_bytes();
        let mut txn = self.env.begin_rw_txn()?;
        match txn.get(self.receipts, key) {
            Ok(bytes) => {
                let envelope =
                    decode_receipt_envelope(bytes).map_err(|_| IntakeError::CorruptCommitState)?;
                let receipt = match envelope {
                    CommitReceiptEnvelopeV5::IntakeV2(receipt) => receipt,
                    CommitReceiptEnvelopeV5::SweepV1(_) => {
                        return Err(SweepError::CrossKindConflict.into());
                    }
                };
                let nullifier = txn
                    .get(self.nullifiers, key)
                    .map_err(|_| IntakeError::CorruptCommitState)?;
                if nullifier != receipt.manifest_digest
                    || receipt.operation_id != request.operation_id()
                {
                    return Err(IntakeError::CorruptCommitState.into());
                }
                self.validate_receipt_state(&txn, &receipt)?;
                if receipt.realm_id != *request.realm_id()
                    || receipt.manifest_digest != digest
                    || receipt.authority != *request.authority()
                {
                    return Err(IntakeError::IdempotencyConflict.into());
                }
                return Ok(CommitOutcome {
                    receipt,
                    disposition: CommitDisposition::Replay,
                });
            }
            Err(lmdb::Error::NotFound) => {}
            Err(e) => return Err(e.into()),
        }
        match txn.get(self.nullifiers, key) {
            Ok(_) => return Err(IntakeError::CorruptCommitState.into()),
            Err(lmdb::Error::NotFound) => {}
            Err(e) => return Err(e.into()),
        }
        let realm: [u8; 16] = txn
            .get(self.default, &META_REALM_ID)
            .map_err(|_| StoreError::CorruptVersionHeader)?
            .try_into()
            .map_err(|_| StoreError::CorruptVersionHeader)?;
        if realm != *request.realm_id() {
            return Err(IntakeError::IdempotencyConflict.into());
        }
        let epoch = u64::from_be_bytes(
            txn.get(self.default, &META_EPOCH)
                .map_err(|_| StoreError::CorruptVersionHeader)?
                .try_into()
                .map_err(|_| StoreError::CorruptVersionHeader)?,
        );
        if epoch != request.expected_epoch() {
            return Err(IntakeError::StaleEpoch {
                expected: request.expected_epoch(),
                actual: epoch,
            }
            .into());
        }
        let id = u64::from_be_bytes(
            txn.get(self.default, &META_NEXT_RECORD)
                .map_err(|_| StoreError::CorruptVersionHeader)?
                .try_into()
                .map_err(|_| StoreError::CorruptVersionHeader)?,
        );
        let next_id = id.checked_add(1).ok_or(IntakeError::IdExhausted)?;
        let post_epoch = epoch.checked_add(1).ok_or(IntakeError::EpochExhausted)?;
        let domain = match request.kind() {
            IntakeKind::Reported => Domain::Reported,
            IntakeKind::System => Domain::System,
            IntakeKind::Simulated => Domain::Simulated,
        };
        let duplicate = if !derived_terms.is_empty() {
            let mut candidate_ids: Option<Vec<u64>> = None;
            for term in &derived_terms {
                match txn.get(self.postings, term) {
                    Ok(bytes) => {
                        let ids: Vec<u64> = rmp_serde::from_slice(bytes)?;
                        if ids.is_empty() {
                            candidate_ids = Some(Vec::new());
                            break;
                        }
                        if candidate_ids.as_ref().is_none_or(|c| ids.len() < c.len()) {
                            candidate_ids = Some(ids);
                        }
                    }
                    Err(lmdb::Error::NotFound) => {
                        candidate_ids = Some(Vec::new());
                        break;
                    }
                    Err(e) => return Err(e.into()),
                }
            }

            let mut found = false;
            if let Some(ids) = candidate_ids {
                for candidate_id in ids {
                    if let Ok(bytes) = txn.get(self.records, &bytes_u64(candidate_id)) {
                        let r = self.decode_stored_record(candidate_id, bytes)?;
                        if r.domain() == domain
                            && r.content() == request.content()
                            && r.source() == request.source()
                        {
                            found = true;
                            break;
                        }
                    }
                }
            }
            found
        } else {
            let mut cursor = txn.open_ro_cursor(self.records)?;
            let mut found = false;
            for (key, bytes) in cursor.iter() {
                let r = self.decode_stored_record(record_key_id(key)?, bytes)?;
                if r.domain() == domain
                    && r.content() == request.content()
                    && r.source() == request.source()
                {
                    found = true;
                    break;
                }
            }
            found
        };
        if duplicate {
            return Err(StoreError::Msg("duplicate_exact".into()));
        }
        let record = EvidenceRecord::from_wire(
            id,
            domain,
            Class::Evidence,
            request.content().to_string(),
            request.source().to_string(),
            1.0,
            RecordStatus::Persistent,
            id,
        );
        let wire = rmp_serde::to_vec(&WireRecord {
            id,
            domain: domain_to_u8(domain),
            class: class_to_u8(Class::Evidence),
            content: request.content().to_string(),
            source: request.source().to_string(),
            confidence: 1.0,
            status: status_to_u8(RecordStatus::Persistent),
            created_at: id,
        })?;
        // The receipt digest binds the plaintext wire bytes in every mode; the
        // stored value is sealed under the record-scope DEK when mode B/C.
        let record_digest: [u8; 32] = Sha256::digest(&wire).into();
        let stored = self.encode_stored_record(id, record.created_at(), &wire)?;
        txn.put(
            self.records,
            &bytes_u64(id),
            &stored,
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        self.fail_after(1)?;
        let mut posting_hash = Sha256::new();
        posting_hash.update(b"wm.gen3.postings.v1");
        posting_hash.update((derived_terms.len() as u64).to_be_bytes());
        for term in &derived_terms {
            let mut ids: Vec<u64> = match txn.get(self.postings, term) {
                Ok(bytes) => rmp_serde::from_slice(bytes)?,
                Err(lmdb::Error::NotFound) => Vec::new(),
                Err(e) => return Err(e.into()),
            };
            if !ids.contains(&id) {
                ids.push(id);
            }
            let encoded = rmp_serde::to_vec(&ids)?;
            txn.put(self.postings, term, &encoded, lmdb::WriteFlags::empty())?;
            posting_hash.update((term.len() as u64).to_be_bytes());
            posting_hash.update(term.as_bytes());
            posting_hash.update((encoded.len() as u64).to_be_bytes());
            posting_hash.update(&encoded);
        }
        let postings_digest: [u8; 32] = posting_hash.finalize().into();
        self.fail_after(2)?;
        let receipt = CommitReceipt {
            version: COMMIT_RECEIPT_VERSION,
            realm_id: realm,
            operation_id: request.operation_id(),
            manifest_digest: digest,
            authority: request.authority().clone(),
            capability_class: FEASIBILITY_CAPABILITY_CLASS,
            compiler_scope: capability.scope().to_string(),
            authority_digest,
            operation_kind: REMEMBER_OPERATION_KIND,
            target_table: 1,
            pre_epoch: epoch,
            post_epoch,
            record_id: record.id(),
            created_at: id,
            record_digest,
            postings_digest,
            vector_effect: 0,
            committed: true,
        };
        let receipt_bytes =
            encode_receipt_envelope(&CommitReceiptEnvelopeV5::IntakeV2(receipt.clone()))?;
        txn.put(
            self.default,
            &META_NEXT_RECORD,
            &bytes_u64(next_id),
            lmdb::WriteFlags::empty(),
        )?;
        txn.put(
            self.default,
            &META_EPOCH,
            &bytes_u64(post_epoch),
            lmdb::WriteFlags::empty(),
        )?;
        self.fail_after(3)?;
        txn.put(
            self.nullifiers,
            key,
            &digest,
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        self.fail_after(4)?;
        txn.put(
            self.receipts,
            key,
            &receipt_bytes,
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        self.fail_after(5)?;
        txn.commit()?;
        Ok(CommitOutcome {
            receipt,
            disposition: CommitDisposition::Committed,
        })
    }

    fn validate_receipt_state<T: Transaction>(
        &self,
        txn: &T,
        receipt: &CommitReceipt,
    ) -> Result<(), StoreError> {
        let realm: [u8; 16] = txn
            .get(self.default, &META_REALM_ID)
            .map_err(|_| StoreError::CorruptVersionHeader)?
            .try_into()
            .map_err(|_| StoreError::CorruptVersionHeader)?;
        let authority_digest = receipt.authority.digest();
        if receipt.version != COMMIT_RECEIPT_VERSION
            || !receipt.committed
            || receipt.vector_effect != 0
            || receipt.capability_class != FEASIBILITY_CAPABILITY_CLASS
            || receipt.compiler_scope != INTAKE_SCOPE
            || receipt.authority_digest != authority_digest
            || receipt.operation_kind != REMEMBER_OPERATION_KIND
            || receipt.target_table != 1
            || !receipt.authority.is_canonical()
            || receipt.created_at != receipt.record_id
            || receipt.post_epoch
                != receipt
                    .pre_epoch
                    .checked_add(1)
                    .ok_or(IntakeError::CorruptCommitState)?
            || receipt.realm_id != realm
        {
            return Err(IntakeError::CorruptCommitState.into());
        }
        let current_epoch = u64::from_be_bytes(
            txn.get(self.default, &META_EPOCH)
                .map_err(|_| StoreError::CorruptVersionHeader)?
                .try_into()
                .map_err(|_| StoreError::CorruptVersionHeader)?,
        );
        let next_record = u64::from_be_bytes(
            txn.get(self.default, &META_NEXT_RECORD)
                .map_err(|_| StoreError::CorruptVersionHeader)?
                .try_into()
                .map_err(|_| StoreError::CorruptVersionHeader)?,
        );
        if receipt.post_epoch > current_epoch || receipt.record_id >= next_record {
            return Err(IntakeError::CorruptCommitState.into());
        }
        let wire = txn
            .get(self.records, &bytes_u64(receipt.record_id))
            .map_err(|_| IntakeError::CorruptCommitState)?;
        let plaintext = self
            .open_stored_record(receipt.record_id, wire)
            .map_err(|_| IntakeError::CorruptCommitState)?;
        let record = decode_record(&plaintext).map_err(|_| IntakeError::CorruptCommitState)?;
        if record.id() != receipt.record_id || record.created_at() != receipt.created_at {
            return Err(IntakeError::CorruptCommitState.into());
        }
        let actual: [u8; 32] = Sha256::digest(&plaintext).into();
        if actual != receipt.record_digest {
            return Err(IntakeError::CorruptCommitState.into());
        }
        Ok(())
    }

    #[cfg(test)]
    fn fail_after(&self, stage: u8) -> Result<(), StoreError> {
        if self.fail_after_stage.get() == Some(stage) {
            return Err(StoreError::Msg(format!(
                "injected abort after stage {stage}"
            )));
        }
        Ok(())
    }
    #[cfg(not(test))]
    fn fail_after(&self, _stage: u8) -> Result<(), StoreError> {
        Ok(())
    }

    fn ensure_writable(&self) -> Result<(), StoreError> {
        if self.readonly {
            return Err(StoreError::Msg("store opened read-only".into()));
        }
        Ok(())
    }

    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Legacy direct counter allocation. Production sweeps allocate inside the
    /// authorized `commit_sweep` transaction; this path is test/reference only.
    #[cfg(any(test, feature = "operator", feature = "reference-models"))]
    fn bump_counter(&self, key: &str) -> Result<u64, StoreError> {
        self.ensure_writable()?;
        let mut txn = self.env.begin_rw_txn()?;
        let db = self.default;
        let bytes = match txn.get(db, &key) {
            Ok(bytes) if bytes.len() == 8 => bytes,
            Ok(_) | Err(lmdb::Error::NotFound) => return Err(StoreError::CorruptVersionHeader),
            Err(e) => return Err(e.into()),
        };
        let current = u64::from_be_bytes(
            bytes
                .try_into()
                .map_err(|_| StoreError::CorruptVersionHeader)?,
        );
        let next =
            bytes_u64(
                current
                    .checked_add(1)
                    .ok_or_else(|| StoreError::CounterOverflow {
                        key: key.to_string(),
                    })?,
            );
        txn.put(db, &key, &next, lmdb::WriteFlags::empty())?;
        txn.commit()?;
        Ok(current)
    }

    #[cfg(any(test, feature = "operator", feature = "reference-models"))]
    pub(crate) fn alloc_relation_id(&self) -> Result<u64, StoreError> {
        self.bump_counter(META_NEXT_RELATION)
    }
    #[cfg(any(test, feature = "reference-models"))]
    pub(crate) fn alloc_sweep(&self) -> Result<u64, StoreError> {
        self.bump_counter(META_SWEEP)
    }

    /// Append a record and update its term postings in one transaction
    /// (ingest performance: one read-write txn per record, not per term).
    #[cfg(any(test, feature = "reference-models"))]
    pub(crate) fn put_record_and_postings(
        &self,
        record: &EvidenceRecord,
        terms: &[String],
    ) -> Result<(), StoreError> {
        self.ensure_writable()?;
        let wire = WireRecord {
            id: record.id(),
            domain: domain_to_u8(record.domain()),
            class: class_to_u8(record.class()),
            content: record.content().to_string(),
            source: record.source().to_string(),
            confidence: record.confidence(),
            status: status_to_u8(record.status()),
            created_at: record.created_at(),
        };
        let key = bytes_u64(record.id());
        let value = rmp_serde::to_vec(&wire)?;
        let stored = self.encode_stored_record(record.id(), record.created_at(), &value)?;
        let mut txn = self.env.begin_rw_txn()?;
        if txn.get(self.records, &key).is_ok() {
            return Err(StoreError::Msg(format!(
                "record {} already exists",
                record.id()
            )));
        }
        txn.put(self.records, &key, &stored, lmdb::WriteFlags::empty())?;
        for term in terms {
            let mut ids: Vec<u64> = match txn.get(self.postings, &term) {
                Ok(bytes) => rmp_serde::from_slice(bytes)?,
                Err(lmdb::Error::NotFound) => Vec::new(),
                Err(e) => return Err(e.into()),
            };
            if !ids.contains(&record.id()) {
                ids.push(record.id());
                let posting = rmp_serde::to_vec(&ids)?;
                txn.put(self.postings, &term, &posting, lmdb::WriteFlags::empty())?;
            }
        }
        txn.commit()?;
        Ok(())
    }

    /// Reference/test bulk seeder for performance benches: writes records and
    /// postings in chunked write transactions (no per-record fsync). Production
    /// ingestion never uses this path.
    #[cfg(any(test, feature = "reference-models"))]
    pub(crate) fn seed_records_bulk(&self, records: &[EvidenceRecord]) -> Result<(), StoreError> {
        self.ensure_writable()?;
        let mut next_id = 0u64;
        for chunk in records.chunks(1_000) {
            let mut txn = self.env.begin_rw_txn()?;
            for record in chunk {
                let wire = WireRecord {
                    id: record.id(),
                    domain: domain_to_u8(record.domain()),
                    class: class_to_u8(record.class()),
                    content: record.content().to_string(),
                    source: record.source().to_string(),
                    confidence: record.confidence(),
                    status: status_to_u8(record.status()),
                    created_at: record.created_at(),
                };
                let value = rmp_serde::to_vec(&wire)?;
                let stored = self.encode_stored_record(record.id(), record.created_at(), &value)?;
                txn.put(
                    self.records,
                    &bytes_u64(record.id()),
                    &stored,
                    lmdb::WriteFlags::NO_OVERWRITE,
                )?;
                for term in crate::field::tokenize(record.content()) {
                    let mut ids: Vec<u64> = match txn.get(self.postings, &term) {
                        Ok(bytes) => rmp_serde::from_slice(bytes)?,
                        Err(lmdb::Error::NotFound) => Vec::new(),
                        Err(e) => return Err(e.into()),
                    };
                    if !ids.contains(&record.id()) {
                        ids.push(record.id());
                    }
                    txn.put(
                        self.postings,
                        &term,
                        &rmp_serde::to_vec(&ids)?,
                        lmdb::WriteFlags::empty(),
                    )?;
                }
                next_id = next_id.max(record.id().saturating_add(1));
            }
            txn.commit()?;
        }
        let mut txn = self.env.begin_rw_txn()?;
        let current = read_counter(&txn, self.default, META_NEXT_RECORD)?;
        txn.put(
            self.default,
            &META_NEXT_RECORD,
            &bytes_u64(current.max(next_id)),
            lmdb::WriteFlags::empty(),
        )?;
        txn.commit()?;
        Ok(())
    }

    pub fn get_record(&self, id: u64) -> Result<Option<EvidenceRecord>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let db = self.records;
        match txn.get(db, &bytes_u64(id)) {
            Ok(bytes) => Ok(Some(self.decode_stored_record(id, bytes)?)),
            Err(lmdb::Error::NotFound) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    pub fn iter_records(&self) -> Result<Vec<EvidenceRecord>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let db = self.records;
        let mut cursor = txn.open_ro_cursor(db)?;
        let mut out = Vec::new();
        for item in cursor.iter() {
            let (key, bytes) = item;
            out.push(self.decode_stored_record(record_key_id(key)?, bytes)?);
        }
        Ok(out)
    }

    pub fn record_count(&self) -> Result<usize, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let next_id = read_counter(&txn, self.default, META_NEXT_RECORD)?;
        Ok(next_id as usize)
    }

    pub fn postings(&self, term: &str) -> Result<Vec<u64>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let db = self.postings;
        match txn.get(db, &term) {
            Ok(bytes) => Ok(rmp_serde::from_slice(bytes)?),
            Err(lmdb::Error::NotFound) => Ok(Vec::new()),
            Err(e) => Err(e.into()),
        }
    }

    pub fn df(&self, term: &str) -> Result<usize, StoreError> {
        Ok(self.postings(term)?.len())
    }

    /// Direct relation write. Unauthorized by construction: production relation
    /// writes go through `commit_sweep`; this path is test/reference only.
    #[cfg(any(test, feature = "operator", feature = "reference-models"))]
    pub(crate) fn put_relation(&self, relation: &Relation) -> Result<(), StoreError> {
        self.ensure_writable()?;
        let key = bytes_u64(relation.id());
        let value = rmp_serde::to_vec(relation)?;
        let mut txn = self.env.begin_rw_txn()?;
        let db = self.relations;
        if txn.get(db, &key).is_ok() {
            return Err(StoreError::Msg(format!(
                "relation {} already exists",
                relation.id()
            )));
        }
        txn.put(db, &key, &value, lmdb::WriteFlags::empty())?;
        bump_relation_view_stamp(&mut txn, self.default)?;
        txn.commit()?;
        self.invalidate_relations_view();
        Ok(())
    }

    pub fn iter_relations(&self) -> Result<Vec<Relation>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let db = self.relations;
        let mut cursor = txn.open_ro_cursor(db)?;
        let mut out = Vec::new();
        for item in cursor.iter() {
            let (_, bytes) = item;
            out.push(rmp_serde::from_slice(bytes)?);
        }
        Ok(out)
    }

    /// Cheap cross-process change signal for relation writes. lmdb 0.8
    /// exposes neither `Env::info()` nor transaction ids, so relation writes
    /// bump this in-store stamp in their own transaction instead. Missing
    /// (pre-stamp stores) reads as 0.
    fn read_relation_view_stamp(&self) -> Result<u64, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        match txn.get(self.default, &META_RELATION_VIEW) {
            Ok(bytes) if bytes.len() == 8 => Ok(u64::from_be_bytes(
                bytes
                    .try_into()
                    .map_err(|_| StoreError::CorruptVersionHeader)?,
            )),
            Ok(_) => Err(StoreError::CorruptVersionHeader),
            Err(lmdb::Error::NotFound) => Ok(0),
            Err(e) => Err(e.into()),
        }
    }

    /// Lazily built, process-local relation adjacency for recall. The first
    /// call scans the relations keyspace once; later calls share the cached
    /// view while the store's relation stamp is unchanged. The stamp moves on
    /// every relation write — including writes committed by another process
    /// (CLI sweep, second server) — so a warm handle never serves a stale
    /// supersede/source resolution. Builds happen under the handle mutex, so a
    /// concurrent write cannot be overwritten by a stale view, and failed
    /// builds are not cached (the next call retries). This never persists
    /// state: the cache lives and dies with the handle.
    pub(crate) fn relations_view(&self) -> Arc<RelationsView> {
        let mut guard = self
            .cached_relations_view
            .lock()
            .expect("relations view lock");
        let stamp = match self.read_relation_view_stamp() {
            Ok(stamp) => stamp,
            // Do not cache a read failure as an empty view.
            Err(_) => return Arc::new(RelationsView::default()),
        };
        if let Some((cached_stamp, view)) = guard.as_ref()
            && *cached_stamp == stamp
        {
            return Arc::clone(view);
        }
        let relations = match self.iter_relations() {
            Ok(relations) => relations,
            // Transient read error: serve an empty view, cache nothing.
            Err(_) => return Arc::new(RelationsView::default()),
        };
        let view = Arc::new(RelationsView::derive(&relations));
        *guard = Some((stamp, Arc::clone(&view)));
        view
    }

    /// Drop the derived relation adjacency after a relation write. The stamp
    /// bump alone would also force a rebuild; this keeps same-handle caches
    /// observably cold without waiting for the next stamp read.
    pub(crate) fn invalidate_relations_view(&self) {
        *self
            .cached_relations_view
            .lock()
            .expect("relations view lock") = None;
    }

    /// Whether the derived relation adjacency is currently cached (evidence
    /// helper for invalidation tests).
    #[cfg(test)]
    pub(crate) fn relations_view_cached(&self) -> bool {
        self.cached_relations_view
            .lock()
            .expect("relations view lock")
            .is_some()
    }

    /// Tokenizer/format marker of the postings index, when the store carries
    /// one (absent on pre-marker stores and fresh environments).
    pub(crate) fn identity_index_marker(&self) -> Result<Option<String>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        match txn.get(self.default, &META_IDENTITY_INDEX) {
            Ok(bytes) => Ok(Some(String::from_utf8_lossy(bytes).into_owned())),
            Err(lmdb::Error::NotFound) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    /// Backfill the postings-index marker so later opens can take the fast
    /// postings-based duplicate probe.
    pub(crate) fn set_identity_index_marker(&self, marker: &str) -> Result<(), StoreError> {
        self.ensure_writable()?;
        let marker_bytes: &[u8] = marker.as_bytes();
        let mut txn = self.env.begin_rw_txn()?;
        txn.put(
            self.default,
            &META_IDENTITY_INDEX,
            &marker_bytes,
            lmdb::WriteFlags::empty(),
        )?;
        txn.commit()?;
        Ok(())
    }

    /// Growth metrics from filesystem metadata plus the configured map size.
    pub fn map_stats(&self) -> Result<StoreMapStats, String> {
        let data_path = self.path.join("data.mdb");
        let data_bytes = std::fs::metadata(&data_path)
            .map_err(|e| format!("store map stats: {}: {e}", data_path.display()))?
            .len();
        let map_bytes = configured_map_size() as u64;
        let used_fraction = if map_bytes == 0 {
            0.0
        } else {
            data_bytes as f64 / map_bytes as f64
        };
        Ok(StoreMapStats {
            data_bytes,
            map_bytes,
            used_fraction,
        })
    }

    /// Structural debug counter: stored-record decodes performed by this
    /// handle (lazy-hydration assertions; never a timing probe).
    #[cfg(test)]
    pub(crate) fn decode_count(&self) -> u64 {
        self.decode_count.get()
    }

    /// Record vector by id (L2-normalized f32[384]).
    pub(crate) fn put_vector(&self, id: u64, vector: &[f32]) -> Result<(), StoreError> {
        self.ensure_writable()?;
        let key = bytes_u64(id);
        let value = rmp_serde::to_vec(&vector.to_vec())?;
        let mut txn = self.env.begin_rw_txn()?;
        txn.put(self.embeddings, &key, &value, lmdb::WriteFlags::empty())?;
        txn.commit()?;
        Ok(())
    }

    pub fn get_vector(&self, id: u64) -> Result<Option<Vec<f32>>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        match txn.get(self.embeddings, &bytes_u64(id)) {
            Ok(bytes) => Ok(Some(rmp_serde::from_slice(bytes)?)),
            Err(lmdb::Error::NotFound) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    pub fn iter_vectors(&self) -> Result<Vec<(u64, Vec<f32>)>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let mut cursor = txn.open_ro_cursor(self.embeddings)?;
        let mut out = Vec::new();
        for (key, bytes) in cursor.iter() {
            if key.len() == 8 {
                let id = u64::from_be_bytes(key.try_into().unwrap_or([0; 8]));
                out.push((id, rmp_serde::from_slice(bytes)?));
            }
        }
        Ok(out)
    }

    /// Content-hash embedding cache (dedup + cross-process reuse).
    pub(crate) fn put_embedding_cache(&self, hash: &str, vector: &[f32]) -> Result<(), StoreError> {
        self.ensure_writable()?;
        let value = rmp_serde::to_vec(&vector.to_vec())?;
        let mut txn = self.env.begin_rw_txn()?;
        txn.put(self.embed_cache, &hash, &value, lmdb::WriteFlags::empty())?;
        txn.commit()?;
        Ok(())
    }

    /// Number of derived cache entries (test/evidence helper; never canonical).
    #[cfg(test)]
    pub(crate) fn embedding_cache_len(&self) -> Result<usize, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let mut cursor = txn.open_ro_cursor(self.embed_cache)?;
        Ok(cursor.iter().count())
    }

    pub fn get_embedding_cache(&self, hash: &str) -> Result<Option<Vec<f32>>, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        match txn.get(self.embed_cache, &hash) {
            Ok(bytes) => Ok(Some(rmp_serde::from_slice(bytes)?)),
            Err(lmdb::Error::NotFound) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    // ---- Gate 9A Slice 1: authorized sweep (v5) ----

    /// Read-only peek at the sweep counter. Disabled sweeps never allocate; they
    /// may still report the current counter value.
    pub(crate) fn peek_sweep_counter(&self) -> Result<u64, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        read_counter(&txn, self.default, META_SWEEP.as_bytes())
    }

    /// Coherent, bounded preflight for sweep planning: one read transaction;
    /// records, postings, tokens and relations are bounded before or while they
    /// are decoded; any refusal returns with no state touched.
    pub(crate) fn sweep_preflight(
        &self,
        limits: SweepLimits,
    ) -> Result<SweepPreflightData, StoreError> {
        let txn = self.env.begin_ro_txn()?;
        let realm_id: [u8; 16] = txn
            .get(self.default, &META_REALM_ID)
            .map_err(|_| StoreError::CorruptVersionHeader)?
            .try_into()
            .map_err(|_| StoreError::CorruptVersionHeader)?;
        let epoch = read_counter(&txn, self.default, META_EPOCH)?;
        let next_sweep_id = read_counter(&txn, self.default, META_SWEEP.as_bytes())?;
        let mut observed = SweepObserved {
            records_scanned: 0,
            raw_record_bytes: 0,
            largest_record_bytes: 0,
            postings_bytes: 0,
            token_occurrences: 0,
            relations_scanned: 0,
            pair_examinations: 0,
            effects: 0,
        };

        let mut records: Vec<EvidenceRecord> = Vec::new();
        {
            let mut cursor = txn.open_ro_cursor(self.records)?;
            for (key, bytes) in cursor.iter() {
                add_count(&mut observed.records_scanned, 1)?;
                if observed.records_scanned > limits.max_records_scanned {
                    return Err(limit_error(
                        "records_scanned",
                        observed.records_scanned,
                        limits.max_records_scanned,
                    ));
                }
                // Decode guard: refuse oversized values before deserialization.
                let wire_len = bytes.len() as u64;
                if wire_len
                    > limits
                        .max_single_record_bytes
                        .saturating_add(MAX_WIRE_RECORD_OVERHEAD)
                {
                    return Err(limit_error(
                        "largest_record_bytes",
                        wire_len,
                        limits.max_single_record_bytes,
                    ));
                }
                let record = self.decode_stored_record(record_key_id(key)?, bytes)?;
                let record_bytes = record.content().len() as u64 + record.source().len() as u64;
                if record_bytes > limits.max_single_record_bytes {
                    return Err(limit_error(
                        "largest_record_bytes",
                        record_bytes,
                        limits.max_single_record_bytes,
                    ));
                }
                add_count(&mut observed.raw_record_bytes, record_bytes)?;
                if observed.raw_record_bytes > limits.max_raw_record_bytes {
                    return Err(limit_error(
                        "raw_record_bytes",
                        observed.raw_record_bytes,
                        limits.max_raw_record_bytes,
                    ));
                }
                observed.largest_record_bytes = observed.largest_record_bytes.max(record_bytes);
                records.push(record);
            }
        }

        let mut token_ids: std::collections::BTreeMap<String, Vec<u64>> =
            std::collections::BTreeMap::new();
        for record in &records {
            for token in crate::field::tokenize(record.content()) {
                add_count(&mut observed.token_occurrences, 1)?;
                if observed.token_occurrences > limits.max_token_occurrences {
                    return Err(limit_error(
                        "token_occurrences",
                        observed.token_occurrences,
                        limits.max_token_occurrences,
                    ));
                }
                token_ids.entry(token).or_default().push(record.id());
            }
        }

        let mut df: std::collections::BTreeMap<String, u64> = std::collections::BTreeMap::new();
        for term in token_ids.keys() {
            match txn.get(self.postings, term) {
                Ok(bytes) => {
                    add_count(&mut observed.postings_bytes, bytes.len() as u64)?;
                    if observed.postings_bytes > limits.max_postings_bytes {
                        return Err(limit_error(
                            "postings_bytes",
                            observed.postings_bytes,
                            limits.max_postings_bytes,
                        ));
                    }
                    let ids: Vec<u64> = rmp_serde::from_slice(bytes)?;
                    df.insert(term.clone(), ids.len() as u64);
                }
                Err(lmdb::Error::NotFound) => {
                    df.insert(term.clone(), 0);
                }
                Err(e) => return Err(e.into()),
            }
        }

        let mut relations: Vec<Relation> = Vec::new();
        {
            let mut cursor = txn.open_ro_cursor(self.relations)?;
            for (_, bytes) in cursor.iter() {
                add_count(&mut observed.relations_scanned, 1)?;
                if observed.relations_scanned > limits.max_relations_scanned {
                    return Err(limit_error(
                        "relations_scanned",
                        observed.relations_scanned,
                        limits.max_relations_scanned,
                    ));
                }
                relations.push(rmp_serde::from_slice(bytes)?);
            }
        }

        let mut vectors: std::collections::BTreeMap<u64, Vec<f32>> =
            std::collections::BTreeMap::new();
        {
            let mut cursor = txn.open_ro_cursor(self.embeddings)?;
            for (key, bytes) in cursor.iter() {
                if key.len() == 8 {
                    let id = u64::from_be_bytes(key.try_into().unwrap_or([0; 8]));
                    if let Ok(vec) = rmp_serde::from_slice(bytes) {
                        vectors.insert(id, vec);
                    }
                }
            }
        }

        Ok(SweepPreflightData {
            realm_id,
            epoch,
            next_sweep_id,
            records,
            relations,
            df,
            vectors,
            observed,
        })
    }

    /// Atomically commit one authorized sweep plan. Fresh commits apply all
    /// relation effects, both counters, one epoch advance, one nullifier and one
    /// tagged receipt inside a single LMDB write transaction. A matching committed
    /// receipt returns replay without applying anything.
    pub(crate) fn commit_sweep(
        &self,
        capability: CommitCapability,
        request: &SweepRequest,
    ) -> Result<SweepOutcome, StoreError> {
        self.ensure_writable()?;
        request.validate()?;
        if capability.authorized_digest() != request.digest() {
            return Err(SweepError::UnauthorizedCapability { field: "digest" }.into());
        }
        if capability.scope() != SWEEP_SCOPE {
            return Err(SweepError::UnauthorizedCapability { field: "scope" }.into());
        }
        if capability.feasibility_operation_id() != Some(request.operation_id()) {
            return Err(SweepError::UnauthorizedCapability {
                field: "operation_id",
            }
            .into());
        }
        if capability.feasibility_realm_id() != Some(*request.realm_id()) {
            return Err(SweepError::UnauthorizedCapability { field: "realm_id" }.into());
        }
        if capability.feasibility_expected_epoch() != Some(request.expected_epoch()) {
            return Err(SweepError::UnauthorizedCapability {
                field: "expected_epoch",
            }
            .into());
        }
        if capability.feasibility_authority_digest() != Some(request.authority_digest()) {
            return Err(SweepError::UnauthorizedCapability {
                field: "authority_digest",
            }
            .into());
        }
        if capability.feasibility_operation_kind() != Some(SWEEP_OPERATION_KIND) {
            return Err(SweepError::UnauthorizedCapability {
                field: "operation_kind",
            }
            .into());
        }

        let operation_id = request.operation_id();
        let key = operation_id.as_bytes();
        let mut txn = self.env.begin_rw_txn()?;

        match txn.get(self.receipts, key) {
            Ok(bytes) => {
                let envelope = decode_receipt_envelope(bytes)
                    .map_err(|_| SweepError::ReceiptState("receipt envelope is not decodable"))?;
                let receipt = match envelope {
                    CommitReceiptEnvelopeV5::SweepV1(receipt) => receipt,
                    CommitReceiptEnvelopeV5::IntakeV2(_) => {
                        return Err(SweepError::CrossKindConflict.into());
                    }
                };
                self.validate_sweep_receipt_state(&txn, &receipt)?;
                if receipt.realm_id != *request.realm_id()
                    || receipt.manifest_digest != request.digest()
                    || receipt.authority_digest != request.authority_digest()
                {
                    return Err(SweepError::ReplayMismatch.into());
                }
                return Ok(SweepOutcome {
                    receipt,
                    disposition: CommitDisposition::Replay,
                });
            }
            Err(lmdb::Error::NotFound) => {}
            Err(e) => return Err(e.into()),
        }
        match txn.get(self.nullifiers, key) {
            Ok(_) => {
                return Err(SweepError::ReceiptState("nullifier has no paired receipt").into());
            }
            Err(lmdb::Error::NotFound) => {}
            Err(e) => return Err(e.into()),
        }

        let realm: [u8; 16] = txn
            .get(self.default, &META_REALM_ID)
            .map_err(|_| StoreError::CorruptVersionHeader)?
            .try_into()
            .map_err(|_| StoreError::CorruptVersionHeader)?;
        if realm != *request.realm_id() {
            return Err(SweepError::RealmMismatch.into());
        }
        let epoch = read_counter(&txn, self.default, META_EPOCH)?;
        if epoch != request.expected_epoch() {
            return Err(SweepError::StaleEpoch {
                expected: request.expected_epoch(),
                actual: epoch,
            }
            .into());
        }
        let sweep_id = read_counter(&txn, self.default, META_SWEEP.as_bytes())?;
        let next_sweep = sweep_id
            .checked_add(1)
            .ok_or(SweepError::CounterExhausted)?;
        let mut next_relation = read_counter(&txn, self.default, META_NEXT_RELATION.as_bytes())?;
        let relation_floor = next_relation;
        let post_epoch = epoch.checked_add(1).ok_or(SweepError::CounterExhausted)?;

        let mut allocated: Vec<u64> = Vec::new();
        for effect in request.effects() {
            match effect {
                SweepEffect::CreateSupersedes {
                    src,
                    dst,
                    confidence_bits,
                    rule_id,
                } => {
                    let confidence = f32::from_bits(*confidence_bits);
                    if !confidence.is_finite()
                        || !(0.0..=1.0).contains(&confidence)
                        || rule_id != crate::field::RULE_ID
                    {
                        return Err(SweepError::InvalidEffect("invalid create effect").into());
                    }
                    if txn.get(self.records, &bytes_u64(*src)).is_err()
                        || txn.get(self.records, &bytes_u64(*dst)).is_err()
                    {
                        return Err(SweepError::ReceiptState(
                            "create effect references a missing record",
                        )
                        .into());
                    }
                    let relation = Relation::new(next_relation, *src, *dst, confidence, sweep_id);
                    let value = rmp_serde::to_vec(&relation)?;
                    txn.put(
                        self.relations,
                        &bytes_u64(next_relation),
                        &value,
                        lmdb::WriteFlags::NO_OVERWRITE,
                    )?;
                    allocated.push(next_relation);
                    next_relation = next_relation
                        .checked_add(1)
                        .ok_or(SweepError::CounterExhausted)?;
                }
                SweepEffect::SetRelationState {
                    relation_id,
                    expected_prior_state,
                    next_state,
                } => {
                    if *relation_id >= relation_floor {
                        return Err(SweepError::ReceiptState(
                            "state effect targets an uncommitted relation",
                        )
                        .into());
                    }
                    let relation_key = bytes_u64(*relation_id);
                    let bytes = txn.get(self.relations, &relation_key).map_err(|_| {
                        SweepError::StateConflict {
                            relation_id: *relation_id,
                        }
                    })?;
                    let mut relation: Relation =
                        rmp_serde::from_slice(bytes).map_err(|_| SweepError::StateConflict {
                            relation_id: *relation_id,
                        })?;
                    if relation.state() != *expected_prior_state {
                        return Err(SweepError::StateConflict {
                            relation_id: *relation_id,
                        }
                        .into());
                    }
                    relation.set_state(*next_state);
                    let value = rmp_serde::to_vec(&relation)?;
                    txn.put(
                        self.relations,
                        &relation_key,
                        &value,
                        lmdb::WriteFlags::empty(),
                    )?;
                }
            }
        }
        if !request.effects().is_empty() {
            bump_relation_view_stamp(&mut txn, self.default)?;
        }
        self.fail_after(1)?;

        txn.put(
            self.default,
            &META_NEXT_RELATION.as_bytes(),
            &bytes_u64(next_relation),
            lmdb::WriteFlags::empty(),
        )?;
        self.fail_after(2)?;
        txn.put(
            self.default,
            &META_SWEEP.as_bytes(),
            &bytes_u64(next_sweep),
            lmdb::WriteFlags::empty(),
        )?;
        txn.put(
            self.default,
            &META_EPOCH,
            &bytes_u64(post_epoch),
            lmdb::WriteFlags::empty(),
        )?;
        self.fail_after(3)?;
        txn.put(
            self.nullifiers,
            key,
            &request.digest(),
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        self.fail_after(4)?;

        let effect_count =
            u64::try_from(request.effects().len()).map_err(|_| SweepError::LengthOverflow)?;
        let outcomes = outcomes_digest(request.effects(), &allocated)?;
        let receipt = SweepReceipt {
            version: SWEEP_RECEIPT_VERSION,
            realm_id: realm,
            operation_id,
            manifest_digest: request.digest(),
            authority_digest: request.authority_digest(),
            compiler_scope: capability.scope().to_string(),
            operation_kind: SWEEP_OPERATION_KIND,
            policy_digest: request.policy_digest(),
            limits: request.limits(),
            observed: request.observed(),
            usage_digest: request.usage().digest(),
            process_instance_id: *request.usage().process_instance_id(),
            usage_sequence: request.usage().sequence(),
            usage_evidence_basis: crate::sweep::SWEEP_USAGE_EVIDENCE_BASIS.to_string(),
            usage_restart_persistent: crate::sweep::SWEEP_USAGE_RESTART_PERSISTENT,
            effects_digest: request.effects_digest(),
            effect_count,
            pre_epoch: epoch,
            post_epoch,
            sweep_id,
            allocated_relation_ids: allocated,
            outcomes_digest: outcomes,
            sealed_request: request.encode_for_receipt()?,
            committed: true,
        };
        let receipt_bytes =
            encode_receipt_envelope(&CommitReceiptEnvelopeV5::SweepV1(receipt.clone()))?;
        txn.put(
            self.receipts,
            key,
            &receipt_bytes,
            lmdb::WriteFlags::NO_OVERWRITE,
        )?;
        self.fail_after(5)?;
        self.validate_sweep_receipt_state(&txn, &receipt)?;
        txn.commit()?;
        self.invalidate_relations_view();
        Ok(SweepOutcome {
            receipt,
            disposition: CommitDisposition::Committed,
        })
    }

    /// Authenticated replay of an already committed sweep against the persisted
    /// original plan. Never re-plans or rescans: the stored envelope is validated
    /// inertly and the fresh capability must bind the stored manifest digest.
    pub(crate) fn replay_sweep(
        &self,
        capability: CommitCapability,
        operation_id: OperationId,
    ) -> Result<SweepOutcome, StoreError> {
        let key = operation_id.as_bytes();
        let txn = self.env.begin_ro_txn()?;
        let bytes = match txn.get(self.receipts, key) {
            Ok(bytes) => bytes,
            Err(lmdb::Error::NotFound) => match txn.get(self.nullifiers, key) {
                Ok(_) => {
                    return Err(SweepError::ReceiptState("nullifier has no paired receipt").into());
                }
                Err(lmdb::Error::NotFound) => {
                    return Err(SweepError::ReceiptState("no committed sweep receipt").into());
                }
                Err(e) => return Err(e.into()),
            },
            Err(e) => return Err(e.into()),
        };
        let envelope = decode_receipt_envelope(bytes)
            .map_err(|_| SweepError::ReceiptState("receipt envelope is not decodable"))?;
        let receipt = match envelope {
            CommitReceiptEnvelopeV5::SweepV1(receipt) => receipt,
            CommitReceiptEnvelopeV5::IntakeV2(_) => {
                return Err(SweepError::CrossKindConflict.into());
            }
        };
        self.validate_sweep_receipt_state(&txn, &receipt)?;

        if capability.authorized_digest() != receipt.manifest_digest {
            return Err(SweepError::ReplayMismatch.into());
        }
        if capability.scope() != SWEEP_SCOPE {
            return Err(SweepError::UnauthorizedCapability { field: "scope" }.into());
        }
        if capability.feasibility_operation_id() != Some(operation_id) {
            return Err(SweepError::UnauthorizedCapability {
                field: "operation_id",
            }
            .into());
        }
        if capability.feasibility_realm_id() != Some(receipt.realm_id) {
            return Err(SweepError::UnauthorizedCapability { field: "realm_id" }.into());
        }
        if capability.feasibility_authority_digest() != Some(receipt.authority_digest) {
            return Err(SweepError::UnauthorizedCapability {
                field: "authority_digest",
            }
            .into());
        }
        if capability.feasibility_operation_kind() != Some(SWEEP_OPERATION_KIND) {
            return Err(SweepError::UnauthorizedCapability {
                field: "operation_kind",
            }
            .into());
        }
        // Fresh authority: the capability must bind the current epoch. The stored
        // plan's original epoch is historical and is never re-compared.
        let current_epoch = read_counter(&txn, self.default, META_EPOCH)?;
        if capability.feasibility_expected_epoch() != Some(current_epoch) {
            return Err(SweepError::StaleEpoch {
                expected: capability.feasibility_expected_epoch().unwrap_or(0),
                actual: current_epoch,
            }
            .into());
        }
        Ok(SweepOutcome {
            receipt,
            disposition: CommitDisposition::Replay,
        })
    }

    /// Look up and validate a committed sweep receipt without replaying it.
    pub(crate) fn lookup_sweep_receipt(
        &self,
        operation_id: OperationId,
    ) -> Result<Option<SweepReceipt>, StoreError> {
        let key = operation_id.as_bytes();
        let txn = self.env.begin_ro_txn()?;
        let bytes = match txn.get(self.receipts, key) {
            Ok(bytes) => bytes,
            Err(lmdb::Error::NotFound) => match txn.get(self.nullifiers, key) {
                Ok(_) => {
                    return Err(SweepError::ReceiptState("nullifier has no paired receipt").into());
                }
                Err(lmdb::Error::NotFound) => return Ok(None),
                Err(e) => return Err(e.into()),
            },
            Err(e) => return Err(e.into()),
        };
        let envelope = decode_receipt_envelope(bytes)
            .map_err(|_| SweepError::ReceiptState("receipt envelope is not decodable"))?;
        let receipt = match envelope {
            CommitReceiptEnvelopeV5::SweepV1(receipt) => receipt,
            CommitReceiptEnvelopeV5::IntakeV2(_) => {
                return Err(SweepError::CrossKindConflict.into());
            }
        };
        self.validate_sweep_receipt_state(&txn, &receipt)?;
        Ok(Some(receipt))
    }

    /// Full ledger-side validation of a committed sweep receipt: header chain,
    /// counters, inert plan binding, outcome digest, allocated relations, and the
    /// nullifier pairing. State transitions are not re-checked here because later
    /// sweeps may legitimately advance lifecycle state.
    fn validate_sweep_receipt_state<T: Transaction>(
        &self,
        txn: &T,
        receipt: &SweepReceipt,
    ) -> Result<(), StoreError> {
        let realm: [u8; 16] = txn
            .get(self.default, &META_REALM_ID)
            .map_err(|_| StoreError::CorruptVersionHeader)?
            .try_into()
            .map_err(|_| StoreError::CorruptVersionHeader)?;
        if receipt.version != SWEEP_RECEIPT_VERSION
            || !receipt.committed
            || receipt.operation_kind != SWEEP_OPERATION_KIND
            || receipt.compiler_scope != SWEEP_SCOPE
            || receipt.usage_evidence_basis != crate::sweep::SWEEP_USAGE_EVIDENCE_BASIS
            || receipt.usage_restart_persistent != crate::sweep::SWEEP_USAGE_RESTART_PERSISTENT
            || receipt.realm_id != realm
            || receipt.post_epoch
                != receipt
                    .pre_epoch
                    .checked_add(1)
                    .ok_or(SweepError::ReceiptState("epoch chain invalid"))?
        {
            return Err(SweepError::ReceiptState("receipt header is inconsistent").into());
        }
        let current_epoch = read_counter(txn, self.default, META_EPOCH)?;
        if receipt.post_epoch > current_epoch {
            return Err(SweepError::ReceiptState("receipt epoch is in the future").into());
        }
        let sweep_counter = read_counter(txn, self.default, META_SWEEP.as_bytes())?;
        if receipt.sweep_id >= sweep_counter {
            return Err(SweepError::ReceiptState("sweep id is not committed").into());
        }
        let relation_counter = read_counter(txn, self.default, META_NEXT_RELATION.as_bytes())?;
        let plan = decode_validated_plan(&receipt.sealed_request)?;
        if plan.manifest_digest != receipt.manifest_digest
            || plan.operation_id != receipt.operation_id
            || plan.realm_id != receipt.realm_id
            || plan.limits != receipt.limits
            || plan.observed != receipt.observed
            || plan.policy_digest != receipt.policy_digest
            || plan.usage_digest != receipt.usage_digest
            || plan.process_instance_id != receipt.process_instance_id
            || plan.usage_sequence != receipt.usage_sequence
            || plan.effects_digest != receipt.effects_digest
            || u64::try_from(plan.effects.len()).map_err(|_| SweepError::LengthOverflow)?
                != receipt.effect_count
            || receipt.authority_digest != sweep_authority_digest(&plan.issuer_label)
        {
            return Err(
                SweepError::ReceiptState("receipt does not bind the persisted plan").into(),
            );
        }
        if outcomes_digest(&plan.effects, &receipt.allocated_relation_ids)?
            != receipt.outcomes_digest
        {
            return Err(SweepError::ReceiptState("outcome digest mismatch").into());
        }
        let mut created = plan.effects.iter().filter_map(|effect| match effect {
            SweepEffect::CreateSupersedes { src, dst, .. } => Some((*src, *dst)),
            SweepEffect::SetRelationState { .. } => None,
        });
        for relation_id in &receipt.allocated_relation_ids {
            if *relation_id >= relation_counter {
                return Err(
                    SweepError::ReceiptState("allocated relation id is not committed").into(),
                );
            }
            let bytes = txn
                .get(self.relations, &bytes_u64(*relation_id))
                .map_err(|_| SweepError::ReceiptState("allocated relation is missing"))?;
            let relation: Relation = rmp_serde::from_slice(bytes)
                .map_err(|_| SweepError::ReceiptState("allocated relation is corrupt"))?;
            let expected = created.next().ok_or(SweepError::ReceiptState(
                "allocated ids exceed create effects",
            ))?;
            if relation.created_sweep() != receipt.sweep_id
                || (relation.src(), relation.dst()) != expected
            {
                return Err(SweepError::ReceiptState(
                    "allocated relation does not match its effect",
                )
                .into());
            }
        }
        if created.next().is_some() {
            return Err(SweepError::ReceiptState("create effects exceed allocated ids").into());
        }
        for effect in &plan.effects {
            if let SweepEffect::SetRelationState { relation_id, .. } = effect {
                txn.get(self.relations, &bytes_u64(*relation_id))
                    .map_err(|_| SweepError::StateConflict {
                        relation_id: *relation_id,
                    })?;
            }
        }
        let nullifier = txn
            .get(self.nullifiers, receipt.operation_id.as_bytes())
            .map_err(|_| SweepError::ReceiptState("nullifier is missing"))?;
        if nullifier != receipt.manifest_digest.as_slice() {
            return Err(SweepError::ReceiptState("nullifier does not bind the receipt").into());
        }
        Ok(())
    }
}

fn read_counter<T: Transaction>(txn: &T, db: Database, key: &[u8]) -> Result<u64, StoreError> {
    let bytes = match txn.get(db, &key) {
        Ok(bytes) if bytes.len() == 8 => bytes,
        _ => return Err(StoreError::CorruptVersionHeader),
    };
    Ok(u64::from_be_bytes(
        bytes
            .try_into()
            .map_err(|_| StoreError::CorruptVersionHeader)?,
    ))
}

/// Bump the relation-write stamp inside the caller's write transaction, so a
/// committed relation write and its change signal are atomic.
fn bump_relation_view_stamp(
    txn: &mut lmdb::RwTransaction<'_>,
    default: Database,
) -> Result<(), StoreError> {
    let current = match txn.get(default, &META_RELATION_VIEW) {
        Ok(bytes) if bytes.len() == 8 => u64::from_be_bytes(
            bytes
                .try_into()
                .map_err(|_| StoreError::CorruptVersionHeader)?,
        ),
        Ok(_) => 0,
        Err(lmdb::Error::NotFound) => 0,
        Err(e) => return Err(e.into()),
    };
    txn.put(
        default,
        &META_RELATION_VIEW,
        &bytes_u64(current.saturating_add(1)),
        lmdb::WriteFlags::empty(),
    )?;
    Ok(())
}

fn add_count(target: &mut u64, amount: u64) -> Result<(), SweepError> {
    *target = target
        .checked_add(amount)
        .ok_or(SweepError::LengthOverflow)?;
    Ok(())
}

fn limit_error(dimension: &'static str, observed: u64, limit: u64) -> StoreError {
    SweepError::LimitExceeded {
        dimension,
        observed,
        limit,
    }
    .into()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::evidence::RatifiedChannel;
    use crate::intake::OperationId;
    use crate::pulse_compiler::{authorize_intake, authorize_sweep, authorize_sweep_replay};
    use crate::sweep::SWEEP_PROFILE_V1;

    struct TempStore(PathBuf);
    impl TempStore {
        fn new(label: &str) -> Self {
            let path =
                std::env::temp_dir().join(format!("wm-gen3-store-{label}-{}", std::process::id()));
            let _ = std::fs::remove_dir_all(&path);
            Self(path)
        }
    }
    impl Drop for TempStore {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    fn request(store: &Store, op: [u8; 16], epoch: u64, content: &str) -> IntakeRequest {
        IntakeRequest::new(
            &RatifiedChannel::stub("synthetic-store-test"),
            OperationId::from_bytes(op),
            store.realm_id().unwrap(),
            epoch,
            0,
            IntakeKind::Reported,
            content.into(),
            "fixture:store".into(),
        )
        .unwrap()
    }

    fn capability(store: &Store, request: &IntakeRequest) -> CommitCapability {
        authorize_intake(
            &RatifiedChannel::stub("synthetic-store-test"),
            request,
            &store.authorization_snapshot().unwrap(),
        )
        .unwrap()
    }

    fn data_hash(path: &Path) -> [u8; 32] {
        Sha256::digest(std::fs::read(path.join("data.mdb")).unwrap()).into()
    }

    fn assert_intake_unchanged(store: &Store, before: [u8; 32]) {
        assert_eq!(store.record_count().unwrap(), 0);
        assert_eq!(store.epoch().unwrap(), 0);
        assert_eq!(data_hash(store.path()), before);
    }

    fn raw_header(path: &Path, version: &[u8], realm: &[u8], initializing: bool, named_dbs: usize) {
        std::fs::create_dir_all(path).unwrap();
        let mut builder = lmdb::Environment::new();
        builder.set_max_dbs(16).set_map_size(1 << 30);
        let env = builder.open_with_permissions(path, 0o600).unwrap();
        let default = env.open_db(None).unwrap();
        let mut txn = env.begin_rw_txn().unwrap();
        if initializing {
            txn.put(default, &META_INITIALIZING, &[1], lmdb::WriteFlags::empty())
                .unwrap();
        } else {
            if !version.is_empty() {
                txn.put(
                    default,
                    &META_FORMAT_VERSION,
                    &version,
                    lmdb::WriteFlags::empty(),
                )
                .unwrap();
            }
            txn.put(default, &META_REALM_ID, &realm, lmdb::WriteFlags::empty())
                .unwrap();
            txn.put(
                default,
                &META_EPOCH,
                &bytes_u64(0),
                lmdb::WriteFlags::empty(),
            )
            .unwrap();
            txn.put(
                default,
                &META_NEXT_RECORD,
                &bytes_u64(0),
                lmdb::WriteFlags::empty(),
            )
            .unwrap();
            txn.put(
                default,
                &META_NEXT_RELATION,
                &bytes_u64(0),
                lmdb::WriteFlags::empty(),
            )
            .unwrap();
            txn.put(
                default,
                &META_SWEEP,
                &bytes_u64(0),
                lmdb::WriteFlags::empty(),
            )
            .unwrap();
        }
        txn.commit().unwrap();
        for name in [
            DB_RECORDS,
            DB_RELATIONS,
            DB_POSTINGS,
            DB_EMBEDDINGS,
            DB_EMBED_CACHE,
            DB_NULLIFIERS,
            DB_RECEIPTS,
        ]
        .into_iter()
        .take(named_dbs)
        {
            env.create_db(Some(name), lmdb::DatabaseFlags::empty())
                .unwrap();
        }
    }

    #[test]
    fn test_corrupt_wire_record_rejected_fail_closed() {
        let corrupt_domain = WireRecord {
            id: 1,
            domain: 255,
            class: 0,
            content: "test".into(),
            source: "test".into(),
            confidence: 1.0,
            status: 0,
            created_at: 0,
        };
        let bytes = rmp_serde::to_vec(&corrupt_domain).unwrap();
        let res = decode_record(&bytes);
        assert!(
            matches!(res, Err(StoreError::Msg(m)) if m.contains("invalid wire domain tag: 255"))
        );

        let corrupt_class = WireRecord {
            id: 2,
            domain: 0,
            class: 99,
            content: "test".into(),
            source: "test".into(),
            confidence: 1.0,
            status: 0,
            created_at: 0,
        };
        let bytes = rmp_serde::to_vec(&corrupt_class).unwrap();
        let res = decode_record(&bytes);
        assert!(matches!(res, Err(StoreError::Msg(m)) if m.contains("invalid wire class tag: 99")));

        let corrupt_status = WireRecord {
            id: 3,
            domain: 0,
            class: 0,
            content: "test".into(),
            source: "test".into(),
            confidence: 1.0,
            status: 42,
            created_at: 0,
        };
        let bytes = rmp_serde::to_vec(&corrupt_status).unwrap();
        let res = decode_record(&bytes);
        assert!(
            matches!(res, Err(StoreError::Msg(m)) if m.contains("invalid wire status tag: 42"))
        );
    }

    #[test]
    fn intake_commit_reopen_and_authenticated_retry_are_coherent() {
        let tmp = TempStore::new("commit-reopen");
        let store = Store::open(&tmp.0).unwrap();
        let intake_request = request(&store, [1; 16], 0, "synthetic durable record");
        let stale = request(&store, [2; 16], 0, "stale payload");
        let stale_capability = capability(&store, &stale);
        let outcome = store
            .commit_intake(
                capability(&store, &intake_request),
                &intake_request,
                &crate::field::tokenize(intake_request.content()),
            )
            .unwrap();
        assert_eq!(outcome.disposition, CommitDisposition::Committed);
        assert_eq!(outcome.receipt.record_id, 0);
        assert_eq!(store.epoch().unwrap(), 1);
        drop(store);
        let reopened = Store::open(&tmp.0).unwrap();
        assert_eq!(reopened.record_count().unwrap(), 1);
        assert_eq!(reopened.epoch().unwrap(), 1);
        let cached = reopened
            .lookup_intake_receipt(&intake_request)
            .unwrap()
            .unwrap();
        assert_eq!(cached, outcome.receipt);
        assert_eq!(reopened.epoch().unwrap(), 1);
        let conflict = request(&reopened, [1; 16], 1, "different payload");
        assert!(matches!(
            reopened.lookup_intake_receipt(&conflict),
            Err(StoreError::Intake(IntakeError::IdempotencyConflict))
        ));
        assert!(matches!(
            reopened.commit_intake(
                stale_capability,
                &stale,
                &crate::field::tokenize(stale.content())
            ),
            Err(StoreError::Intake(IntakeError::StaleEpoch { .. }))
        ));
    }

    #[test]
    fn compiler_issued_capability_cannot_commit_a_different_request() {
        let tmp = TempStore::new("wrong-issued-request");
        let store = Store::open(&tmp.0).unwrap();
        let issued_for = request(&store, [31; 16], 0, "synthetic bound payload A");
        let presented = request(&store, [32; 16], 0, "synthetic bound payload B");
        let before = data_hash(&tmp.0);

        // Both requests are independently feasible against the same store snapshot.
        // The presented request must not reuse the other request's real compiler token.
        let result = store.commit_intake(
            capability(&store, &issued_for),
            &presented,
            &crate::field::tokenize(presented.content()),
        );
        assert!(matches!(
            result,
            Err(StoreError::Intake(IntakeError::UnauthorizedCapability {
                field: "digest"
            }))
        ));
        assert_intake_unchanged(&store, before);
    }

    #[test]
    fn arbitrated_capability_cannot_cross_the_feasibility_boundary() {
        let tmp = TempStore::new("arbitrated-capability");
        let store = Store::open(&tmp.0).unwrap();
        let intake = request(&store, [33; 16], 0, "synthetic feasibility boundary");
        let before = data_hash(&tmp.0);
        // This is a valid arbitrated warrant with matching digest and scope.  Its
        // absent feasibility bindings, rather than a test-only forged field, must
        // make the Store reject it.
        let arbitrated =
            crate::pulse_compiler::test_arbitrated_capability(intake.digest(), 0, INTAKE_SCOPE);
        let result = store.commit_intake(
            arbitrated,
            &intake,
            &crate::field::tokenize(intake.content()),
        );
        assert!(matches!(
            result,
            Err(StoreError::Intake(IntakeError::UnauthorizedCapability {
                field: "operation_id"
            }))
        ));
        assert_intake_unchanged(&store, before);
    }

    #[test]
    fn injected_commit_abort_rolls_back_every_staged_effect() {
        for stage in 1..=5 {
            let tmp = TempStore::new(&format!("rollback-{stage}"));
            let store = Store::open(&tmp.0).unwrap();
            let intake = request(&store, [stage; 16], 0, "synthetic rollback");
            store.fail_after_stage.set(Some(stage));
            assert!(
                store
                    .commit_intake(
                        capability(&store, &intake),
                        &intake,
                        &crate::field::tokenize(intake.content())
                    )
                    .is_err()
            );
            drop(store);
            let reopened = Store::open(&tmp.0).unwrap();
            assert_eq!(reopened.record_count().unwrap(), 0, "stage {stage}");
            assert_eq!(reopened.epoch().unwrap(), 0, "stage {stage}");
            for term in crate::field::tokenize(intake.content()) {
                assert!(
                    reopened.postings(&term).unwrap().is_empty(),
                    "stage {stage}: {term}"
                );
            }
            let txn = reopened.env.begin_ro_txn().unwrap();
            assert_eq!(
                txn.get(reopened.default, &META_NEXT_RECORD).unwrap(),
                bytes_u64(0)
            );
            assert!(matches!(
                txn.get(reopened.nullifiers, &intake.operation_id().as_bytes()),
                Err(lmdb::Error::NotFound)
            ));
            assert!(matches!(
                txn.get(reopened.receipts, &intake.operation_id().as_bytes()),
                Err(lmdb::Error::NotFound)
            ));
            drop(txn);
            let next = request(&reopened, [stage.wrapping_add(10); 16], 0, "synthetic next");
            assert_eq!(
                reopened
                    .commit_intake(
                        capability(&reopened, &next),
                        &next,
                        &crate::field::tokenize(next.content())
                    )
                    .unwrap()
                    .receipt
                    .record_id,
                0
            );
        }
    }

    #[test]
    fn incompatible_and_partial_formats_refuse_without_data_mutation() {
        for (label, version, realm, marker, dbs) in [
            ("unversioned", vec![], vec![7; 16], false, 1),
            ("old", vec![0, 0, 0, 2], vec![7; 16], false, 0),
            ("v3", vec![0, 0, 0, 3], vec![7; 16], false, 0),
            // v5 is fresh-only: pre-v5 stores refuse, no migration/adoption.
            ("v4", vec![0, 0, 0, 4], vec![7; 16], false, 0),
            ("future", vec![0, 0, 0, 6], vec![7; 16], false, 0),
            ("bad-version", vec![3], vec![7; 16], false, 0),
            (
                "bad-realm",
                STORE_FORMAT_VERSION.to_be_bytes().to_vec(),
                vec![7; 15],
                false,
                0,
            ),
            (
                "missing-db",
                STORE_FORMAT_VERSION.to_be_bytes().to_vec(),
                vec![7; 16],
                false,
                6,
            ),
            ("initializing", vec![], vec![], true, 4),
        ] {
            let tmp = TempStore::new(label);
            raw_header(&tmp.0, &version, &realm, marker, dbs);
            let before = data_hash(&tmp.0);
            let error = Store::open(&tmp.0)
                .err()
                .expect("unsupported fixture must refuse");
            match label {
                "old" | "v3" | "v4" | "unversioned" => {
                    assert!(matches!(error, StoreError::IncompatibleFormat))
                }
                "future" => assert!(matches!(error, StoreError::UnsupportedFutureVersion)),
                "bad-version" | "bad-realm" => {
                    assert!(matches!(error, StoreError::CorruptVersionHeader))
                }
                _ => assert!(matches!(error, StoreError::InterruptedInitialization)),
            }
            assert_eq!(data_hash(&tmp.0), before, "{label}");
            assert!(Store::open_readonly(&tmp.0).is_err(), "{label}");
            assert_eq!(data_hash(&tmp.0), before, "{label}");
        }
        for db_count in 0..=7 {
            let tmp = TempStore::new(&format!("initializing-{db_count}"));
            raw_header(&tmp.0, &[], &[], true, db_count);
            let before = data_hash(&tmp.0);
            assert!(matches!(
                Store::open(&tmp.0),
                Err(StoreError::InterruptedInitialization)
            ));
            assert!(matches!(
                Store::open_readonly(&tmp.0),
                Err(StoreError::InterruptedInitialization)
            ));
            assert_eq!(data_hash(&tmp.0), before);
        }
        for key in [
            META_EPOCH,
            META_NEXT_RECORD,
            META_NEXT_RELATION.as_bytes(),
            META_SWEEP.as_bytes(),
        ] {
            let tmp = TempStore::new("bad-counter-width");
            let store = Store::open(&tmp.0).unwrap();
            let mut txn = store.env.begin_rw_txn().unwrap();
            txn.put(store.default, &key, &[0; 7], lmdb::WriteFlags::empty())
                .unwrap();
            txn.commit().unwrap();
            drop(store);
            let before = data_hash(&tmp.0);
            assert!(matches!(
                Store::open(&tmp.0),
                Err(StoreError::CorruptVersionHeader)
            ));
            assert!(matches!(
                Store::open_readonly(&tmp.0),
                Err(StoreError::CorruptVersionHeader)
            ));
            assert_eq!(data_hash(&tmp.0), before);
        }
    }

    #[test]
    fn one_sided_nullifier_and_receipt_state_is_corrupt() {
        for remove_receipt in [false, true] {
            let tmp = TempStore::new(if remove_receipt {
                "missing-receipt"
            } else {
                "missing-nullifier"
            });
            let store = Store::open(&tmp.0).unwrap();
            let intake = request(&store, [8; 16], 0, "synthetic pairing");
            store
                .commit_intake(
                    capability(&store, &intake),
                    &intake,
                    &crate::field::tokenize(intake.content()),
                )
                .unwrap();
            let operation_id = intake.operation_id();
            let mut txn = store.env.begin_rw_txn().unwrap();
            txn.del(
                if remove_receipt {
                    store.receipts
                } else {
                    store.nullifiers
                },
                operation_id.as_bytes(),
                None,
            )
            .unwrap();
            txn.commit().unwrap();
            assert!(matches!(
                store.lookup_intake_receipt(&intake),
                Err(StoreError::Intake(IntakeError::CorruptCommitState))
            ));
        }
    }

    #[test]
    fn paired_receipt_v2_compiler_bindings_refuse_without_lookup_mutation() {
        for field in ["capability_class", "compiler_scope", "authority_digest"] {
            let tmp = TempStore::new(&format!("receipt-v2-{field}"));
            let store = Store::open(&tmp.0).unwrap();
            let intake = request(&store, [34; 16], 0, "synthetic receipt v2");
            store
                .commit_intake(
                    capability(&store, &intake),
                    &intake,
                    &crate::field::tokenize(intake.content()),
                )
                .unwrap();
            let mut txn = store.env.begin_rw_txn().unwrap();
            let envelope = decode_receipt_envelope(
                txn.get(store.receipts, intake.operation_id().as_bytes())
                    .unwrap(),
            )
            .unwrap();
            let CommitReceiptEnvelopeV5::IntakeV2(mut receipt) = envelope else {
                panic!("expected a committed intake envelope");
            };
            match field {
                "capability_class" => receipt.capability_class ^= 0xff,
                "compiler_scope" => receipt.compiler_scope.push_str(".corrupt"),
                "authority_digest" => receipt.authority_digest[0] ^= 0xff,
                _ => unreachable!(),
            }
            let corrupted =
                encode_receipt_envelope(&CommitReceiptEnvelopeV5::IntakeV2(receipt)).unwrap();
            txn.put(
                store.receipts,
                intake.operation_id().as_bytes(),
                &corrupted,
                lmdb::WriteFlags::empty(),
            )
            .unwrap();
            txn.commit().unwrap();
            let before = data_hash(&tmp.0);

            assert!(matches!(
                store.lookup_intake_receipt(&intake),
                Err(StoreError::Intake(IntakeError::CorruptCommitState))
            ));
            assert_eq!(store.record_count().unwrap(), 1);
            assert_eq!(store.epoch().unwrap(), 1);
            assert_eq!(data_hash(&tmp.0), before, "{field}");
        }
    }

    #[test]
    fn relation_and_sweep_counters_fail_closed_and_preserve_state() {
        for (label, key, allocate) in [
            (
                "relation",
                META_NEXT_RELATION,
                Store::alloc_relation_id as fn(&Store) -> Result<u64, StoreError>,
            ),
            (
                "sweep",
                META_SWEEP,
                Store::alloc_sweep as fn(&Store) -> Result<u64, StoreError>,
            ),
        ] {
            let tmp = TempStore::new(&format!("counter-normal-{label}"));
            let store = Store::open(&tmp.0).unwrap();
            assert_eq!(allocate(&store).unwrap(), 0);
            assert_eq!(allocate(&store).unwrap(), 1);
            drop(store);
            let reopened = Store::open(&tmp.0).unwrap();
            let txn = reopened.env.begin_ro_txn().unwrap();
            assert_eq!(txn.get(reopened.default, &key).unwrap(), bytes_u64(2));
            drop(txn);

            for (case, value, delete) in [
                ("malformed", vec![0; 7], false),
                ("missing", vec![], true),
                ("max", u64::MAX.to_be_bytes().to_vec(), false),
            ] {
                let tmp = TempStore::new(&format!("counter-{label}-{case}"));
                let store = Store::open(&tmp.0).unwrap();
                let mut txn = store.env.begin_rw_txn().unwrap();
                if delete {
                    txn.del(store.default, &key, None).unwrap();
                } else {
                    txn.put(store.default, &key, &value, lmdb::WriteFlags::empty())
                        .unwrap();
                }
                txn.commit().unwrap();
                let before = data_hash(&tmp.0);
                let result = allocate(&store);
                match case {
                    "max" => assert!(matches!(result, Err(StoreError::CounterOverflow { .. }))),
                    _ => assert!(matches!(result, Err(StoreError::CorruptVersionHeader))),
                }
                assert_eq!(data_hash(&tmp.0), before, "{label}-{case}");
                drop(store);
                if case == "max" {
                    let reopened = Store::open(&tmp.0).unwrap();
                    let txn = reopened.env.begin_ro_txn().unwrap();
                    assert_eq!(
                        txn.get(reopened.default, &key).unwrap(),
                        u64::MAX.to_be_bytes()
                    );
                } else {
                    assert!(matches!(
                        Store::open(&tmp.0),
                        Err(StoreError::CorruptVersionHeader)
                    ));
                }
            }
        }
    }

    fn sweep_request(
        store: &Store,
        op: [u8; 16],
        epoch: u64,
        effects: Vec<SweepEffect>,
        observed: SweepObserved,
    ) -> SweepRequest {
        SweepRequest::synthetic(
            &RatifiedChannel::stub("synthetic-store-test"),
            OperationId::from_bytes(op),
            store.realm_id().unwrap(),
            epoch,
            SWEEP_PROFILE_V1,
            observed,
            [6; 32],
            crate::sweep::VolatileUsageSnapshot::synthetic([3; 16], 1, Vec::new()),
            effects,
        )
        .unwrap()
    }

    fn sweep_capability(store: &Store, request: &SweepRequest) -> CommitCapability {
        authorize_sweep(
            &RatifiedChannel::stub("synthetic-store-test"),
            request,
            &store.authorization_snapshot().unwrap(),
        )
        .unwrap()
    }

    fn create_effect(src: u64, dst: u64) -> SweepEffect {
        SweepEffect::CreateSupersedes {
            src,
            dst,
            confidence_bits: 0.9_f32.to_bits(),
            rule_id: crate::field::RULE_ID.into(),
        }
    }

    fn sweep_observed(
        records: u64,
        bytes: u64,
        largest: u64,
        relations: u64,
        effects: u64,
    ) -> SweepObserved {
        SweepObserved {
            records_scanned: records,
            raw_record_bytes: bytes,
            largest_record_bytes: largest,
            postings_bytes: 0,
            token_occurrences: 0,
            relations_scanned: relations,
            pair_examinations: 0,
            effects,
        }
    }

    #[test]
    fn sweep_commit_replay_and_cross_kind_conflict() {
        let tmp = TempStore::new("sweep-commit-replay");
        let store = Store::open(&tmp.0).unwrap();
        let first = request(&store, [1; 16], 0, "sweep source one");
        let second = request(&store, [2; 16], 1, "sweep source two");
        store
            .commit_intake(
                capability(&store, &first),
                &first,
                &crate::field::tokenize(first.content()),
            )
            .unwrap();
        store
            .commit_intake(
                capability(&store, &second),
                &second,
                &crate::field::tokenize(second.content()),
            )
            .unwrap();
        assert_eq!(store.epoch().unwrap(), 2);

        let sweep = sweep_request(
            &store,
            [7; 16],
            2,
            vec![create_effect(1, 0)],
            sweep_observed(2, 40, 25, 0, 1),
        );
        // Two fresh capabilities for the same plan: one commits, one retries.
        // Re-authorizing after the commit would (correctly) be stale, so the
        // retry uses authority issued while the plan's epoch was current.
        let capability_commit = sweep_capability(&store, &sweep);
        let capability_retry = sweep_capability(&store, &sweep);
        let outcome = store.commit_sweep(capability_commit, &sweep).unwrap();
        assert_eq!(outcome.disposition, CommitDisposition::Committed);
        assert_eq!(outcome.receipt.sweep_id, 0);
        assert_eq!(store.epoch().unwrap(), 3);
        let relations = store.iter_relations().unwrap();
        assert_eq!(relations.len(), 1);
        assert_eq!((relations[0].src(), relations[0].dst()), (1, 0));

        // Same-process retry replays without applying anything.
        let retry = store.commit_sweep(capability_retry, &sweep).unwrap();
        assert_eq!(retry.disposition, CommitDisposition::Replay);
        assert_eq!(retry.receipt, outcome.receipt);
        assert_eq!(store.epoch().unwrap(), 3);

        // Cross-restart replay: fresh capability bound to the stored plan digest.
        let operation_id = OperationId::from_bytes([7; 16]);
        let cached = store.lookup_sweep_receipt(operation_id).unwrap().unwrap();
        let replay_capability = authorize_sweep_replay(
            &RatifiedChannel::stub("synthetic-store-test"),
            cached.manifest_digest,
            operation_id,
            cached.realm_id,
            &store.authorization_snapshot().unwrap(),
        )
        .unwrap();
        let replayed = store.replay_sweep(replay_capability, operation_id).unwrap();
        assert_eq!(replayed.disposition, CommitDisposition::Replay);
        assert_eq!(replayed.receipt, outcome.receipt);

        // The same operation id may not be reused by intake (cross-kind conflict).
        let collide = request(&store, [7; 16], 3, "colliding intake payload");
        let result = store.commit_intake(
            capability(&store, &collide),
            &collide,
            &crate::field::tokenize(collide.content()),
        );
        assert!(matches!(
            result,
            Err(StoreError::Sweep(SweepError::CrossKindConflict))
        ));
        assert_eq!(store.epoch().unwrap(), 3);
        assert_eq!(store.record_count().unwrap(), 2);
    }

    #[test]
    fn sweep_commit_abort_rolls_back_every_stage() {
        for stage in 1..=5 {
            let tmp = TempStore::new(&format!("sweep-rollback-{stage}"));
            let store = Store::open(&tmp.0).unwrap();
            let first = request(&store, [stage; 16], 0, "sweep rollback source one");
            let second = request(
                &store,
                [stage.wrapping_add(40); 16],
                1,
                "sweep rollback source two",
            );
            store
                .commit_intake(
                    capability(&store, &first),
                    &first,
                    &crate::field::tokenize(first.content()),
                )
                .unwrap();
            store
                .commit_intake(
                    capability(&store, &second),
                    &second,
                    &crate::field::tokenize(second.content()),
                )
                .unwrap();
            let sweep = sweep_request(
                &store,
                [stage.wrapping_add(80); 16],
                2,
                vec![create_effect(1, 0)],
                sweep_observed(2, 40, 25, 0, 1),
            );
            store.fail_after_stage.set(Some(stage));
            assert!(
                store
                    .commit_sweep(sweep_capability(&store, &sweep), &sweep)
                    .is_err(),
                "stage {stage} must abort"
            );
            drop(store);
            let reopened = Store::open(&tmp.0).unwrap();
            assert_eq!(reopened.epoch().unwrap(), 2, "stage {stage}");
            assert!(
                reopened.iter_relations().unwrap().is_empty(),
                "stage {stage}"
            );
            let txn = reopened.env.begin_ro_txn().unwrap();
            assert_eq!(
                txn.get(reopened.default, &META_SWEEP.as_bytes()).unwrap(),
                bytes_u64(0),
                "stage {stage}"
            );
            assert_eq!(
                txn.get(reopened.default, &META_NEXT_RELATION.as_bytes())
                    .unwrap(),
                bytes_u64(0),
                "stage {stage}"
            );
            assert!(matches!(
                txn.get(reopened.nullifiers, sweep.operation_id().as_bytes()),
                Err(lmdb::Error::NotFound)
            ));
            assert!(matches!(
                txn.get(reopened.receipts, sweep.operation_id().as_bytes()),
                Err(lmdb::Error::NotFound)
            ));
        }
    }

    #[test]
    fn sweep_state_conflict_refuses_without_mutation() {
        let tmp = TempStore::new("sweep-state-conflict");
        let store = Store::open(&tmp.0).unwrap();
        let first = request(&store, [11; 16], 0, "state conflict source one");
        let second = request(&store, [12; 16], 1, "state conflict source two");
        store
            .commit_intake(
                capability(&store, &first),
                &first,
                &crate::field::tokenize(first.content()),
            )
            .unwrap();
        store
            .commit_intake(
                capability(&store, &second),
                &second,
                &crate::field::tokenize(second.content()),
            )
            .unwrap();
        let create = sweep_request(
            &store,
            [13; 16],
            2,
            vec![create_effect(1, 0)],
            sweep_observed(2, 48, 27, 0, 1),
        );
        store
            .commit_sweep(sweep_capability(&store, &create), &create)
            .unwrap();
        assert_eq!(store.epoch().unwrap(), 3);

        let wrong = sweep_request(
            &store,
            [14; 16],
            3,
            vec![SweepEffect::SetRelationState {
                relation_id: 0,
                expected_prior_state: crate::field::RelationState::Persistent,
                next_state: crate::field::RelationState::Cold,
            }],
            sweep_observed(2, 48, 27, 1, 1),
        );
        let before = data_hash(&tmp.0);
        let result = store.commit_sweep(sweep_capability(&store, &wrong), &wrong);
        assert!(matches!(
            result,
            Err(StoreError::Sweep(SweepError::StateConflict {
                relation_id: 0
            }))
        ));
        assert_eq!(store.epoch().unwrap(), 3);
        assert_eq!(data_hash(&tmp.0), before);

        let right = sweep_request(
            &store,
            [15; 16],
            3,
            vec![SweepEffect::SetRelationState {
                relation_id: 0,
                expected_prior_state: crate::field::RelationState::Candidate,
                next_state: crate::field::RelationState::Persistent,
            }],
            sweep_observed(2, 48, 27, 1, 1),
        );
        let outcome = store
            .commit_sweep(sweep_capability(&store, &right), &right)
            .unwrap();
        assert_eq!(outcome.disposition, CommitDisposition::Committed);
        assert_eq!(
            store.iter_relations().unwrap()[0].state(),
            crate::field::RelationState::Persistent
        );
        assert_eq!(store.epoch().unwrap(), 4);
    }

    #[test]
    fn sweep_receipt_tamper_refuses_fail_closed() {
        let tmp = TempStore::new("sweep-receipt-tamper");
        let store = Store::open(&tmp.0).unwrap();
        let first = request(&store, [21; 16], 0, "tamper source one");
        let second = request(&store, [22; 16], 1, "tamper source two");
        store
            .commit_intake(
                capability(&store, &first),
                &first,
                &crate::field::tokenize(first.content()),
            )
            .unwrap();
        store
            .commit_intake(
                capability(&store, &second),
                &second,
                &crate::field::tokenize(second.content()),
            )
            .unwrap();
        let sweep = sweep_request(
            &store,
            [23; 16],
            2,
            vec![create_effect(1, 0)],
            sweep_observed(2, 40, 25, 0, 1),
        );
        store
            .commit_sweep(sweep_capability(&store, &sweep), &sweep)
            .unwrap();
        let operation_id = OperationId::from_bytes([23; 16]);
        let mut txn = store.env.begin_rw_txn().unwrap();
        let mut bytes = txn
            .get(store.receipts, operation_id.as_bytes())
            .unwrap()
            .to_vec();
        let last = bytes.len() - 1;
        bytes[last] ^= 0xff;
        txn.put(
            store.receipts,
            operation_id.as_bytes(),
            &bytes,
            lmdb::WriteFlags::empty(),
        )
        .unwrap();
        txn.commit().unwrap();
        assert!(matches!(
            store.lookup_sweep_receipt(operation_id),
            Err(StoreError::Sweep(SweepError::ReceiptState(_)))
        ));
    }

    // ── At-rest integration (Q39 slices A–B) ──────────────────────────────

    fn raw_record(store: &Store, id: u64) -> Vec<u8> {
        let txn = store.env.begin_ro_txn().unwrap();
        txn.get(store.records, &bytes_u64(id)).unwrap().to_vec()
    }

    fn commit_plaintext(store: &Store, op: [u8; 16], content: &str) -> (IntakeRequest, u64) {
        let intake = request(store, op, store.epoch().unwrap(), content);
        let outcome = store
            .commit_intake(
                capability(store, &intake),
                &intake,
                &crate::field::tokenize(intake.content()),
            )
            .unwrap();
        (intake, outcome.receipt.record_id)
    }

    #[test]
    fn at_rest_off_creates_no_keyring_and_stays_byte_identical() {
        let tmp = TempStore::new("at-rest-off");
        let before_reopen;
        {
            let store = Store::open_with_at_rest(&tmp.0, &AtRestConfig::off()).unwrap();
            assert_eq!(store.at_rest_status(), AtRestStatus::Absent);
            assert!(store.at_rest_state().is_none());

            let (intake, id) = commit_plaintext(&store, [41; 16], "plaintext body stays wire");
            let stored = raw_record(&store, id);
            assert!(!crate::at_rest::is_sealed_record(&stored));
            let decoded: WireRecord = rmp_serde::from_slice(&stored).unwrap();
            assert_eq!(decoded.content, intake.content());

            assert!(store.env.open_db(Some(crate::at_rest::KEYRING_DB)).is_err());
            assert!(!tmp.0.join(crate::at_rest::AT_REST_KEY_FILE).exists());
            before_reopen = data_hash(&tmp.0);
        }

        // Reopening off must not write a keyring DBI, a key file, or bytes.
        let store = Store::open(&tmp.0).unwrap();
        assert_eq!(store.at_rest_status(), AtRestStatus::Absent);
        assert_eq!(data_hash(&tmp.0), before_reopen);
        assert_eq!(
            store.get_record(0).unwrap().unwrap().content(),
            "plaintext body stays wire"
        );
    }

    #[test]
    fn at_rest_keyfile_seals_bodies_and_roundtrips_across_reopen() {
        let tmp = TempStore::new("at-rest-keyfile");
        let key = "aa".repeat(32);
        let (id, expected);
        {
            let store =
                Store::open_with_at_rest(&tmp.0, &AtRestConfig::keyfile_with_root_key(key.clone()))
                    .unwrap();
            assert_eq!(
                store.at_rest_state().unwrap().dek_count(),
                crate::at_rest::scope_count()
            );
            let (intake, record_id) = commit_plaintext(&store, [42; 16], "sealed body roundtrip");
            id = record_id;
            expected = intake.content().to_string();

            let stored = raw_record(&store, id);
            assert!(crate::at_rest::is_sealed_record(&stored));
            assert_eq!(&stored[..4], b"WMEN");

            let record = store.get_record(id).unwrap().unwrap();
            assert_eq!(record.content(), expected);
            assert_eq!(store.iter_records().unwrap().len(), 1);
            // Receipt replay re-verifies digests over the unsealed plaintext.
            let cached = store.lookup_intake_receipt(&intake).unwrap().unwrap();
            assert_eq!(cached.record_id, id);
        }

        let reopened =
            Store::open_with_at_rest(&tmp.0, &AtRestConfig::keyfile_with_root_key(key)).unwrap();
        assert_eq!(
            reopened.get_record(id).unwrap().unwrap().content(),
            expected
        );
    }

    #[test]
    fn at_rest_wrong_key_refuses_and_never_reinitializes() {
        let tmp = TempStore::new("at-rest-wrong-key");
        let key_a = "aa".repeat(32);
        let key_b = "bb".repeat(32);
        let before;
        {
            let store = Store::open_with_at_rest(
                &tmp.0,
                &AtRestConfig::keyfile_with_root_key(key_a.clone()),
            )
            .unwrap();
            before = store.at_rest_state().unwrap().meta().clone();
            let _ = commit_plaintext(&store, [43; 16], "bound to key A");
        }

        let error =
            match Store::open_with_at_rest(&tmp.0, &AtRestConfig::keyfile_with_root_key(key_b)) {
                Ok(_) => panic!("wrong root key must refuse"),
                Err(error) => error,
            };
        assert!(error.to_string().contains("unlock failed"), "{error}");

        let reopened =
            Store::open_with_at_rest(&tmp.0, &AtRestConfig::keyfile_with_root_key(key_a)).unwrap();
        assert_eq!(
            reopened.at_rest_state().unwrap().meta(),
            &before,
            "a failed unlock must never re-initialize the keyring"
        );
        assert_eq!(
            reopened.get_record(0).unwrap().unwrap().content(),
            "bound to key A"
        );
    }

    #[test]
    fn at_rest_off_writable_open_of_keyring_store_is_refused() {
        let tmp = TempStore::new("at-rest-split-brain");
        let key = "aa".repeat(32);
        let _ =
            Store::open_with_at_rest(&tmp.0, &AtRestConfig::keyfile_with_root_key(key)).unwrap();

        let error = match Store::open_with_at_rest(&tmp.0, &AtRestConfig::off()) {
            Ok(_) => panic!("plaintext writable open of an at-rest store must fail closed"),
            Err(error) => error,
        };
        let message = error.to_string();
        assert!(message.contains("keyring"), "{message}");
        assert!(message.contains("off"), "{message}");
        assert!(message.contains("split-brain"), "{message}");

        // Read-only inspection still discloses the mode without the key.
        match Store::open_readonly(&tmp.0).unwrap().at_rest_status() {
            AtRestStatus::Present(present) => {
                assert_eq!(present.meta.mode, crate::at_rest::AtRestMode::Keyfile);
                assert_eq!(present.wrapped_deks, crate::at_rest::scope_count());
            }
            other => panic!("expected Present, got {other:?}"),
        }
    }

    #[test]
    fn at_rest_sealed_value_without_key_fails_closed() {
        let tmp = TempStore::new("at-rest-no-key");
        let key = "aa".repeat(32);
        let id: u64;
        {
            let store = Store::open_with_at_rest(&tmp.0, &AtRestConfig::keyfile_with_root_key(key))
                .unwrap();
            (_, id) = commit_plaintext(&store, [44; 16], "needs the key to open");
        }

        let inspection = Store::open_readonly(&tmp.0).unwrap();
        let error = inspection.get_record(id).unwrap_err();
        assert!(error.to_string().contains("at-rest"), "{error}");
        assert!(
            error.to_string().contains("no at-rest key") || error.to_string().contains("sealed"),
            "{error}"
        );
        assert!(inspection.iter_records().is_err());
    }

    #[test]
    fn at_rest_migration_seals_plaintext_and_is_idempotent() {
        let tmp = TempStore::new("at-rest-migrate");
        let key = "aa".repeat(32);

        // Pre-existing plaintext records written while the store was `off`.
        let (legacy_one, id_one);
        {
            let store = Store::open_with_at_rest(&tmp.0, &AtRestConfig::off()).unwrap();
            let (request_one, record_one) =
                commit_plaintext(&store, [51; 16], "legacy plaintext one");
            let (_, record_two) = commit_plaintext(&store, [52; 16], "legacy plaintext two");
            legacy_one = request_one;
            id_one = record_one;
            assert!(!crate::at_rest::is_sealed_record(&raw_record(
                &store, record_one
            )));
            assert!(!crate::at_rest::is_sealed_record(&raw_record(
                &store, record_two
            )));
        }

        // Upgrade: the keyring initializes over the existing plaintext store.
        let store =
            Store::open_with_at_rest(&tmp.0, &AtRestConfig::keyfile_with_root_key(key)).unwrap();

        let dry = store.migrate_at_rest_records(1, true).unwrap();
        assert!(dry.dry_run);
        assert_eq!(dry.sealed, 2);
        assert_eq!(dry.already_sealed, 0);
        assert!(
            !crate::at_rest::is_sealed_record(&raw_record(&store, id_one)),
            "dry-run must not write"
        );

        let report = store.migrate_at_rest_records(1, false).unwrap();
        assert_eq!(report.sealed, 2);
        assert_eq!(report.skipped, 0);
        assert!(report.done);
        assert!(crate::at_rest::is_sealed_record(&raw_record(
            &store, id_one
        )));
        assert_eq!(
            store.get_record(id_one).unwrap().unwrap().content(),
            "legacy plaintext one"
        );
        // Sealed replay still validates (digest is over the plaintext body).
        assert!(store.lookup_intake_receipt(&legacy_one).is_ok());

        let ledger_after = store.at_rest_migration_ledger().unwrap().unwrap();
        assert_eq!(ledger_after.version, 1);
        let state = ledger_after.galaxies.get(RECORD_SCOPE).unwrap();
        assert!(state.done);
        assert_eq!(state.encrypted, 2);
        assert_eq!(state.cursor_hex.len(), 16);

        let second = store.migrate_at_rest_records(1, false).unwrap();
        assert_eq!(second.sealed, 0);
        assert!(second.done);
        assert_eq!(
            store.at_rest_migration_ledger().unwrap().unwrap(),
            ledger_after,
            "a completed pass must not rewrite the ledger"
        );
    }

    /// Wave-3 fix: a relation committed by ANOTHER handle (think: CLI sweep or
    /// a second server process) must be observed by an already-warm adjacency
    /// cache. The relation stamp is bumped in the writer's transaction, so the
    /// reader rebuilds instead of serving stale supersede/source resolution.
    #[test]
    fn relation_view_rebuilds_after_another_handles_write() {
        let tmp = TempStore::new("relations-cross-handle");
        let reader = Store::open(&tmp.0).unwrap();
        let writer = Store::open(&tmp.0).unwrap();

        let warm = reader.relations_view();
        assert!(
            warm.superseded_by.is_empty(),
            "fresh store has no relations"
        );
        assert!(reader.relations_view_cached(), "reader cache is warm");

        writer
            .put_relation(&Relation::new(1, 100, 101, 0.9, 0))
            .expect("second handle writes a relation");

        let observed = reader.relations_view();
        assert_eq!(
            observed.superseded_by.get(&101),
            Some(&1),
            "warm reader must observe the other handle's relation write"
        );
        assert!(observed.sources.contains(&100));

        // Same-handle writes keep invalidating as before.
        writer
            .put_relation(&Relation::associate(2, 101, 102, 0.4, 0))
            .expect("second relation write");
        let observed = reader.relations_view();
        assert!(
            observed
                .graph_edges
                .get(&102)
                .is_some_and(|edges| edges.iter().any(|(dst, _)| *dst == 101)),
            "associative edge from the other handle is observed too"
        );
    }
}
