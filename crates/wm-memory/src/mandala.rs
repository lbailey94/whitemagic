//! Mandala Compartments — isolated LMDB environments per security tier.
//!
//! Each compartment (Research, Sandbox, Production, Secure) has its own
//! LMDB environment, Tantivy index, and association store, providing
//! complete storage isolation between tiers.
//!
//! Governance configuration (rate limits, Dharma gate strictness, resource
//! rules) is handled at a higher level (e.g., wm-mcp) to avoid circular
//! dependencies. This module focuses purely on storage isolation.
//!
//! - **Research**: Small map size (256MB), for experimentation
//! - **Sandbox**: Small map size (256MB), for testing
//! - **Production**: 1GB map, for live data
//! - **Secure**: 4GB map, read-only by default, for hardened data

use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::{AssociationStore, MemoryStore, SearchEngine};
use serde::{Deserialize, Serialize};
use wm_core::Result;

/// Security tier for a Mandala compartment.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MandalaLevel {
    /// Experimental — 256MB map, for experimentation.
    Research,
    /// Testing — 256MB map, isolated from production.
    Sandbox,
    /// Live — 1GB map, for production workloads.
    Production,
    /// Hardened — 4GB map, read-only by default.
    Secure,
}

impl MandalaLevel {
    /// All levels in order of increasing strictness.
    #[must_use]
    pub const fn all() -> &'static [Self] {
        &[
            Self::Research,
            Self::Sandbox,
            Self::Production,
            Self::Secure,
        ]
    }

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Research => "research",
            Self::Sandbox => "sandbox",
            Self::Production => "production",
            Self::Secure => "secure",
        }
    }

    /// Directory name for this compartment.
    #[must_use]
    pub const fn dir_name(self) -> &'static str {
        self.as_str()
    }

    /// LMDB map size in bytes for this compartment.
    #[must_use]
    pub const fn map_size(self) -> usize {
        match self {
            Self::Research | Self::Sandbox => 256 * 1024 * 1024, // 256 MB
            Self::Production => 1024 * 1024 * 1024,              // 1 GB
            Self::Secure => 4 * 1024 * 1024 * 1024,              // 4 GB
        }
    }

    /// Whether this compartment is read-only by default.
    #[must_use]
    pub const fn read_only_default(self) -> bool {
        matches!(self, Self::Secure)
    }

    /// Parse from string (case-insensitive).
    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_ascii_lowercase().as_str() {
            "research" => Some(Self::Research),
            "sandbox" => Some(Self::Sandbox),
            "production" => Some(Self::Production),
            "secure" => Some(Self::Secure),
            _ => None,
        }
    }
}

impl std::fmt::Display for MandalaLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Configuration for a single Mandala compartment.
#[derive(Debug, Clone)]
pub struct CompartmentConfig {
    /// Security level.
    pub level: MandalaLevel,
    /// Base path for this compartment's LMDB/Tantivy files.
    pub path: PathBuf,
    /// Override map size (None = use level default).
    pub map_size: Option<usize>,
    /// Whether this compartment is read-only.
    pub read_only: bool,
}

impl CompartmentConfig {
    /// Create a config for the given level at the base path.
    #[must_use]
    pub fn new(level: MandalaLevel, base_path: &Path) -> Self {
        let path = base_path.join(level.dir_name());
        Self {
            level,
            path,
            map_size: None,
            read_only: level.read_only_default(),
        }
    }

    /// Effective map size.
    #[must_use]
    pub fn effective_map_size(&self) -> usize {
        self.map_size.unwrap_or_else(|| self.level.map_size())
    }

    /// Override map size.
    #[must_use]
    pub const fn with_map_size(mut self, size: usize) -> Self {
        self.map_size = Some(size);
        self
    }

    /// Set read-only flag.
    #[must_use]
    pub const fn read_only(mut self, ro: bool) -> Self {
        self.read_only = ro;
        self
    }
}

/// An opened Mandala compartment with isolated stores.
///
/// Each compartment has completely separate LMDB, Tantivy, and association
/// storage. Data written to one compartment is invisible to others.
pub struct Compartment {
    /// Configuration for this compartment.
    pub config: CompartmentConfig,
    /// Isolated LMDB memory store.
    pub store: Arc<MemoryStore>,
    /// Isolated Tantivy search engine.
    pub search: Arc<SearchEngine>,
    /// Isolated association store.
    pub associations: Arc<AssociationStore>,
}

impl Compartment {
    /// Open a compartment from its config.
    pub fn open(config: CompartmentConfig) -> Result<Self> {
        std::fs::create_dir_all(&config.path)
            .map_err(|e| wm_core::CoreError::Memory(format!("create compartment dir: {e}")))?;

        let store = Arc::new(MemoryStore::open(
            &config.path,
            config.effective_map_size(),
        )?);

        let search_path = config.path.join("tantivy");
        std::fs::create_dir_all(&search_path)
            .map_err(|e| wm_core::CoreError::Memory(format!("create tantivy dir: {e}")))?;
        let search = Arc::new(SearchEngine::open(&search_path)?);

        let associations = Arc::new(AssociationStore::open(store.env())?);

        Ok(Self {
            config,
            store,
            search,
            associations,
        })
    }

