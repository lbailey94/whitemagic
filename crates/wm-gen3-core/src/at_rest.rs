//! At-rest keyring + record sealing — Gen3 port of v9 Q39 slices A–B.
//!
//! One root key (RK) per store; one random 256-bit data-encryption key (DEK)
//! per scope, wrapped by `KEK = hkdf32(rk, "wm/galaxy-dek/v1/<scope>")` with
//! XChaCha20-Poly1305 and the same info string as AAD (so a wrapped DEK
//! cannot be transplanted between scopes). A `rk:check` row (AEAD wrap of a
//! fixed known plaintext under RK) is the wrong-key discriminator, written in
//! the same transaction as the DEKs.
//!
//! Scopes: the v9-era galaxy vocabulary ([`GALAXIES`], reused from
//! [`crate::compat::GEN2_GALAXY_DBS`], so sealed v9 stores stay openable by
//! the keyring that covered them) plus the Gen3 native record scope
//! ([`RECORD_SCOPE`] = the `records` DBI, whose bodies this module seals with
//! the [`crate::at_rest`] WMEN envelope). Gen3's galaxy routing is dynamic
//! (`corpus:<galaxy>` sources), so it is *not* safe to invent a DEK per
//! runtime galaxy; the store's record space is a single scope.
//!
//! Layout decisions (ported from v9):
//! - The generated key file lives at the store **root**, next to the seal
//!   key: when the open path's final component is `lmdb` (the standard
//!   `<store-root>/lmdb` layout) the key is `<store-root>/.at_rest_key`;
//!   other layouts (tests, custom paths) keep it inside the directory passed
//!   to the store open.
//! - The keyring DBI is **not** part of the store's required schema: legacy
//!   stores and strict read-only opens never create it.
//! - A writable open with `WM_AT_REST_MODE=off` onto a store whose keyring
//!   meta exists is refused (split-brain guard); read-only inspection still
//!   reports the mode.
//!
//! Design: v9 `docs/Q39_CRYPTO_ERASURE_DESIGN.md` §2/§3/§7.

use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::aead::{Aead, Payload};
use chacha20poly1305::{KeyInit, XChaCha20Poly1305, XNonce};
use lmdb::{Cursor, Database, DatabaseFlags, Environment, Transaction, WriteFlags};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::collections::HashMap;
use std::fmt;
use std::path::{Path, PathBuf};
use zeroize::Zeroizing;

/// LMDB DBI holding the at-rest key material.
pub const KEYRING_DB: &str = "keyring";
/// Keyring row holding the (non-secret) meta JSON.
pub const KEYRING_META_KEY: &[u8] = b"meta";
/// Keyring row holding the wrong-key discriminator (AEAD wrap of a fixed
/// known plaintext under RK; AAD `wm/at-rest/rk-check/v1`).
pub const RK_CHECK_KEY: &[u8] = b"rk:check";
/// Prefix of the `dek:<scope>` rows holding wrapped scope DEKs.
pub const DEK_KEY_PREFIX: &str = "dek:";
/// Keyring row holding the seal-on-rewrite migration ledger (JSON).
pub const MIGRATION_LEDGER_KEY: &[u8] = b"migration:v1";
/// Current keyring meta format version.
pub const KEYRING_FORMAT_VERSION: u32 = 1;
/// AAD (and known plaintext) for the `rk:check` row.
pub const RK_CHECK_INFO: &str = "wm/at-rest/rk-check/v1";
/// Fixed known plaintext wrapped under RK into `rk:check`.
pub const RK_CHECK_PLAINTEXT: &[u8] = b"wm/at-rest/rk-check/v1";
/// Default generated key-file name.
pub const AT_REST_KEY_FILE: &str = ".at_rest_key";
/// Final path component that marks the standard `<store-root>/lmdb` layout.
const AT_REST_LMDB_DIR: &str = "lmdb";
/// Root-key length (and generated key-file length) in bytes.
pub const AT_REST_KEY_LEN: usize = 32;

/// Gen3 native record scope: the `records` DBI whose bodies are sealed.
pub const RECORD_SCOPE: &str = "records";

/// Known v9-era galaxy sub-databases covered by the keyring. Reused from the
/// compat reader so sealed v9 records remain openable with the same keyring.
pub const GALAXIES: &[&str] = crate::compat::GEN2_GALAXY_DBS;

/// Every scope the keyring wraps a DEK for: the v9 galaxy vocabulary plus the
/// Gen3 native record scope.
pub fn scopes() -> impl Iterator<Item = &'static str> {
    GALAXIES
        .iter()
        .copied()
        .chain(std::iter::once(RECORD_SCOPE))
}

/// Number of scopes the keyring is expected to cover.
#[must_use]
pub const fn scope_count() -> usize {
    GALAXIES.len() + 1
}

/// Resolve the generated key-file path for a store directory.
///
/// Standard layouts pass `<store-root>/lmdb` to the store open: the key is
/// placed at the store root, `<store-root>/.at_rest_key`, next to
/// `.seal_key` — outside the directory that LMDB maintenance and restore
/// tooling rewrites. Non-standard layouts (tests, custom paths whose final
/// component is not `lmdb`) keep the key inside the directory passed in.
#[must_use]
pub fn generated_key_path(store_dir: &Path) -> PathBuf {
    let is_standard = store_dir
        .file_name()
        .is_some_and(|name| name == AT_REST_LMDB_DIR);
    if is_standard {
        if let Some(root) = store_dir.parent().filter(|p| !p.as_os_str().is_empty()) {
            return root.join(AT_REST_KEY_FILE);
        }
    }
    store_dir.join(AT_REST_KEY_FILE)
}

/// Wrap-layout version byte (row layout: `version || 24-byte nonce || AEAD ct+tag`).
const WRAP_VERSION: u8 = 1;
const NONCE_LEN: usize = 24;
const TAG_LEN: usize = 16;
/// Version byte + nonce.
const WRAP_HEADER_LEN: usize = 1 + NONCE_LEN;
/// Minimum wrapped-secret length (header + tag).
const WRAP_MIN_LEN: usize = WRAP_HEADER_LEN + TAG_LEN;

/// Argon2id parameters ruled for mode C (OWASP minimum: 19 MiB, t=2, p=1).
const ARGON2_SALT_LEN: usize = 16;
const ARGON2_M_COST_KIB: u32 = 19_456;
const ARGON2_T_COST: u32 = 2;
const ARGON2_P_COST: u32 = 1;
const ARGON2_VERSION: u32 = 0x13;
/// Upper bounds for Argon2 parameters accepted from keyring meta: the meta
/// row is store-local data, and a tampered one must not turn unlock into a
/// resource-exhaustion primitive (E10 Q39A finding).
const ARGON2_M_COST_MAX_KIB: u32 = 1_048_576; // 1 GiB
const ARGON2_T_COST_MAX: u32 = 64;
const ARGON2_P_COST_MAX: u32 = 16;

/// At-rest failure: always carries an actionable, non-secret message.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AtRestError {
    /// Human-readable failure reason.
    Msg(String),
}

impl AtRestError {
    /// Build an error from any displayable message.
    pub(crate) fn msg(message: impl Into<String>) -> Self {
        Self::Msg(message.into())
    }

    /// The underlying message.
    #[must_use]
    pub fn message(&self) -> &str {
        match self {
            Self::Msg(message) => message,
        }
    }
}

impl fmt::Display for AtRestError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.message())
    }
}

impl std::error::Error for AtRestError {}

impl From<lmdb::Error> for AtRestError {
    fn from(error: lmdb::Error) -> Self {
        Self::Msg(format!("lmdb: {error}"))
    }
}

/// Local result alias for at-rest operations.
pub type Result<T, E = AtRestError> = std::result::Result<T, E>;

fn mem_err(message: impl Into<String>) -> AtRestError {
    AtRestError::msg(message)
}

// ── Configuration ──────────────────────────────────────────────────────

/// At-rest mode for a store.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AtRestMode {
    /// Plaintext pass-through: no keyring, no behavior change.
    Off,
    /// Mode B — RK from `WM_AT_REST_ROOT_KEY`, `WM_AT_REST_KEY_FILE`, or a
    /// generated store-local key file.
    Keyfile,
    /// Mode C — RK = Argon2id(passphrase).
    Passphrase,
}

impl AtRestMode {
    /// Parse the `WM_AT_REST_MODE` spelling (case-insensitive).
    #[must_use]
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().as_str() {
            "off" => Some(Self::Off),
            "keyfile" => Some(Self::Keyfile),
            "passphrase" => Some(Self::Passphrase),
            _ => None,
        }
    }

    /// Canonical lowercase spelling (also the `meta.mode` serde form).
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Off => "off",
            Self::Keyfile => "keyfile",
            Self::Passphrase => "passphrase",
        }
    }
}

impl std::fmt::Display for AtRestMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Environment-driven at-rest configuration.
///
/// Deliberately no `Debug`: it can carry the root key and the passphrase.
#[derive(Clone)]
pub struct AtRestConfig {
    mode: AtRestMode,
    root_key: Option<Zeroizing<String>>,
    key_file: Option<PathBuf>,
    passphrase: Option<Zeroizing<String>>,
}

impl Default for AtRestConfig {
    fn default() -> Self {
        Self::off()
    }
}

