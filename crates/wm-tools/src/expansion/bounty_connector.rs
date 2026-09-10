//! Bounty auto-connector — `bounty.scan`, `bounty.import`.
//!
//! Scans external bounty platforms, matches bounties against agent
//! capabilities, and imports the best matches into a local board.
//! Ports the v26 Python `bounty_connector.py` + `bounty_platforms.py`
//! semantics (platform adapters, capability-overlap matching, import
//! into a local board) to the Rust tool surface. The board entries feed
//! the EconomicFirewall surfaces (`bounty.create` / `link_escrow` /
//! `complete` — see `wm-governance::economic_firewall::ECONOMIC_TOOLS`);
//! this module does not modify them.
//!
//! v1 is offline-safe: adapters are the in-memory [`MockBountyPlatform`]
//! (tests + demo) and [`StaticJsonPlatform`] (JSON file fixture). A real
//! HTTP adapter is a follow-up.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashSet;
use std::path::PathBuf;
use std::sync::{Arc, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};

/// Platform adapter error type (v1 adapters are local, so `String`).
type PlatformResult<T> = Result<T, String>;

// ── Data model ───────────────────────────────────────────────────────

/// Lifecycle state of a bounty on the local board.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BountyState {
    /// Listed on the external platform.
    #[default]
    Open,
    /// Claimed on the external platform.
    Claimed,
    /// Deadline passed.
    Expired,
    /// Imported into the local board.
    Imported,
}

/// A bounty listed on an external platform.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bounty {
    /// Platform-local identifier (unique per platform).
    pub id: String,
    /// Platform name (e.g. "mock", "immunefi").
    pub platform: String,
    /// Short title.
    pub title: String,
    /// Full description.
    #[serde(default)]
    pub description: String,
    /// Reward amount (in `reward_currency` units).
    #[serde(default)]
    pub reward_amount: f64,
    /// Reward currency (default "USDC", mirroring the Python adapters).
    #[serde(default = "default_currency")]
    pub reward_currency: String,
    /// Capabilities required to complete the work.
    #[serde(default)]
    pub required_capabilities: Vec<String>,
    /// External URL for the listing.
    #[serde(default)]
    pub url: String,
    /// Current state.
    #[serde(default)]
    pub state: BountyState,
    /// Posting timestamp (epoch seconds).
    #[serde(default)]
    pub posted_at: i64,
    /// Optional expiry timestamp (epoch seconds).
    #[serde(default)]
    pub expires_at: Option<i64>,
}

fn default_currency() -> String {
    "USDC".to_string()
}

impl Bounty {
    /// Convenience constructor for fixtures and adapters.
    #[must_use]
    pub fn new(
        platform: &str,
        id: &str,
        title: &str,
        reward_amount: f64,
        required_capabilities: Vec<String>,
    ) -> Self {
        Self {
            id: id.to_string(),
            platform: platform.to_string(),
            title: title.to_string(),
            description: String::new(),
            reward_amount,
            reward_currency: default_currency(),
            required_capabilities,
            url: String::new(),
            state: BountyState::Open,
            posted_at: 0,
            expires_at: None,
        }
    }

    /// Dedupe key: platform + external id.
    #[must_use]
    pub fn key(&self) -> (String, String) {
        (self.platform.clone(), self.id.clone())
    }
}

/// A bounty imported into the local board.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportedBounty {
    /// Local board id (uuid v4).
    pub local_id: String,
    /// The imported bounty (state set to `Imported`).
    pub bounty: Bounty,
    /// Capability match score at scan time, if it was scanned.
    #[serde(default)]
    pub match_score: Option<f64>,
    /// Import timestamp (epoch seconds).
    pub imported_at: i64,
}

// ── Platform adapters ────────────────────────────────────────────────

/// Protocol for external bounty platform adapters (port of the Python
/// `BountyPlatform` protocol; v1 is read-only — `fetch_open` only).
pub trait BountyPlatform: Send + Sync {
    /// Platform name.
    fn name(&self) -> &str;
    /// Fetch currently open bounties.
    fn fetch_open(&self) -> PlatformResult<Vec<Bounty>>;
}

