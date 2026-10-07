//! Zero-dependency Gen2 LMDB compatibility reader and census module.
//!
//! Provides zero-loss, read-only extraction of legacy Gen2 `EpisodicRecord`s from
//! Gen2 LMDB stores without importing ANY Gen2 (`wm-*`) crate dependency, strictly
//! upholding Law Closure and Evidence Closure.
//!
//! In accordance with the Gen3 Kernel Contract (Article 1), this module NEVER directly
//! mutates any store; it is strictly a read-only compatibility surface for census,
//! inspection, and sovereign pulse compilation during migration.

use std::collections::{BTreeMap, HashSet};
use std::fmt;
use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};
use lmdb::{Cursor, Database, Environment, EnvironmentFlags, Transaction};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::ops::{ImportKind, RememberItem, Substrate};

fn bytes_to_hex(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        use std::fmt::Write;
        let _ = write!(s, "{b:02x}");
    }
    s
}

/// Errors encountered while reading or decoding legacy Gen2 stores.
#[derive(Debug)]
pub enum CompatError {
    Lmdb(lmdb::Error),
    Decode(rmp_serde::decode::Error),
    StoreNotFound(PathBuf),
    DatabaseNotFound(&'static str),
    InvalidKeyLength { expected: usize, actual: usize },
    Msg(String),
}

impl fmt::Display for CompatError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Lmdb(e) => write!(f, "compat lmdb error: {e}"),
            Self::Decode(e) => write!(f, "compat msgpack decode error: {e}"),
            Self::StoreNotFound(p) => {
                write!(f, "compat store directory not found: {}", p.display())
            }
            Self::DatabaseNotFound(db) => {
                write!(f, "compat database '{db}' not found in LMDB store")
            }
            Self::InvalidKeyLength { expected, actual } => {
                write!(f, "invalid key length: expected {expected}, got {actual}")
            }
            Self::Msg(m) => write!(f, "compat error: {m}"),
        }
    }
}

impl std::error::Error for CompatError {}

impl From<lmdb::Error> for CompatError {
    fn from(e: lmdb::Error) -> Self {
        Self::Lmdb(e)
    }
}

impl From<rmp_serde::decode::Error> for CompatError {
    fn from(e: rmp_serde::decode::Error) -> Self {
        Self::Decode(e)
    }
}

/// Broad class of an event in the Gen2 agent experience stream.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Gen2EpisodicKind {
    Observation,
    UserStatement,
    AssistantResponse,
    ToolCall,
    ToolResult,
    Decision,
    Error,
    SystemEvent,
}

impl fmt::Display for Gen2EpisodicKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Observation => write!(f, "observation"),
            Self::UserStatement => write!(f, "user_statement"),
            Self::AssistantResponse => write!(f, "assistant_response"),
            Self::ToolCall => write!(f, "tool_call"),
            Self::ToolResult => write!(f, "tool_result"),
            Self::Decision => write!(f, "decision"),
            Self::Error => write!(f, "error"),
            Self::SystemEvent => write!(f, "system_event"),
        }
    }
}

/// Origin of a Gen2 source record.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Gen2ProvenanceSource {
    User,
    Tool,
    Agent,
    External,
    System,
}

impl fmt::Display for Gen2ProvenanceSource {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::User => write!(f, "user"),
            Self::Tool => write!(f, "tool"),
            Self::Agent => write!(f, "agent"),
            Self::External => write!(f, "external"),
            Self::System => write!(f, "system"),
        }
    }
}

/// Source and authority metadata for a Gen2 episodic record.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Gen2Provenance {
    pub source: Gen2ProvenanceSource,
    pub actor: Option<String>,
    pub source_id: Option<Uuid>,
    pub confidence: f32,
}

/// Relation between a derived item and source evidence in Gen2.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Gen2EvidenceRelation {
    Supports,
    Contradicts,
    DerivedFrom,
    Supersedes,
}

/// A reference to source evidence in Gen2.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Gen2EvidenceRef {
    pub record_id: Uuid,
    pub relation: Gen2EvidenceRelation,
    pub start: Option<u32>,
    pub end: Option<u32>,
}

/// Current lifecycle state of a Gen2 source record.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "state")]
pub enum Gen2ValidityState {
    Active,
    Superseded { by: Uuid },
    Revoked { reason: String },
    Archived,
    Erased,
}

impl fmt::Display for Gen2ValidityState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Active => write!(f, "active"),
            Self::Superseded { by } => write!(f, "superseded(by: {by})"),
            Self::Revoked { reason } => write!(f, "revoked({reason})"),
            Self::Archived => write!(f, "archived"),
            Self::Erased => write!(f, "erased"),
        }
    }
}

/// Lossless source record for the v6 episodic memory lane in Gen2.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Gen2EpisodicRecord {
    pub schema_version: u16,
    pub id: Uuid,
    pub session_id: Option<Uuid>,
    pub sequence: u64,
    pub kind: Gen2EpisodicKind,
    pub content: String,
    pub content_hash: String,
    pub provenance: Gen2Provenance,
    pub validity: Gen2ValidityState,
    #[serde(default)]
    pub is_private: bool,
    #[serde(default)]
    pub model_exclude: bool,
    pub evidence: Vec<Gen2EvidenceRef>,
    pub created_at: DateTime<Utc>,
}

impl Gen2EpisodicRecord {
    /// Compute the expected SHA-256 hex digest for content.
    #[must_use]
    pub fn compute_content_hash(content: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    /// Validate that the record's content matches its immutable content hash.
    #[must_use]
    pub fn validate_hash(&self) -> bool {
        let expected = Self::compute_content_hash(&self.content);
        self.content_hash == expected
    }

    /// Map to a Gen3 `RememberItem` candidate for pulse compilation.
    #[must_use]
    pub fn to_remember_item(&self) -> RememberItem {
        let kind = match self.kind {
            Gen2EpisodicKind::Observation
            | Gen2EpisodicKind::UserStatement
            | Gen2EpisodicKind::AssistantResponse
            | Gen2EpisodicKind::ToolCall
            | Gen2EpisodicKind::ToolResult => ImportKind::Reported,
            Gen2EpisodicKind::SystemEvent
            | Gen2EpisodicKind::Error
            | Gen2EpisodicKind::Decision => ImportKind::System,
        };
        let source = self
            .provenance
            .actor
            .clone()
            .unwrap_or_else(|| format!("{}:{}", self.provenance.source, self.kind));
        RememberItem {
            content: self.content.clone(),
            source,
            kind,
        }
    }
}

/// Comprehensive census statistics extracted from a Gen2 LMDB store.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Gen2Census {
    pub store_path: PathBuf,
    pub total_records: u64,
    pub valid_hashes: u64,
    pub hash_mismatches: u64,
    pub kinds: BTreeMap<String, u64>,
    pub sources: BTreeMap<String, u64>,
    pub validity: BTreeMap<String, u64>,
    pub distinct_sessions: usize,
    pub earliest_record: Option<DateTime<Utc>>,
    pub latest_record: Option<DateTime<Utc>>,
    pub private_records: u64,
    pub model_exclude_records: u64,
}

impl Gen2Census {
    /// Integrity ratio (1.0 = 100% byte integrity of all contents against SHA-256 hashes).
    #[must_use]
    pub fn integrity_ratio(&self) -> f64 {
        if self.total_records == 0 {
            1.0
        } else {
            self.valid_hashes as f64 / self.total_records as f64
        }
    }
}

/// Read-only compatibility reader over a Gen2 LMDB memory store.
pub struct Gen2Reader {
    path: PathBuf,
    env: Environment,
    db: Database,
}

impl Gen2Reader {
    const DB_NAME: &'static str = "episodic_records";

    /// Open an existing Gen2 LMDB store in read-only, lock-free inspection mode.
    pub fn open(path: impl AsRef<Path>) -> Result<Self, CompatError> {
        let path = path.as_ref().to_path_buf();
        if !path.is_dir() {
            return Err(CompatError::StoreNotFound(path));
        }

        let env = Environment::new()
            .set_max_dbs(32)
            .set_flags(EnvironmentFlags::READ_ONLY | EnvironmentFlags::NO_LOCK)
            .open(&path)?;

        let db = env
            .open_db(Some(Self::DB_NAME))
            .map_err(|_| CompatError::DatabaseNotFound(Self::DB_NAME))?;

        Ok(Self { path, env, db })
    }

    /// Return the raw record count by scanning keys.
    pub fn count(&self) -> Result<u64, CompatError> {
        let tx = self.env.begin_ro_txn()?;
        let mut count = 0u64;
        {
            let mut cursor = tx.open_ro_cursor(self.db)?;
            for _ in cursor.iter() {
                count += 1;
            }
        }
        tx.commit()?;
        Ok(count)
    }

    /// Count rows in a named galaxy DBI without decoding them.
    ///
    /// Returns `Ok(None)` when the DBI is absent. Used for non-memory and
    /// sealed lanes where an exact volume count is needed for accounting but
    /// per-row decoding is neither safe nor useful.
    pub fn count_galaxy_db(&self, db_name: &str) -> Result<Option<u64>, CompatError> {
        let db = match self.env.open_db(Some(db_name)) {
            Ok(db) => db,
            Err(lmdb::Error::NotFound) => return Ok(None),
            Err(e) => return Err(CompatError::Lmdb(e)),
        };
        let tx = self.env.begin_ro_txn()?;
        let mut count = 0u64;
        {
            let mut cursor = tx.open_ro_cursor(db)?;
            for _ in cursor.iter() {
                count += 1;
            }
        }
        tx.commit()?;
        Ok(Some(count))
    }

    /// Read a single record by its 16-byte UUID.
    pub fn get_record(&self, id: Uuid) -> Result<Option<Gen2EpisodicRecord>, CompatError> {
        let tx = self.env.begin_ro_txn()?;
        match tx.get(self.db, id.as_bytes()) {
            Ok(bytes) => {
                let record: Gen2EpisodicRecord = rmp_serde::from_slice(bytes)?;
                tx.commit()?;
                Ok(Some(record))
            }
            Err(lmdb::Error::NotFound) => {
                tx.commit()?;
                Ok(None)
            }
            Err(e) => Err(CompatError::Lmdb(e)),
        }
    }

    /// Scan records with an optional maximum limit.
    pub fn scan_records(
        &self,
        limit: Option<usize>,
    ) -> Result<Vec<Gen2EpisodicRecord>, CompatError> {
        let tx = self.env.begin_ro_txn()?;
        let mut records = Vec::new();
        let max = limit.unwrap_or(usize::MAX);

        {
            let mut cursor = tx.open_ro_cursor(self.db)?;
            for (key, val) in cursor.iter() {
                if records.len() >= max {
                    break;
                }
                if key.len() != 16 {
                    return Err(CompatError::InvalidKeyLength {
                        expected: 16,
                        actual: key.len(),
                    });
                }
                let record: Gen2EpisodicRecord = rmp_serde::from_slice(val)?;
                records.push(record);
            }
        }
        tx.commit()?;
        Ok(records)
    }

