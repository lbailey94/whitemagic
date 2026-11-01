//! Explicit, versioned temporal assertions over already admitted records.
//!
//! These assertions preserve what an operator supplied and when this process
//! accepted it. They do not establish that the asserted value is true.

use chrono::{DateTime, SecondsFormat, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

#[cfg(unix)]
fn validate_private_file(file: &File, description: &str) -> Result<(), TemporalError> {
    use std::os::unix::fs::MetadataExt;
    let metadata = file
        .metadata()
        .map_err(|e| TemporalError(format!("{description} metadata failed: {e}")))?;
    if !metadata.is_file() {
        return Err(TemporalError(format!(
            "{description} must be a regular file"
        )));
    }
    if metadata.mode() & 0o077 != 0 {
        return Err(TemporalError(format!(
            "{description} permissions expose plaintext or lock state; expected owner-only access"
        )));
    }
    if metadata.uid() != rustix::process::geteuid().as_raw() {
        return Err(TemporalError(format!(
            "{description} must be owned by the current user"
        )));
    }
    Ok(())
}

#[cfg(unix)]
fn open_private_read(path: &Path, description: &str) -> Result<Option<File>, TemporalError> {
    let fd = match rustix::fs::open(
        path,
        rustix::fs::OFlags::RDONLY
            | rustix::fs::OFlags::NOFOLLOW
            | rustix::fs::OFlags::NONBLOCK
            | rustix::fs::OFlags::CLOEXEC,
        rustix::fs::Mode::empty(),
    ) {
        Ok(fd) => fd,
        Err(e) if e == rustix::io::Errno::NOENT => return Ok(None),
        Err(e) => return Err(TemporalError(format!("{description} open failed: {e}"))),
    };
    let file = File::from(fd);
    validate_private_file(&file, description)?;
    Ok(Some(file))
}

#[cfg(unix)]
fn open_private_append(path: &Path, description: &str) -> Result<(File, bool), TemporalError> {
    let existed = match std::fs::symlink_metadata(path) {
        Ok(_) => true,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => false,
        Err(e) => {
            return Err(TemporalError(format!(
                "{description} path metadata failed: {e}"
            )));
        }
    };
    let fd = rustix::fs::open(
        path,
        rustix::fs::OFlags::WRONLY
            | rustix::fs::OFlags::APPEND
            | rustix::fs::OFlags::CREATE
            | rustix::fs::OFlags::NOFOLLOW
            | rustix::fs::OFlags::NONBLOCK
            | rustix::fs::OFlags::CLOEXEC,
        rustix::fs::Mode::from_bits_truncate(0o600),
    )
    .map_err(|e| TemporalError(format!("{description} open failed: {e}")))?;
    let file = File::from(fd);
    validate_private_file(&file, description)?;
    Ok((file, existed))
}

#[cfg(not(unix))]
fn open_private_read(_path: &Path, _description: &str) -> Result<Option<File>, TemporalError> {
    Err(TemporalError(
        "temporal sidecars require Unix safe file operations".into(),
    ))
}
#[cfg(not(unix))]
fn open_private_append(_path: &Path, _description: &str) -> Result<(File, bool), TemporalError> {
    Err(TemporalError(
        "temporal sidecars require Unix safe file operations".into(),
    ))
}

pub const LEDGER_NAME: &str = "temporal-assertions-v1.jsonl";
pub const MAX_ASSERTIONS: usize = 4096;
pub const MAX_LEDGER_BYTES: usize = 8 * 1024 * 1024;
pub const MAX_VALUE_BYTES: usize = 4096;
pub const MAX_KEY_BYTES: usize = 256;
pub const MAX_OPERATION_ID_BYTES: usize = 128;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum TemporalBound {
    Instant { at: String },
    Unbounded,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TemporalAssertionRequest {
    pub operation_id: String,
    pub record_id: u64,
    pub namespace: String,
    pub subject: String,
    pub predicate: String,
    pub source_id: String,
    pub value: String,
    pub valid_from: TemporalBound,
    pub valid_until: TemporalBound,
    pub supersedes: Option<u64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TemporalMode {
    Current,
    History,
    AsOf,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TemporalQuery {
    pub mode: TemporalMode,
    pub namespace: String,
    pub subject: String,
    pub predicate: Option<String>,
    pub valid_at: Option<String>,
    pub known_at: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TemporalAssertionResult {
    pub schema_version: u32,
    pub assertion_id: u64,
    pub recorded_at: String,
    pub valid_from: TemporalBound,
    pub valid_until: TemporalBound,
    pub record_id: u64,
    pub content_sha256: String,
    pub record_source: String,
    pub replayed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TemporalStatus {
    Resolved,
    Conflict,
    TimeUnknown,
    NoEvidence,
    History,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TemporalEvidence {
    pub assertion_id: u64,
    pub record_id: u64,
    pub value: String,
    pub source_id: String,
    pub record_source: String,
    pub content_sha256: String,
    pub recorded_at: String,
    pub valid_from: TemporalBound,
    pub valid_until: TemporalBound,
    pub supersedes: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TemporalEvidenceGroup {
    pub predicate: String,
    pub status: TemporalStatus,
    pub evidence: Vec<TemporalEvidence>,
    pub conflicting_values: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TemporalQueryResult {
    pub schema_version: u32,
    pub mode: TemporalMode,
    pub namespace: String,
    pub subject: String,
    pub valid_at: Option<String>,
    pub known_at: String,
    pub groups: Vec<TemporalEvidenceGroup>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TemporalError(pub String);
impl std::fmt::Display for TemporalError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}
impl std::error::Error for TemporalError {}
impl From<String> for TemporalError {
    fn from(s: String) -> Self {
        Self(s)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct LedgerEntry {
    pub schema_version: u32,
    pub assertion_id: u64,
    pub operation_id: String,
    pub recorded_at: String,
    pub record_id: u64,
    pub namespace: String,
    pub subject: String,
    pub predicate: String,
    pub source_id: String,
    pub value: String,
    pub valid_from: TemporalBound,
    pub valid_until: TemporalBound,
    pub supersedes: Option<u64>,
    pub content_sha256: String,
    pub record_source: String,
    pub store_realm_id: String,
    pub prev_digest: String,
    pub entry_digest: String,
}

#[derive(Serialize)]
struct DigestBody<'a> {
    schema_version: u32,
    assertion_id: u64,
    operation_id: &'a str,
    recorded_at: &'a str,
    record_id: u64,
    namespace: &'a str,
    subject: &'a str,
    predicate: &'a str,
    source_id: &'a str,
    value: &'a str,
    valid_from: &'a TemporalBound,
    valid_until: &'a TemporalBound,
    supersedes: Option<u64>,
    content_sha256: &'a str,
    record_source: &'a str,
    store_realm_id: &'a str,
    prev_digest: &'a str,
}

pub(crate) fn parse_instant(input: &str) -> Result<DateTime<Utc>, TemporalError> {
    if input.len() > 64 || !input.contains('T') {
        return Err(TemporalError("time must be offset-bearing RFC3339".into()));
    }
    if input.contains(":60") {
        return Err(TemporalError(
            "leap-second representations are not accepted".into(),
        ));
    }
    let parsed = DateTime::parse_from_rfc3339(input)
        .map_err(|_| TemporalError("invalid RFC3339 instant".into()))?;
    Ok(parsed.with_timezone(&Utc))
}
pub(crate) fn format_instant(value: DateTime<Utc>) -> String {
    value.to_rfc3339_opts(SecondsFormat::Nanos, true)
}
pub(crate) fn normalize_bound(bound: &TemporalBound) -> Result<TemporalBound, TemporalError> {
    match bound {
        TemporalBound::Instant { at } => Ok(TemporalBound::Instant {
            at: format_instant(parse_instant(at)?),
        }),
        _ => Ok(bound.clone()),
    }
}
pub(crate) fn validate_interval(
    from: &TemporalBound,
    until: &TemporalBound,
) -> Result<(), TemporalError> {
    if let (TemporalBound::Instant { at: a }, TemporalBound::Instant { at: b }) = (from, until) {
        if parse_instant(a)? >= parse_instant(b)? {
            return Err(TemporalError(
                "valid_from must be before valid_until".into(),
            ));
        }
    }
    Ok(())
}
pub(crate) enum Applicability {
    Yes,
    No,
    Unknown,
}
pub(crate) fn applicability(
    from: &TemporalBound,
    until: &TemporalBound,
    at: DateTime<Utc>,
) -> Result<Applicability, TemporalError> {
    let lo = match from {
        TemporalBound::Instant { at: x } => {
            if at < parse_instant(x)? {
                return Ok(Applicability::No);
            }
            false
        }
        TemporalBound::Unbounded => false,
        TemporalBound::Unknown => true,
    };
    let hi = match until {
        TemporalBound::Instant { at: x } => {
            if at >= parse_instant(x)? {
                return Ok(Applicability::No);
            }
            false
        }
        TemporalBound::Unbounded => false,
        TemporalBound::Unknown => true,
    };
    Ok(if lo || hi {
        Applicability::Unknown
    } else {
        Applicability::Yes
    })
}
pub(crate) fn to_evidence(e: &LedgerEntry) -> TemporalEvidence {
    TemporalEvidence {
        assertion_id: e.assertion_id,
        record_id: e.record_id,
        value: e.value.clone(),
        source_id: e.source_id.clone(),
        record_source: e.record_source.clone(),
        content_sha256: e.content_sha256.clone(),
        recorded_at: e.recorded_at.clone(),
        valid_from: e.valid_from.clone(),
        valid_until: e.valid_until.clone(),
        supersedes: e.supersedes,
    }
}
pub(crate) fn validate_request(
    req: &TemporalAssertionRequest,
) -> Result<(TemporalBound, TemporalBound), TemporalError> {
    for (name, value) in [
        ("namespace", &req.namespace),
        ("subject", &req.subject),
        ("predicate", &req.predicate),
        ("source_id", &req.source_id),
    ] {
        if value.is_empty() || value.len() > MAX_KEY_BYTES || value.chars().any(char::is_control) {
            return Err(TemporalError(format!(
                "{name} must be nonempty, control-free, and at most {MAX_KEY_BYTES} bytes"
            )));
        }
    }
    if req.operation_id.is_empty()
        || req.operation_id.len() > MAX_OPERATION_ID_BYTES
        || req.operation_id.chars().any(char::is_control)
    {
        return Err(TemporalError(
            "operation_id must be nonempty, control-free, and at most 128 bytes".into(),
        ));
    }
    if req.value.is_empty() || req.value.len() > MAX_VALUE_BYTES {
        return Err(TemporalError(
            "value must be nonempty and at most 4096 bytes".into(),
        ));
    }
    let from = normalize_bound(&req.valid_from)?;
    let until = normalize_bound(&req.valid_until)?;
    validate_interval(&from, &until)?;
    Ok((from, until))
}
pub(crate) fn digest(entry: &LedgerEntry) -> Result<String, TemporalError> {
    let body = DigestBody {
        schema_version: entry.schema_version,
        assertion_id: entry.assertion_id,
        operation_id: &entry.operation_id,
        recorded_at: &entry.recorded_at,
        record_id: entry.record_id,
        namespace: &entry.namespace,
        subject: &entry.subject,
        predicate: &entry.predicate,
        source_id: &entry.source_id,
        value: &entry.value,
        valid_from: &entry.valid_from,
        valid_until: &entry.valid_until,
        supersedes: entry.supersedes,
        content_sha256: &entry.content_sha256,
        record_source: &entry.record_source,
        store_realm_id: &entry.store_realm_id,
        prev_digest: &entry.prev_digest,
    };
    let bytes = serde_json::to_vec(&body).map_err(|e| TemporalError(e.to_string()))?;
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(b"WhiteMagic temporal assertion v1\0");
    h.update(bytes);
    Ok(format!("{:x}", h.finalize()))
}

pub(crate) fn realm_hex(realm: [u8; 16]) -> String {
    let mut out = String::with_capacity(32);
    for byte in realm {
        use std::fmt::Write as _;
        let _ = write!(out, "{byte:02x}");
    }
    out
}
pub(crate) fn sync_ledger(path: &Path) -> Result<(), TemporalError> {
    open_private_read(path, "temporal ledger")?
        .ok_or_else(|| TemporalError("temporal ledger disappeared before sync".into()))?
        .sync_all()
        .map_err(|e| TemporalError(format!("temporal ledger durability sync failed: {e}")))?;
    let parent = path
        .parent()
        .ok_or_else(|| TemporalError("temporal ledger has no parent directory".into()))?;
    File::open(parent)
        .and_then(|f| f.sync_all())
        .map_err(|e| TemporalError(format!("temporal ledger parent directory sync failed: {e}")))
}

pub(crate) fn load_ledger(path: &Path) -> Result<Vec<LedgerEntry>, TemporalError> {
    let Some(file) = open_private_read(path, "temporal ledger")? else {
        return Ok(Vec::new());
    };
    let size = file
        .metadata()
        .map_err(|e| TemporalError(e.to_string()))?
        .len() as usize;
    if size > MAX_LEDGER_BYTES {
        return Err(TemporalError("temporal ledger exceeds 8MiB bound".into()));
    }
    let mut bytes = Vec::with_capacity(size);
    file.take((MAX_LEDGER_BYTES + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|e| TemporalError(format!("temporal ledger read failed: {e}")))?;
    if bytes.len() > MAX_LEDGER_BYTES {
        return Err(TemporalError("temporal ledger exceeds 8MiB bound".into()));
    }
    if !bytes.is_empty() && !bytes.ends_with(b"\n") {
        return Err(TemporalError("temporal ledger has a torn final row".into()));
    }
    let text = std::str::from_utf8(&bytes)
        .map_err(|_| TemporalError("temporal ledger is not UTF-8".into()))?;
    let mut rows: Vec<LedgerEntry> = Vec::new();
    let mut ops = HashSet::new();
    let mut prev = String::from("genesis");
    for (i, line) in text.lines().enumerate() {
        if line.is_empty() {
            return Err(TemporalError(format!(
                "temporal ledger has empty row {}",
                i + 1
            )));
        }
        reject_duplicate_keys(line)?;
        let e: LedgerEntry = serde_json::from_str(line)
            .map_err(|e| TemporalError(format!("temporal ledger row {} invalid: {e}", i + 1)))?;
        if e.schema_version != 1 || e.assertion_id != rows.len() as u64 + 1 {
            return Err(TemporalError(format!(
                "temporal ledger row {} has invalid version or sequence",
                i + 1
            )));
        }
        if e.prev_digest != prev || digest(&e)? != e.entry_digest {
            return Err(TemporalError(format!(
                "temporal ledger row {} hash chain mismatch",
                i + 1
            )));
        }
        if !ops.insert(e.operation_id.clone()) {
            return Err(TemporalError(format!(
                "temporal ledger duplicate operation id at row {}",
                i + 1
            )));
        }
        for (name, value) in [
            ("namespace", &e.namespace),
            ("subject", &e.subject),
            ("predicate", &e.predicate),
            ("source_id", &e.source_id),
            ("record_source", &e.record_source),
        ] {
            if value.is_empty()
                || value.len() > MAX_KEY_BYTES
                || value.chars().any(char::is_control)
            {
                return Err(TemporalError(format!(
                    "invalid {name} in temporal row {}",
                    i + 1
                )));
            }
        }
        if e.value.is_empty()
            || e.value.len() > MAX_VALUE_BYTES
            || e.operation_id.is_empty()
            || e.operation_id.len() > MAX_OPERATION_ID_BYTES
            || e.operation_id.chars().any(char::is_control)
            || e.content_sha256.len() != 64
            || !e.content_sha256.chars().all(|c| c.is_ascii_hexdigit())
            || e.store_realm_id.len() != 32
            || !e.store_realm_id.chars().all(|c| c.is_ascii_hexdigit())
        {
            return Err(TemporalError(format!(
                "invalid field size in temporal row {}",
                i + 1
            )));
        }
        let from = normalize_bound(&e.valid_from)?;
        let until = normalize_bound(&e.valid_until)?;
        if from != e.valid_from || until != e.valid_until {
            return Err(TemporalError(format!(
                "non-normalized bounds in temporal row {}",
                i + 1
            )));
        }
        validate_interval(&from, &until)?;
        let recorded = parse_instant(&e.recorded_at)?;
        if let Some(previous) = rows.last() {
            if recorded < parse_instant(&previous.recorded_at)? {
                return Err(TemporalError(
                    "recorded_at regresses in temporal ledger".into(),
                ));
            }
        }
        if let Some(sup) = e.supersedes {
            if sup == 0 || sup >= e.assertion_id {
                return Err(TemporalError(
                    "temporal supersedes reference must point backward".into(),
                ));
            }
            let prior = &rows[(sup - 1) as usize];
            if prior.namespace != e.namespace
                || prior.subject != e.subject
                || prior.predicate != e.predicate
                || prior.source_id != e.source_id
                || prior.record_id == e.record_id
                || !matches!(&e.valid_from, TemporalBound::Instant { .. })
            {
                return Err(TemporalError(
                    "invalid temporal supersedes key, source, record, or effective bound".into(),
                ));
            }
            if rows.iter().any(|r| r.supersedes == Some(sup)) {
                return Err(TemporalError(
                    "temporal assertion has multiple corrections".into(),
                ));
            }
        }
        prev = e.entry_digest.clone();
        rows.push(e);
        if rows.len() > MAX_ASSERTIONS {
            return Err(TemporalError(
                "temporal ledger exceeds 4096 assertions".into(),
            ));
        }
    }
    Ok(rows)
}

fn reject_duplicate_keys(line: &str) -> Result<(), TemporalError> {
    // Strict duplicate-member check before serde's map decoder (which otherwise keeps the last value).
    let mut stack: Vec<HashSet<String>> = Vec::new();
    let mut i = 0;
    let b = line.as_bytes();
    while i < b.len() {
        match b[i] {
            b'{' => {
                stack.push(HashSet::new());
                i += 1;
            }
            b'}' => {
                stack.pop();
                i += 1;
            }
            b'"' => {
                let start = i;
                i += 1;
                let mut esc = false;
                while i < b.len() {
                    if esc {
                        esc = false;
                    } else if b[i] == b'\\' {
                        esc = true;
                    } else if b[i] == b'"' {
                        break;
                    }
                    i += 1;
                }
                if i >= b.len() {
                    return Err(TemporalError("unterminated JSON string".into()));
                }
                let end = i;
                i += 1;
                let mut j = i;
                while j < b.len() && b[j].is_ascii_whitespace() {
                    j += 1;
                }
                if j < b.len() && b[j] == b':' {
                    let key: String = serde_json::from_str(&line[start..=end])
                        .map_err(|_| TemporalError("invalid JSON key".into()))?;
                    if !stack
                        .last_mut()
                        .ok_or_else(|| TemporalError("invalid JSON object".into()))?
                        .insert(key)
                    {
                        return Err(TemporalError("duplicate JSON object member".into()));
                    }
                }
            }
            _ => i += 1,
        }
    }
    Ok(())
}

#[cfg(unix)]
pub(crate) struct LedgerLock(File);
#[cfg(unix)]
impl LedgerLock {
    pub(crate) fn acquire(dir: &Path) -> Result<Self, TemporalError> {
        use rustix::fs::{FlockOperation, flock};
        let path = dir.join("temporal-assertions-v1.lock");
        let fd = rustix::fs::open(
            &path,
            rustix::fs::OFlags::RDWR
                | rustix::fs::OFlags::CREATE
                | rustix::fs::OFlags::NOFOLLOW
                | rustix::fs::OFlags::NONBLOCK
                | rustix::fs::OFlags::CLOEXEC,
            rustix::fs::Mode::from_bits_truncate(0o600),
        )
        .map_err(|e| TemporalError(format!("temporal lock open failed: {e}")))?;
        let file = File::from(fd);
        validate_private_file(&file, "temporal lock")?;
        let start = std::time::Instant::now();
        loop {
            match flock(&file, FlockOperation::NonBlockingLockExclusive) {
                Ok(()) => return Ok(Self(file)),
                Err(e) if e == rustix::io::Errno::WOULDBLOCK => {
                    if start.elapsed() > std::time::Duration::from_secs(2) {
                        return Err(TemporalError("temporal ledger lock timed out".into()));
                    }
                    std::thread::sleep(std::time::Duration::from_millis(10));
                }
                Err(e) => return Err(TemporalError(format!("temporal lock failed: {e}"))),
            }
        }
    }
}
#[cfg(unix)]
impl Drop for LedgerLock {
    fn drop(&mut self) {
        let _ = rustix::fs::flock(&self.0, rustix::fs::FlockOperation::Unlock);
    }
}

#[cfg(unix)]
pub(crate) struct LedgerReadLock(File);
#[cfg(unix)]
impl LedgerReadLock {
    pub(crate) fn acquire(dir: &Path) -> Result<Self, TemporalError> {
        use rustix::fs::{FlockOperation, flock};
        let path = dir.join("temporal-assertions-v1.lock");
        let fd = rustix::fs::open(
            &path,
            rustix::fs::OFlags::RDONLY
                | rustix::fs::OFlags::NOFOLLOW
                | rustix::fs::OFlags::NONBLOCK
                | rustix::fs::OFlags::CLOEXEC,
            rustix::fs::Mode::empty(),
        )
        .map_err(|e| TemporalError(format!("existing temporal lock open failed: {e}")))?;
        let file = File::from(fd);
        validate_private_file(&file, "temporal lock")?;
        let start = std::time::Instant::now();
        loop {
            match flock(&file, FlockOperation::NonBlockingLockShared) {
                Ok(()) => return Ok(Self(file)),
                Err(e) if e == rustix::io::Errno::WOULDBLOCK => {
                    if start.elapsed() > std::time::Duration::from_secs(2) {
                        return Err(TemporalError(
                            "temporal ledger shared lock timed out".into(),
                        ));
                    }
                    std::thread::sleep(std::time::Duration::from_millis(10));
                }
                Err(e) => return Err(TemporalError(format!("temporal shared lock failed: {e}"))),
            }
        }
    }
}
#[cfg(unix)]
impl Drop for LedgerReadLock {
    fn drop(&mut self) {
        let _ = rustix::fs::flock(&self.0, rustix::fs::FlockOperation::Unlock);
    }
}

#[cfg(not(unix))]
pub(crate) struct LedgerLock;
#[cfg(not(unix))]
pub(crate) struct LedgerReadLock;
#[cfg(not(unix))]
impl LedgerLock {
    pub(crate) fn acquire(_dir: &Path) -> Result<Self, TemporalError> {
        Err(TemporalError(
            "temporal ledger access is unsupported on this platform; v1 requires Unix flock".into(),
        ))
    }
}

pub(crate) fn append_entry(path: &Path, entry: &LedgerEntry) -> Result<(), TemporalError> {
    let serialized = serde_json::to_vec(entry).map_err(|e| TemporalError(e.to_string()))?;
    let (mut f, existed) = open_private_append(path, "temporal ledger")?;
    f.write_all(&serialized)
        .and_then(|_| f.write_all(b"\n"))
        .and_then(|_| f.sync_all())
        .map_err(|e| TemporalError(format!("temporal ledger append/fsync failed: {e}")))?;
    if !existed {
        let parent = path
            .parent()
            .ok_or_else(|| TemporalError("temporal ledger path has no parent".into()))?;
        File::open(parent)
            .and_then(|directory| directory.sync_all())
            .map_err(|e| TemporalError(format!("temporal ledger directory sync failed: {e}")))?;
    }
    Ok(())
}

#[cfg(test)]
pub(crate) fn append_torn_for_test(path: &Path, entry: &LedgerEntry) -> Result<(), TemporalError> {
    let bytes = serde_json::to_vec(entry).map_err(|e| TemporalError(e.to_string()))?;
    let (mut f, _) = open_private_append(path, "temporal ledger")?;
    f.write_all(&bytes[..bytes.len() / 2])
        .and_then(|_| f.sync_all())
        .map_err(|e| TemporalError(e.to_string()))
}