/// In-memory fixture platform for tests and offline demos.
#[derive(Debug, Default)]
pub struct MockBountyPlatform {
    bounties: Vec<Bounty>,
}

impl MockBountyPlatform {
    #[must_use]
    pub const fn new(bounties: Vec<Bounty>) -> Self {
        Self { bounties }
    }
}

impl BountyPlatform for MockBountyPlatform {
    fn name(&self) -> &str {
        "mock"
    }

    fn fetch_open(&self) -> PlatformResult<Vec<Bounty>> {
        Ok(self
            .bounties
            .iter()
            .filter(|b| b.state == BountyState::Open)
            .cloned()
            .collect())
    }
}

/// Offline-safe platform that loads bounties from a JSON file
/// (either a bare array or `{"bounties": [...]}`).
#[derive(Debug, Clone)]
pub struct StaticJsonPlatform {
    name: String,
    path: PathBuf,
}

impl StaticJsonPlatform {
    /// Create a platform backed by a JSON fixture file. The file is read
    /// on every `fetch_open` (cheap local reads; no caching needed at v1).
    #[must_use]
    pub fn new(name: &str, path: PathBuf) -> Self {
        Self {
            name: name.to_string(),
            path,
        }
    }

    fn parse(contents: &str) -> PlatformResult<Vec<Bounty>> {
        let value: Value =
            serde_json::from_str(contents).map_err(|e| format!("invalid bounty JSON: {e}"))?;
        let items = match &value {
            Value::Array(items) => items.clone(),
            Value::Object(map) => map
                .get("bounties")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default(),
            _ => Vec::new(),
        };
        items
            .iter()
            .map(|item| {
                serde_json::from_value::<Bounty>(item.clone())
                    .map_err(|e| format!("invalid bounty entry: {e}"))
            })
            .collect()
    }
}

impl BountyPlatform for StaticJsonPlatform {
    fn name(&self) -> &str {
        &self.name
    }

    fn fetch_open(&self) -> PlatformResult<Vec<Bounty>> {
        let contents = std::fs::read_to_string(&self.path)
            .map_err(|e| format!("cannot read bounty fixture {}: {e}", self.path.display()))?;
        let mut bounties = Self::parse(&contents)?;
        for bounty in &mut bounties {
            if bounty.platform.is_empty() {
                bounty.platform.clone_from(&self.name);
            }
        }
        Ok(bounties
            .into_iter()
            .filter(|b| b.state == BountyState::Open)
            .collect())
    }
}

// TODO(v2): HTTP platform adapter (e.g. reaching.ai / Immunefi public API),
// mirroring the Python ReachingAIPlatform — needs a network-capable client,
// an API-key env knob, and TTL caching like the Python `_PlatformCache`.

// ── Capability matching ──────────────────────────────────────────────

/// Capability matcher — token-overlap scoring with an exact-phrase bonus.
#[derive(Debug, Clone, Default)]
pub struct CapabilityMatcher;

impl CapabilityMatcher {
    /// Score how well `capabilities` cover `bounty.required_capabilities`.
    ///
    /// Normalized lowercase comparison. Score = exact-phrase coverage
    /// (fraction of required capabilities matched verbatim) + 0.2 × token
    /// Jaccard overlap, clamped to [0, 1]. Bounties with no required
    /// capabilities default to 0.5 (Python `_match_agent` semantics).
    #[must_use]
    pub fn match_score(&self, bounty: &Bounty, capabilities: &[String]) -> f64 {
        let agent: HashSet<String> = capabilities
            .iter()
            .map(|c| c.trim().to_lowercase())
            .filter(|c| !c.is_empty())
            .collect();
        if bounty.required_capabilities.is_empty() {
            return 0.5;
        }
        let required: Vec<String> = bounty
            .required_capabilities
            .iter()
            .map(|c| c.trim().to_lowercase())
            .filter(|c| !c.is_empty())
            .collect();
        if required.is_empty() {
            return 0.5;
        }
        let exact = required.iter().filter(|r| agent.contains(*r)).count();
        let exact_ratio = exact as f64 / required.len() as f64;
        let jaccard = token_jaccard(&required, &agent);
        0.2f64.mul_add(jaccard, exact_ratio).clamp(0.0, 1.0)
    }