    /// Run a complete census and integrity audit over the store.
    pub fn census(&self) -> Result<Gen2Census, CompatError> {
        let tx = self.env.begin_ro_txn()?;

        let mut total_records = 0u64;
        let mut valid_hashes = 0u64;
        let mut hash_mismatches = 0u64;
        let mut kinds: BTreeMap<String, u64> = BTreeMap::new();
        let mut sources: BTreeMap<String, u64> = BTreeMap::new();
        let mut validity: BTreeMap<String, u64> = BTreeMap::new();
        let mut sessions: HashSet<Uuid> = HashSet::new();
        let mut earliest_record: Option<DateTime<Utc>> = None;
        let mut latest_record: Option<DateTime<Utc>> = None;
        let mut private_records = 0u64;
        let mut model_exclude_records = 0u64;

        {
            let mut cursor = tx.open_ro_cursor(self.db)?;
            for (key, val) in cursor.iter() {
                if key.len() != 16 {
                    return Err(CompatError::InvalidKeyLength {
                        expected: 16,
                        actual: key.len(),
                    });
                }
                let record: Gen2EpisodicRecord = rmp_serde::from_slice(val)?;
                total_records += 1;

                if record.validate_hash() {
                    valid_hashes += 1;
                } else {
                    hash_mismatches += 1;
                }

                *kinds.entry(record.kind.to_string()).or_default() += 1;
                *sources
                    .entry(record.provenance.source.to_string())
                    .or_default() += 1;

                let validity_key = match &record.validity {
                    Gen2ValidityState::Active => "active".to_string(),
                    Gen2ValidityState::Superseded { .. } => "superseded".to_string(),
                    Gen2ValidityState::Revoked { .. } => "revoked".to_string(),
                    Gen2ValidityState::Archived => "archived".to_string(),
                    Gen2ValidityState::Erased => "erased".to_string(),
                };
                *validity.entry(validity_key).or_default() += 1;

                if let Some(sid) = record.session_id {
                    sessions.insert(sid);
                }

                if record.is_private {
                    private_records += 1;
                }
                if record.model_exclude {
                    model_exclude_records += 1;
                }

                earliest_record = match earliest_record {
                    None => Some(record.created_at),
                    Some(earliest) => Some(earliest.min(record.created_at)),
                };
                latest_record = match latest_record {
                    None => Some(record.created_at),
                    Some(latest) => Some(latest.max(record.created_at)),
                };
            }
        }

        tx.commit()?;

        Ok(Gen2Census {
            store_path: self.path.clone(),
            total_records,
            valid_hashes,
            hash_mismatches,
            kinds,
            sources,
            validity,
            distinct_sessions: sessions.len(),
            earliest_record,
            latest_record,
            private_records,
            model_exclude_records,
        })
    }

    /// Return the path to the legacy store directory.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Scan records from the legacy store, cleanly partitioning valid records from
    /// damaged or corrupted records with zero panics and complete forensic quarantine.
    pub fn scan_with_quarantine(
        &self,
        limit: Option<usize>,
        validate_hashes: bool,
    ) -> Result<(Vec<Gen2EpisodicRecord>, Vec<QuarantinedGen2Record>), CompatError> {
        let tx = self.env.begin_ro_txn()?;
        let mut valid_records = Vec::new();
        let mut quarantined = Vec::new();
        let max = limit.unwrap_or(usize::MAX);

        {
            let mut cursor = tx.open_ro_cursor(self.db)?;
            for (key, val) in cursor.iter() {
                if valid_records.len() >= max {
                    break;
                }
                let key_hex = bytes_to_hex(key);
                if key.len() != 16 {
                    quarantined.push(QuarantinedGen2Record {
                        raw_key_hex: key_hex,
                        raw_val_len: val.len(),
                        reason: format!("InvalidKeyLength: expected 16, got {}", key.len()),
                        timestamp: Utc::now(),
                    });
                    continue;
                }
                let record_res: Result<Gen2EpisodicRecord, _> = rmp_serde::from_slice(val);
                match record_res {
                    Ok(record) => {
                        if validate_hashes && !record.validate_hash() {
                            quarantined.push(QuarantinedGen2Record {
                                raw_key_hex: key_hex,
                                raw_val_len: val.len(),
                                reason: format!(
                                    "ContentHashMismatch: recorded={}, expected={}",
                                    record.content_hash,
                                    Gen2EpisodicRecord::compute_content_hash(&record.content)
                                ),
                                timestamp: Utc::now(),
                            });
                        } else if record.content.trim().is_empty() {
                            quarantined.push(QuarantinedGen2Record {
                                raw_key_hex: key_hex,
                                raw_val_len: val.len(),
                                reason: "EmptyContent".to_string(),
                                timestamp: Utc::now(),
                            });
                        } else {
                            valid_records.push(record);
                        }
                    }
                    Err(e) => {
                        quarantined.push(QuarantinedGen2Record {
                            raw_key_hex: key_hex,
                            raw_val_len: val.len(),
                            reason: format!("MsgPackDecodeError: {e}"),
                            timestamp: Utc::now(),
                        });
                    }
                }
            }
        }
        tx.commit()?;
        Ok((valid_records, quarantined))
    }
}

/// A record from a legacy store that was diverted into quarantine due to corruption or mismatch.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct QuarantinedGen2Record {
    pub raw_key_hex: String,
    pub raw_val_len: usize,
    pub reason: String,
    pub timestamp: DateTime<Utc>,
}

/// Options controlling legacy store migration into Gen3.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationOptions {
    pub batch_size: usize,
    pub dry_run: bool,
    pub validate_hashes: bool,
    pub allow_noise: bool,
    pub quarantine_path: Option<PathBuf>,
}

impl Default for MigrationOptions {
    fn default() -> Self {
        Self {
            batch_size: 100,
            dry_run: false,
            validate_hashes: true,
            allow_noise: false,
            quarantine_path: None,
        }
    }
}

/// Per-record-type accounting so no migrated, duplicated, or skipped record is
/// silent. `skipped` is keyed by normalized reason (for example
/// `decode_error`, `empty_content`, `non_memory_lane`, `sealed`,
/// `duplicate_exact`, `noise_class`, `refused_by_kernel`).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct RecordTypeAccounting {
    #[serde(default)]
    pub migrated: usize,
    #[serde(default)]
    pub duplicates: usize,
    #[serde(default)]
    pub skipped: BTreeMap<String, usize>,
}

impl RecordTypeAccounting {
    fn migrate(&mut self) {
        self.migrated += 1;
    }

    fn duplicate(&mut self) {
        self.duplicates += 1;
    }

    fn skip(&mut self, reason: &str) {
        *self.skipped.entry(reason.to_string()).or_default() += 1;
    }
}

/// Cryptographically verifiable receipt certifying a migration execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationReceipt {
    pub source_store: PathBuf,
    pub target_store: PathBuf,
    pub total_scanned: usize,
    pub migrated_count: usize,
    pub duplicate_skipped: usize,
    pub quarantined_count: usize,
    pub target_epoch: u64,
    pub timestamp: DateTime<Utc>,
    pub receipt_digest: String,
    /// v9 galaxy-substrate rows scanned (decoded + undecodable), across all
    /// discovered galaxy DBIs. Reported separately from the episodic
    /// `total_scanned` aggregate to preserve the historical receipt contract.
    #[serde(default)]
    pub galaxy_total_scanned: usize,
    /// v9 galaxy rows newly ingested into Gen3 galaxies.
    #[serde(default)]
    pub galaxy_migrated: usize,
    /// v9 galaxy rows already present (exact-content dedupe).
    #[serde(default)]
    pub galaxy_duplicates: usize,
    /// v9 galaxy rows a best-effort decoder could not read (quarantined).
    #[serde(default)]
    pub galaxy_decode_skipped: usize,
    /// v9 galaxy rows quarantined after decode (refusals, noise, emptiness).
    #[serde(default)]
    pub galaxy_quarantined: usize,
    /// Per-type migrated/duplicate/skip accounting. Episodic records appear as
    /// `episodic:<kind>`; galaxy rows as `galaxy:<v9-dbi>`.
    #[serde(default)]
    pub by_record_type: BTreeMap<String, RecordTypeAccounting>,
    /// True when this receipt describes a simulation: nothing was written to
    /// the target store and no quarantine file was created.
    #[serde(default)]
    pub dry_run: bool,
}