/// Parse a raw `WM_AT_REST_MODE` value: unset is `off`, anything
/// unrecognized is a hard error (fail-closed — a typo must never silently
/// downgrade a store to plaintext).
pub fn mode_from_env_value(value: Option<&str>) -> Result<AtRestMode> {
    match value {
        Some(raw) => AtRestMode::parse(raw).ok_or_else(|| {
            mem_err(format!(
                "WM_AT_REST_MODE='{raw}' is not off|keyfile|passphrase — refusing to open \
                 (fail-closed); fix or unset the variable"
            ))
        }),
        None => Ok(AtRestMode::Off),
    }
}

impl AtRestConfig {
    /// Dark by default — zero behavior change.
    #[must_use]
    pub const fn off() -> Self {
        Self {
            mode: AtRestMode::Off,
            root_key: None,
            key_file: None,
            passphrase: None,
        }
    }

    /// Read `WM_AT_REST_MODE` (off | keyfile | passphrase, default off),
    /// `WM_AT_REST_KEY_FILE`, `WM_AT_REST_ROOT_KEY`, `WM_AT_REST_PASSPHRASE`.
    ///
    /// A set-but-unrecognized mode refuses the read (fail-closed): a typo
    /// must never silently downgrade an open to plaintext pass-through.
    pub fn from_env() -> Result<Self> {
        let mode = mode_from_env_value(std::env::var("WM_AT_REST_MODE").ok().as_deref())?;
        let root_key = std::env::var("WM_AT_REST_ROOT_KEY")
            .ok()
            .filter(|v| !v.is_empty())
            .map(Zeroizing::new);
        let key_file = std::env::var("WM_AT_REST_KEY_FILE")
            .ok()
            .filter(|v| !v.is_empty())
            .map(PathBuf::from);
        let passphrase = std::env::var("WM_AT_REST_PASSPHRASE")
            .ok()
            .filter(|v| !v.is_empty())
            .map(Zeroizing::new);
        Ok(Self {
            mode,
            root_key,
            key_file,
            passphrase,
        })
    }

    /// Mode-B config with an explicit material root key (64 hex chars or 32
    /// raw bytes). Tests use this to avoid env mutation.
    #[must_use]
    pub fn keyfile_with_root_key(material: impl Into<String>) -> Self {
        Self {
            mode: AtRestMode::Keyfile,
            root_key: Some(Zeroizing::new(material.into())),
            key_file: None,
            passphrase: None,
        }
    }

    /// Mode-B config with an explicit key file (created if missing).
    #[must_use]
    pub fn keyfile_with_key_file(path: impl Into<PathBuf>) -> Self {
        Self {
            mode: AtRestMode::Keyfile,
            root_key: None,
            key_file: Some(path.into()),
            passphrase: None,
        }
    }

    /// Mode-B config that resolves the generated key file
    /// ([`generated_key_path`]: store root for the standard layout).
    #[must_use]
    pub const fn keyfile() -> Self {
        Self {
            mode: AtRestMode::Keyfile,
            root_key: None,
            key_file: None,
            passphrase: None,
        }
    }

    /// Mode-C config with an explicit passphrase.
    #[must_use]
    pub fn passphrase(passphrase: impl Into<String>) -> Self {
        Self {
            mode: AtRestMode::Passphrase,
            root_key: None,
            key_file: None,
            passphrase: Some(Zeroizing::new(passphrase.into())),
        }
    }

    /// Configured mode.
    #[must_use]
    pub const fn mode(&self) -> AtRestMode {
        self.mode
    }
}

// ── Meta / status ──────────────────────────────────────────────────────

/// Non-secret Argon2id parameters recorded in the keyring meta (mode C).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Argon2Params {
    /// Memory cost in KiB.
    pub m_cost_kib: u32,
    /// Time cost (iterations).
    pub t_cost: u32,
    /// Parallelism.
    pub p_cost: u32,
    /// Argon2 version constant (0x13 = v19).
    pub version: u32,
    /// Random 16-byte salt, hex-encoded.
    pub salt_hex: String,
}

/// Non-secret keyring meta row (JSON).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct KeyringMeta {
    /// Keyring format version ([`KEYRING_FORMAT_VERSION`]).
    pub format_version: u32,
    /// Mode the store was initialized under.
    pub mode: AtRestMode,
    /// How the RK was obtained at initialization: `env_root_key` |
    /// `key_file` | `generated_key_file` | `argon2id_passphrase`.
    pub key_source: String,
    /// RFC 3339 creation timestamp.
    pub created_at: String,
    /// Argon2id parameters (mode C only; `None` for mode B).
    #[serde(default)]
    pub argon2: Option<Argon2Params>,
}

/// Read-only at-rest disclosure status (meta only — never resolves the RK).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AtRestStatus {
    /// No keyring in this store: plaintext pass-through.
    Absent,
    /// Keyring present and parseable.
    Present(AtRestStatusPresent),
    /// Keyring present but the meta row is unreadable/unsupported — the
    /// store refuses writable opens until repaired (fail-closed).
    Malformed {
        /// Human-readable reason for the disclosure line.
        reason: String,
    },
}

/// Parsed keyring status for a store with at-rest state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AtRestStatusPresent {
    /// Non-secret meta.
    pub meta: KeyringMeta,
    /// Wrapped `dek:*` rows found in the keyring DBI.
    pub wrapped_deks: usize,
    /// Scopes the keyring is expected to cover (v9 galaxies + Gen3 records).
    pub galaxies: usize,
    /// Resolved key-file path when the RK came from a file (generated or
    /// explicitly configured); `None` for env material / passphrase.
    pub key_file: Option<PathBuf>,
}

/// Unlocked keyring state for a writable at-rest store.
///
/// Holds the unwrapped scope DEKs (zeroized on drop).
pub struct AtRestState {
    meta: KeyringMeta,
    key_file: Option<PathBuf>,
    deks: HashMap<String, Zeroizing<[u8; AT_REST_KEY_LEN]>>,
}

impl AtRestState {
    /// Non-secret keyring meta.
    #[must_use]
    pub const fn meta(&self) -> &KeyringMeta {
        &self.meta
    }

    /// Unwrapped DEK for a scope, by `Galaxy::db_name()` /
    /// [`RECORD_SCOPE`] name.
    #[must_use]
    pub fn galaxy_dek(&self, galaxy_db_name: &str) -> Option<&[u8; AT_REST_KEY_LEN]> {
        self.deks.get(galaxy_db_name).map(|dek| &**dek)
    }

    /// Number of unwrapped DEKs held.
    #[must_use]
    pub fn dek_count(&self) -> usize {
        self.deks.len()
    }

    /// Status view (meta + counts), never exposing key bytes.
    #[must_use]
    pub fn status(&self) -> AtRestStatusPresent {
        AtRestStatusPresent {
            meta: self.meta.clone(),
            wrapped_deks: self.deks.len(),
            galaxies: scope_count(),
            key_file: self.key_file.clone(),
        }
    }
}

// ── Crypto primitives ──────────────────────────────────────────────────

pub(crate) fn fill_random(buf: &mut [u8]) -> Result<()> {
    getrandom::fill(buf).map_err(|e| {
        mem_err(format!(
            "at-rest entropy source failed ({e}) — refusing to generate weak key material"
        ))
    })
}

pub(crate) fn hex_encode(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        out.push(HEX[(b >> 4) as usize] as char);
        out.push(HEX[(b & 0x0f) as usize] as char);
    }
    out
}

fn hex_decode(hex: &str) -> Option<Vec<u8>> {
    if hex.len() % 2 != 0 {
        return None;
    }
    let mut out = Vec::with_capacity(hex.len() / 2);
    for chunk in hex.as_bytes().chunks_exact(2) {
        let hi = hex_val(chunk[0])?;
        let lo = hex_val(chunk[1])?;
        out.push((hi << 4) | lo);
    }
    Some(out)
}

const fn hex_val(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(b - b'a' + 10),
        b'A'..=b'F' => Some(b - b'A' + 10),
        _ => None,
    }
}

/// Row layout: `version byte || 24-byte nonce || XChaCha20-Poly1305 ct+tag`.
fn wrap(key: &[u8; AT_REST_KEY_LEN], info: &str, plaintext: &[u8]) -> Result<Vec<u8>> {
    let cipher = XChaCha20Poly1305::new(key.into());
    let mut nonce = [0u8; NONCE_LEN];
    fill_random(&mut nonce)?;
    let ciphertext = cipher
        .encrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: plaintext,
                aad: info.as_bytes(),
            },
        )
        .map_err(|_| mem_err("at-rest wrap failed (AEAD error)"))?;
    let mut out = Vec::with_capacity(WRAP_HEADER_LEN + ciphertext.len());
    out.push(WRAP_VERSION);
    out.extend_from_slice(&nonce);
    out.extend_from_slice(&ciphertext);
    Ok(out)
}

/// Reverse of [`wrap`]; any bitflip in the version byte, nonce, ciphertext,
/// tag, AAD, or key makes this fail closed.
fn unwrap_secret(
    key: &[u8; AT_REST_KEY_LEN],
    info: &str,
    blob: &[u8],
) -> std::result::Result<Zeroizing<Vec<u8>>, String> {
    if blob.len() < WRAP_MIN_LEN {
        return Err(format!(
            "wrapped value is {} bytes (minimum {WRAP_MIN_LEN})",
            blob.len()
        ));
    }
    if blob[0] != WRAP_VERSION {
        return Err(format!(
            "unsupported wrap version {} (expected {WRAP_VERSION})",
            blob[0]
        ));
    }
    let cipher = XChaCha20Poly1305::new(key.into());
    let nonce = XNonce::from_slice(&blob[1..WRAP_HEADER_LEN]);
    let ciphertext = &blob[WRAP_HEADER_LEN..];
    cipher
        .decrypt(
            nonce,
            Payload {
                msg: ciphertext,
                aad: info.as_bytes(),
            },
        )
        .map(Zeroizing::new)
        .map_err(|_| "ciphertext authentication failed".to_string())
}