    /// Filter + rank bounties by match score (descending). Bounties below
    /// `min_score` are dropped.
    #[must_use]
    pub fn match_bounties(
        &self,
        bounties: &[Bounty],
        capabilities: &[String],
        min_score: f64,
    ) -> Vec<(Bounty, f64)> {
        let mut scored: Vec<(Bounty, f64)> = bounties
            .iter()
            .map(|b| (b.clone(), self.match_score(b, capabilities)))
            .filter(|(_, score)| *score >= min_score)
            .collect();
        scored.sort_by(|a, b| {
            b.1.partial_cmp(&a.1)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| {
                    b.0.reward_amount
                        .partial_cmp(&a.0.reward_amount)
                        .unwrap_or(std::cmp::Ordering::Equal)
                })
        });
        scored
    }
}

fn tokens_of(capability: &str) -> HashSet<String> {
    capability
        .split(|c: char| !c.is_alphanumeric())
        .filter(|t| !t.is_empty())
        .map(str::to_string)
        .collect()
}

fn token_jaccard(required: &[String], agent: &HashSet<String>) -> f64 {
    let req_tokens: HashSet<String> = required.iter().flat_map(|c| tokens_of(c)).collect();
    let agent_tokens: HashSet<String> = agent.iter().flat_map(|c| tokens_of(c)).collect();
    if req_tokens.is_empty() && agent_tokens.is_empty() {
        return 0.0;
    }
    let inter = req_tokens.intersection(&agent_tokens).count();
    let union = req_tokens.union(&agent_tokens).count();
    if union == 0 {
        return 0.0;
    }
    inter as f64 / union as f64
}

// ── Local board (JSON-file persistence) ──────────────────────────────

/// Local bounty board — imported bounties persisted to a JSON file.
#[derive(Debug)]
pub struct BountyBoard {
    path: PathBuf,
    entries: RwLock<Vec<ImportedBounty>>,
}

impl BountyBoard {
    /// Open (or create) a board backed by `path`. Existing entries are
    /// loaded; a missing file starts an empty board.
    pub fn open(path: PathBuf) -> Result<Self, String> {
        let entries = if path.exists() {
            let contents = std::fs::read_to_string(&path)
                .map_err(|e| format!("cannot read bounty board {}: {e}", path.display()))?;
            Self::parse_entries(&contents)?
        } else {
            Vec::new()
        };
        Ok(Self {
            path,
            entries: RwLock::new(entries),
        })
    }

    /// Deserialize board contents (`{"imported": [...]}` or a bare array).
    pub fn parse_entries(contents: &str) -> Result<Vec<ImportedBounty>, String> {
        let value: Value =
            serde_json::from_str(contents).map_err(|e| format!("invalid board JSON: {e}"))?;
        let items = match &value {
            Value::Array(items) => items.clone(),
            Value::Object(map) => map
                .get("imported")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default(),
            _ => Vec::new(),
        };
        items
            .iter()
            .map(|item| {
                serde_json::from_value::<ImportedBounty>(item.clone())
                    .map_err(|e| format!("invalid board entry: {e}"))
            })
            .collect()
    }

    /// Serialize board entries for persistence.
    #[must_use]
    pub fn to_json(&self) -> Value {
        let entries = self.entries.read().map(|e| e.clone()).unwrap_or_default();
        json!({ "imported": entries })
    }

    /// Replace in-memory entries from persisted JSON (restore path).
    pub fn from_json(&self, value: &Value) -> Result<(), String> {
        let items = value
            .get("imported")
            .and_then(Value::as_array)
            .cloned()
            .unwrap_or_default();
        let mut parsed = Vec::with_capacity(items.len());
        for item in &items {
            parsed.push(
                serde_json::from_value::<ImportedBounty>(item.clone())
                    .map_err(|e| format!("invalid board entry: {e}"))?,
            );
        }
        if let Ok(mut entries) = self.entries.write() {
            *entries = parsed;
        }
        self.save()
    }