    /// Security level of this compartment.
    #[must_use]
    pub const fn level(&self) -> MandalaLevel {
        self.config.level
    }

    /// Whether this compartment is read-only.
    #[must_use]
    pub const fn is_read_only(&self) -> bool {
        self.config.read_only
    }
}

/// Manager for all Mandala compartments.
///
/// Opens and manages isolated LMDB environments for each security tier.
/// Each compartment has completely separate storage, search, and associations.
pub struct MandalaManager {
    /// Base path for all compartments.
    base_path: PathBuf,
    /// Opened compartments.
    compartments: ahash::AHashMap<MandalaLevel, Compartment>,
}

impl MandalaManager {
    /// Create a new manager at the given base path.
    /// Does not open any compartments — call `open_compartment` for each.
    #[must_use]
    pub fn new(base_path: &Path) -> Self {
        Self {
            base_path: base_path.to_path_buf(),
            compartments: ahash::AHashMap::new(),
        }
    }

    /// Open a single compartment at the given level.
    pub fn open_compartment(&mut self, level: MandalaLevel) -> Result<&Compartment> {
        let config = CompartmentConfig::new(level, &self.base_path);
        let compartment = Compartment::open(config)?;
        self.compartments.insert(level, compartment);
        Ok(self.compartments.get(&level).unwrap())
    }

    /// Open all four compartments.
    pub fn open_all(&mut self) -> Result<()> {
        for level in MandalaLevel::all() {
            self.open_compartment(*level)?;
        }
        Ok(())
    }

    /// Get a compartment by level.
    #[must_use]
    pub fn get(&self, level: MandalaLevel) -> Option<&Compartment> {
        self.compartments.get(&level)
    }

    /// Get a compartment by level (mutable access).
    #[must_use]
    pub fn get_mut(&mut self, level: MandalaLevel) -> Option<&mut Compartment> {
        self.compartments.get_mut(&level)
    }

    /// List all opened compartment levels.
    #[must_use]
    pub fn opened_levels(&self) -> Vec<MandalaLevel> {
        self.compartments.keys().copied().collect()
    }

    /// Number of opened compartments.
    #[must_use]
    pub fn len(&self) -> usize {
        self.compartments.len()
    }