/// Canonical 32-byte root key from `WM_AT_REST_ROOT_KEY`-style material
/// (64 hex chars decode; 32 raw bytes pass through).
fn root_key_from_material(material: &str) -> Result<Zeroizing<[u8; AT_REST_KEY_LEN]>> {
    let bytes = Zeroizing::new(crate::kdf::root_bytes(material));
    if bytes.len() != AT_REST_KEY_LEN {
        return Err(mem_err(format!(
            "at-rest root key material is {} bytes after canonicalization, expected \
             {AT_REST_KEY_LEN} (use 64 hex chars or 32 raw bytes)",
            bytes.len()
        )));
    }
    let mut out = Zeroizing::new([0u8; AT_REST_KEY_LEN]);
    out.copy_from_slice(&bytes);
    Ok(out)
}

fn argon2_params(salt: &[u8; ARGON2_SALT_LEN]) -> Argon2Params {
    Argon2Params {
        m_cost_kib: ARGON2_M_COST_KIB,
        t_cost: ARGON2_T_COST,
        p_cost: ARGON2_P_COST,
        version: ARGON2_VERSION,
        salt_hex: hex_encode(salt),
    }
}

/// Reject Argon2 parameters from keyring meta that this build would not
/// have written: an unsupported version or values large enough to exhaust
/// memory/CPU on unlock (fail-closed, before any allocation).
fn validate_argon2_params(params: &Argon2Params) -> Result<()> {
    if params.version != ARGON2_VERSION {
        return Err(mem_err(format!(
            "at-rest Argon2 version {} is not supported (expected {ARGON2_VERSION})",
            params.version
        )));
    }
    if params.m_cost_kib > ARGON2_M_COST_MAX_KIB
        || params.t_cost > ARGON2_T_COST_MAX
        || params.p_cost > ARGON2_P_COST_MAX
    {
        return Err(mem_err(format!(
            "at-rest Argon2 parameters exceed sane bounds (m={} KiB max {ARGON2_M_COST_MAX_KIB}, \
             t={} max {ARGON2_T_COST_MAX}, p={} max {ARGON2_P_COST_MAX}) — refusing to derive",
            params.m_cost_kib, params.t_cost, params.p_cost
        )));
    }
    Ok(())
}

fn derive_rk_from_passphrase(
    passphrase: &str,
    params: &Argon2Params,
) -> Result<Zeroizing<[u8; AT_REST_KEY_LEN]>> {
    validate_argon2_params(params)?;
    let salt = hex_decode(&params.salt_hex)
        .ok_or_else(|| mem_err("at-rest keyring meta has a non-hex Argon2 salt"))?;
    let params = Params::new(
        params.m_cost_kib,
        params.t_cost,
        params.p_cost,
        Some(AT_REST_KEY_LEN),
    )
    .map_err(|e| mem_err(format!("at-rest Argon2 parameters rejected: {e}")))?;
    let argon = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);
    let mut out = Zeroizing::new([0u8; AT_REST_KEY_LEN]);
    argon
        .hash_password_into(passphrase.as_bytes(), &salt, out.as_mut())
        .map_err(|e| mem_err(format!("at-rest Argon2 derivation failed: {e}")))?;
    Ok(out)
}

/// Open (read) an existing key file; when `allow_create` is set and the file
/// is missing, generate 32 bytes with mode 0600. Never regenerates over an
/// existing file, and never falls back to weak entropy.
fn load_or_create_key_file(
    path: &Path,
    allow_create: bool,
) -> Result<Zeroizing<[u8; AT_REST_KEY_LEN]>> {
    if path.exists() {
        let bytes = Zeroizing::new(std::fs::read(path).map_err(|e| {
            mem_err(format!(
                "cannot read at-rest key file {}: {e}",
                path.display()
            ))
        })?);
        if bytes.len() != AT_REST_KEY_LEN {
            return Err(mem_err(format!(
                "at-rest key file {} is {} bytes, expected {AT_REST_KEY_LEN}",
                path.display(),
                bytes.len()
            )));
        }
        let mut out = Zeroizing::new([0u8; AT_REST_KEY_LEN]);
        out.copy_from_slice(&bytes);
        return Ok(out);
    }
    if !allow_create {
        return Err(mem_err(format!(
            "at-rest key file is missing at {} — refusing to regenerate (keyring meta exists); \
             restore the file or provide WM_AT_REST_ROOT_KEY",
            path.display()
        )));
    }
    let mut key = Zeroizing::new([0u8; AT_REST_KEY_LEN]);
    fill_random(key.as_mut())?;
    write_key_file(path, &key)?;
    Ok(key)
}

fn write_key_file(path: &Path, key: &[u8; AT_REST_KEY_LEN]) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| {
            mem_err(format!(
                "cannot create key-file directory {}: {e}",
                parent.display()
            ))
        })?;
    }
    #[cfg(unix)]
    {
        use std::io::Write as _;
        use std::os::unix::fs::OpenOptionsExt as _;
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(path)
            .map_err(|e| {
                mem_err(format!(
                    "cannot create at-rest key file {}: {e}",
                    path.display()
                ))
            })?;
        file.write_all(key).map_err(|e| {
            mem_err(format!(
                "cannot write at-rest key file {}: {e}",
                path.display()
            ))
        })?;
    }
    #[cfg(not(unix))]
    {
        std::fs::write(path, key).map_err(|e| {
            mem_err(format!(
                "cannot write at-rest key file {}: {e}",
                path.display()
            ))
        })?;
    }
    Ok(())
}

// ── Keyring read/write ─────────────────────────────────────────────────

enum KeyringPresence {
    /// No keyring DBI, or an empty one (crash between DBI creation and the
    /// init transaction) — writable opens may (re)initialize.
    Absent,
    /// Meta parses.
    Meta(Box<KeyringMeta>),
    /// Meta exists but cannot be parsed — fail closed.
    Unreadable(String),
}

/// Any rows at all in the keyring DBI? Distinguishes a truly-empty DBI
/// (crash between `create_db` and the init transaction — safe to
/// re-initialize) from orphaned key material (`dek:*`/`rk:check` rows with
/// no `meta` row), which must fail closed rather than be overwritten.
fn keyring_has_rows<T: Transaction>(tx: &T, db: Database) -> Result<bool> {
    let mut cursor = tx
        .open_ro_cursor(db)
        .map_err(|e| mem_err(format!("LMDB cursor failed for the at-rest keyring: {e}")))?;
    Ok(cursor.iter().next().is_some())
}

fn read_presence(env: &Environment) -> Result<KeyringPresence> {
    let db = match env.open_db(Some(KEYRING_DB)) {
        Ok(db) => db,
        Err(lmdb::Error::NotFound) => return Ok(KeyringPresence::Absent),
        Err(e) => {
            return Err(mem_err(format!(
                "LMDB open_db failed for the at-rest keyring: {e}"
            )));
        }
    };
    let tx = env
        .begin_ro_txn()
        .map_err(|e| mem_err(format!("LMDB ro_txn failed (at-rest keyring): {e}")))?;
    let presence = match tx.get(db, &KEYRING_META_KEY) {
        Ok(bytes) => match serde_json::from_slice::<KeyringMeta>(bytes) {
            // A future-format keyring must fail the writable path too, not
            // just the disclosure path: older code must never interpret
            // rows it does not understand (forward-compat, E10 Q39A).
            Ok(meta) if meta.format_version != KEYRING_FORMAT_VERSION => {
                KeyringPresence::Unreadable(format!(
                    "unsupported keyring format_version {} (this build reads \
                     {KEYRING_FORMAT_VERSION})",
                    meta.format_version
                ))
            }
            Ok(meta) => KeyringPresence::Meta(Box::new(meta)),
            Err(e) => KeyringPresence::Unreadable(e.to_string()),
        },
        Err(lmdb::Error::NotFound) => {
            if keyring_has_rows(&tx, db)? {
                KeyringPresence::Unreadable(
                    "the keyring DBI holds `dek:*`/`rk:check` rows but no `meta` row \
                     (orphaned key material)"
                        .to_string(),
                )
            } else {
                KeyringPresence::Absent
            }
        }
        Err(e) => {
            return Err(mem_err(format!(
                "LMDB read failed for the at-rest keyring meta: {e}"
            )));
        }
    };
    tx.commit()
        .map_err(|e| mem_err(format!("LMDB commit failed (at-rest keyring): {e}")))?;
    Ok(presence)
}

/// Optionally open the keyring DBI on read paths — never creates.
pub fn open_keyring_optional(env: &Environment) -> Result<Option<Database>> {
    match env.open_db(Some(KEYRING_DB)) {
        Ok(db) => Ok(Some(db)),
        Err(lmdb::Error::NotFound) => Ok(None),
        Err(e) => Err(mem_err(format!(
            "LMDB open_db failed for the optional at-rest keyring: {e}"
        ))),
    }
}