    fn save(&self) -> Result<(), String> {
        let value = {
            let entries = self.entries.read().map_err(|e| e.to_string())?;
            json!({ "imported": *entries })
        };
        let contents = serde_json::to_string_pretty(&value).map_err(|e| e.to_string())?;
        std::fs::write(&self.path, contents)
            .map_err(|e| format!("cannot write bounty board {}: {e}", self.path.display()))
    }

    /// Import a bounty (dedupe by platform + id). The stored copy gets
    /// state `Imported` and a fresh local id.
    pub fn import(&self, bounty: &Bounty) -> Result<ImportedBounty, String> {
        let key = bounty.key();
        {
            let entries = self.entries.read().map_err(|e| e.to_string())?;
            if let Some(existing) = entries.iter().find(|e| e.bounty.key() == key) {
                return Err(format!(
                    "bounty {}/{} already imported (local id {})",
                    key.0, key.1, existing.local_id
                ));
            }
        }
        let imported = ImportedBounty {
            local_id: uuid::Uuid::new_v4().to_string(),
            bounty: Bounty {
                state: BountyState::Imported,
                ..bounty.clone()
            },
            match_score: None,
            imported_at: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .ok()
                .and_then(|d| i64::try_from(d.as_secs()).ok())
                .unwrap_or(0),
        };
        {
            let mut entries = self.entries.write().map_err(|e| e.to_string())?;
            entries.push(imported.clone());
        }
        self.save()?;
        Ok(imported)
    }

    /// All imported bounties.
    #[must_use]
    pub fn list(&self) -> Vec<ImportedBounty> {
        self.entries.read().map(|e| e.clone()).unwrap_or_default()
    }

    /// Board file path.
    #[must_use]
    pub fn path(&self) -> &std::path::Path {
        &self.path
    }
}

// ── Connector ────────────────────────────────────────────────────────

/// Scans registered platforms, matches bounties to capabilities, and
/// imports matches into the local board.
pub struct BountyConnector {
    platforms: Vec<Arc<dyn BountyPlatform>>,
    matcher: CapabilityMatcher,
    board: Arc<BountyBoard>,
}

impl BountyConnector {
    /// Create a connector over a shared board.
    #[must_use]
    pub fn new(board: Arc<BountyBoard>) -> Self {
        Self {
            platforms: Vec::new(),
            matcher: CapabilityMatcher,
            board,
        }
    }

    /// Register a platform adapter (builder style).
    #[must_use]
    pub fn with_platform(mut self, platform: Arc<dyn BountyPlatform>) -> Self {
        self.platforms.push(platform);
        self
    }

    /// The shared board.
    #[must_use]
    pub const fn board(&self) -> &Arc<BountyBoard> {
        &self.board
    }

    /// Fetch a single open bounty by platform + external id (the
    /// `bounty.import` tool path). Failing platforms are skipped, like
    /// the Python `scan_and_match` warning-and-continue behavior.
    pub fn fetch_bounty(&self, platform: &str, id: &str) -> PlatformResult<Bounty> {
        for adapter in &self.platforms {
            if adapter.name() != platform {
                continue;
            }
            if let Ok(bounties) = adapter.fetch_open() {
                if let Some(bounty) = bounties.into_iter().find(|b| b.id == id) {
                    return Ok(bounty);
                }
            }
        }
        Err(format!(
            "bounty {id} not found on platform '{platform}' (or platform scan failed)"
        ))
    }

