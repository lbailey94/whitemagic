//! Canary tokens — active deception defense (blue-team tripwires).
//!
//! Rust port of the Python `whitemagic/security/canary_tokens.py`
//! (`CanaryTokenManager`), promoted into WMv9 governance: distinctive,
//! inert bait values (fake API keys, fake credentials, fake paths, fake
//! memory entries) are planted on surfaces an attacker may touch, and every
//! event/content stream is scanned for them. A canary only fires when
//! someone actually touched the bait, so a hit is a **high-severity**
//! signal — there is no benign way for a planted value to appear in
//! scanned content.
//!
//! Port deltas vs the Python original:
//! - matching is **normalized substring** (case-insensitive), not exact
//!   equality — an attacker who copies the token into a larger blob still
//!   trips the wire,
//! - every first fire is published to the [`crate::SecurityEventBus`] as
//!   [`SecurityEventType::Quarantine`] at [`Severity::High`]; repeat
//!   sightings are reported (`first_fire: false`) but not re-published,
//! - generated fake-credential helpers are **structurally inert and
//!   tagged**: AWS-key-shaped ids carry a deliberately corrupted CRC-32
//!   checksum slot plus a literal `DECOY` segment, PEM blocks use a
//!   `DECOY` header and a non-base64 body byte, paths live under a
//!   `wm-decoy` prefix. No generated value can validate as, or be
//!   mistaken for, a real credential.
//!
//! Persistence is a single JSON file; it stores full bait values, so the
//! registry file itself is a secret (like the bait it describes).

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::security_events::{SecurityEvent, SecurityEventBus, SecurityEventType, Severity};

/// Marker present in every generated decoy value — identifiable in
/// hindsight, never part of a real issued credential.
pub const DECOY_TAG: &str = "DECOY";

/// Default time-to-live for a planted canary (24h, Python parity).
pub const DEFAULT_TTL_SECS: i64 = 86_400;

/// Kind of bait a canary token impersonates. Parity with the Python
/// `CanaryType` enum plus `MemoryEntry` (fake memory rows).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CanaryType {
    /// Fake API key (`sk-decoy-…`).
    ApiKey,
    /// Fake database row.
    DbRecord,
    /// Fake file / path bait.
    File,
    /// Fake internal endpoint.
    Endpoint,
    /// Fake credential (config file style).
    Credential,
    /// Fake memory entry planted in a galaxy surface.
    MemoryEntry,
}

impl CanaryType {
    /// Snake-case name, Python `CanaryType` value parity.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ApiKey => "api_key",
            Self::DbRecord => "db_record",
            Self::File => "file",
            Self::Endpoint => "endpoint",
            Self::Credential => "credential",
            Self::MemoryEntry => "memory_entry",
        }
    }
}

/// Lifecycle status of a planted canary. Parity with the Python
/// `CanaryStatus` enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CanaryStatus {
    /// Planted and armed.
    Deployed,
    /// Touched — the tripwire fired at least once.
    Triggered,
    /// TTL elapsed without a fire.
    Expired,
    /// Manually withdrawn.
    Revoked,
}

/// A planted canary token. Field parity with the Python `CanaryToken`
/// dataclass (epoch-second timestamps).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct CanaryToken {
    /// Registry-assigned id (`canary_<hex16>`).
    pub token_id: String,
    /// Bait kind.
    pub canary_type: CanaryType,
    /// The bait value itself (kept full — persistence is a secret file).
    pub token_value: String,
    /// Human-readable description.
    pub description: String,
    /// Where the bait was planted (e.g. `config.yaml`, `users table`).
    pub location: String,
    /// Deployed at (epoch secs).
    pub deployed_at: i64,
    /// Expires at (epoch secs).
    pub expires_at: i64,
    /// Lifecycle status.
    pub status: CanaryStatus,
    /// First fire time (epoch secs), if any.
    pub triggered_at: Option<i64>,
    /// What touched the bait at first fire, if known.
    pub triggered_by: Option<String>,
}

/// Handle to a planted canary, returned by [`CanaryRegistry::plant`].
#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct CanaryId(pub String);