/// Read-only status from a keyring DBI handle (never resolves the RK).
pub fn read_status(env: &Environment, db: Database, store_dir: &Path) -> AtRestStatus {
    {
        let tx = match env.begin_ro_txn() {
            Ok(tx) => tx,
            Err(e) => {
                return AtRestStatus::Malformed {
                    reason: format!("LMDB ro_txn failed: {e}"),
                };
            }
        };
        let meta = match tx.get(db, &KEYRING_META_KEY) {
            Ok(bytes) => match serde_json::from_slice::<KeyringMeta>(bytes) {
                Ok(meta) => meta,
                Err(e) => {
                    return AtRestStatus::Malformed {
                        reason: format!("meta row does not parse as keyring JSON: {e}"),
                    };
                }
            },
            Err(lmdb::Error::NotFound) => {
                return match keyring_has_rows(&tx, db) {
                    Ok(true) => AtRestStatus::Malformed {
                        reason: "the keyring DBI holds `dek:*`/`rk:check` rows but no `meta` \
                                 row (orphaned key material)"
                            .to_string(),
                    },
                    Ok(false) => AtRestStatus::Absent,
                    Err(e) => AtRestStatus::Malformed {
                        reason: e.to_string(),
                    },
                };
            }
            Err(e) => {
                return AtRestStatus::Malformed {
                    reason: format!("meta row unreadable: {e}"),
                };
            }
        };

        let mut wrapped_deks = 0usize;
        let mut has_rk_check = false;
        match tx.open_ro_cursor(db) {
            Ok(mut cursor) => {
                for (key, _) in cursor.iter() {
                    if key.starts_with(DEK_KEY_PREFIX.as_bytes()) {
                        wrapped_deks += 1;
                    } else if key == RK_CHECK_KEY {
                        has_rk_check = true;
                    }
                }
            }
            Err(e) => {
                return AtRestStatus::Malformed {
                    reason: format!("keyring cursor failed: {e}"),
                };
            }
        }
        let _ = tx.commit();

        if meta.format_version != KEYRING_FORMAT_VERSION {
            return AtRestStatus::Malformed {
                reason: format!(
                    "unsupported keyring format_version {} (this build reads {KEYRING_FORMAT_VERSION})",
                    meta.format_version
                ),
            };
        }
        if meta.mode == AtRestMode::Passphrase && meta.argon2.is_none() {
            return AtRestStatus::Malformed {
                reason: "mode is 'passphrase' but the Argon2 parameters are missing".to_string(),
            };
        }
        if !has_rk_check {
            return AtRestStatus::Malformed {
                reason: "the rk:check wrong-key discriminator row is missing".to_string(),
            };
        }

        let key_file = disclosed_key_file(&meta, store_dir);
        AtRestStatus::Present(AtRestStatusPresent {
            meta,
            wrapped_deks,
            galaxies: scope_count(),
            key_file,
        })
    }
}

// ── Open-time integration ──────────────────────────────────────────────

/// Resolve the RK for a first initialization, generating mode-C salt and the
/// per-mode key source.
struct NewRootKey {
    rk: Zeroizing<[u8; AT_REST_KEY_LEN]>,
    key_source: &'static str,
    argon2: Option<Argon2Params>,
}

/// Key-file path disclosed for a keyring rooted in a file. The generated
/// store-local path is derivable from the store alone; an explicitly
/// configured path was an open-time input never recorded in the meta, so it
/// is disclosed only when this environment still has `WM_AT_REST_KEY_FILE`.
fn disclosed_key_file(meta: &KeyringMeta, store_dir: &Path) -> Option<PathBuf> {
    match meta.key_source.as_str() {
        "generated_key_file" => Some(generated_key_path(store_dir)),
        "key_file" => std::env::var("WM_AT_REST_KEY_FILE")
            .ok()
            .filter(|value| !value.is_empty())
            .map(PathBuf::from),
        _ => None,
    }
}

fn resolve_new_root_key(store_dir: &Path, config: &AtRestConfig) -> Result<NewRootKey> {
    match config.mode {
        AtRestMode::Passphrase => {
            let passphrase = config.passphrase.as_deref().ok_or_else(|| {
                mem_err(
                    "WM_AT_REST_MODE=passphrase requires WM_AT_REST_PASSPHRASE to initialize \
                     the store",
                )
            })?;
            let mut salt = [0u8; ARGON2_SALT_LEN];
            fill_random(&mut salt)?;
            let params = argon2_params(&salt);
            let rk = derive_rk_from_passphrase(passphrase, &params)?;
            Ok(NewRootKey {
                rk,
                key_source: "argon2id_passphrase",
                argon2: Some(params),
            })
        }
        AtRestMode::Keyfile => {
            if let Some(material) = config.root_key.as_deref() {
                return Ok(NewRootKey {
                    rk: root_key_from_material(material)?,
                    key_source: "env_root_key",
                    argon2: None,
                });
            }
            if let Some(path) = &config.key_file {
                let rk = load_or_create_key_file(path, true)?;
                return Ok(NewRootKey {
                    rk,
                    key_source: "key_file",
                    argon2: None,
                });
            }
            let path = generated_key_path(store_dir);
            let rk = load_or_create_key_file(&path, true)?;
            Ok(NewRootKey {
                rk,
                key_source: "generated_key_file",
                argon2: None,
            })
        }
        AtRestMode::Off => Err(mem_err(
            "at-rest keyring initialization requested with mode 'off'",
        )),
    }
}

fn resolve_existing_root_key(
    store_dir: &Path,
    config: &AtRestConfig,
    meta: &KeyringMeta,
) -> Result<Zeroizing<[u8; AT_REST_KEY_LEN]>> {
    match config.mode {
        AtRestMode::Passphrase => {
            let passphrase = config.passphrase.as_deref().ok_or_else(|| {
                mem_err("at-rest unlock failed: this store is mode C — set WM_AT_REST_PASSPHRASE")
            })?;
            let params = meta.argon2.as_ref().ok_or_else(|| {
                mem_err("at-rest keyring meta is mode C but has no Argon2 parameters")
            })?;
            derive_rk_from_passphrase(passphrase, params)
        }
        AtRestMode::Keyfile => {
            if let Some(material) = config.root_key.as_deref() {
                return root_key_from_material(material);
            }
            if let Some(path) = &config.key_file {
                return load_or_create_key_file(path, false);
            }
            match meta.key_source.as_str() {
                "generated_key_file" => {
                    load_or_create_key_file(&generated_key_path(store_dir), false)
                }
                "env_root_key" => Err(mem_err(
                    "at-rest unlock failed: this store's keyring was initialized from \
                     WM_AT_REST_ROOT_KEY — set it (this is not a wrong-key error, the source \
                     was simply not provided)",
                )),
                "key_file" => Err(mem_err(
                    "at-rest unlock failed: this store's keyring was initialized from a \
                     configured key file — set WM_AT_REST_KEY_FILE",
                )),
                other => Err(mem_err(format!(
                    "at-rest unlock failed: unknown key source '{other}' — provide \
                     WM_AT_REST_ROOT_KEY or WM_AT_REST_KEY_FILE"
                ))),
            }
        }
        AtRestMode::Off => Err(mem_err("at-rest unlock requested with mode 'off'")),
    }
}

fn dek_key(galaxy_db_name: &str) -> String {
    format!("{DEK_KEY_PREFIX}{galaxy_db_name}")
}