    /// Scan all platforms, match against `capabilities`, return matches
    /// (bounty, score, platform) sorted by score descending. Platforms
    /// whose scan fails are skipped.
    #[must_use]
    pub fn scan(&self, capabilities: &[String], min_score: f64) -> Vec<(Bounty, f64, String)> {
        let mut all: Vec<Bounty> = Vec::new();
        for platform in &self.platforms {
            if let Ok(bounties) = platform.fetch_open() {
                all.extend(bounties);
            }
        }
        self.matcher
            .match_bounties(&all, capabilities, min_score)
            .into_iter()
            .map(|(bounty, score)| {
                let platform = bounty.platform.clone();
                (bounty, score, platform)
            })
            .collect()
    }

    /// Import a bounty into the local board (dedupe by platform + id).
    pub fn import(&self, bounty: &Bounty) -> PlatformResult<ImportedBounty> {
        self.board.import(bounty)
    }
}

// ── Tools ────────────────────────────────────────────────────────────

/// `bounty.scan` — scan platforms and match against capabilities.
pub struct BountyScanTool {
    connector: Arc<BountyConnector>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BountyScanTool {
    #[must_use]
    pub fn new(connector: Arc<BountyConnector>) -> Self {
        Self {
            connector,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for BountyScanTool {
    fn name(&self) -> &str {
        "bounty.scan"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Scan external bounty platforms and match open bounties against agent capabilities. Args: capabilities (list of strings), min_score (float, default 0.0)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let capabilities: Vec<String> = args
            .get("capabilities")
            .and_then(Value::as_array)
            .map(|items| {
                items
                    .iter()
                    .filter_map(Value::as_str)
                    .map(str::to_string)
                    .collect()
            })
            .unwrap_or_default();
        let min_score = args.get("min_score").and_then(Value::as_f64).unwrap_or(0.0);
        let matches = self.connector.scan(&capabilities, min_score);
        let matches_json: Vec<Value> = matches
            .iter()
            .map(|(bounty, score, platform)| {
                json!({
                    "bounty": bounty,
                    "score": score,
                    "platform": platform,
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "min_score": min_score,
            "matched": matches_json.len(),
            "matches": matches_json,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `bounty.import` — import a matched bounty into the local board.
pub struct BountyImportTool {
    connector: Arc<BountyConnector>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BountyImportTool {
    #[must_use]
    pub fn new(connector: Arc<BountyConnector>) -> Self {
        Self {
            connector,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Filesystem],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for BountyImportTool {
    fn name(&self) -> &str {
        "bounty.import"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Import an open bounty into the local board (deduped by platform + id). Args: platform (string), id (string). Non-destructive."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let platform = args
            .get("platform")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("missing 'platform' argument".into()))?;
        let id = args
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("missing 'id' argument".into()))?;
        let bounty = self
            .connector
            .fetch_bounty(platform, id)
            .map_err(CoreError::InvalidArgs)?;
        let imported = self
            .connector
            .import(&bounty)
            .map_err(CoreError::InvalidArgs)?;
        Ok(json!({
            "status": "success",
            "local_id": imported.local_id,
            "imported_at": imported.imported_at,
            "bounty": imported.bounty,
            "board_path": self.connector.board().path().display().to_string(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the bounty tools (2).
#[must_use]
pub fn register_bounty(
    registry: &wm_dispatch::ToolRegistry,
    connector: Arc<BountyConnector>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(std::sync::Arc::new(BountyScanTool::new(connector.clone())))
        .register(std::sync::Arc::new(BountyImportTool::new(connector)))
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn bounty(id: &str, title: &str, caps: &[&str]) -> Bounty {
        Bounty::new(
            "mock",
            id,
            title,
            100.0,
            caps.iter().map(|c| (*c).to_string()).collect(),
        )
    }

    fn temp_board() -> (BountyBoard, tempfile::TempDir) {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("bounty_board.json");
        let board = BountyBoard::open(path).unwrap();
        (board, dir)
    }

    fn caps(list: &[&str]) -> Vec<String> {
        list.iter().map(|c| (*c).to_string()).collect()
    }

    #[test]
    fn mock_platform_fetch_open() {
        let platform = MockBountyPlatform::new(vec![
            bounty("b1", "Audit X", &["rust"]),
            bounty("b2", "Fix Y", &["python"]),
        ]);
        assert_eq!(platform.name(), "mock");
        let open = platform.fetch_open().unwrap();
        assert_eq!(open.len(), 2);
        assert_eq!(open[0].id, "b1");
    }

    #[test]
    fn mock_platform_skips_non_open() {
        let mut claimed = bounty("b2", "Claimed", &["rust"]);
        claimed.state = BountyState::Claimed;
        let platform = MockBountyPlatform::new(vec![bounty("b1", "Open", &["rust"]), claimed]);
        let open = platform.fetch_open().unwrap();
        assert_eq!(open.len(), 1);
        assert_eq!(open[0].id, "b1");
    }

    #[test]
    fn match_scoring_exact_beats_partial_beats_none() {
        let matcher = CapabilityMatcher;
        let bounty = bounty("b1", "Rust audit", &["rust", "sql"]);
        let exact = matcher.match_score(&bounty, &caps(&["rust", "sql", "go"]));
        let partial = matcher.match_score(&bounty, &caps(&["rust", "go"]));
        let none = matcher.match_score(&bounty, &caps(&["python", "haskell"]));
        assert!(exact > partial);
        assert!(partial > none);
        assert!((exact - 1.0).abs() < 1e-9);
    }

    #[test]
    fn match_scoring_case_insensitive() {
        let matcher = CapabilityMatcher;
        let bounty = bounty("b1", "Rust audit", &["Rust", "SQL"]);
        let lower = matcher.match_score(&bounty, &caps(&["rust", "sql"]));
        let upper = matcher.match_score(&bounty, &caps(&["RUST", "SQL"]));
        assert!((lower - upper).abs() < 1e-9);
        assert!((lower - 1.0).abs() < 1e-9);
    }

    #[test]
    fn no_required_caps_defaults_to_half() {
        let matcher = CapabilityMatcher;
        let bounty = bounty("b1", "Anything", &[]);
        assert!((matcher.match_score(&bounty, &caps(&["rust"])) - 0.5).abs() < 1e-9);
        assert!((matcher.match_score(&bounty, &[]) - 0.5).abs() < 1e-9);
    }

    #[test]
    fn match_bounties_sorted_desc_and_filtered() {
        let matcher = CapabilityMatcher;
        let bounties = vec![
            bounty("weak", "Weak match", &["haskell"]),
            bounty("strong", "Strong match", &["rust"]),
            bounty("none", "No match", &["cobol"]),
        ];
        let matched = matcher.match_bounties(&bounties, &caps(&["rust"]), 0.0);
        assert_eq!(matched[0].0.id, "strong");
        assert!(matched[0].1 > matched[1].1);
        let filtered = matcher.match_bounties(&bounties, &caps(&["rust"]), 0.9);
        assert_eq!(filtered.len(), 1);
        assert_eq!(filtered[0].0.id, "strong");
    }

    #[test]
    fn static_json_platform_loads_fixture() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("fixture.json");
        std::fs::write(
            &path,
            json!({"bounties": [{
                "id": "fx1",
                "platform": "static",
                "title": "Fixture bounty",
                "reward_amount": 50.0,
                "required_capabilities": ["rust"]
            }]})
            .to_string(),
        )
        .unwrap();
        let platform = StaticJsonPlatform::new("static", path);
        let open = platform.fetch_open().unwrap();
        assert_eq!(open.len(), 1);
        assert_eq!(open[0].id, "fx1");
        assert_eq!(open[0].platform, "static");
        assert_eq!(open[0].reward_currency, "USDC");
    }

    #[test]
    fn static_json_platform_missing_file_errors() {
        let platform = StaticJsonPlatform::new("static", PathBuf::from("/nonexistent/x.json"));
        assert!(platform.fetch_open().is_err());
    }

    #[test]
    fn import_and_dedupe() {
        let (board, _dir) = temp_board();
        let connector = BountyConnector::new(Arc::new(board)).with_platform(Arc::new(
            MockBountyPlatform::new(vec![bounty("b1", "Audit X", &["rust"])]),
        ));
        let fetched = connector.fetch_bounty("mock", "b1").unwrap();
        let imported = connector.import(&fetched).unwrap();
        assert_eq!(imported.bounty.state, BountyState::Imported);
        assert!(!imported.local_id.is_empty());

        let again = connector.import(&fetched);
        assert!(again.is_err());
        assert!(again.unwrap_err().contains("already imported"));

        // fetch from a platform that does not exist
        assert!(connector.fetch_bounty("nope", "b1").is_err());
    }

    #[test]
    fn board_persistence_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("board.json");
        let board = BountyBoard::open(path.clone()).unwrap();
        board.import(&bounty("b1", "Audit X", &["rust"])).unwrap();
        board.import(&bounty("b2", "Fix Y", &["python"])).unwrap();
        assert_eq!(board.list().len(), 2);

        let reopened = BountyBoard::open(path).unwrap();
        let list = reopened.list();
        assert_eq!(list.len(), 2);
        assert_eq!(list[0].bounty.id, "b1");
        assert_eq!(list[0].bounty.state, BountyState::Imported);
    }

    #[test]
    fn connector_scan_returns_matches_with_platform() {
        let (board, _dir) = temp_board();
        let connector = BountyConnector::new(Arc::new(board))
            .with_platform(Arc::new(MockBountyPlatform::new(vec![
                bounty("b1", "Rust audit", &["rust"]),
                bounty("b2", "Python fix", &["python"]),
            ])))
            .with_platform(Arc::new(StaticJsonPlatform::new(
                "static",
                PathBuf::from("/nonexistent/x.json"),
            )));
        let matches = connector.scan(&caps(&["rust"]), 0.0);
        assert_eq!(matches.len(), 2);
        assert_eq!(matches[0].0.id, "b1");
        assert_eq!(matches[0].2, "mock");
        // failing platform (missing fixture file) is skipped, not fatal
        let strict = connector.scan(&caps(&["rust"]), 0.9);
        assert_eq!(strict.len(), 1);
    }

    #[tokio::test]
    async fn scan_tool_returns_ok_payload() {
        let (board, _dir) = temp_board();
        let connector = Arc::new(
            BountyConnector::new(Arc::new(board)).with_platform(Arc::new(MockBountyPlatform::new(
                vec![bounty("b1", "Rust audit", &["rust"])],
            ))),
        );
        let tool = BountyScanTool::new(connector);
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({"capabilities": ["rust"], "min_score": 0.5}),
            )
            .await;
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["matched"], 1);
        assert_eq!(v["matches"][0]["bounty"]["id"], "b1");
        assert_eq!(v["matches"][0]["platform"], "mock");
    }

    #[tokio::test]
    async fn import_tool_imports_then_dedupes() {
        let (board, _dir) = temp_board();
        let connector = Arc::new(
            BountyConnector::new(Arc::new(board)).with_platform(Arc::new(MockBountyPlatform::new(
                vec![bounty("b1", "Rust audit", &["rust"])],
            ))),
        );
        let tool = BountyImportTool::new(connector.clone());
        let mut ctx = Context::default();

        let result = tool
            .call(&mut ctx, json!({"platform": "mock", "id": "b1"}))
            .await;
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["bounty"]["state"], "imported");
        let local_id = v["local_id"].as_str().unwrap().to_string();
        assert!(!local_id.is_empty());

        // second import of the same platform+id is an error
        let result = tool
            .call(&mut ctx, json!({"platform": "mock", "id": "b1"}))
            .await;
        assert!(result.is_err());

        // board has exactly one entry
        assert_eq!(connector.board().list().len(), 1);
    }

    #[tokio::test]
    async fn import_tool_requires_args() {
        let (board, _dir) = temp_board();
        let tool = BountyImportTool::new(Arc::new(BountyConnector::new(Arc::new(board))));
        let mut ctx = Context::default();
        assert!(tool.call(&mut ctx, json!({})).await.is_err());
        assert!(
            tool.call(&mut ctx, json!({"platform": "mock"}))
                .await
                .is_err()
        );
    }
}