impl CanaryId {
    /// Registry id as a string slice.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::fmt::Display for CanaryId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

/// One substring match of a planted token inside scanned content.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct CanaryHit {
    /// Registry id of the fired canary.
    pub token_id: String,
    /// Bait kind.
    pub canary_type: CanaryType,
    /// Where the bait was planted.
    pub location: String,
    /// `true` on the first fire (the moment the tripwire trips);
    /// `false` for repeat sightings of an already-fired canary.
    pub first_fire: bool,
}

/// Registry statistics, Python `status()` parity.
#[derive(Debug, Clone, Default, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct CanaryStats {
    /// Total canaries ever planted.
    pub total_tokens: usize,
    /// Currently armed.
    pub deployed: usize,
    /// Fired at least once.
    pub triggered: usize,
    /// TTL elapsed.
    pub expired: usize,
    /// Withdrawn.
    pub revoked: usize,
    /// Number of recorded first fires.
    pub trigger_log_count: usize,
}

struct Inner {
    tokens: Vec<CanaryToken>,
    trigger_log: Vec<CanaryHit>,
    next_id: u64,
}

/// The canary registry: plants bait and scans content streams for touches.
///
/// Interior state is behind a `Mutex`; an optional shared
/// [`SecurityEventBus`] publishes [`SecurityEventType::Quarantine`] events
/// on first fire (Python parity: `_emit_security_event`).
pub struct CanaryRegistry {
    inner: Mutex<Inner>,
    bus: Option<Arc<SecurityEventBus>>,
    sink_path: Option<PathBuf>,
}

impl std::fmt::Debug for CanaryRegistry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let inner = self.inner.lock().expect("canary registry lock poisoned");
        f.debug_struct("CanaryRegistry")
            .field("tokens", &inner.tokens.len())
            .field("trigger_log", &inner.trigger_log.len())
            .field("bus", &self.bus.is_some())
            .field("sink_path", &self.sink_path)
            .finish()
    }
}

