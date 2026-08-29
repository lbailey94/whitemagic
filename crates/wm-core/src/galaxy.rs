//! Galaxy — The 14 memory galaxies.
//!
//! Each galaxy is a named LMDB sub-database storing related memories.
//! The galaxy taxonomy is preserved from v2.

use serde::{Deserialize, Serialize};
use std::fmt;

/// The 14 memory galaxies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Galaxy {
    /// Artistic/creative memories
    Aria,
    /// Consciousness stream
    Citta,
    /// Knowledge/documents
    Codex,
    /// Session journals
    Journals,
    /// Dream cycle outputs
    Dreams,
    /// Research notes
    Research,
    /// Session recordings
    Sessions,
    /// System state/config
    Substrate,
    /// Tutorial memories
    Tutorial,
    /// Cross-galaxy index
    Universal,
    /// Karma ledger
    Karma,
    /// Governance rules
    Dharma,
    /// Cross-memory links
    Associations,
    /// Vector embeddings
    Embeddings,
}

impl Galaxy {
    /// Total number of galaxies.
    pub const COUNT: usize = 14;

    /// All galaxies in order.
    #[must_use]
    pub const fn all() -> [Self; 14] {
        [
            Self::Aria,
            Self::Citta,
            Self::Codex,
            Self::Journals,
            Self::Dreams,
            Self::Research,
            Self::Sessions,
            Self::Substrate,
            Self::Tutorial,
            Self::Universal,
            Self::Karma,
            Self::Dharma,
            Self::Associations,
            Self::Embeddings,
        ]
    }

    /// Galaxies that store `Memory` records (excluding special-purpose galaxies).
    ///
    /// Karma, Dharma, Associations, and Embeddings store non-Memory data
    /// (KarmaEntry, rules, association links, vectors) and should be skipped
    /// when scanning for memories.
    #[must_use]
    pub const fn memory_galaxies() -> [Self; 10] {
        [
            Self::Aria,
            Self::Citta,
            Self::Codex,
            Self::Journals,
            Self::Dreams,
            Self::Research,
            Self::Sessions,
            Self::Substrate,
            Self::Tutorial,
            Self::Universal,
        ]
    }

    /// LMDB sub-database name.
    #[must_use]
    pub const fn db_name(self) -> &'static str {
        match self {
            Self::Aria => "aria",
            Self::Citta => "citta",
            Self::Codex => "codex",
            Self::Journals => "journals",
            Self::Dreams => "dreams",
            Self::Research => "research",
            Self::Sessions => "sessions",
            Self::Substrate => "substrate",
            Self::Tutorial => "tutorial",
            Self::Universal => "universal",
            Self::Karma => "karma",
            Self::Dharma => "dharma",
            Self::Associations => "associations",
            Self::Embeddings => "embeddings",
        }
    }

    /// Human-readable description.
    #[must_use]
    pub const fn description(self) -> &'static str {
        match self {
            Self::Aria => "Artistic/creative memories",
            Self::Citta => "Consciousness stream",
            Self::Codex => "Knowledge/documents",
            Self::Journals => "Session journals",
            Self::Dreams => "Dream cycle outputs",
            Self::Research => "Research notes",
            Self::Sessions => "Session recordings",
            Self::Substrate => "System state/config",
            Self::Tutorial => "Tutorial memories",
            Self::Universal => "Cross-galaxy index",
            Self::Karma => "Karma ledger",
            Self::Dharma => "Governance rules",
            Self::Associations => "Cross-memory links",
            Self::Embeddings => "Vector embeddings",
        }
    }

    /// Parse a galaxy from its LMDB sub-database name.
    ///
    /// Returns `None` if the name doesn't match any galaxy.
    #[must_use]
    pub fn from_db_name(name: &str) -> Option<Self> {
        Self::all().into_iter().find(|g| g.db_name() == name)
    }
}

impl fmt::Display for Galaxy {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.db_name())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn galaxy_count_is_14() {
        assert_eq!(Galaxy::COUNT, 14);
        assert_eq!(Galaxy::all().len(), 14);
    }

    #[test]
    fn galaxy_db_names_unique() {
        let names: Vec<_> = Galaxy::all().iter().map(|g| g.db_name()).collect();
        let unique: std::collections::HashSet<_> = names.iter().collect();
        assert_eq!(names.len(), unique.len());
    }

    #[test]
    fn memory_galaxies_excludes_special_purpose() {
        let mg = Galaxy::memory_galaxies();
        assert_eq!(mg.len(), 10);
        assert!(!mg.contains(&Galaxy::Karma));
        assert!(!mg.contains(&Galaxy::Dharma));
        assert!(!mg.contains(&Galaxy::Associations));
        assert!(!mg.contains(&Galaxy::Embeddings));
    }
}