/// Initialize a fresh keyring: `meta`, `rk:check`, and one wrapped DEK per
/// scope in one write transaction. Re-checks for a concurrent first-init
/// inside the transaction (last-writer-wins keyrings are a split-brain; the
/// loser unlocks instead of overwriting).
fn initialize(
    env: &Environment,
    store_dir: &Path,
    config: &AtRestConfig,
) -> Result<(Database, AtRestState)> {
    let db = env
        .create_db(Some(KEYRING_DB), DatabaseFlags::default())
        .map_err(|e| mem_err(format!("LMDB create_db failed for keyring: {e}")))?;
    let mut tx = env
        .begin_rw_txn()
        .map_err(|e| mem_err(format!("LMDB rw_txn failed (at-rest init): {e}")))?;

    // Lost a concurrent first-init race: the winner's keyring is authoritative.
    match tx.get(db, &KEYRING_META_KEY) {
        Ok(existing) => {
            let meta: KeyringMeta = serde_json::from_slice(existing).map_err(|e| {
                mem_err(format!(
                    "at-rest keyring appeared during initialization but its meta does not \
                     parse: {e}"
                ))
            })?;
            tx.abort();
            if meta.format_version != KEYRING_FORMAT_VERSION {
                return Err(mem_err(format!(
                    "at-rest keyring appeared during initialization with unsupported \
                     format_version {} (this build reads {KEYRING_FORMAT_VERSION}) — \
                     refusing to touch it",
                    meta.format_version
                )));
            }
            if meta.mode != config.mode {
                return Err(mem_err(format!(
                    "at-rest mode mismatch: store was initialized as '{}' but this open \
                     requested '{}'",
                    meta.mode, config.mode
                )));
            }
            let state = unlock(env, db, store_dir, config, meta)?;
            return Ok((db, state));
        }
        Err(lmdb::Error::NotFound) => {
            if keyring_has_rows(&tx, db)? {
                tx.abort();
                return Err(mem_err(
                    "at-rest keyring DBI contains rows but no `meta` row — refusing to \
                     initialize over orphaned key material (fail-closed); restore the meta \
                     row or deliberately remove the keyring DBI",
                ));
            }
        }
        Err(e) => return Err(mem_err(format!("LMDB read failed (at-rest init): {e}"))),
    }

    let resolved = resolve_new_root_key(store_dir, config)?;
    let meta = KeyringMeta {
        format_version: KEYRING_FORMAT_VERSION,
        mode: config.mode,
        key_source: resolved.key_source.to_string(),
        created_at: chrono::Utc::now().to_rfc3339(),
        argon2: resolved.argon2.clone(),
    };
    let meta_json = serde_json::to_vec(&meta)
        .map_err(|e| mem_err(format!("at-rest meta serialization failed: {e}")))?;
    let check = wrap(&resolved.rk, RK_CHECK_INFO, RK_CHECK_PLAINTEXT)?;

    let mut deks: HashMap<String, Zeroizing<[u8; AT_REST_KEY_LEN]>> = HashMap::new();
    for name in scopes() {
        let mut dek = Zeroizing::new([0u8; AT_REST_KEY_LEN]);
        fill_random(dek.as_mut())?;
        let info = crate::kdf::galaxy_dek_info(name);
        let kek = Zeroizing::new(crate::kdf::hkdf32(&resolved.rk[..], &info));
        let wrapped = wrap(&kek, &info, &dek[..])?;
        tx.put(db, &dek_key(name), &wrapped, WriteFlags::default())
            .map_err(|e| mem_err(format!("LMDB put failed (at-rest DEK {name}): {e}")))?;
        deks.insert(name.to_string(), dek);
    }
    tx.put(db, &KEYRING_META_KEY, &meta_json, WriteFlags::default())
        .map_err(|e| mem_err(format!("LMDB put failed (at-rest meta): {e}")))?;
    tx.put(db, &RK_CHECK_KEY, &check, WriteFlags::default())
        .map_err(|e| mem_err(format!("LMDB put failed (at-rest rk:check): {e}")))?;
    tx.commit()
        .map_err(|e| mem_err(format!("LMDB commit failed (at-rest init): {e}")))?;

    let key_file = disclosed_key_file(&meta, store_dir);
    Ok((
        db,
        AtRestState {
            meta,
            key_file,
            deks,
        },
    ))
}

/// Unlock an existing keyring: verify `rk:check`, then unwrap every scope DEK.
fn unlock(
    env: &Environment,
    db: Database,
    store_dir: &Path,
    config: &AtRestConfig,
    meta: KeyringMeta,
) -> Result<AtRestState> {
    let rk = resolve_existing_root_key(store_dir, config, &meta)?;
    let tx = env
        .begin_ro_txn()
        .map_err(|e| mem_err(format!("LMDB ro_txn failed (at-rest unlock): {e}")))?;

    let check_blob = tx.get(db, &RK_CHECK_KEY).map_err(|e| {
        mem_err(format!(
            "at-rest keyring is missing its rk:check row ({e}) — refusing to unlock (fail-closed)"
        ))
    })?;
    let check = unwrap_secret(&rk, RK_CHECK_INFO, check_blob).map_err(|reason| {
        mem_err(format!(
            "at-rest unlock failed: the provided root key/passphrase does not match this \
             store's keyring ({reason})"
        ))
    })?;
    if check.as_slice() != RK_CHECK_PLAINTEXT {
        return Err(mem_err(
            "at-rest unlock failed: rk:check plaintext mismatch",
        ));
    }

    let mut deks: HashMap<String, Zeroizing<[u8; AT_REST_KEY_LEN]>> = HashMap::new();
    for name in scopes() {
        let blob = tx.get(db, &dek_key(name)).map_err(|e| {
            mem_err(format!(
                "at-rest keyring is missing the wrapped DEK row for scope '{name}' ({e}) — \
                 refusing to unlock (fail-closed)"
            ))
        })?;
        let info = crate::kdf::galaxy_dek_info(name);
        let kek = Zeroizing::new(crate::kdf::hkdf32(&rk[..], &info));
        let dek_bytes = unwrap_secret(&kek, &info, blob).map_err(|reason| {
            mem_err(format!(
                "at-rest keyring corrupt: wrapped DEK '{name}' failed authentication \
                 ({reason})"
            ))
        })?;
        let mut dek = Zeroizing::new([0u8; AT_REST_KEY_LEN]);
        dek.copy_from_slice(&dek_bytes);
        deks.insert(name.to_string(), dek);
    }
    tx.commit()
        .map_err(|e| mem_err(format!("LMDB commit failed (at-rest unlock): {e}")))?;

    let key_file = disclosed_key_file(&meta, store_dir);
    Ok(AtRestState {
        meta,
        key_file,
        deks,
    })
}

/// Open-time at-rest integration for a writable store.
///
/// Returns the keyring DBI handle (when a keyring exists) and the unlocked
/// state. `off` on a keyring store refuses (split-brain guard); a mode
/// mismatch refuses with an actionable message.
pub fn open_at_rest(
    env: &Environment,
    store_dir: &Path,
    config: &AtRestConfig,
) -> Result<(Option<Database>, Option<AtRestState>)> {
    let presence = read_presence(env)?;
    match (config.mode, presence) {
        (AtRestMode::Off, KeyringPresence::Absent) => Ok((None, None)),
        (AtRestMode::Off, KeyringPresence::Meta(meta)) => Err(mem_err(format!(
            "at-rest keyring present (mode '{}') but this writable open requested mode 'off' \
             — refusing a plaintext open of an at-rest store (split-brain guard); set \
             WM_AT_REST_MODE={} with the matching key source, or use a read-only inspection open",
            meta.mode, meta.mode
        ))),
        (AtRestMode::Off, KeyringPresence::Unreadable(reason)) => Err(mem_err(format!(
            "at-rest keyring present but its state is unreadable/malformed ({reason}) — \
             refusing writable mode 'off' (fail-closed); inspect with a read-only path"
        ))),
        (mode, KeyringPresence::Meta(meta)) => {
            if meta.mode != mode {
                return Err(mem_err(format!(
                    "at-rest mode mismatch: store keyring is mode '{}' but WM_AT_REST_MODE is \
                     '{}' — set WM_AT_REST_MODE={} and unlock with the matching key source",
                    meta.mode, mode, meta.mode
                )));
            }
            let db = env
                .open_db(Some(KEYRING_DB))
                .map_err(|e| mem_err(format!("LMDB open_db failed for keyring: {e}")))?;
            let state = unlock(env, db, store_dir, config, *meta)?;
            Ok((Some(db), Some(state)))
        }
        (_mode, KeyringPresence::Absent) => {
            let (db, state) = initialize(env, store_dir, config)?;
            Ok((Some(db), Some(state)))
        }
        (_mode, KeyringPresence::Unreadable(reason)) => Err(mem_err(format!(
            "at-rest keyring present but its state is unreadable/malformed ({reason}) — \
             refusing to initialize over it (fail-closed); restore the keyring or the key material"
        ))),
    }
}

// ── WMEN record envelope ───────────────────────────────────────────────

/// Magic prefix of a Q39 slice-B sealed record value.
pub const RECORD_MAGIC: [u8; 4] = *b"WMEN";

/// Envelope format version written after [`RECORD_MAGIC`].
pub const RECORD_FORMAT_VERSION: u8 = 1;

/// XChaCha20-Poly1305 nonce length.
pub const RECORD_NONCE_LEN: usize = 24;

/// Bytes before the ciphertext: magic + version byte + content version + nonce.
pub const RECORD_HEADER_LEN: usize = 4 + 1 + 8 + RECORD_NONCE_LEN;

/// Smallest well-formed sealed record (header + Poly1305 tag).
pub const RECORD_MIN_LEN: usize = RECORD_HEADER_LEN + 16;

/// AAD info prefix binding a record body to its scope.
const RECORD_AAD_INFO: &[u8] = b"wm/record-aead/v1";

/// Whether `bytes` carries the sealed-record magic. Our plaintext encodings
/// start with a msgpack array/map header, never `WMEN`, so this is
/// unambiguous for values this codec produces; an unknown future envelope
/// version still reaches [`open_record`] and fails closed there.
#[must_use]
pub fn is_sealed_record(bytes: &[u8]) -> bool {
    bytes.len() >= RECORD_MAGIC.len() && bytes[..RECORD_MAGIC.len()] == RECORD_MAGIC
}

/// AAD binding a record body to its scope, identity, and content version
/// (Q39 §2 ruling 1): `info || name_len || scope name || record id ||
/// version`, lengths/fixed-width fields making the encoding injective.
#[must_use]
pub fn record_aad(galaxy_db_name: &str, record_id: &[u8; 16], version: u64) -> Vec<u8> {
    let name = galaxy_db_name.as_bytes();
    let mut aad = Vec::with_capacity(RECORD_AAD_INFO.len() + 2 + name.len() + 16 + 8);
    aad.extend_from_slice(RECORD_AAD_INFO);
    aad.extend_from_slice(&(name.len() as u16).to_le_bytes());
    aad.extend_from_slice(name);
    aad.extend_from_slice(record_id);
    aad.extend_from_slice(&version.to_le_bytes());
    aad
}