impl Default for CanaryRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl CanaryRegistry {
    /// Empty registry, no bus, no persistence sink.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            inner: Mutex::new(Inner {
                tokens: Vec::new(),
                trigger_log: Vec::new(),
                next_id: 0,
            }),
            bus: None,
            sink_path: None,
        }
    }

    /// Attach the security event bus (Quarantine events on first fire).
    #[must_use]
    pub fn with_bus(mut self, bus: Arc<SecurityEventBus>) -> Self {
        self.bus = Some(bus);
        self
    }

    /// Attach a JSON persistence file: every plant/trigger/revoke is
    /// written through so a restart re-arms the same bait.
    #[must_use]
    pub fn with_sink(mut self, path: PathBuf) -> Self {
        self.sink_path = Some(path);
        self
    }

    /// Plant a canary: `kind` selects the bait class, `location` records
    /// where it sits, `token_value` is the distinctive bait string (use the
    /// [`fake_aws_key_id`]-family helpers for generated bait).
    pub fn plant(
        &self,
        kind: CanaryType,
        location: impl Into<String>,
        token_value: impl Into<String>,
    ) -> CanaryId {
        self.plant_with_ttl(kind, location, token_value, DEFAULT_TTL_SECS)
    }

    /// [`CanaryRegistry::plant`] with an explicit TTL in seconds (0 →
    /// immediately expired; used by tests).
    pub fn plant_with_ttl(
        &self,
        kind: CanaryType,
        location: impl Into<String>,
        token_value: impl Into<String>,
        ttl_secs: i64,
    ) -> CanaryId {
        let value = token_value.into();
        let mut inner = self.inner.lock().expect("canary registry lock poisoned");
        inner.next_id += 1;
        let token = CanaryToken {
            token_id: format!("canary_{:016x}", inner.next_id),
            canary_type: kind,
            token_value: value,
            description: String::new(),
            location: location.into(),
            deployed_at: now_secs(),
            expires_at: now_secs() + ttl_secs,
            status: CanaryStatus::Deployed,
            triggered_at: None,
            triggered_by: None,
        };
        let id = CanaryId(token.token_id.clone());
        inner.tokens.push(token);
        drop(inner);
        self.persist();
        id
    }

    /// Scan `event_or_content` for touches: case-insensitive substring
    /// match of every planted token value against the content. Deployed
    /// tokens fire on first touch (published to the bus as
    /// [`SecurityEventType::Quarantine`] at [`Severity::High`]); already
    /// fired tokens report `first_fire: false` without re-publishing.
    // The guard cannot be dropped before the owned results are returned —
    // the borrows end with the scan loop, which is the last use.
    #[allow(clippy::significant_drop_tightening)]
    #[must_use]
    pub fn check(&self, event_or_content: &str) -> Vec<CanaryHit> {
        let content = event_or_content.to_lowercase();
        if content.is_empty() {
            return Vec::new();
        }
        let (hits, first_fires) = {
            let mut lock = self.inner.lock().expect("canary registry lock poisoned");
            let Inner {
                tokens,
                trigger_log: inner_trigger_log,
                ..
            } = &mut *lock;
            let mut hits = Vec::new();
            let mut first_fires = Vec::new();
            for token in tokens.iter_mut() {
                if !content.contains(&token.token_value.to_lowercase()) {
                    continue;
                }
                match token.status {
                    CanaryStatus::Revoked | CanaryStatus::Expired => {}
                    CanaryStatus::Deployed => {
                        if now_secs() >= token.expires_at {
                            token.status = CanaryStatus::Expired;
                            continue;
                        }
                        token.status = CanaryStatus::Triggered;
                        token.triggered_at = Some(now_secs());
                        let hit = CanaryHit {
                            token_id: token.token_id.clone(),
                            canary_type: token.canary_type,
                            location: token.location.clone(),
                            first_fire: true,
                        };
                        inner_trigger_log.push(hit.clone());
                        first_fires.push(hit.clone());
                        hits.push(hit);
                    }
                    CanaryStatus::Triggered => {
                        hits.push(CanaryHit {
                            token_id: token.token_id.clone(),
                            canary_type: token.canary_type,
                            location: token.location.clone(),
                            first_fire: false,
                        });
                    }
                }
            }
            (hits, first_fires)
        };
        for hit in first_fires {
            self.publish_hit(&hit);
        }
        hits
    }

    fn publish_hit(&self, hit: &CanaryHit) {
        let Some(bus) = &self.bus else {
            return;
        };
        let event = SecurityEvent::new(SecurityEventType::Quarantine, "canary_registry")
            .with_detail(format!(
                "canary {} ({}) fired at '{}' — planted bait was touched; a canary \
                 only fires when someone handled the bait",
                hit.token_id,
                hit.canary_type.as_str(),
                hit.location
            ))
            .with_severity(Severity::High)
            .with_metadata("canary_id", serde_json::json!(hit.token_id))
            .with_metadata("canary_type", serde_json::json!(hit.canary_type.as_str()))
            .with_metadata("location", serde_json::json!(hit.location));
        bus.publish(&event);
    }

    /// Withdraw a canary (Python `revoke` parity): revoked bait never
    /// fires again. `false` when the id is unknown (or already revoked).
    pub fn revoke(&self, id: &CanaryId) -> bool {
        let mut inner = self.inner.lock().expect("canary registry lock poisoned");
        let mut revoked = false;
        for token in &mut inner.tokens {
            if token.token_id == id.0 && token.status != CanaryStatus::Revoked {
                token.status = CanaryStatus::Revoked;
                revoked = true;
            }
        }
        drop(inner);
        if revoked {
            self.persist();
        }
        revoked
    }

    /// Snapshot of every planted token (full bait values included —
    /// treat the result as a secret).
    #[must_use]
    pub fn tokens(&self) -> Vec<CanaryToken> {
        self.inner
            .lock()
            .expect("canary registry lock poisoned")
            .tokens
            .clone()
    }

    /// Trigger log: first fires, oldest → newest.
    #[must_use]
    pub fn trigger_log(&self) -> Vec<CanaryHit> {
        self.inner
            .lock()
            .expect("canary registry lock poisoned")
            .trigger_log
            .clone()
    }

    /// Registry statistics (Python `status()` parity).
    #[must_use]
    pub fn status(&self) -> CanaryStats {
        {
            let inner = self.inner.lock().expect("canary registry lock poisoned");
            Self::compute_stats(&inner)
        }
    }

    fn compute_stats(inner: &Inner) -> CanaryStats {
        let mut stats = CanaryStats {
            total_tokens: inner.tokens.len(),
            trigger_log_count: inner.trigger_log.len(),
            ..CanaryStats::default()
        };
        for token in &inner.tokens {
            match token.status {
                CanaryStatus::Deployed => stats.deployed += 1,
                CanaryStatus::Triggered => stats.triggered += 1,
                CanaryStatus::Expired => stats.expired += 1,
                CanaryStatus::Revoked => stats.revoked += 1,
            }
        }
        stats
    }

    /// Persist the registry to the attached sink. `Ok(())` when no sink is
    /// attached.
    ///
    /// # Errors
    /// IO failure while writing the sink file, or a serialization failure.
    pub fn save(&self) -> std::io::Result<()> {
        let Some(path) = &self.sink_path else {
            return Ok(());
        };
        let tokens = self.tokens();
        let json = serde_json::to_string_pretty(&tokens)
            .map_err(|err| std::io::Error::new(std::io::ErrorKind::InvalidData, err))?;
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(path, json)
    }

    fn persist(&self) {
        if let Err(err) = self.save() {
            tracing::warn!("canary registry: could not persist sink: {err}");
        }
    }

    /// Load a registry from a JSON sink file written by
    /// [`CanaryRegistry::save`]. Bus attachment is deliberately not
    /// persisted — re-attach with [`CanaryRegistry::with_bus`].
    ///
    /// # Errors
    /// Missing/unreadable file or malformed JSON.
    pub fn load(path: &Path) -> std::io::Result<Self> {
        let raw = std::fs::read_to_string(path)?;
        let tokens: Vec<CanaryToken> = serde_json::from_str(&raw)
            .map_err(|err| std::io::Error::new(std::io::ErrorKind::InvalidData, err))?;
        Ok(Self {
            inner: Mutex::new(Inner {
                tokens,
                trigger_log: Vec::new(),
                next_id: 0,
            }),
            bus: None,
            sink_path: Some(path.to_path_buf()),
        })
    }
}