impl MigrationReceipt {
    #[must_use]
    pub fn compute_digest(
        source: &Path,
        target: &Path,
        scanned: usize,
        migrated: usize,
        skipped: usize,
        quarantined: usize,
        epoch: u64,
        ts: &DateTime<Utc>,
    ) -> String {
        let mut hasher = Sha256::new();
        hasher.update(source.to_string_lossy().as_bytes());
        hasher.update(b":");
        hasher.update(target.to_string_lossy().as_bytes());
        hasher.update(b":");
        hasher.update(scanned.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(migrated.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(skipped.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(quarantined.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(epoch.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(ts.to_rfc3339().as_bytes());
        format!("{:x}", hasher.finalize())
    }
}

/// Migrate a legacy Gen2 LMDB store into a Gen3 Substrate via sovereign pulses.
///
/// Available when the `operator` feature is enabled.
#[cfg(feature = "operator")]
pub fn migrate_gen2_to_gen3(
    reader: &Gen2Reader,
    substrate: &mut Substrate,
    options: &MigrationOptions,
) -> Result<MigrationReceipt, CompatError> {
    let authority = crate::evidence::RatifiedChannel::mint("wm-migration-operator");
    migrate_gen2_to_gen3_with_authority(reader, substrate, options, authority)
}

/// Migrate a legacy Gen2 LMDB store into a Gen3 Substrate using an explicitly provided intake authority.
///
/// Migrates both the v6 episodic lane (`episodic_records`) and every v9 galaxy
/// DBI discovered through [`GEN2_GALAXY_DBS`]. Galaxy rows are routed to their
/// Gen3 destination via [`gen3_galaxy_for_gen2_db`] using the canonical
/// `corpus:<galaxy>:<tags>` source convention, with the original v9 DBI kept
/// as a `v9db:<name>` tag. The migration is additive and idempotent: exact
/// content/source dedupe makes reruns no-ops, and undecodable galaxy rows are
/// quarantined with per-type accounting instead of being silently dropped.
pub fn migrate_gen2_to_gen3_with_authority(
    reader: &Gen2Reader,
    substrate: &mut Substrate,
    options: &MigrationOptions,
    authority: crate::evidence::RatifiedChannel,
) -> Result<MigrationReceipt, CompatError> {
    let (valid_records, mut quarantined) =
        reader.scan_with_quarantine(None, options.validate_hashes)?;
    let total_scanned = valid_records.len() + quarantined.len();

    let old_noise = substrate.noise_enabled();
    if options.allow_noise {
        substrate.set_noise_enabled(false);
    }

    let old_budget = substrate.budget();
    substrate.set_budget(0);

    let mut migrated_count = 0;
    let mut duplicate_skipped = 0;
    let mut by_record_type: BTreeMap<String, RecordTypeAccounting> = BTreeMap::new();

    substrate.set_intake_authority(authority);

    for chunk in valid_records.chunks(options.batch_size.max(1)) {
        let items: Vec<RememberItem> = chunk.iter().map(|r| r.to_remember_item()).collect();
        if options.dry_run {
            for (idx, item) in items.iter().enumerate() {
                let kind_tag = crate::ops::kind_tag(item.kind);
                let key = crate::ops::identity_key(&item.content, &item.source, kind_tag);
                let acct = by_record_type
                    .entry(format!("episodic:{}", chunk[idx].kind))
                    .or_default();
                if substrate.identity_map().contains_key(&key) {
                    duplicate_skipped += 1;
                    acct.duplicate();
                } else {
                    migrated_count += 1;
                    acct.migrate();
                }
            }
        } else {
            let outcomes = substrate.remember_batch(&items);
            for (idx, outcome) in outcomes.into_iter().enumerate() {
                let orig = &chunk[idx];
                let acct = by_record_type
                    .entry(format!("episodic:{}", orig.kind))
                    .or_default();
                match outcome {
                    Ok(record_id) => {
                        migrated_count += 1;
                        acct.migrate();
                        substrate.bind_uuid(orig.id, record_id);
                    }
                    Err(err) if err == "duplicate_exact" => {
                        duplicate_skipped += 1;
                        acct.duplicate();
                        let kind_tag = crate::ops::kind_tag(items[idx].kind);
                        let key = crate::ops::identity_key(
                            &items[idx].content,
                            &items[idx].source,
                            kind_tag,
                        );
                        if let Some(&existing_id) = substrate.identity_map().get(&key) {
                            substrate.bind_uuid(orig.id, existing_id);
                        }
                    }
                    Err(err) => {
                        acct.skip(if err == "noise_class" {
                            "noise_class"
                        } else {
                            "refused_by_kernel"
                        });
                        quarantined.push(QuarantinedGen2Record {
                            raw_key_hex: orig.id.as_hyphenated().to_string(),
                            raw_val_len: orig.content.len(),
                            reason: format!("RefusedByKernel: {err}"),
                            timestamp: Utc::now(),
                        });
                    }
                }
            }
        }
    }

    // ------------------------------------------------------------------
    // v9 galaxy DBI ingestion (additive; per-DB accounting; idempotent).
    // ------------------------------------------------------------------
    let mut galaxy_total_scanned = 0usize;
    let mut galaxy_migrated = 0usize;
    let mut galaxy_duplicates = 0usize;
    let mut galaxy_decode_skipped = 0usize;
    let mut galaxy_quarantined = 0usize;

    for db in GEN2_GALAXY_DBS {
        let acct_key = format!("galaxy:{db}");
        if !is_memory_galaxy_db(db) {
            if let Some(count) = reader.count_galaxy_db(db)? {
                galaxy_total_scanned += count as usize;
                let acct = by_record_type.entry(acct_key).or_default();
                *acct
                    .skipped
                    .entry("non_memory_lane".to_string())
                    .or_default() += count as usize;
            }
            continue;
        }

        let scan = match reader.scan_galaxy_db(db, None) {
            Ok(scan) => scan,
            Err(CompatError::Msg(msg)) if msg.starts_with("sealed") => {
                let count = reader.count_galaxy_db(db)?.unwrap_or(0) as usize;
                galaxy_total_scanned += count;
                let acct = by_record_type.entry(acct_key).or_default();
                *acct.skipped.entry("sealed".to_string()).or_default() += count;
                continue;
            }
            Err(err) => {
                let acct = by_record_type.entry(acct_key).or_default();
                acct.skip("scan_error");
                quarantined.push(QuarantinedGen2Record {
                    raw_key_hex: format!("<{db}>"),
                    raw_val_len: 0,
                    reason: format!("GalaxyScanError[{db}]: {err}"),
                    timestamp: Utc::now(),
                });
                continue;
            }
        };

        galaxy_total_scanned += scan.records.len() + scan.decode_skipped;
        galaxy_decode_skipped += scan.decode_skipped;
        galaxy_quarantined += scan.decode_skipped;
        {
            let acct = by_record_type.entry(acct_key.clone()).or_default();
            if scan.decode_skipped > 0 {
                *acct.skipped.entry("decode_error".to_string()).or_default() += scan.decode_skipped;
            }
        }
        quarantined.extend(scan.quarantined);

        for chunk in scan.records.chunks(options.batch_size.max(1)) {
            let items: Vec<RememberItem> = chunk.iter().map(galaxy_record_to_item).collect();
            let acct = by_record_type.entry(acct_key.clone()).or_default();
            if options.dry_run {
                for item in &items {
                    let kind_tag = crate::ops::kind_tag(item.kind);
                    let key = crate::ops::identity_key(&item.content, &item.source, kind_tag);
                    if substrate.identity_map().contains_key(&key) {
                        galaxy_duplicates += 1;
                        acct.duplicate();
                    } else {
                        galaxy_migrated += 1;
                        acct.migrate();
                    }
                }
            } else {
                let outcomes = substrate.remember_batch(&items);
                for (idx, outcome) in outcomes.into_iter().enumerate() {
                    let orig = &chunk[idx];
                    match outcome {
                        Ok(record_id) => {
                            galaxy_migrated += 1;
                            acct.migrate();
                            substrate.bind_uuid(orig.id, record_id);
                        }
                        Err(err) if err == "duplicate_exact" => {
                            galaxy_duplicates += 1;
                            acct.duplicate();
                            let kind_tag = crate::ops::kind_tag(items[idx].kind);
                            let key = crate::ops::identity_key(
                                &items[idx].content,
                                &items[idx].source,
                                kind_tag,
                            );
                            if let Some(&existing_id) = substrate.identity_map().get(&key) {
                                substrate.bind_uuid(orig.id, existing_id);
                            }
                        }
                        Err(err) => {
                            galaxy_quarantined += 1;
                            acct.skip(if err == "noise_class" {
                                "noise_class"
                            } else {
                                "refused_by_kernel"
                            });
                            quarantined.push(QuarantinedGen2Record {
                                raw_key_hex: orig.id.as_hyphenated().to_string(),
                                raw_val_len: orig.content.len(),
                                reason: format!("RefusedByKernel[{db}]: {err}"),
                                timestamp: Utc::now(),
                            });
                        }
                    }
                }
            }
        }
    }

    if options.allow_noise {
        substrate.set_noise_enabled(old_noise);
    }
    substrate.set_budget(old_budget);

    // Dry runs accumulate quarantine rows in memory/report only: no file is
    // created and no directory is touched.
    if !options.dry_run {
        if let Some(q_path) = &options.quarantine_path {
            if !quarantined.is_empty() {
                if let Some(parent) = q_path.parent() {
                    let _ = std::fs::create_dir_all(parent);
                }
                if let Ok(mut file) = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(q_path)
                {
                    use std::io::Write;
                    for q in &quarantined {
                        if let Ok(line) = serde_json::to_string(q) {
                            let _ = writeln!(file, "{line}");
                        }
                    }
                }
            }
        }
    }

    let target_epoch = substrate.store().epoch().unwrap_or(0);
    let now = Utc::now();
    let digest = MigrationReceipt::compute_digest(
        reader.path(),
        substrate.store().path(),
        total_scanned,
        migrated_count,
        duplicate_skipped,
        quarantined.len(),
        target_epoch,
        &now,
    );

    Ok(MigrationReceipt {
        source_store: reader.path().to_path_buf(),
        target_store: substrate.store().path().to_path_buf(),
        total_scanned,
        migrated_count,
        duplicate_skipped,
        quarantined_count: quarantined.len(),
        target_epoch,
        timestamp: now,
        receipt_digest: digest,
        galaxy_total_scanned,
        galaxy_migrated,
        galaxy_duplicates,
        galaxy_decode_skipped,
        galaxy_quarantined,
        by_record_type,
        dry_run: options.dry_run,
    })
}

/// Target-safe dry-run census: simulate the full migration without creating
/// the target store and without writing anything.
///
/// Unlike the general migration entry point, this function never opens a
/// store it could create: it requires `<target_store>/data.mdb` to already
/// exist and returns `CompatError::Msg` containing `target missing` otherwise
/// ("a nonzero-result dry run reports 'target missing' instead of creating").
/// No quarantine file is written; per-type skip accounting still rides in the
/// returned receipt.
#[cfg(any(test, feature = "operator"))]
pub fn dry_run_migration_census(
    reader: &Gen2Reader,
    target_store: &Path,
    options: &MigrationOptions,
) -> Result<MigrationReceipt, CompatError> {
    let data_mdb = target_store.join("data.mdb");
    if !data_mdb.is_file() {
        return Err(CompatError::Msg(format!(
            "target missing: {} does not contain data.mdb; dry-run never creates the target store",
            target_store.display()
        )));
    }

    // Open without a journal so no journal file is created, and force the
    // options into dry-run mode.
    let mut substrate = Substrate::open(target_store, None, crate::constitution::default_view())
        .map_err(CompatError::Msg)?;
    let mut dry_options = options.clone();
    dry_options.dry_run = true;
    dry_options.quarantine_path = None;
    #[cfg(test)]
    let authority = crate::evidence::RatifiedChannel::stub("wm-dry-run-census");
    #[cfg(not(test))]
    let authority = crate::evidence::RatifiedChannel::mint("wm-dry-run-census");
    migrate_gen2_to_gen3_with_authority(reader, &mut substrate, &dry_options, authority)
}

/// Project one v9 galaxy record onto a Gen3 `RememberItem`, routed through the
/// canonical `corpus:<gen3-galaxy>:<tags>` source convention.
fn galaxy_record_to_item(record: &Gen2GalaxyRecord) -> RememberItem {
    let galaxy = gen3_galaxy_for_gen2_db(&record.db);
    let mut tags: Vec<String> = record
        .tags
        .iter()
        .map(|t| t.trim().to_string())
        .filter(|t| !t.is_empty())
        .collect();
    tags.push(format!("v9db:{}", record.db));
    RememberItem {
        content: record.content.clone(),
        source: format!("corpus:{galaxy}:{}", tags.join(",")),
        kind: ImportKind::Reported,
    }
}

/// Map a v9 galaxy sub-database name to its Gen3 destination galaxy.
///
/// Gen3 decodes the destination from a record's `source` using the canonical
/// `corpus:<galaxy>:<tags>` convention (`starter_galaxy::extract_galaxy_from_source`),
/// so migration writes `corpus:<mapped>:<tags>,v9db:<original>`. The `v9db:`
/// tag keeps the provenance of the original lane visible even when it is
/// normalized away.
///
/// Mapping table (everything unmapped defaults to `codex`):
///
/// | v9 DBI      | Gen3 galaxy | rationale                                        |
/// |-------------|-------------|--------------------------------------------------|
/// | `codex`     | `codex`     | canonical long-term store                        |
/// | `journals`  | `journals`  | journaling lane has a natural Gen3 counterpart   |
/// | `dreams`    | `dreams`    | dream-cycle artifacts stay together              |
/// | `research`  | `research`  | research lane has a natural Gen3 counterpart     |
/// | `sessions`  | `sessions`  | session evidence stays addressable per session   |
/// | `universal` | `universal` | shared foundational corpus                       |
/// | `tutorial`  | `guide`     | v9 tutorial content is the Gen3 starter guide    |
/// | `substrate` | `codex`     | v9-internal substrate lane folds into `codex`    |
/// | `aria`      | `codex`     | v9-only feeling-tone lane folds into `codex`     |
/// | `citta`     | `codex`     | v9-only mental-factor lane folds into `codex`    |
///
/// Infrastructure lanes carried in `GEN2_GALAXY_DBS` but not memory-bearing
/// (`associations`, `embeddings`, `karma`, `dharma`, `valkyrie`, `receipts`)
/// are recorded under `non_memory_lane` accounting rather than being force-
/// decoded as memories; see [`is_memory_galaxy_db`].
#[must_use]
pub fn gen3_galaxy_for_gen2_db(db: &str) -> &'static str {
    match db {
        "codex" => "codex",
        "journals" => "journals",
        "dreams" => "dreams",
        "research" => "research",
        "sessions" => "sessions",
        "universal" => "universal",
        "tutorial" => "guide",
        "substrate" | "aria" | "citta" => "codex",
        _ => "codex",
    }
}

/// Whether a v9 galaxy DBI is expected to contain `Memory` wrapper records.
///
/// The declared non-memory lanes are counted with an explicit
/// `non_memory_lane` skip reason and are never decoded as memories, which
/// keeps multi-million-row infrastructure tables (e.g. `karma`) from being
/// quarantined row-by-row.
#[must_use]
pub fn is_memory_galaxy_db(db: &str) -> bool {
    matches!(
        db,
        "aria"
            | "citta"
            | "codex"
            | "dreams"
            | "journals"
            | "research"
            | "sessions"
            | "substrate"
            | "telemetry"
            | "tutorial"
            | "universal"
    )
}

/// Known v9-era galaxy LMDB sub-databases (`Galaxy::db_name()` vocabulary).
pub const GEN2_GALAXY_DBS: &[&str] = &[
    "aria",
    "citta",
    "codex",
    "journals",
    "dreams",
    "research",
    "sessions",
    "substrate",
    "tutorial",
    "universal",
    "karma",
    "dharma",
    "associations",
    "embeddings",
    "valkyrie",
    "telemetry",
    "receipts",
];

/// Minimal decode target for v9 `Memory` records. Unknown fields — including
/// binary coordinate/embedding blobs that a JSON value cannot represent — are
/// skipped by serde, so no v9 crate dependency is needed.
#[derive(Debug, Default, Deserialize)]
struct V9MemoryLite {
    #[serde(default)]
    metadata: V9MetadataLite,
    #[serde(default)]
    content: String,
}

#[derive(Debug, Default, Deserialize)]
struct V9MetadataLite {
    #[serde(default, deserialize_with = "deserialize_uuid_lenient")]
    id: Option<Uuid>,
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default)]
    importance: f32,
    #[serde(default)]
    created_at: Option<String>,
    #[serde(default)]
    model_exclude: bool,
    #[serde(default)]
    is_private: bool,
    #[serde(default)]
    source: Option<String>,
    #[serde(default)]
    agent_id: Option<String>,
    #[serde(default)]
    title: Option<String>,
    #[serde(default)]
    topic: Option<String>,
}

/// Accept a UUID encoded either as msgpack bytes (non-human-readable v9
/// encoding) or as a hyphenated string.
fn deserialize_uuid_lenient<'de, D>(deserializer: D) -> Result<Option<Uuid>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum UuidOrString {
        Uuid(Uuid),
        String(String),
    }
    let value = Option::<UuidOrString>::deserialize(deserializer)?;
    Ok(match value {
        Some(UuidOrString::Uuid(id)) => Some(id),
        Some(UuidOrString::String(s)) => Uuid::parse_str(&s).ok(),
        None => None,
    })
}