    /// Whether any compartments are opened.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.compartments.is_empty()
    }

    /// Base path for all compartments.
    #[must_use]
    pub fn base_path(&self) -> &Path {
        &self.base_path
    }

    /// Close a compartment (drops all stores and releases LMDB file handles).
    pub fn close(&mut self, level: MandalaLevel) -> bool {
        self.compartments.remove(&level).is_some()
    }

    /// Close all compartments.
    pub fn close_all(&mut self) {
        self.compartments.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mandala_level_ordering() {
        let levels = MandalaLevel::all();
        assert_eq!(levels.len(), 4);
        assert_eq!(levels[0], MandalaLevel::Research);
        assert_eq!(levels[3], MandalaLevel::Secure);
    }

    #[test]
    fn mandala_level_str_roundtrip() {
        for level in MandalaLevel::all() {
            let s = level.as_str();
            let back = MandalaLevel::parse(s).unwrap();
            assert_eq!(*level, back);
        }
    }

    #[test]
    fn mandala_level_parse_case_insensitive() {
        assert_eq!(
            MandalaLevel::parse("RESEARCH"),
            Some(MandalaLevel::Research)
        );
        assert_eq!(
            MandalaLevel::parse("Production"),
            Some(MandalaLevel::Production)
        );
        assert_eq!(MandalaLevel::parse("unknown"), None);
    }

    #[test]
    fn mandala_level_map_size_increases_with_strictness() {
        let sizes: Vec<_> = MandalaLevel::all().iter().map(|l| l.map_size()).collect();
        assert!(sizes[0] < sizes[2]); // Research < Production
        assert!(sizes[2] < sizes[3]); // Production < Secure
    }

    #[test]
    fn secure_is_read_only_by_default() {
        assert!(!MandalaLevel::Research.read_only_default());
        assert!(!MandalaLevel::Sandbox.read_only_default());
        assert!(!MandalaLevel::Production.read_only_default());
        assert!(MandalaLevel::Secure.read_only_default());
    }

    #[test]
    fn compartment_config_defaults() {
        let tmp = tempfile::tempdir().unwrap();
        let config = CompartmentConfig::new(MandalaLevel::Production, tmp.path());
        assert_eq!(config.level, MandalaLevel::Production);
        assert!(config.path.ends_with("production"));
        assert_eq!(
            config.effective_map_size(),
            MandalaLevel::Production.map_size()
        );
        assert!(!config.read_only);
    }

    #[test]
    fn compartment_config_overrides() {
        let tmp = tempfile::tempdir().unwrap();
        let config = CompartmentConfig::new(MandalaLevel::Sandbox, tmp.path())
            .with_map_size(512 * 1024 * 1024)
            .read_only(true);
        assert_eq!(config.effective_map_size(), 512 * 1024 * 1024);
        assert!(config.read_only);
    }

    #[test]
    fn compartment_open_creates_stores() {
        let tmp = tempfile::tempdir().unwrap();
        let config = CompartmentConfig::new(MandalaLevel::Research, tmp.path());
        let compartment = Compartment::open(config).unwrap();

        // Stores should be initialized
        assert_eq!(compartment.level(), MandalaLevel::Research);
        assert!(!compartment.is_read_only());

        // LMDB should have the 14 galaxies
        use wm_core::Galaxy;
        for galaxy in Galaxy::all() {
            let _ = compartment.store.galaxy_db(galaxy).unwrap();
        }
    }

    #[test]
    fn compartment_open_secure_is_strict() {
        let tmp = tempfile::tempdir().unwrap();
        let config = CompartmentConfig::new(MandalaLevel::Secure, tmp.path());
        let compartment = Compartment::open(config).unwrap();

        assert_eq!(compartment.level(), MandalaLevel::Secure);
        assert!(compartment.is_read_only());
    }

    #[test]
    fn mandala_manager_open_single() {
        let tmp = tempfile::tempdir().unwrap();
        let mut manager = MandalaManager::new(tmp.path());
        manager.open_compartment(MandalaLevel::Sandbox).unwrap();

        assert_eq!(manager.len(), 1);
        assert!(manager.get(MandalaLevel::Sandbox).is_some());
        assert!(manager.get(MandalaLevel::Research).is_none());
    }

    #[test]
    fn mandala_manager_open_all() {
        let tmp = tempfile::tempdir().unwrap();
        let mut manager = MandalaManager::new(tmp.path());
        manager.open_all().unwrap();

        assert_eq!(manager.len(), 4);
        for level in MandalaLevel::all() {
            assert!(manager.get(*level).is_some(), "missing compartment {level}");
        }
    }

    #[test]
    fn mandala_manager_close() {
        let tmp = tempfile::tempdir().unwrap();
        let mut manager = MandalaManager::new(tmp.path());
        manager.open_all().unwrap();
        assert_eq!(manager.len(), 4);

        manager.close(MandalaLevel::Research);
        assert_eq!(manager.len(), 3);
        assert!(manager.get(MandalaLevel::Research).is_none());

        manager.close_all();
        assert_eq!(manager.len(), 0);
        assert!(manager.is_empty());
    }

    #[test]
    fn mandala_manager_opened_levels() {
        let tmp = tempfile::tempdir().unwrap();
        let mut manager = MandalaManager::new(tmp.path());
        manager.open_compartment(MandalaLevel::Production).unwrap();
        manager.open_compartment(MandalaLevel::Secure).unwrap();

        let levels = manager.opened_levels();
        assert_eq!(levels.len(), 2);
        assert!(levels.contains(&MandalaLevel::Production));
        assert!(levels.contains(&MandalaLevel::Secure));
    }

    #[test]
    fn compartments_are_isolated() {
        let tmp = tempfile::tempdir().unwrap();
        let mut manager = MandalaManager::new(tmp.path());
        manager.open_compartment(MandalaLevel::Research).unwrap();
        manager.open_compartment(MandalaLevel::Production).unwrap();

        let research = manager.get(MandalaLevel::Research).unwrap();
        let production = manager.get(MandalaLevel::Production).unwrap();

        // Write to research
        let mem = crate::Memory::new(wm_core::Galaxy::Codex, "research data".into());
        research.store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        // Should not be visible in production
        let result = production
            .store
            .get(wm_core::Galaxy::Codex, mem.metadata.id)
            .unwrap();
        assert!(result.is_none(), "data leaked between compartments!");

        // But should be visible in research
        let result = research
            .store
            .get(wm_core::Galaxy::Codex, mem.metadata.id)
            .unwrap();
        assert!(result.is_some());
    }

    #[test]
    fn compartment_paths_are_separate() {
        let tmp = tempfile::tempdir().unwrap();
        let mut manager = MandalaManager::new(tmp.path());
        manager.open_all().unwrap();

        for level in MandalaLevel::all() {
            let compartment = manager.get(*level).unwrap();
            let path = &compartment.config.path;
            assert!(path.ends_with(level.dir_name()));
            assert!(path.exists(), "compartment path should exist");
        }
    }

    #[test]
    fn mandala_level_display() {
        assert_eq!(format!("{}", MandalaLevel::Research), "research");
        assert_eq!(format!("{}", MandalaLevel::Secure), "secure");
    }

    #[test]
    fn mandala_level_serde() {
        let json = serde_json::to_string(&MandalaLevel::Production).unwrap();
        assert_eq!(json, "\"production\"");
        let back: MandalaLevel = serde_json::from_str(&json).unwrap();
        assert_eq!(back, MandalaLevel::Production);
    }
}