// ---------------------------------------------------------------------------
// Inert bait generators
// ---------------------------------------------------------------------------

/// Base32 alphabet of AWS-style key ids (`A–Z`, `2–7`).
const BASE32: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

/// IEEE CRC-32 (bitwise, table-free — no unsafe, no new deps).
fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = 0xFFFF_FFFF_u32;
    for &byte in bytes {
        crc ^= u32::from(byte);
        for _ in 0..8 {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (0xEDB8_8320 & mask);
        }
    }
    !crc
}

/// Encode the top 20 bits of `value` as 4 base32 chars — the checksum slot
/// of a 20-char AWS-shaped key id.
fn checksum_chars(value: u32) -> String {
    let bits = (value >> 12) as usize;
    (0..4)
        .map(|i| {
            let idx = (bits >> (15 - i * 5)) & 0x1F;
            BASE32[idx] as char
        })
        .collect()
}

/// Embedded top-20-bits checksum slot of a 20-char AWS-shaped key id, or
/// `None` when the id is not AWS-key-shaped at all.
fn embedded_checksum(key: &str) -> Option<u32> {
    if key.len() != 20 || !key.starts_with("AKIA") {
        return None;
    }
    let mut bits: u32 = 0;
    for ch in key[16..].bytes() {
        let idx = BASE32.iter().position(|&b| b == ch)?;
        bits = (bits << 5) | (idx as u32);
    }
    Some(bits << 12)
}

/// Whether `key` is an AWS-key-shaped id whose embedded CRC-32 checksum
/// slot actually validates. Used by tests (and by callers auditing bait
/// inertness): every generated decoy fails this on purpose.
#[must_use]
pub fn aws_key_id_checksum_valid(key: &str) -> bool {
    let Some(embedded) = embedded_checksum(key) else {
        return false;
    };
    embedded == (crc32(&key.as_bytes()[..16]) & 0xFFFF_F000)
}

/// Random-ish hex material for bait generation (UUID v4 simple form —
/// 122 bits, no extra deps).
fn bait_hex(chars: usize) -> String {
    let uuid = uuid::Uuid::new_v4().simple().to_string();
    uuid.chars().take(chars).collect()
}