/// Map a Gen3 `u64` record id (the `records` DBI key is `u64` big-endian)
/// onto the 16-byte record identity the v9 AAD encoding expects: the id in
/// the first 8 bytes and zeroes after. Injective, and stable across reopens.
#[must_use]
pub fn record_identity(record_id: u64) -> [u8; 16] {
    let mut identity = [0u8; 16];
    identity[..8].copy_from_slice(&record_id.to_be_bytes());
    identity
}

/// Sealed-record content version, when `blob` carries the envelope.
#[must_use]
pub fn sealed_record_version(blob: &[u8]) -> Option<u64> {
    if !is_sealed_record(blob) || blob.len() < RECORD_HEADER_LEN {
        return None;
    }
    let mut bytes = [0u8; 8];
    bytes.copy_from_slice(&blob[5..13]);
    Some(u64::from_le_bytes(bytes))
}

/// Seal a plaintext record body under the scope DEK. The content version
/// travels in the (AAD-bound) header so readers can rebuild the AAD before
/// decrypting.
#[must_use = "the sealed bytes are the value to store"]
pub fn seal_record(
    plaintext: &[u8],
    key: &[u8; 32],
    galaxy_db_name: &str,
    record_id: &[u8; 16],
    version: u64,
) -> std::result::Result<Vec<u8>, String> {
    let cipher = XChaCha20Poly1305::new(key.into());
    let mut nonce = [0u8; RECORD_NONCE_LEN];
    fill_random(&mut nonce).map_err(|e| format!("record seal entropy: {e}"))?;
    let aad = record_aad(galaxy_db_name, record_id, version);
    let ciphertext = cipher
        .encrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: plaintext,
                aad: &aad,
            },
        )
        .map_err(|_| "record seal failed (AEAD error)".to_string())?;
    let mut out = Vec::with_capacity(RECORD_HEADER_LEN + ciphertext.len());
    out.extend_from_slice(&RECORD_MAGIC);
    out.push(RECORD_FORMAT_VERSION);
    out.extend_from_slice(&version.to_le_bytes());
    out.extend_from_slice(&nonce);
    out.extend_from_slice(&ciphertext);
    Ok(out)
}

/// Open a sealed record body for `galaxy_db_name`/`record_id`. Any wrong
/// key, wrong identity (transplanted ciphertext), bitflip, or truncation
/// fails closed.
pub fn open_record(
    blob: &[u8],
    key: &[u8; 32],
    galaxy_db_name: &str,
    record_id: &[u8; 16],
) -> std::result::Result<Zeroizing<Vec<u8>>, String> {
    if blob.len() < RECORD_MIN_LEN {
        return Err(format!(
            "sealed record is {} bytes (minimum {RECORD_MIN_LEN})",
            blob.len()
        ));
    }
    if !is_sealed_record(blob) {
        return Err("value does not carry the WMEN record envelope".to_string());
    }
    if blob[4] != RECORD_FORMAT_VERSION {
        return Err(format!(
            "unsupported record envelope version {} (expected {RECORD_FORMAT_VERSION})",
            blob[4]
        ));
    }
    let version = sealed_record_version(blob).expect("length checked above");
    let aad = record_aad(galaxy_db_name, record_id, version);
    let cipher = XChaCha20Poly1305::new(key.into());
    let nonce = XNonce::from_slice(&blob[13..RECORD_HEADER_LEN]);
    let plaintext = cipher
        .decrypt(
            nonce,
            Payload {
                msg: &blob[RECORD_HEADER_LEN..],
                aad: &aad,
            },
        )
        .map_err(|_| {
            "record open failed (wrong key, tampered ciphertext, or AAD mismatch)".to_string()
        })?;
    Ok(Zeroizing::new(plaintext))
}

// ── Slice-B migration ledger ───────────────────────────────────────────

/// Per-scope progress row in the seal-on-rewrite migration ledger.
///
/// Crash-safe resume contract: `encrypted` is the count of records sealed
/// so far, `cursor_hex` is the last *scanned* key (hex) — records are
/// idempotently re-encryptable, so a crash between a batch commit and the
/// ledger write only repeats a bounded amount of work. `done` means the
/// scope's key space was scanned to the end.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct MigrationGalaxyState {
    /// Records sealed under the scope DEK so far (this migration run).
    pub encrypted: u64,
    /// Last scanned raw key, hex-encoded; empty = start of the keyspace.
    #[serde(default)]
    pub cursor_hex: String,
    /// Whether the whole keyspace has been scanned.
    #[serde(default)]
    pub done: bool,
}

/// The `migration:v1` ledger row (keyring DBI).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MigrationLedger {
    /// Ledger format version.
    #[serde(default = "default_migration_ledger_version")]
    pub version: u32,
    /// Per-scope progress, keyed by scope name (`records` for Gen3).
    #[serde(default)]
    pub galaxies: BTreeMap<String, MigrationGalaxyState>,
    /// RFC 3339 timestamp of the last ledger update.
    #[serde(default)]
    pub updated_at: String,
}

impl Default for MigrationLedger {
    fn default() -> Self {
        Self {
            version: default_migration_ledger_version(),
            galaxies: BTreeMap::new(),
            updated_at: String::new(),
        }
    }
}

const fn default_migration_ledger_version() -> u32 {
    1
}

/// Read the migration ledger from an already-open keyring DBI. A missing
/// row is the default (no migration has run); an unreadable row is a hard
/// error (a corrupt ledger must never silently restart a migration).
pub fn read_migration_ledger(env: &Environment, db: Database) -> Result<MigrationLedger> {
    let tx = env
        .begin_ro_txn()
        .map_err(|e| mem_err(format!("LMDB ro_txn failed (migration ledger): {e}")))?;
    let ledger = match tx.get(db, &MIGRATION_LEDGER_KEY) {
        Ok(bytes) => serde_json::from_slice::<MigrationLedger>(bytes).map_err(|e| {
            mem_err(format!(
                "migration ledger row does not parse as JSON ({e}) — refusing to migrate over it"
            ))
        })?,
        Err(lmdb::Error::NotFound) => MigrationLedger::default(),
        Err(e) => {
            return Err(mem_err(format!("LMDB read failed (migration ledger): {e}")));
        }
    };
    tx.commit()
        .map_err(|e| mem_err(format!("LMDB commit failed (migration ledger): {e}")))?;
    Ok(ledger)
}

