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

    substrate.set_intake_authority(authority);

    for chunk in valid_records.chunks(options.batch_size.max(1)) {
        let items: Vec<RememberItem> = chunk.iter().map(|r| r.to_remember_item()).collect();
        if options.dry_run {
            for item in &items {
                let kind_tag = crate::ops::kind_tag(item.kind);
                let key = crate::ops::identity_key(&item.content, &item.source, kind_tag);
                if substrate.identity_map().contains_key(&key) {
                    duplicate_skipped += 1;
                } else {
                    migrated_count += 1;
                }
            }
        } else {
            let outcomes = substrate.remember_batch(&items);
            for (idx, outcome) in outcomes.into_iter().enumerate() {
                match outcome {
                    Ok(record_id) => {
                        migrated_count += 1;
                        let orig = &chunk[idx];
                        substrate.bind_uuid(orig.id, record_id);
                    }
                    Err(err) if err == "duplicate_exact" => {
                        duplicate_skipped += 1;
                        let orig = &chunk[idx];
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
                        let orig = &chunk[idx];
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

    if options.allow_noise {
        substrate.set_noise_enabled(old_noise);
    }
    substrate.set_budget(old_budget);

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

    #[test]
    fn test_real_gen2_store_census() {
        let path = Path::new("/home/lucas/Desktop/WHITEMAGIC/data/WMdata/projects/planning/lmdb");
        if !path.join("data.mdb").is_file() {
            eprintln!("skipping test_real_gen2_store_census: test store not found on this host");
            return;
        }

        let reader = Gen2Reader::open(path).expect("open gen2 reader");
        let census = reader.census().expect("run census");

        println!("=== GEN2 REAL STORE CENSUS ===");
        println!("Store: {}", census.store_path.display());
        println!("Total Records: {}", census.total_records);
        println!("Valid Hashes: {}", census.valid_hashes);
        println!("Hash Mismatches: {}", census.hash_mismatches);
        println!("Integrity Ratio: {:.4}", census.integrity_ratio());
        println!("Distinct Sessions: {}", census.distinct_sessions);
        println!("Kinds breakdown: {:?}", census.kinds);
        println!("Sources breakdown: {:?}", census.sources);
        println!("Validity breakdown: {:?}", census.validity);
        println!("Earliest record: {:?}", census.earliest_record);
        println!("Latest record: {:?}", census.latest_record);

        assert!(census.total_records > 0, "store should have records");
        assert_eq!(census.hash_mismatches, 0, "zero hash corruption permitted");
        assert_eq!(
            census.integrity_ratio(),
            1.0,
            "100% hash integrity required"
        );

        // Scan 5 sample records and verify conversion to Gen3 RememberItem
        let samples = reader.scan_records(Some(5)).expect("scan 5 records");
        assert_eq!(samples.len(), 5);
        for record in &samples {
            assert!(record.validate_hash());
            let remember = record.to_remember_item();
            assert!(!remember.content.is_empty());
        }
    }
}