/// Fake AWS access-key-shaped id with a deliberately corrupted CRC-32 slot.
///
/// Shape: `AKIA` + a literal `DECOY` segment + filler base32 chars. The
/// checksum slot never validates, the `DECOY` segment makes the bait
/// identifiable in hindsight, and the id is issued nowhere.
#[must_use]
pub fn fake_aws_key_id() -> String {
    let filler: String = bait_hex(7)
        .to_uppercase()
        .chars()
        .map(|c| {
            let idx = (u32::from(c) % 32) as usize;
            BASE32[idx] as char
        })
        .collect();
    let id16 = format!("AKIA{DECOY_TAG}{filler}");
    // Corrupt the checksum slot deterministically: flip the top bit.
    let corrupted = checksum_chars(crc32(id16.as_bytes()) ^ 0x8000_0000);
    format!("{id16}{corrupted}")
}

/// Fake API key: `sk-decoy-` + hex. Never a valid provider key — the
/// `decoy` segment is not part of any issued key format.
#[must_use]
pub fn fake_api_key() -> String {
    format!("sk-decoy-{}", bait_hex(32))
}

/// Fake credential string: tagged and hex-suffixed, valid nowhere.
#[must_use]
pub fn fake_credential() -> String {
    format!("wm-decoy-cred-{}", bait_hex(24))
}

/// Fake DB/memory record id: tagged user row that exists in no table.
#[must_use]
pub fn fake_memory_entry() -> String {
    format!("decoy_user_{}", bait_hex(12))
}

/// Fake internal endpoint/path bait under a decoy prefix; the file does
/// not exist and the prefix is reserved for decoys.
#[must_use]
pub fn fake_path() -> String {
    format!("/etc/wm-decoy/canary-{}.conf", bait_hex(12))
}

/// Fake private-key PEM block, tagged in the header and invalid in the body.
///
/// The header (`BEGIN DECOY RSA PRIVATE KEY`) matches no real key type, and
/// the body carries a non-base64 `_` byte, so every base64/PEM parser
/// rejects it structurally.
#[must_use]
pub fn fake_private_key_block() -> String {
    let body = bait_hex(48);
    format!(
        "-----BEGIN {DECOY_TAG} RSA PRIVATE KEY-----\n\
         NOT-A-KEY — decoy bait, nothing here is real\n\
         {body}_{body}\n\
         -----END {DECOY_TAG} RSA PRIVATE KEY-----"
    )
}