/// Frozen pre-`70495ef` positional schema (30-field metadata array), ported
/// from the v9 codec's `LegacyMemory`. Unneeded positions decode as
/// `IgnoredAny` so binary encodings cannot poison extraction; the exact order
/// is load-bearing and must not be edited.
#[derive(Deserialize)]
struct V9LegacyMemory {
    metadata: V9LegacyMetadata,
    content: String,
    #[serde(default)]
    _embedding: Option<serde::de::IgnoredAny>,
}

/// Frozen pre-`70495ef` positional metadata schema, ported from the v9 codec's
/// `LegacyMemory`. Fields are read by fixed position. The exact order is
/// load-bearing and must not be edited.
struct V9LegacyMetadata {
    id: Uuid,
    tags: Vec<String>,
    importance: f32,
    created_at: Option<String>,
    is_private: bool,
    model_exclude: bool,
    source: Option<String>,
    agent_id: Option<String>,
    title: Option<String>,
    topic: Option<String>,
}

impl<'de> Deserialize<'de> for V9LegacyMetadata {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        struct LegacyVisitor;

        impl<'de> serde::de::Visitor<'de> for LegacyVisitor {
            type Value = V9LegacyMetadata;

            fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                write!(
                    f,
                    "a v9 legacy positional metadata array (at least 26 fields)"
                )
            }

            fn visit_seq<A>(self, mut seq: A) -> Result<Self::Value, A::Error>
            where
                A: serde::de::SeqAccess<'de>,
            {
                use serde::de::Error as _;
                // Positions 0..=25 are required. A truncated array must fail
                // (and be quarantined) rather than silently defaulting
                // `tags`/`importance`; nil is still accepted for the
                // `Option`-typed positions because the v9 schema stores them
                // as nullable, so only element *presence* is mandatory.
                // Positions 26+ (`tier`, `class`, `dup_count`,
                // `revision_count`) are optional tail fields and are drained.
                macro_rules! required {
                    ($idx:expr, $ty:ty) => {
                        seq.next_element::<$ty>()?
                            .ok_or_else(|| A::Error::invalid_length($idx, &self))?
                    };
                }

                let id: Uuid = required!(0, Uuid);
                let _galaxy = required!(1, serde::de::IgnoredAny);
                let _content_hash = required!(2, serde::de::IgnoredAny);
                let tags: Vec<String> = required!(3, Vec<String>);
                let importance: f32 = required!(4, f32);
                let created_at: Option<String> = required!(5, Option<String>);
                for idx in 6..16 {
                    required!(idx, serde::de::IgnoredAny);
                }
                let is_private: bool = required!(16, bool);
                let model_exclude: bool = required!(17, bool);
                let source: Option<String> = required!(18, Option<String>);
                for idx in 19..23 {
                    required!(idx, serde::de::IgnoredAny);
                }
                let agent_id: Option<String> = required!(23, Option<String>);
                let title: Option<String> = required!(24, Option<String>);
                let topic: Option<String> = required!(25, Option<String>);
                while seq.next_element::<serde::de::IgnoredAny>()?.is_some() {}
                Ok(V9LegacyMetadata {
                    id,
                    tags,
                    importance,
                    created_at,
                    is_private,
                    model_exclude,
                    source,
                    agent_id,
                    title,
                    topic,
                })
            }
        }

        deserializer.deserialize_seq(LegacyVisitor)
    }
}

/// One decoded v9 galaxy record (extracted fields; unknown v9 fields skipped).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Gen2GalaxyRecord {
    pub db: String,
    pub id: Uuid,
    pub content: String,
    pub created_at: DateTime<Utc>,
    pub tags: Vec<String>,
    pub importance: f32,
    pub is_private: bool,
    pub model_exclude: bool,
    #[serde(default)]
    pub source: Option<String>,
    #[serde(default)]
    pub agent_id: Option<String>,
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub topic: Option<String>,
}

/// A galaxy scan: decoded records plus the count of undecodable records
/// (legacy positional encodings outside the named-field schema) and the
/// forensic quarantine rows for those undecodable records.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Gen2GalaxyScan {
    pub records: Vec<Gen2GalaxyRecord>,
    pub decode_skipped: usize,
    #[serde(default)]
    pub quarantined: Vec<QuarantinedGen2Record>,
}

/// One v9 `session_turn` record (parsed from a Sessions-galaxy record body).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Gen2SessionTurn {
    #[serde(default)]
    pub session_id: String,
    #[serde(default)]
    pub sequence: u64,
    #[serde(default = "default_turn_role")]
    pub role: String,
    #[serde(default)]
    pub turn_type: String,
    #[serde(default)]
    pub content: serde_json::Value,
    #[serde(default)]
    pub importance: f64,
    #[serde(default)]
    pub timestamp: u64,
    #[serde(default)]
    pub track: Option<String>,
    #[serde(default)]
    pub turn_id: Option<String>,
    #[serde(default, rename = "type")]
    pub record_type: String,
}

fn default_turn_role() -> String {
    "user".to_string()
}

/// One decoded v9 session-galaxy record of any accepted type.
///
/// `record_type` is the normalized Gen3 lane (`session_turn`, `session_start`,
/// `checkpoint`, `session_end`, `message`); `source_type` preserves the
/// literal v9 `type` string (empty when the payload was untyped or raw text).
/// `record_id` is the stable v9 LMDB record UUID, used for exact idempotence
/// and as the session-lane fallback when the payload carries no session id.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Gen2SessionRecord {
    pub record_id: Uuid,
    pub created_at: DateTime<Utc>,
    pub tags: Vec<String>,
    pub record_type: String,
    pub source_type: String,
    pub session_id: String,
    pub sequence: u64,
    pub role: String,
    pub turn_id: String,
    pub content: String,
    pub parsed: Option<serde_json::Value>,
    pub timestamp: u64,
    pub importance: f64,
    pub track: Option<String>,
    pub encoding: String,
}

/// Normalize a v9 session payload `type` into a Gen3 session lane. Unknown
/// typed payloads are preserved as `message` (their literal type survives in
/// [`Gen2SessionRecord::source_type`]) so nothing is silently dropped.
fn normalize_session_type(raw: &str) -> &'static str {
    match raw {
        "session_turn" | "turn" => "session_turn",
        "session_start" | "start" => "session_start",
        "checkpoint" | "session_checkpoint" | "session_summary" | "summary" => "checkpoint",
        "session_end" | "session_close" => "session_end",
        _ => "message",
    }
}

/// Receipt for a v9 session-turn migration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionMigrationReceipt {
    pub source_store: PathBuf,
    pub target_session_log: PathBuf,
    pub total_turns: usize,
    pub migrated: usize,
    pub duplicates_skipped: usize,
    pub quarantined: usize,
    pub decode_skipped: usize,
    pub sessions: usize,
    pub timestamp: DateTime<Utc>,
    pub receipt_digest: String,
    /// Per-lane migrated/duplicate/skip accounting (`session_turn`,
    /// `session_start`, `checkpoint`, `session_end`, `message`).
    #[serde(default)]
    pub by_type: BTreeMap<String, RecordTypeAccounting>,
    /// Aggregate skip reasons across every lane.
    #[serde(default)]
    pub skipped_by_reason: BTreeMap<String, usize>,
    /// Path of the forensic quarantine log for undecodable session rows, when
    /// any were written.
    #[serde(default)]
    pub quarantine_log: Option<PathBuf>,
    /// True when this receipt describes a simulation: neither the session log
    /// nor a quarantine file was created.
    #[serde(default)]
    pub dry_run: bool,
}