/// Write the migration ledger row (same transaction discipline as record
/// batches: one txn per update, called after each committed batch).
pub fn write_migration_ledger(
    env: &Environment,
    db: Database,
    ledger: &MigrationLedger,
) -> Result<()> {
    let json = serde_json::to_vec(ledger)
        .map_err(|e| mem_err(format!("migration ledger serialization failed: {e}")))?;
    let mut tx = env
        .begin_rw_txn()
        .map_err(|e| mem_err(format!("LMDB rw_txn failed (migration ledger): {e}")))?;
    tx.put(db, &MIGRATION_LEDGER_KEY, &json, WriteFlags::default())
        .map_err(|e| mem_err(format!("LMDB put failed (migration ledger): {e}")))?;
    tx.commit()
        .map_err(|e| mem_err(format!("LMDB commit failed (migration ledger): {e}")))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TempDir(PathBuf);

    impl TempDir {
        fn new(label: &str) -> Self {
            let path = std::env::temp_dir().join(format!(
                "wm-gen3-at-rest-{label}-{}-{:?}",
                std::process::id(),
                std::thread::current().id()
            ));
            let _ = std::fs::remove_dir_all(&path);
            Self(path)
        }

        fn path(&self) -> &Path {
            &self.0
        }
    }

    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    fn test_env(path: &Path) -> Environment {
        std::fs::create_dir_all(path).unwrap();
        Environment::new()
            .set_max_dbs(16)
            .set_map_size(64 << 20)
            .open(path)
            .unwrap()
    }

    fn raw_keyring_rows(path: &Path) -> Vec<(Vec<u8>, Vec<u8>)> {
        let env = Environment::new()
            .set_max_dbs(64)
            .set_flags(lmdb::EnvironmentFlags::READ_ONLY)
            .open(path)
            .unwrap();
        let db = match env.open_db(Some(KEYRING_DB)) {
            Ok(db) => db,
            Err(_) => return Vec::new(),
        };
        let tx = env.begin_ro_txn().unwrap();
        let mut cursor = tx.open_ro_cursor(db).unwrap();
        let rows: Vec<(Vec<u8>, Vec<u8>)> = cursor
            .iter()
            .map(|(key, value)| (key.to_vec(), value.to_vec()))
            .collect();
        drop(cursor);
        let _ = tx.commit();
        rows
    }

    fn init_keyfile(dir: &Path) -> (Environment, Database, AtRestState) {
        let env = test_env(dir);
        let (db, state) = open_at_rest(&env, dir, &AtRestConfig::keyfile()).unwrap();
        (env, db.unwrap(), state.unwrap())
    }

    #[test]
    fn generated_key_path_follows_the_layout_rule() {
        assert_eq!(
            generated_key_path(Path::new("/srv/store/lmdb")),
            PathBuf::from("/srv/store/.at_rest_key"),
            "standard <store-root>/lmdb layout puts the key at the store root"
        );
        assert_eq!(
            generated_key_path(Path::new("/srv/custom")),
            PathBuf::from("/srv/custom/.at_rest_key"),
            "non-standard layouts keep the key inside the open path"
        );
        assert_eq!(
            generated_key_path(Path::new("lmdb")),
            PathBuf::from("lmdb/.at_rest_key"),
            "a bare relative 'lmdb' has no usable parent — keep it local"
        );
    }

    #[test]
    fn keyfile_init_wraps_all_scopes_and_writes_a_0600_key_file() {
        let tmp = TempDir::new("init");
        let (_env, _db, state) = init_keyfile(tmp.path());

        assert_eq!(state.dek_count(), scope_count());
        let meta = state.meta();
        assert_eq!(meta.format_version, KEYRING_FORMAT_VERSION);
        assert_eq!(meta.mode, AtRestMode::Keyfile);
        assert_eq!(meta.key_source, "generated_key_file");
        assert!(meta.argon2.is_none());

        let key_path = tmp.path().join(AT_REST_KEY_FILE);
        let bytes = std::fs::read(&key_path).unwrap();
        assert_eq!(bytes.len(), AT_REST_KEY_LEN);
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            let mode = std::fs::metadata(&key_path).unwrap().permissions().mode();
            assert_eq!(mode & 0o777, 0o600, "key file must be owner-only");
        }

        let rows = raw_keyring_rows(tmp.path());
        let dek_rows = rows
            .iter()
            .filter(|(key, _)| key.starts_with(DEK_KEY_PREFIX.as_bytes()))
            .count();
        assert_eq!(dek_rows, scope_count(), "one wrapped DEK per scope");
        assert!(rows.iter().any(|(key, _)| key == KEYRING_META_KEY));
        assert!(rows.iter().any(|(key, _)| key == RK_CHECK_KEY));

        // Every wrapped row has the documented layout: version, nonce, ct+tag.
        for (key, value) in &rows {
            if key.starts_with(DEK_KEY_PREFIX.as_bytes()) {
                assert_eq!(value[0], WRAP_VERSION);
                assert_eq!(value.len(), WRAP_HEADER_LEN + AT_REST_KEY_LEN + TAG_LEN);
            }
        }
    }

    #[test]
    fn reopen_unwraps_identical_deks_and_deks_differ_per_scope() {
        let tmp = TempDir::new("reopen");
        let first = {
            let (_env, _db, state) = init_keyfile(tmp.path());
            scopes()
                .map(|name| {
                    (
                        name.to_string(),
                        *state.galaxy_dek(name).expect("scope DEK"),
                    )
                })
                .collect::<Vec<_>>()
        };
        let env2 = test_env(tmp.path());
        let (_, state2) = open_at_rest(&env2, tmp.path(), &AtRestConfig::keyfile()).unwrap();
        let state2 = state2.unwrap();
        let second = scopes()
            .map(|name| {
                (
                    name.to_string(),
                    *state2.galaxy_dek(name).expect("scope DEK"),
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(first, second, "same key file must unwrap identical DEKs");

        let unique: std::collections::HashSet<[u8; AT_REST_KEY_LEN]> =
            first.iter().map(|(_, dek)| *dek).collect();
        assert_eq!(
            unique.len(),
            scope_count(),
            "every scope must get its own DEK"
        );
    }

    #[test]
    fn wrong_root_key_refuses_unlock_and_never_reinitializes() {
        let tmp = TempDir::new("wrong-key");
        let hex_a = "aa".repeat(AT_REST_KEY_LEN);
        let hex_b = "bb".repeat(AT_REST_KEY_LEN);
        {
            let env = test_env(tmp.path());
            drop(
                open_at_rest(
                    &env,
                    tmp.path(),
                    &AtRestConfig::keyfile_with_root_key(hex_a.clone()),
                )
                .unwrap(),
            );
        }
        let before = raw_keyring_rows(tmp.path());

        let env = test_env(tmp.path());
        let error = match open_at_rest(
            &env,
            tmp.path(),
            &AtRestConfig::keyfile_with_root_key(hex_b),
        ) {
            Ok(_) => panic!("wrong root key must refuse"),
            Err(error) => error,
        };
        assert!(error.to_string().contains("unlock failed"), "{error}");
        assert_eq!(
            raw_keyring_rows(tmp.path()),
            before,
            "a failed unlock must never rewrite the keyring"
        );

        let env_again = test_env(tmp.path());
        let (_, state) = open_at_rest(
            &env_again,
            tmp.path(),
            &AtRestConfig::keyfile_with_root_key(hex_a),
        )
        .unwrap();
        assert_eq!(state.unwrap().dek_count(), scope_count());
    }

    #[test]
    fn off_writable_open_of_a_keyring_store_is_refused_but_read_status_reports() {
        let tmp = TempDir::new("split-brain");
        {
            let env = test_env(tmp.path());
            let _ = init_keyfile_rows(&env, tmp.path());
        }

        let env = test_env(tmp.path());
        let error = match open_at_rest(&env, tmp.path(), &AtRestConfig::off()) {
            Ok(_) => panic!("plaintext writable open of an at-rest store must fail closed"),
            Err(error) => error,
        };
        let message = error.to_string();
        assert!(message.contains("keyring"), "{message}");
        assert!(message.contains("off"), "{message}");
        assert!(message.contains("split-brain"), "{message}");

        let db = open_keyring_optional(&env).unwrap().expect("keyring");
        match read_status(&env, db, tmp.path()) {
            AtRestStatus::Present(present) => {
                assert_eq!(present.meta.mode, AtRestMode::Keyfile);
                assert_eq!(present.wrapped_deks, scope_count());
                assert_eq!(present.galaxies, scope_count());
                assert!(
                    present
                        .key_file
                        .as_deref()
                        .is_some_and(|path| path.ends_with(AT_REST_KEY_FILE))
                );
            }
            other => panic!("expected Present, got {other:?}"),
        }
    }

    fn init_keyfile_rows(env: &Environment, dir: &Path) -> Database {
        let (db, _state) = open_at_rest(env, dir, &AtRestConfig::keyfile()).unwrap();
        db.unwrap()
    }

    #[test]
    fn off_creates_no_keyring_dbi_files_or_state() {
        let tmp = TempDir::new("off-clean");
        let env = test_env(tmp.path());
        let (db, state) = open_at_rest(&env, tmp.path(), &AtRestConfig::off()).unwrap();
        assert!(db.is_none());
        assert!(state.is_none());
        assert!(
            env.open_db(Some(KEYRING_DB)).is_err(),
            "off must not create the keyring DBI"
        );
        assert!(!tmp.path().join(AT_REST_KEY_FILE).exists());
        assert!(!tmp.path().join("keyring").exists());
    }

    #[test]
    fn passphrase_mode_stores_argon2_params_and_rejects_wrong_passphrase() {
        let tmp = TempDir::new("passphrase");
        {
            let env = test_env(tmp.path());
            let (_, state) = open_at_rest(
                &env,
                tmp.path(),
                &AtRestConfig::passphrase("correct horse battery staple"),
            )
            .unwrap();
            let meta = state.unwrap().meta().clone();
            assert_eq!(meta.mode, AtRestMode::Passphrase);
            assert_eq!(meta.key_source, "argon2id_passphrase");
            let argon = meta.argon2.expect("argon2 params stored");
            assert_eq!(argon.m_cost_kib, ARGON2_M_COST_KIB);
            assert_eq!(argon.t_cost, ARGON2_T_COST);
            assert_eq!(argon.p_cost, ARGON2_P_COST);
            assert_eq!(argon.version, ARGON2_VERSION);
            assert_eq!(argon.salt_hex.len(), ARGON2_SALT_LEN * 2);
            assert!(hex_decode(&argon.salt_hex).is_some());
        }

        let env = test_env(tmp.path());
        let error = match open_at_rest(
            &env,
            tmp.path(),
            &AtRestConfig::passphrase("wrong passphrase"),
        ) {
            Ok(_) => panic!("wrong passphrase must refuse"),
            Err(error) => error,
        };
        assert!(error.to_string().contains("unlock failed"), "{error}");

        let env_ok = test_env(tmp.path());
        drop(
            open_at_rest(
                &env_ok,
                tmp.path(),
                &AtRestConfig::passphrase("correct horse battery staple"),
            )
            .unwrap(),
        );

        let env_mismatch = test_env(tmp.path());
        let mismatch = match open_at_rest(&env_mismatch, tmp.path(), &AtRestConfig::keyfile()) {
            Ok(_) => panic!("mode mismatch must refuse"),
            Err(error) => error,
        };
        assert!(mismatch.to_string().contains("mode mismatch"), "{mismatch}");
    }

    #[test]
    fn first_init_recovers_from_an_empty_keyring_dbi() {
        // Crash simulation: the keyring DBI exists (create_db committed) but
        // the meta/DEK transaction never landed.
        let tmp = TempDir::new("empty-dbi");
        {
            let env = test_env(tmp.path());
            env.create_db(Some(KEYRING_DB), DatabaseFlags::default())
                .unwrap();
        }
        let env = test_env(tmp.path());
        let (_, state) = open_at_rest(&env, tmp.path(), &AtRestConfig::keyfile()).unwrap();
        let state = state.unwrap();
        assert_eq!(state.dek_count(), scope_count());
        assert_eq!(state.meta().key_source, "generated_key_file");
        assert!(
            raw_keyring_rows(tmp.path())
                .iter()
                .any(|(key, _)| key == KEYRING_META_KEY)
        );
    }

    #[test]
    fn orphan_keyring_rows_without_meta_refuse_init() {
        let tmp = TempDir::new("orphan");
        {
            let env = test_env(tmp.path());
            let db = env
                .create_db(Some(KEYRING_DB), DatabaseFlags::default())
                .unwrap();
            let mut tx = env.begin_rw_txn().unwrap();
            tx.put(
                db,
                b"dek:records",
                b"orphaned wrapped DEK",
                WriteFlags::default(),
            )
            .unwrap();
            tx.put(
                db,
                &RK_CHECK_KEY,
                b"orphaned rk:check",
                WriteFlags::default(),
            )
            .unwrap();
            tx.commit().unwrap();
        }
        let before = raw_keyring_rows(tmp.path());

        let env = test_env(tmp.path());
        match open_at_rest(&env, tmp.path(), &AtRestConfig::keyfile()) {
            Ok(_) => panic!("orphan rows must refuse keyfile initialization"),
            Err(error) => {
                let message = error.to_string();
                assert!(message.contains("meta"), "{message}");
                assert!(
                    message.contains("orphan") && message.contains("fail-closed"),
                    "{message}"
                );
            }
        }
        assert_eq!(
            raw_keyring_rows(tmp.path()),
            before,
            "refusals must not rewrite the orphaned rows"
        );
        assert!(
            !tmp.path().join(AT_REST_KEY_FILE).exists(),
            "a refused init must not write a key file"
        );
    }

    #[test]
    fn future_keyring_format_version_refuses() {
        let tmp = TempDir::new("future-format");
        let _ = init_keyfile(tmp.path());
        let rows = raw_keyring_rows(tmp.path());
        let meta_bytes = rows
            .iter()
            .find(|(key, _)| key.as_slice() == KEYRING_META_KEY)
            .map(|(_, value)| value.clone())
            .expect("keyring meta row");
        let mut meta: serde_json::Value = serde_json::from_slice(&meta_bytes).unwrap();
        meta["format_version"] = serde_json::json!(99);
        {
            let env = test_env(tmp.path());
            let db = env.open_db(Some(KEYRING_DB)).unwrap();
            let mut tx = env.begin_rw_txn().unwrap();
            tx.put(
                db,
                &KEYRING_META_KEY,
                &serde_json::to_vec(&meta).unwrap(),
                WriteFlags::default(),
            )
            .unwrap();
            tx.commit().unwrap();
        }
        let env = test_env(tmp.path());
        match open_at_rest(&env, tmp.path(), &AtRestConfig::keyfile()) {
            Ok(_) => panic!("a future keyring format must refuse writable opens"),
            Err(error) => assert!(
                error
                    .to_string()
                    .contains("unsupported keyring format_version"),
                "{error}"
            ),
        }
        let db = open_keyring_optional(&env).unwrap().expect("keyring");
        match read_status(&env, db, tmp.path()) {
            AtRestStatus::Malformed { reason } => assert!(reason.contains("format_version")),
            other => panic!("expected Malformed for a future format, got {other:?}"),
        }
    }

    #[test]
    fn hostile_argon2_params_from_meta_are_rejected_before_derivation() {
        let salt_hex = "00".repeat(ARGON2_SALT_LEN);
        let huge = Argon2Params {
            m_cost_kib: 4_000_000,
            t_cost: ARGON2_T_COST,
            p_cost: ARGON2_P_COST,
            version: ARGON2_VERSION,
            salt_hex,
        };
        let error = derive_rk_from_passphrase("passphrase", &huge).unwrap_err();
        assert!(error.to_string().contains("exceed sane bounds"), "{error}");

        let wrong_version = Argon2Params {
            version: 0x10,
            ..huge
        };
        let error = derive_rk_from_passphrase("passphrase", &wrong_version).unwrap_err();
        assert!(error.to_string().contains("version"), "{error}");
    }

    #[test]
    fn envelope_roundtrip_and_tamper_detection() {
        let key = [7u8; 32];
        let id = record_identity(42);
        let plaintext = b"plaintext record body".as_slice();
        let sealed = seal_record(plaintext, &key, RECORD_SCOPE, &id, 3).unwrap();

        assert!(!is_sealed_record(plaintext));
        assert!(is_sealed_record(&sealed));
        assert_eq!(&sealed[..4], b"WMEN");
        assert_eq!(sealed[4], RECORD_FORMAT_VERSION);
        assert_eq!(sealed_record_version(&sealed), Some(3));

        let opened = open_record(&sealed, &key, RECORD_SCOPE, &id).unwrap();
        assert_eq!(&opened[..], plaintext);

        assert!(open_record(&sealed, &[8u8; 32], RECORD_SCOPE, &id).is_err());
        assert!(open_record(&sealed, &key, "sessions", &id).is_err());
        assert!(open_record(&sealed, &key, RECORD_SCOPE, &record_identity(43)).is_err());
        assert!(open_record(&sealed, &key, RECORD_SCOPE, &id).is_ok());

        let mut flipped = sealed.clone();
        let last = flipped.len() - 1;
        flipped[last] ^= 0x01;
        assert!(open_record(&flipped, &key, RECORD_SCOPE, &id).is_err());

        let truncated = &sealed[..sealed.len() - 1];
        assert!(open_record(truncated, &key, RECORD_SCOPE, &id).is_err());

        let mut bad_version = sealed.clone();
        bad_version[4] = 9;
        assert!(open_record(&bad_version, &key, RECORD_SCOPE, &id).is_err());

        let mut header_version_flip = sealed.clone();
        header_version_flip[5] ^= 0x01;
        assert!(open_record(&header_version_flip, &key, RECORD_SCOPE, &id).is_err());
    }

    #[test]
    fn wrap_bitflip_sweep_and_aad_binding() {
        let key_a = [0x11u8; AT_REST_KEY_LEN];
        let key_b = [0x22u8; AT_REST_KEY_LEN];
        let info_a = crate::kdf::galaxy_dek_info("codex");
        let info_b = crate::kdf::galaxy_dek_info("sessions");
        let dek = [0x33u8; AT_REST_KEY_LEN];

        let kek_a = crate::kdf::hkdf32(&key_a, &info_a);
        let kek_b = crate::kdf::hkdf32(&key_b, &info_b);
        let wrapped = wrap(&kek_a, &info_a, &dek).unwrap();

        assert!(unwrap_secret(&kek_a, &info_a, &wrapped).is_ok());
        assert!(
            unwrap_secret(&kek_a, &info_b, &wrapped).is_err(),
            "info-string AAD swap must fail"
        );
        assert!(
            unwrap_secret(&kek_b, &info_a, &wrapped).is_err(),
            "foreign KEK must fail"
        );
        assert_ne!(kek_a, kek_b, "per-scope KEKs must not collide");

        for byte in 0..wrapped.len() {
            for bit in 0..8u8 {
                let mut tampered = wrapped.clone();
                tampered[byte] ^= 1 << bit;
                assert!(
                    unwrap_secret(&kek_a, &info_a, &tampered).is_err(),
                    "bit {bit} of byte {byte} must fail authentication"
                );
            }
        }
        assert!(unwrap_secret(&kek_a, &info_a, &wrapped[..WRAP_MIN_LEN - 1]).is_err());
    }

    #[test]
    fn record_aad_is_injective_across_name_boundaries() {
        let id = record_identity(7);
        assert_ne!(record_aad("a", &id, 1), record_aad("ab", &id, 1));
        assert_ne!(record_aad("codex", &id, 1), record_aad("codex", &id, 2));
        assert_eq!(record_aad("codex", &id, 1), record_aad("codex", &id, 1));
    }

    #[test]
    fn migration_ledger_roundtrips_and_rejects_corruption() {
        let tmp = TempDir::new("ledger");
        let (env, db, _state) = init_keyfile(tmp.path());
        let mut ledger = read_migration_ledger(&env, db).unwrap();
        assert_eq!(ledger.version, 1);
        assert!(ledger.galaxies.is_empty());

        ledger.galaxies.insert(
            RECORD_SCOPE.to_string(),
            MigrationGalaxyState {
                encrypted: 3,
                cursor_hex: "00ff".into(),
                done: false,
            },
        );
        ledger.updated_at = "2026-10-06T00:00:00Z".into();
        write_migration_ledger(&env, db, &ledger).unwrap();
        assert_eq!(read_migration_ledger(&env, db).unwrap(), ledger);

        let mut tx = env.begin_rw_txn().unwrap();
        tx.put(
            db,
            &MIGRATION_LEDGER_KEY,
            b"not json",
            WriteFlags::default(),
        )
        .unwrap();
        tx.commit().unwrap();
        assert!(read_migration_ledger(&env, db).is_err());
    }

    #[test]
    fn unrecognized_env_mode_value_is_a_hard_error() {
        assert_eq!(mode_from_env_value(None).unwrap(), AtRestMode::Off);
        assert_eq!(
            mode_from_env_value(Some(" KeyFile ")).unwrap(),
            AtRestMode::Keyfile
        );
        for invalid in ["", "keyfil", "on", "off2", "plaintext"] {
            let error = mode_from_env_value(Some(invalid))
                .expect_err("unrecognized WM_AT_REST_MODE must be refused");
            assert!(
                error.to_string().contains("WM_AT_REST_MODE"),
                "{invalid}: {error}"
            );
            assert!(
                error.to_string().contains("fail-closed"),
                "{invalid}: {error}"
            );
        }
    }
}