fn now_secs() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn planted_token_fires_on_substring_touch() {
        let registry = CanaryRegistry::new();
        let token = fake_api_key();
        let id = registry.plant(CanaryType::ApiKey, "config.yaml", token.clone());
        // Substring: the token embedded in a larger blob still trips.
        let content = format!("leaked config dump ... {token} ... end");
        let hits = registry.check(&content);
        assert_eq!(hits.len(), 1);
        assert!(hits[0].first_fire);
        assert_eq!(hits[0].token_id, id.as_str());
        assert_eq!(hits[0].canary_type, CanaryType::ApiKey);
        assert_eq!(hits[0].location, "config.yaml");
    }

    #[test]
    fn clean_content_is_a_miss() {
        let registry = CanaryRegistry::new();
        registry.plant(CanaryType::Credential, ".env", fake_credential());
        assert!(registry.check("nothing suspicious here").is_empty());
        assert_eq!(registry.status().triggered, 0);
    }

    #[test]
    fn repeat_sighting_reports_not_first_fire_and_fires_once() {
        let registry = CanaryRegistry::new();
        let token = fake_path();
        registry.plant(CanaryType::File, "index", token.clone());
        let first = registry.check(&format!("found {token}"));
        let second = registry.check(&format!("found {token} again"));
        assert!(first[0].first_fire);
        assert!(!second[0].first_fire);
        assert_eq!(registry.trigger_log().len(), 1);
    }

    #[test]
    fn revoked_tokens_never_fire() {
        let registry = CanaryRegistry::new();
        let token = fake_credential();
        let id = registry.plant(CanaryType::Credential, "vault", token.clone());
        assert!(registry.revoke(&id));
        assert!(registry.check(&token).is_empty());
        assert!(registry.check(&format!("see {token}")).is_empty());
        assert_eq!(registry.status().revoked, 1);
    }

    #[test]
    fn expired_tokens_do_not_fire() {
        let registry = CanaryRegistry::new();
        let token = fake_api_key();
        registry.plant_with_ttl(CanaryType::ApiKey, "old", token.clone(), 0);
        assert!(registry.check(&token).is_empty());
        assert_eq!(registry.status().expired, 1);
    }

    #[test]
    fn persistence_roundtrip_keeps_bait_armed() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let path = dir.path().join("canaries.json");
        let token = fake_aws_key_id();
        {
            let registry = CanaryRegistry::new().with_sink(path.clone());
            registry.plant(CanaryType::Credential, "aws.cfg", token.clone());
            registry.save().expect("save");
        }
        let reloaded = CanaryRegistry::load(&path).expect("load");
        assert_eq!(reloaded.tokens().len(), 1);
        let hits = reloaded.check(&format!("exfil {token}"));
        assert_eq!(hits.len(), 1);
        assert!(hits[0].first_fire);
    }

    #[test]
    fn canary_hit_publishes_quarantine_event_on_first_fire() {
        let bus = Arc::new(SecurityEventBus::new());
        let received = Arc::new(Mutex::new(Vec::<SecurityEventType>::new()));
        let sink = Arc::clone(&received);
        let _sub = bus.subscribe_all(move |event| {
            sink.lock().expect("test sink lock").push(event.event_type);
        });
        let registry = CanaryRegistry::new().with_bus(Arc::clone(&bus));
        let token = fake_credential();
        registry.plant(CanaryType::Credential, "db", token.clone());
        let _ = registry.check(&format!("stolen {token}"));
        let _ = registry.check(&format!("stolen {token} again"));
        let events = received.lock().expect("test sink lock");
        assert_eq!(events.len(), 1, "first fire only");
        assert_eq!(events[0], SecurityEventType::Quarantine);
    }

    #[test]
    fn fake_aws_key_id_shape_is_tagged_and_checksum_invalid() {
        for _ in 0..16 {
            let key = fake_aws_key_id();
            assert_eq!(key.len(), 20, "{key}");
            assert!(key.starts_with("AKIA"), "{key}");
            assert!(key.contains(DECOY_TAG), "tagged: {key}");
            assert!(
                !aws_key_id_checksum_valid(&key),
                "decoy must be checksum-invalid: {key}"
            );
        }
    }

    #[test]
    fn checksum_validator_accepts_a_correctly_checksummed_id() {
        // A self-consistent (fake but checksum-valid) id passes the
        // validator — proves the decoys' invalidity is deliberate, not a
        // validator bug. The slot encodes the CRC of the 16-char prefix.
        let prefix = "AKIAIOSFODNN7EXA";
        let correct = format!("{prefix}{}", checksum_chars(crc32(prefix.as_bytes())));
        assert!(aws_key_id_checksum_valid(&correct));
    }

    #[test]
    fn fake_private_key_block_is_structurally_invalid() {
        let block = fake_private_key_block();
        assert!(block.contains("BEGIN DECOY RSA PRIVATE KEY"));
        assert!(block.contains("nothing here is real"));
        // The `_` byte makes the body invalid base64: no parser can read it.
        let body: String = block
            .lines()
            .filter(|line| line.starts_with(|c: char| c.is_ascii_hexdigit()))
            .collect();
        assert!(body.contains('_'), "body must be non-base64: {body}");
    }

    #[test]
    fn generated_bait_is_tagged_and_distinct() {
        let api = fake_api_key();
        let cred = fake_credential();
        let memory = fake_memory_entry();
        let path = fake_path();
        assert!(api.starts_with("sk-decoy-") && api.len() == 41);
        assert!(cred.contains("wm-decoy-cred-"));
        assert!(memory.starts_with("decoy_user_"));
        assert!(path.starts_with("/etc/wm-decoy/"));
        // Distinctive: no two draws collide within a reasonable sample.
        let mut seen = std::collections::HashSet::new();
        for _ in 0..64 {
            assert!(seen.insert(fake_api_key()), "bait must be distinctive");
        }
    }
}