impl SessionMigrationReceipt {
    #[must_use]
    pub fn compute_digest(
        source: &Path,
        target: &Path,
        total: usize,
        migrated: usize,
        skipped: usize,
        quarantined: usize,
        decode_skipped: usize,
        ts: &DateTime<Utc>,
    ) -> String {
        let mut hasher = Sha256::new();
        hasher.update(source.to_string_lossy().as_bytes());
        hasher.update(b":");
        hasher.update(target.to_string_lossy().as_bytes());
        hasher.update(b":");
        hasher.update(total.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(migrated.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(skipped.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(quarantined.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(decode_skipped.to_string().as_bytes());
        hasher.update(b":");
        hasher.update(ts.to_rfc3339().as_bytes());
        format!("{:x}", hasher.finalize())
    }
}

impl Gen2Reader {
    /// Scan one v9 galaxy sub-database. Absent DBIs yield an empty scan.
    ///
    /// At-rest sealed records (`WMEN` magic) are refused loudly rather than
    /// mis-parsed; records outside the named-field schema are counted in
    /// `decode_skipped` instead of aborting the scan.
    pub fn scan_galaxy_db(
        &self,
        db_name: &str,
        limit: Option<usize>,
    ) -> Result<Gen2GalaxyScan, CompatError> {
        let db = match self.env.open_db(Some(db_name)) {
            Ok(db) => db,
            Err(lmdb::Error::NotFound) => {
                return Ok(Gen2GalaxyScan {
                    records: Vec::new(),
                    decode_skipped: 0,
                    quarantined: Vec::new(),
                });
            }
            Err(e) => return Err(CompatError::Lmdb(e)),
        };

        let tx = self.env.begin_ro_txn()?;
        let mut records = Vec::new();
        let mut quarantined: Vec<QuarantinedGen2Record> = Vec::new();
        let mut sealed = false;
        let max = limit.unwrap_or(usize::MAX);
        {
            let mut cursor = tx.open_ro_cursor(db)?;
            for (key, val) in cursor.iter() {
                if records.len() >= max {
                    break;
                }
                if val.starts_with(b"WMEN") {
                    sealed = true;
                    break;
                }
                match decode_galaxy_record(db_name, key, val) {
                    Ok(record) => records.push(record),
                    Err(e) => quarantined.push(QuarantinedGen2Record {
                        raw_key_hex: bytes_to_hex(key),
                        raw_val_len: val.len(),
                        reason: format!("GalaxyDecodeError[{db_name}]: {e}"),
                        timestamp: Utc::now(),
                    }),
                }
            }
        }
        tx.commit()?;

        if sealed {
            return Err(CompatError::Msg(format!(
                "sealed (at-rest) records present in '{db_name}'; the store's                  WM_AT_REST key material is required to read them"
            )));
        }
        Ok(Gen2GalaxyScan {
            records,
            decode_skipped: quarantined.len(),
            quarantined,
        })
    }

    /// Scan every known v9 galaxy sub-database.
    pub fn scan_all_galaxy_dbs(
        &self,
        limit_per_db: Option<usize>,
    ) -> Result<Gen2GalaxyScan, CompatError> {
        let mut all = Gen2GalaxyScan {
            records: Vec::new(),
            decode_skipped: 0,
            quarantined: Vec::new(),
        };
        for db in GEN2_GALAXY_DBS {
            let scan = self.scan_galaxy_db(db, limit_per_db)?;
            all.records.extend(scan.records);
            all.decode_skipped += scan.decode_skipped;
            all.quarantined.extend(scan.quarantined);
        }
        Ok(all)
    }

    /// Parse all v9 `session_turn` records from the Sessions galaxy.
    ///
    /// Returns `(turns, decode_skipped)`; turns sort by
    /// (timestamp, session_id, sequence) so replay order is stable even when
    /// records were written concurrently.
    pub fn session_turns(&self) -> Result<(Vec<Gen2SessionTurn>, usize), CompatError> {
        let scan = self.scan_galaxy_db("sessions", None)?;
        let mut skipped = scan.decode_skipped;
        let mut turns = Vec::new();
        for record in scan.records {
            match serde_json::from_str::<Gen2SessionTurn>(&record.content) {
                Ok(turn) => {
                    if turn.record_type != "session_turn" || turn.session_id.is_empty() {
                        skipped += 1;
                        continue;
                    }
                    turns.push(turn);
                }
                Err(_) => skipped += 1,
            }
        }
        turns.sort_by(|a, b| {
            a.timestamp
                .cmp(&b.timestamp)
                .then_with(|| a.session_id.cmp(&b.session_id))
                .then_with(|| a.sequence.cmp(&b.sequence))
        });
        Ok((turns, skipped))
    }

    /// Parse every accepted v9 session record from the Sessions galaxy.
    ///
    /// Accepts `session_turn`, `session_start`, `checkpoint`/`session_summary`,
    /// `session_end`, and `message` payloads (typed JSON), plus untyped JSON
    /// and raw-text rows as best-effort `message` records. Rows that cannot be
    /// decoded at all are returned as forensic quarantine entries instead of
    /// aborting the scan. Records sort by (timestamp, session_id, sequence) so
    /// replay order is stable even when records were written concurrently.
    ///
    /// Returns `(records, quarantine)`; `quarantine.len()` is the count of
    /// undecodable rows.
    pub fn session_records(
        &self,
    ) -> Result<(Vec<Gen2SessionRecord>, Vec<QuarantinedGen2Record>), CompatError> {
        let scan = self.scan_galaxy_db("sessions", None)?;
        let mut quarantined = scan.quarantined;
        let mut records = Vec::new();

        for wrapper in scan.records {
            if wrapper.content.trim().is_empty() {
                quarantined.push(QuarantinedGen2Record {
                    raw_key_hex: wrapper.id.as_hyphenated().to_string(),
                    raw_val_len: wrapper.content.len(),
                    reason: format!("EmptySessionContent[{}]", wrapper.db),
                    timestamp: Utc::now(),
                });
                continue;
            }

            let parsed = serde_json::from_str::<serde_json::Value>(&wrapper.content).ok();
            let object = parsed.as_ref().and_then(|v| v.as_object());
            let source_type = object
                .and_then(|o| o.get("type"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim()
                .to_string();
            let record_type = normalize_session_type(&source_type);
            let encoding = if parsed.is_some() { "json" } else { "text" };

            let string_field = |key: &str| -> Option<String> {
                object
                    .and_then(|o| o.get(key))
                    .and_then(|v| v.as_str())
                    .map(str::trim)
                    .filter(|s| !s.is_empty())
                    .map(str::to_string)
            };

            let session_id = string_field("session_id")
                .or_else(|| string_field("session"))
                .or_else(|| string_field("id"))
                .or_else(|| string_field("cascadeId"))
                .unwrap_or_else(|| wrapper.id.as_hyphenated().to_string());

            let turn_id =
                string_field("turn_id").unwrap_or_else(|| wrapper.id.as_hyphenated().to_string());

            let mut timestamp = object
                .and_then(|o| o.get("timestamp"))
                .and_then(serde_json::Value::as_u64)
                .unwrap_or(0);
            // v9 mixed seconds and milliseconds; normalize ms to seconds.
            if timestamp > 100_000_000_000 {
                timestamp /= 1000;
            }
            if timestamp == 0 {
                timestamp = wrapper.created_at.timestamp().max(0) as u64;
            }

            let sequence = object
                .and_then(|o| o.get("sequence"))
                .and_then(serde_json::Value::as_u64)
                .unwrap_or(0);

            let role = string_field("role").unwrap_or_else(|| match record_type {
                "session_start" | "checkpoint" | "session_end" => "system".to_string(),
                _ => "user".to_string(),
            });

            let importance = object
                .and_then(|o| o.get("importance"))
                .and_then(serde_json::Value::as_f64)
                .unwrap_or(wrapper.importance as f64);

            let track = string_field("track");

            records.push(Gen2SessionRecord {
                record_id: wrapper.id,
                created_at: wrapper.created_at,
                tags: wrapper.tags,
                record_type: record_type.to_string(),
                source_type,
                session_id,
                sequence,
                role,
                turn_id,
                content: wrapper.content,
                parsed,
                timestamp,
                importance,
                track,
                encoding: encoding.to_string(),
            });
        }

        records.sort_by(|a, b| {
            a.timestamp
                .cmp(&b.timestamp)
                .then_with(|| a.session_id.cmp(&b.session_id))
                .then_with(|| a.sequence.cmp(&b.sequence))
        });
        Ok((records, quarantined))
    }
}

fn decode_galaxy_record(
    db_name: &str,
    key: &[u8],
    value: &[u8],
) -> Result<Gen2GalaxyRecord, CompatError> {
    // Legacy positional layout: fixarray(3) whose first element is the
    // metadata array (fixarray <16 fields when truncated/corrupt, array16
    // for the frozen 30, array32 for later 32-field stores). Detecting short
    // arrays too means a truncated row fails the positional visitor's
    // minimum-length check and is quarantined with a precise reason instead
    // of being mis-decoded as a named map. Modern writes are named maps.
    if value.starts_with(&[0x93])
        && value
            .get(1)
            .is_some_and(|b| matches!(b, 0x90..=0x9f | 0xdc | 0xdd))
    {
        let legacy: V9LegacyMemory = rmp_serde::from_slice(value)?;
        if legacy.content.trim().is_empty() {
            return Err(CompatError::Msg(format!(
                "legacy galaxy record in '{db_name}' has empty content"
            )));
        }
        let created_at = legacy
            .metadata
            .created_at
            .as_deref()
            .and_then(|s| DateTime::parse_from_rfc3339(s).ok())
            .map_or_else(Utc::now, |d| d.with_timezone(&Utc));
        return Ok(Gen2GalaxyRecord {
            db: db_name.to_string(),
            id: legacy.metadata.id,
            content: legacy.content,
            created_at,
            tags: legacy.metadata.tags,
            importance: legacy.metadata.importance,
            is_private: legacy.metadata.is_private,
            model_exclude: legacy.metadata.model_exclude,
            source: legacy.metadata.source,
            agent_id: legacy.metadata.agent_id,
            title: legacy.metadata.title,
            topic: legacy.metadata.topic,
        });
    }

    let lite: V9MemoryLite = rmp_serde::from_slice(value)?;
    let id = lite
        .metadata
        .id
        .or_else(|| {
            (key.len() == 16)
                .then(|| Uuid::from_slice(key).ok())
                .flatten()
        })
        .ok_or_else(|| {
            CompatError::Msg(format!(
                "galaxy record in '{db_name}' has no usable id (metadata.id / 16-byte key)"
            ))
        })?;

    if lite.content.trim().is_empty() {
        return Err(CompatError::Msg(format!(
            "galaxy record in '{db_name}' has empty content"
        )));
    }

    let created_at = lite
        .metadata
        .created_at
        .as_deref()
        .and_then(|s| DateTime::parse_from_rfc3339(s).ok())
        .map_or_else(Utc::now, |d| d.with_timezone(&Utc));

    Ok(Gen2GalaxyRecord {
        db: db_name.to_string(),
        id,
        content: lite.content,
        created_at,
        tags: lite.metadata.tags,
        importance: lite.metadata.importance,
        is_private: lite.metadata.is_private,
        model_exclude: lite.metadata.model_exclude,
        source: lite.metadata.source,
        agent_id: lite.metadata.agent_id,
        title: lite.metadata.title,
        topic: lite.metadata.topic,
    })
}

/// Options controlling v9 session-record migration.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SessionMigrationOptions {
    /// Simulate only: neither the session log nor a quarantine file is
    /// written; the receipt still carries would-migrate and skip accounting.
    pub dry_run: bool,
    /// Override for the forensic quarantine log. Defaults to
    /// `session_quarantine.jsonl` next to the session log.
    pub quarantine_path: Option<PathBuf>,
}

/// Migrate v9 session records into a Gen3 store's `session_log.jsonl` — the
/// source of truth for Gen3 `session.continuity` and `session.recall`.
///
/// Accepts `session_turn`, `session_start`, `checkpoint`/`session_summary`,
/// `session_end`, and `message` payloads. Untyped JSON and raw-text rows are
/// preserved as best-effort `message` records keyed by their stable v9 record
/// UUID, so nothing is dropped without accounting. Every lane is counted in
/// [`SessionMigrationReceipt::by_type`]; undecodable rows are written to
/// `session_quarantine.jsonl` next to the log.
///
/// Read-only over the legacy store; idempotent via (turn_id) and
/// (session_id, sequence) keys. Substrate evidence ingestion of migrated
/// records is intentionally not part of this path: continuity/recall read the
/// log directly, and the galaxy-DBI path ingests the Sessions DBI into the
/// Substrate separately.
pub fn migrate_gen2_sessions_to_gen3(
    reader: &Gen2Reader,
    session_log_path: &Path,
) -> Result<SessionMigrationReceipt, CompatError> {
    migrate_gen2_sessions_to_gen3_with_options(
        reader,
        session_log_path,
        &SessionMigrationOptions::default(),
    )
}

/// [`migrate_gen2_sessions_to_gen3`] with explicit options. When
/// `options.dry_run` is set, nothing is written: no session log, no quarantine
/// file, no parent directories.
pub fn migrate_gen2_sessions_to_gen3_with_options(
    reader: &Gen2Reader,
    session_log_path: &Path,
    options: &SessionMigrationOptions,
) -> Result<SessionMigrationReceipt, CompatError> {
    use std::collections::{BTreeSet, HashSet};

    let (records, quarantined_rows) = reader.session_records()?;
    let decode_skipped = quarantined_rows.len();
    let total_records = records.len();

    let mut existing: HashSet<String> = HashSet::new();
    if let Ok(content) = std::fs::read_to_string(session_log_path) {
        for line in content.lines() {
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(line) {
                let sid = value
                    .get("session_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let tid = value.get("turn_id").and_then(|v| v.as_str()).unwrap_or("");
                existing.insert(format!("id:{tid}"));
                // Only turns carry a meaningful (session_id, sequence) key;
                // legacy entries without an explicit `type` are turns.
                let is_turn = value
                    .get("type")
                    .and_then(|v| v.as_str())
                    .is_none_or(|t| t == "session_turn");
                if is_turn {
                    if let Some(seq) = value.get("sequence").and_then(|v| v.as_u64()) {
                        existing.insert(format!("seq:{sid}:{seq}"));
                    }
                }
            }
        }
    }

    let mut entries = String::new();
    let mut migrated = 0usize;
    let mut duplicates_skipped = 0usize;
    let mut quarantined = 0usize;
    let mut sessions: BTreeSet<String> = BTreeSet::new();
    let mut by_type: BTreeMap<String, RecordTypeAccounting> = BTreeMap::new();
    let mut skipped_by_reason: BTreeMap<String, usize> = BTreeMap::new();

    if decode_skipped > 0 {
        let acct = by_type.entry("unknown".to_string()).or_default();
        *acct.skipped.entry("decode_error".to_string()).or_default() += decode_skipped;
        *skipped_by_reason
            .entry("decode_error".to_string())
            .or_default() += decode_skipped;
    }

    for record in &records {
        let acct = by_type.entry(record.record_type.clone()).or_default();
        if record.session_id.is_empty() {
            quarantined += 1;
            acct.skip("missing_session_id");
            *skipped_by_reason
                .entry("missing_session_id".to_string())
                .or_default() += 1;
            continue;
        }
        let is_turn = record.record_type == "session_turn";
        let duplicate = existing.contains(&format!("id:{}", record.turn_id))
            || (is_turn
                && record.sequence > 0
                && existing.contains(&format!("seq:{}:{}", record.session_id, record.sequence)));
        if duplicate {
            duplicates_skipped += 1;
            acct.duplicate();
            continue;
        }

        let content = record
            .parsed
            .clone()
            .unwrap_or_else(|| serde_json::Value::String(record.content.clone()));

        let mut entry = serde_json::Map::new();
        entry.insert("turn_id".into(), record.turn_id.clone().into());
        entry.insert("session_id".into(), record.session_id.clone().into());
        entry.insert("role".into(), record.role.clone().into());
        entry.insert("turn_type".into(), record.record_type.clone().into());
        entry.insert("type".into(), record.record_type.clone().into());
        entry.insert("content".into(), content);
        entry.insert("importance".into(), record.importance.into());
        entry.insert("timestamp".into(), record.timestamp.into());
        if is_turn {
            entry.insert("sequence".into(), record.sequence.into());
        }
        if let Some(track) = &record.track {
            entry.insert("track".into(), track.clone().into());
        }
        if !record.source_type.is_empty() && record.source_type != record.record_type {
            entry.insert("legacy_type".into(), record.source_type.clone().into());
        }
        if record.encoding != "json" {
            entry.insert("legacy_encoding".into(), record.encoding.clone().into());
        }
        entry.insert("migrated_from".into(), "gen2".into());

        entries.push_str(&serde_json::Value::Object(entry).to_string());
        entries.push('\n');
        sessions.insert(record.session_id.clone());
        migrated += 1;
        acct.migrate();
    }

    if migrated > 0 && !options.dry_run {
        if let Some(parent) = session_log_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let mut file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(session_log_path)
            .map_err(|e| CompatError::Msg(format!("session log open failed: {e}")))?;
        use std::io::Write;
        file.write_all(entries.as_bytes())
            .map_err(|e| CompatError::Msg(format!("session log append failed: {e}")))?;
    }

    let quarantine_path = options.quarantine_path.clone().unwrap_or_else(|| {
        session_log_path
            .parent()
            .map(|p| p.join("session_quarantine.jsonl"))
            .unwrap_or_else(|| PathBuf::from("session_quarantine.jsonl"))
    });
    let mut quarantine_log = None;
    if !options.dry_run && !quarantined_rows.is_empty() {
        if let Some(parent) = quarantine_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&quarantine_path)
        {
            use std::io::Write;
            for q in &quarantined_rows {
                if let Ok(line) = serde_json::to_string(q) {
                    let _ = writeln!(file, "{line}");
                }
            }
            quarantine_log = Some(quarantine_path);
        }
    }

    let ts = Utc::now();
    let receipt_digest = SessionMigrationReceipt::compute_digest(
        reader.path(),
        session_log_path,
        total_records,
        migrated,
        duplicates_skipped,
        quarantined,
        decode_skipped,
        &ts,
    );

    Ok(SessionMigrationReceipt {
        source_store: reader.path().to_path_buf(),
        target_session_log: session_log_path.to_path_buf(),
        total_turns: total_records,
        migrated,
        duplicates_skipped,
        quarantined,
        decode_skipped,
        sessions: sessions.len(),
        timestamp: ts,
        receipt_digest,
        by_type,
        skipped_by_reason,
        quarantine_log,
        dry_run: options.dry_run,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_record_hash_computation() {
        let content = "Hello WhiteMagic Gen3 compatibility";
        let hash = Gen2EpisodicRecord::compute_content_hash(content);
        assert_eq!(hash.len(), 64);

        let record = Gen2EpisodicRecord {
            schema_version: 1,
            id: Uuid::new_v4(),
            session_id: Some(Uuid::new_v4()),
            sequence: 1,
            kind: Gen2EpisodicKind::UserStatement,
            content: content.to_string(),
            content_hash: hash,
            provenance: Gen2Provenance {
                source: Gen2ProvenanceSource::User,
                actor: Some("lucas".to_string()),
                source_id: None,
                confidence: 1.0,
            },
            validity: Gen2ValidityState::Active,
            is_private: false,
            model_exclude: false,
            evidence: Vec::new(),
            created_at: Utc::now(),
        };

        assert!(record.validate_hash());
        let item = record.to_remember_item();
        assert_eq!(item.content, content);
        assert_eq!(item.source, "lucas");
    }

    #[test]
    fn test_msgpack_roundtrip() {
        let original = Gen2EpisodicRecord {
            schema_version: 1,
            id: Uuid::new_v4(),
            session_id: None,
            sequence: 42,
            kind: Gen2EpisodicKind::Observation,
            content: "Sensor metric 99.4%".to_string(),
            content_hash: Gen2EpisodicRecord::compute_content_hash("Sensor metric 99.4%"),
            provenance: Gen2Provenance {
                source: Gen2ProvenanceSource::Tool,
                actor: Some("sensor_probe".to_string()),
                source_id: None,
                confidence: 0.95,
            },
            validity: Gen2ValidityState::Active,
            is_private: false,
            model_exclude: false,
            evidence: Vec::new(),
            created_at: Utc::now(),
        };

        let encoded = rmp_serde::to_vec(&original).expect("serialize");
        let decoded: Gen2EpisodicRecord = rmp_serde::from_slice(&encoded).expect("deserialize");
        assert_eq!(original, decoded);
    }

    /// Build a synthetic named-field v9 `Memory` wrapper (no host fixture
    /// dependency). `content` is stored verbatim so raw-text and JSON payloads
    /// can both be exercised.
    fn synthetic_named_memory(id: Uuid, content: &str, galaxy: &str, tags: &[&str]) -> Vec<u8> {
        let memory = serde_json::json!({
            "metadata": {
                "id": id.to_string(),
                "galaxy": galaxy,
                "content_hash": "",
                "tags": tags,
                "importance": 0.8,
                "created_at": Utc::now().to_rfc3339(),
                "model_exclude": false,
                "is_private": false
            },
            "content": content,
        });
        rmp_serde::to_vec_named(&memory).expect("encode synthetic memory")
    }

    fn synthetic_memory(content: &str) -> Vec<u8> {
        synthetic_named_memory(Uuid::new_v4(), content, "sessions", &["synthetic"])
    }

    /// Synthetic v9 positional (`fixarray(3)`, 32-field metadata array) record
    /// bytes, matching the legacy encoding the named-field reader skips.
    #[derive(serde::Serialize)]
    #[allow(clippy::type_complexity)]
    struct LegacyMetaSeq(
        Uuid,
        String,
        String,
        Vec<String>,
        f32,
        String,
        String,
        u64,
        Vec<f32>,
        Vec<f32>,
        String,
        f32,
        f32,
        f32,
        f32,
        bool,
        bool,
        bool,
        String,
        f32,
        f32,
        u64,
        u64,
        String,
        Option<String>,
        Option<String>,
        String,
        String,
        u64,
        Vec<String>,
        Vec<String>,
        u64,
    );

    fn synthetic_legacy_positional(id: Uuid, content: &str, tags: &[&str]) -> Vec<u8> {
        let meta = LegacyMetaSeq(
            id,
            "codex".to_string(),
            "legacy-hash".to_string(),
            tags.iter().map(|t| (*t).to_string()).collect(),
            0.9,
            "2026-01-02T03:04:05Z".to_string(),
            "2026-01-02T03:04:05Z".to_string(),
            0,
            Vec::new(),
            Vec::new(),
            "long_term".to_string(),
            0.5,
            1.0,
            0.0,
            0.0,
            false,
            false,
            false,
            "agent".to_string(),
            0.7,
            30.0,
            0,
            1,
            "system".to_string(),
            None,
            None,
            "working".to_string(),
            "dialogue".to_string(),
            0,
            Vec::<String>::new(),
            Vec::<String>::new(),
            0,
        );
        rmp_serde::to_vec(&(meta, content.to_string(), Option::<u8>::None))
            .expect("encode legacy positional record")
    }

    /// A deliberately truncated positional row (10 metadata fields, far below
    /// the required 26) that must be quarantined, not silently defaulted.
    #[derive(serde::Serialize)]
    struct LegacyMetaTruncated(
        Uuid,
        String,
        String,
        Vec<String>,
        f32,
        String,
        String,
        u64,
        Vec<f32>,
        Vec<f32>,
    );

    fn synthetic_legacy_truncated(id: Uuid, content: &str) -> Vec<u8> {
        let meta = LegacyMetaTruncated(
            id,
            "codex".to_string(),
            "legacy-hash".to_string(),
            vec!["t".to_string()],
            0.9,
            "2026-01-02T03:04:05Z".to_string(),
            "2026-01-02T03:04:05Z".to_string(),
            0,
            Vec::new(),
            Vec::new(),
        );
        rmp_serde::to_vec(&(meta, content.to_string(), Option::<u8>::None))
            .expect("encode truncated positional record")
    }

    /// The minimum complete positional row (26 metadata fields: everything
    /// through `topic`). The documented optional tail (`tier`, `class`,
    /// `dup_count`, `revision_count`) is omitted and must still decode.
    #[derive(serde::Serialize)]
    #[allow(clippy::type_complexity)]
    struct LegacyMetaMinimum(
        Uuid,
        String,
        String,
        Vec<String>,
        f32,
        String,
        String,
        u64,
        Vec<f32>,
        Vec<f32>,
        String,
        f32,
        f32,
        f32,
        f32,
        bool,
        bool,
        bool,
        String,
        f32,
        f32,
        u64,
        u64,
        String,
        Option<String>,
        Option<String>,
    );

    fn synthetic_legacy_minimum(id: Uuid, content: &str) -> Vec<u8> {
        let meta = LegacyMetaMinimum(
            id,
            "codex".to_string(),
            "legacy-hash".to_string(),
            vec!["min".to_string()],
            0.7,
            "2026-03-04T05:06:07Z".to_string(),
            "2026-03-04T05:06:07Z".to_string(),
            0,
            Vec::new(),
            Vec::new(),
            "long_term".to_string(),
            0.5,
            1.0,
            0.0,
            0.0,
            false,
            false,
            false,
            "agent".to_string(),
            0.7,
            30.0,
            0,
            1,
            "system".to_string(),
            None,
            None,
        );
        rmp_serde::to_vec(&(meta, content.to_string(), Option::<u8>::None))
            .expect("encode minimum positional record")
    }

    /// Build a synthetic named-field v9 store with optional raw session values
    /// and galaxy DBIs (no host fixture dependency).
    fn write_synthetic_store_full(
        dir: &Path,
        episodic: &[Gen2EpisodicRecord],
        session_values: &[Vec<u8>],
        galaxies: &[(&str, Vec<Vec<u8>>)],
    ) {
        std::fs::create_dir_all(dir).expect("create synthetic store dir");
        let env = lmdb::Environment::new()
            .set_max_dbs(32)
            .open(dir)
            .expect("open synthetic lmdb env");

        let episodic_db = env
            .create_db(Some("episodic_records"), lmdb::DatabaseFlags::default())
            .expect("create episodic db");
        if !episodic.is_empty() {
            let mut tx = env.begin_rw_txn().expect("rw txn");
            for record in episodic {
                let value = rmp_serde::to_vec(record).expect("encode episodic");
                tx.put(
                    episodic_db,
                    record.id.as_bytes(),
                    &value,
                    lmdb::WriteFlags::default(),
                )
                .expect("put episodic");
            }
            tx.commit().expect("commit episodic");
        }

        if !session_values.is_empty() {
            let db = env
                .create_db(Some("sessions"), lmdb::DatabaseFlags::default())
                .expect("create sessions db");
            let mut tx = env.begin_rw_txn().expect("rw txn");
            for value in session_values {
                let id = Uuid::new_v4();
                tx.put(db, id.as_bytes(), value, lmdb::WriteFlags::default())
                    .expect("put session value");
            }
            tx.commit().expect("commit sessions");
        }

        for (name, values) in galaxies {
            let db = env
                .create_db(Some(name), lmdb::DatabaseFlags::default())
                .expect("create galaxy db");
            let mut tx = env.begin_rw_txn().expect("rw txn");
            for value in values {
                let id = Uuid::new_v4();
                tx.put(db, id.as_bytes(), value, lmdb::WriteFlags::default())
                    .expect("put galaxy value");
            }
            tx.commit().expect("commit galaxy db");
        }

        // Drop the env before any compat reader opens the same path (LMDB
        // allows one environment per path per process).
        drop(env);
    }

    /// Build a synthetic named-field v9 store (no host fixture dependency).
    fn write_synthetic_gen2_store(
        dir: &Path,
        episodic: &[Gen2EpisodicRecord],
        turns: &[serde_json::Value],
    ) {
        let session_values: Vec<Vec<u8>> = turns
            .iter()
            .map(|turn| synthetic_memory(&turn.to_string()))
            .collect();
        write_synthetic_store_full(dir, episodic, &session_values, &[]);
    }

    fn synthetic_episodic(content: &str, sequence: u64) -> Gen2EpisodicRecord {
        Gen2EpisodicRecord {
            schema_version: 1,
            id: Uuid::new_v4(),
            session_id: Some(Uuid::new_v4()),
            sequence,
            kind: Gen2EpisodicKind::SystemEvent,
            content: content.to_string(),
            content_hash: Gen2EpisodicRecord::compute_content_hash(content),
            provenance: Gen2Provenance {
                source: Gen2ProvenanceSource::System,
                actor: Some("synthetic".to_string()),
                source_id: None,
                confidence: 0.9,
            },
            validity: Gen2ValidityState::Active,
            is_private: false,
            model_exclude: false,
            evidence: Vec::new(),
            created_at: Utc::now(),
        }
    }

    fn synthetic_turn(session: &str, sequence: u64, content: &str) -> serde_json::Value {
        serde_json::json!({
            "type": "session_turn",
            "session_id": session,
            "sequence": sequence,
            "role": "user",
            "turn_type": "summary",
            "content": content,
            "importance": 0.8,
            "timestamp": 1_700_000_000u64 + sequence,
            "track": "synthetic"
        })
    }

    #[test]
    fn migration_rerun_is_idempotent() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-migrate-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");
        let episodic = vec![
            synthetic_episodic("first synthetic record", 1),
            synthetic_episodic("second synthetic record", 2),
            synthetic_episodic("third synthetic record", 3),
        ];
        write_synthetic_gen2_store(&src_copy, &episodic, &[]);

        let reader = Gen2Reader::open(&src_copy).expect("open synthetic gen2 store");
        let target = tmp.join("gen3");
        let journal = target.join("journal.jsonl");
        let options = MigrationOptions {
            quarantine_path: Some(tmp.join("quarantine.jsonl")),
            ..MigrationOptions::default()
        };

        let mut substrate = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("open target gen3 store");
        let first = migrate_gen2_to_gen3_with_authority(
            &reader,
            &mut substrate,
            &options,
            crate::evidence::RatifiedChannel::stub("wm-migration-test"),
        )
        .expect("first migration");
        assert_eq!(first.migrated_count, 3, "all synthetic records migrate");
        drop(substrate);

        let mut substrate = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("reopen target gen3 store");
        let second = migrate_gen2_to_gen3_with_authority(
            &reader,
            &mut substrate,
            &options,
            crate::evidence::RatifiedChannel::stub("wm-migration-test"),
        )
        .expect("second migration");
        assert_eq!(
            second.migrated_count, 0,
            "rerun must not migrate duplicates"
        );
        assert_eq!(
            second.duplicate_skipped, first.migrated_count,
            "rerun must classify exactly the previously migrated records as duplicates"
        );

        drop(substrate);
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn session_turn_migration_is_idempotent() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-sessions-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");
        let turns = vec![
            synthetic_turn("sess-a", 1, "first turn"),
            synthetic_turn("sess-b", 1, "other session turn"),
            synthetic_turn("sess-a", 2, "second turn"),
        ];
        write_synthetic_gen2_store(&src_copy, &[], &turns);

        let reader = Gen2Reader::open(&src_copy).expect("open synthetic gen2 store");
        let (parsed, decode_skipped) = reader.session_turns().expect("scan session turns");
        assert_eq!(parsed.len(), 3, "all synthetic turns decode");
        assert_eq!(decode_skipped, 0);

        let log = tmp.join("session_log.jsonl");

        let first = migrate_gen2_sessions_to_gen3(&reader, &log).expect("first session migration");
        assert_eq!(first.migrated, 3, "first run migrates every turn");
        assert_eq!(first.sessions, 2, "two distinct sessions");
        assert_eq!(first.quarantined, 0);

        let second =
            migrate_gen2_sessions_to_gen3(&reader, &log).expect("second session migration");
        assert_eq!(second.migrated, 0, "rerun must not append duplicate turns");
        assert_eq!(second.duplicates_skipped, first.migrated);
        let lines = std::fs::read_to_string(&log)
            .expect("read session log")
            .lines()
            .count();
        assert_eq!(
            lines, first.migrated,
            "session log holds exactly the migrated turns"
        );

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn galaxy_dbi_records_route_to_mapped_gen3_galaxy_and_are_idempotent() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-galaxy-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");
        let journals_id = Uuid::new_v4();
        let tutorial_id = Uuid::new_v4();
        write_synthetic_store_full(
            &src_copy,
            &[],
            &[],
            &[
                (
                    "journals",
                    vec![synthetic_named_memory(
                        journals_id,
                        "journal entry alpha",
                        "journals",
                        &["j1", "j2"],
                    )],
                ),
                (
                    "tutorial",
                    vec![synthetic_named_memory(
                        tutorial_id,
                        "guide lesson beta",
                        "tutorial",
                        &["t1"],
                    )],
                ),
            ],
        );

        let reader = Gen2Reader::open(&src_copy).expect("open synthetic store");
        let target = tmp.join("gen3");
        let journal = target.join("journal.jsonl");
        let options = MigrationOptions {
            batch_size: 8,
            quarantine_path: Some(tmp.join("quarantine.jsonl")),
            ..MigrationOptions::default()
        };

        let mut substrate = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("open target");
        let first = migrate_gen2_to_gen3_with_authority(
            &reader,
            &mut substrate,
            &options,
            crate::evidence::RatifiedChannel::stub("wm-migration-test"),
        )
        .expect("first migration");
        assert_eq!(first.galaxy_total_scanned, 2);
        assert_eq!(first.galaxy_migrated, 2);
        assert_eq!(first.galaxy_duplicates, 0);
        assert_eq!(first.galaxy_decode_skipped, 0);
        assert_eq!(first.by_record_type["galaxy:journals"].migrated, 1);
        assert_eq!(first.by_record_type["galaxy:tutorial"].migrated, 1);
        assert_eq!(substrate.store().record_count().unwrap(), 2);
        assert!(
            substrate.lookup_id_by_uuid(&journals_id).is_some(),
            "galaxy record id must bind to its Gen3 record"
        );
        assert!(substrate.lookup_id_by_uuid(&tutorial_id).is_some());

        let mut sources: Vec<String> = substrate
            .store()
            .iter_records()
            .expect("iter records")
            .iter()
            .map(|r| r.source().to_string())
            .collect();
        sources.sort();
        assert_eq!(
            sources,
            vec![
                "corpus:guide:t1,v9db:tutorial".to_string(),
                "corpus:journals:j1,j2,v9db:journals".to_string(),
            ]
        );
        drop(substrate);

        let mut substrate = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("reopen target");
        let second = migrate_gen2_to_gen3_with_authority(
            &reader,
            &mut substrate,
            &options,
            crate::evidence::RatifiedChannel::stub("wm-migration-test"),
        )
        .expect("second migration");
        assert_eq!(second.galaxy_migrated, 0, "galaxy rerun must not duplicate");
        assert_eq!(
            second.galaxy_duplicates, 2,
            "galaxy rerun classifies both rows as duplicates"
        );
        assert_eq!(substrate.store().record_count().unwrap(), 2);
        drop(substrate);

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn legacy_positional_galaxy_rows_are_recovered() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-legacy-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");
        let legacy_id = Uuid::new_v4();
        write_synthetic_store_full(
            &src_copy,
            &[],
            &[],
            &[(
                "codex",
                vec![synthetic_legacy_positional(
                    legacy_id,
                    "legacy recovered content",
                    &["legacy"],
                )],
            )],
        );

        let reader = Gen2Reader::open(&src_copy).expect("open synthetic store");
        let scan = reader
            .scan_galaxy_db("codex", None)
            .expect("scan legacy galaxy");
        assert_eq!(scan.decode_skipped, 0, "legacy positional rows must decode");
        assert_eq!(scan.records.len(), 1);
        let record = &scan.records[0];
        assert_eq!(record.id, legacy_id);
        assert_eq!(record.content, "legacy recovered content");
        assert_eq!(record.tags, vec!["legacy".to_string()]);
        assert_eq!(record.importance, 0.9);
        assert_eq!(
            record.created_at.to_rfc3339(),
            "2026-01-02T03:04:05+00:00",
            "legacy created_at survives the positional decode"
        );

        let target = tmp.join("gen3");
        let journal = target.join("journal.jsonl");
        let mut substrate = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("open target");
        let receipt = migrate_gen2_to_gen3_with_authority(
            &reader,
            &mut substrate,
            &MigrationOptions {
                batch_size: 4,
                quarantine_path: Some(tmp.join("quarantine.jsonl")),
                ..MigrationOptions::default()
            },
            crate::evidence::RatifiedChannel::stub("wm-migration-test"),
        )
        .expect("migration");
        assert_eq!(receipt.galaxy_migrated, 1);
        assert!(receipt.by_record_type["galaxy:codex"].skipped.is_empty());
        drop(substrate);

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn session_record_types_migrate_with_fields() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-seshapes-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");

        let start = serde_json::json!({
            "type": "session_start",
            "session_id": "sess-1",
            "title": "Start lane",
            "user": "opencode",
            "timestamp": 900u64
        });
        let checkpoint = serde_json::json!({
            "type": "checkpoint",
            "session_id": "sess-1",
            "label": "handoff",
            "handoff": {
                "next_queue": ["finish migration", "report"],
                "open_flags": ["flag-a"]
            },
            "timestamp": 1100u64
        });
        let turn = synthetic_turn("sess-1", 1, "hello world");
        let end = serde_json::json!({
            "type": "session_end",
            "session_id": "sess-1",
            "summary": "done",
            "timestamp": 1200u64
        });
        let untyped_with_sid = serde_json::json!({"foo": "bar", "session_id": "sess-2"});
        let untyped_no_sid = serde_json::json!({"artifactType": "PLAN", "summary": "detached"});

        write_synthetic_store_full(
            &src_copy,
            &[],
            &[
                synthetic_memory(&start.to_string()),
                synthetic_memory(&checkpoint.to_string()),
                synthetic_memory(&turn.to_string()),
                synthetic_memory(&end.to_string()),
                synthetic_memory("plain transcript text"),
                synthetic_memory(&untyped_with_sid.to_string()),
                synthetic_memory(&untyped_no_sid.to_string()),
            ],
            &[],
        );

        let reader = Gen2Reader::open(&src_copy).expect("open synthetic store");
        let (records, quarantine) = reader.session_records().expect("session records");
        assert_eq!(records.len(), 7);
        assert!(quarantine.is_empty());

        let log = tmp.join("session_log.jsonl");
        let first = migrate_gen2_sessions_to_gen3(&reader, &log).expect("first run");
        assert_eq!(first.migrated, 7, "every accepted record migrates");
        assert_eq!(first.duplicates_skipped, 0);
        assert_eq!(first.quarantined, 0);
        assert_eq!(first.decode_skipped, 0);
        assert_eq!(first.by_type["session_turn"].migrated, 1);
        assert_eq!(first.by_type["session_start"].migrated, 1);
        assert_eq!(first.by_type["checkpoint"].migrated, 1);
        assert_eq!(first.by_type["session_end"].migrated, 1);
        assert_eq!(first.by_type["message"].migrated, 3);
        assert_eq!(first.sessions, 4, "sess-1, sess-2, and two orphan lanes");

        let content = std::fs::read_to_string(&log).expect("read log");
        let lines: Vec<serde_json::Value> = content
            .lines()
            .map(|l| serde_json::from_str(l).expect("log line json"))
            .collect();
        assert_eq!(lines.len(), 7);

        let checkpoint_line = lines
            .iter()
            .find(|l| l["type"] == "checkpoint")
            .expect("checkpoint line present");
        assert_eq!(checkpoint_line["turn_type"], "checkpoint");
        assert_eq!(
            checkpoint_line["content"]["handoff"]["next_queue"],
            serde_json::json!(["finish migration", "report"])
        );
        assert_eq!(
            checkpoint_line["content"]["handoff"]["open_flags"],
            serde_json::json!(["flag-a"])
        );
        assert!(
            checkpoint_line.get("sequence").is_none(),
            "non-turn lanes must not claim the (session_id, sequence) dedupe key"
        );

        let start_line = lines
            .iter()
            .find(|l| l["type"] == "session_start")
            .expect("start line present");
        assert_eq!(start_line["content"]["title"], "Start lane");

        let raw_line = lines
            .iter()
            .find(|l| l["content"] == "plain transcript text")
            .expect("raw text message preserved");
        assert_eq!(raw_line["turn_type"], "message");
        assert_eq!(raw_line["legacy_encoding"], "text");

        let second = migrate_gen2_sessions_to_gen3(&reader, &log).expect("second run");
        assert_eq!(second.migrated, 0, "rerun must not append duplicates");
        assert_eq!(second.duplicates_skipped, 7);
        let line_count = std::fs::read_to_string(&log)
            .expect("read log")
            .lines()
            .count();
        assert_eq!(line_count, 7, "log holds exactly one copy of each record");

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn undecodable_rows_land_in_skip_accounting_and_quarantine() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-undecodable-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");

        let garbage_session = vec![0xc1u8, 0x00, 0xde, 0xad, 0xbe, 0xef];
        let garbage_galaxy = vec![0xc1u8, 0x99, 0x01, 0xff];
        write_synthetic_store_full(
            &src_copy,
            &[],
            &[garbage_session],
            &[("codex", vec![garbage_galaxy])],
        );

        let reader = Gen2Reader::open(&src_copy).expect("open synthetic store");
        let (records, quarantine) = reader.session_records().expect("session records");
        assert_eq!(records.len(), 0);
        assert_eq!(quarantine.len(), 1, "garbage session row is quarantined");
        assert!(quarantine[0].reason.contains("GalaxyDecodeError[sessions]"));

        let target = tmp.join("gen3");
        let journal = target.join("journal.jsonl");
        let main_quarantine = tmp.join("quarantine.jsonl");
        let mut substrate = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("open target");
        let receipt = migrate_gen2_to_gen3_with_authority(
            &reader,
            &mut substrate,
            &MigrationOptions {
                batch_size: 4,
                quarantine_path: Some(main_quarantine.clone()),
                ..MigrationOptions::default()
            },
            crate::evidence::RatifiedChannel::stub("wm-migration-test"),
        )
        .expect("migration");
        assert_eq!(
            receipt.galaxy_decode_skipped, 2,
            "codex garbage plus the garbage row in the sessions memory lane"
        );
        assert_eq!(
            receipt.by_record_type["galaxy:codex"].skipped["decode_error"],
            1
        );
        let main_log = std::fs::read_to_string(&main_quarantine).expect("main quarantine");
        assert!(main_log.contains("GalaxyDecodeError[codex]"));

        let log = tmp.join("session_log.jsonl");
        let session_receipt = migrate_gen2_sessions_to_gen3(&reader, &log).expect("session run");
        assert_eq!(session_receipt.decode_skipped, 1);
        assert_eq!(
            session_receipt.by_type["unknown"].skipped["decode_error"],
            1
        );
        assert_eq!(session_receipt.skipped_by_reason["decode_error"], 1);
        assert_eq!(
            session_receipt.quarantine_log,
            Some(tmp.join("session_quarantine.jsonl"))
        );
        let session_log = std::fs::read_to_string(tmp.join("session_quarantine.jsonl"))
            .expect("session quarantine log");
        assert!(session_log.contains("GalaxyDecodeError[sessions]"));
        drop(substrate);

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn truncated_legacy_rows_are_quarantined_and_minimum_rows_decode() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-shortrows-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");
        let truncated_id = Uuid::new_v4();
        let minimum_id = Uuid::new_v4();
        write_synthetic_store_full(
            &src_copy,
            &[],
            &[],
            &[(
                "codex",
                vec![
                    synthetic_legacy_truncated(truncated_id, "truncated row content"),
                    synthetic_legacy_minimum(minimum_id, "minimum row content"),
                ],
            )],
        );

        let reader = Gen2Reader::open(&src_copy).expect("open synthetic store");
        let scan = reader
            .scan_galaxy_db("codex", None)
            .expect("scan short rows");
        assert_eq!(
            scan.records.len(),
            1,
            "only the minimum complete row decodes"
        );
        assert_eq!(scan.decode_skipped, 1, "truncated row must be quarantined");
        let decoded = &scan.records[0];
        assert_eq!(decoded.id, minimum_id);
        assert_eq!(decoded.content, "minimum row content");
        assert_eq!(decoded.tags, vec!["min".to_string()]);
        assert_eq!(decoded.importance, 0.7, "importance must never default");
        assert_eq!(decoded.created_at.to_rfc3339(), "2026-03-04T05:06:07+00:00");
        assert!(
            scan.quarantined[0]
                .reason
                .contains("GalaxyDecodeError[codex]"),
            "truncation reason: {}",
            scan.quarantined[0].reason
        );
        assert!(
            scan.quarantined[0].reason.contains("invalid length"),
            "truncation reason names the length failure: {}",
            scan.quarantined[0].reason
        );

        let target = tmp.join("gen3");
        let journal = target.join("journal.jsonl");
        let quarantine = tmp.join("quarantine.jsonl");
        let mut substrate = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("open target");
        let receipt = migrate_gen2_to_gen3_with_authority(
            &reader,
            &mut substrate,
            &MigrationOptions {
                batch_size: 4,
                quarantine_path: Some(quarantine.clone()),
                ..MigrationOptions::default()
            },
            crate::evidence::RatifiedChannel::stub("wm-migration-test"),
        )
        .expect("migration");
        assert_eq!(receipt.galaxy_migrated, 1);
        assert_eq!(receipt.galaxy_decode_skipped, 1);
        assert_eq!(
            receipt.by_record_type["galaxy:codex"].skipped["decode_error"],
            1
        );
        let log = std::fs::read_to_string(&quarantine).expect("quarantine log");
        assert!(log.contains("invalid length"));
        drop(substrate);

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn dry_run_writes_nothing_and_requires_existing_target() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-dryrun-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");
        write_synthetic_store_full(
            &src_copy,
            &[synthetic_episodic("dry run episodic", 1)],
            &[vec![0xc1u8, 0x00, 0xde]],
            &[(
                "codex",
                vec![synthetic_named_memory(
                    Uuid::new_v4(),
                    "dry run galaxy",
                    "codex",
                    &["d"],
                )],
            )],
        );
        let reader = Gen2Reader::open(&src_copy).expect("open synthetic store");

        let target = tmp.join("gen3");
        let journal = target.join("journal.jsonl");
        // The target must pre-exist for a dry run; create it once.
        {
            let substrate = crate::ops::Substrate::open(
                &target,
                Some(&journal),
                crate::constitution::default_view(),
            )
            .expect("pre-create target");
            drop(substrate);
        }
        assert!(target.join("data.mdb").is_file());

        let quarantine = tmp.join("quarantine.jsonl");
        let options = MigrationOptions {
            batch_size: 4,
            dry_run: true,
            validate_hashes: true,
            allow_noise: false,
            quarantine_path: Some(quarantine.clone()),
        };
        let mut substrate = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("open target");
        let receipt = migrate_gen2_to_gen3_with_authority(
            &reader,
            &mut substrate,
            &options,
            crate::evidence::RatifiedChannel::stub("wm-migration-test"),
        )
        .expect("dry-run migration");
        assert!(receipt.dry_run);
        assert_eq!(receipt.migrated_count, 1);
        assert_eq!(receipt.galaxy_migrated, 1);
        assert_eq!(
            receipt.galaxy_decode_skipped, 1,
            "dry run still accounts undecodable rows in memory"
        );
        assert!(
            !quarantine.exists(),
            "dry run must not write the quarantine file"
        );
        assert_eq!(
            substrate.store().record_count().unwrap(),
            0,
            "dry run must not mutate the target store"
        );
        drop(substrate);

        // A missing target is reported, never created.
        let missing = tmp.join("missing-target");
        let err = dry_run_migration_census(&reader, &missing, &options).expect_err("refuse");
        assert!(
            err.to_string().contains("target missing"),
            "error names the missing target: {err}"
        );
        assert!(
            !missing.exists(),
            "dry-run census must never create the target store"
        );

        // An existing target simulates without writes.
        let census = dry_run_migration_census(&reader, &target, &options).expect("census");
        assert!(census.dry_run);
        assert_eq!(census.migrated_count, 1);
        assert_eq!(census.galaxy_migrated, 1);
        assert!(!quarantine.exists());
        let reopened = crate::ops::Substrate::open(
            &target,
            Some(&journal),
            crate::constitution::default_view(),
        )
        .expect("reopen target");
        assert_eq!(reopened.store().record_count().unwrap(), 0);
        drop(reopened);

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn session_dry_run_writes_nothing() {
        let tmp = std::env::temp_dir().join(format!("wm-gen3-sess-dry-{}", Uuid::new_v4()));
        let src_copy = tmp.join("gen2");
        std::fs::create_dir_all(&src_copy).expect("create temp gen2 dir");
        write_synthetic_store_full(
            &src_copy,
            &[],
            &[synthetic_memory(
                &synthetic_turn("sess-dry", 1, "dry turn").to_string(),
            )],
            &[],
        );
        let reader = Gen2Reader::open(&src_copy).expect("open synthetic store");
        let log = tmp.join("session_log.jsonl");

        let receipt = migrate_gen2_sessions_to_gen3_with_options(
            &reader,
            &log,
            &SessionMigrationOptions {
                dry_run: true,
                quarantine_path: None,
            },
        )
        .expect("dry-run session migration");
        assert!(receipt.dry_run);
        assert_eq!(receipt.migrated, 1, "dry run reports would-migrate");
        assert!(!log.exists(), "dry run must not write the session log");
        assert!(
            !tmp.join("session_quarantine.jsonl").exists(),
            "dry run must not write a quarantine file"
        );

        let live = migrate_gen2_sessions_to_gen3(&reader, &log).expect("live session migration");
        assert!(!live.dry_run);
        assert_eq!(live.migrated, 1);
        assert!(log.exists());

        let rerun = migrate_gen2_sessions_to_gen3(&reader, &log).expect("live rerun");
        assert_eq!(rerun.migrated, 0, "live rerun stays idempotent");
        assert_eq!(rerun.duplicates_skipped, 1);

        let _ = std::fs::remove_dir_all(&tmp);
    }
}
