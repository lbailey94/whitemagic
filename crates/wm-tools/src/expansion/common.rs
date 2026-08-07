//! Shared helpers for expansion tools.

#![forbid(unsafe_code)]

use wm_core::{CoreError, Galaxy};

/// Parse a galaxy name, returning an error for unrecognized names.
pub fn parse_galaxy(s: &str) -> wm_core::Result<Galaxy> {
    match s.to_lowercase().as_str() {
        "aria" => Ok(Galaxy::Aria),
        "citta" => Ok(Galaxy::Citta),
        "codex" => Ok(Galaxy::Codex),
        "journals" => Ok(Galaxy::Journals),
        "dreams" => Ok(Galaxy::Dreams),
        "research" => Ok(Galaxy::Research),
        "sessions" => Ok(Galaxy::Sessions),
        "substrate" => Ok(Galaxy::Substrate),
        "tutorial" => Ok(Galaxy::Tutorial),
        "universal" => Ok(Galaxy::Universal),
        "karma" => Ok(Galaxy::Karma),
        "dharma" => Ok(Galaxy::Dharma),
        "associations" => Ok(Galaxy::Associations),
        "embeddings" => Ok(Galaxy::Embeddings),
        other => Err(CoreError::InvalidArgs(format!(
            "Unknown galaxy: '{other}'. Valid galaxies: aria, citta, codex, journals, dreams, research, sessions, substrate, tutorial, universal, karma, dharma, associations, embeddings"
        ))),
    }
}

/// Parse a galaxy name, falling back to a default for None/empty input.
/// Returns an error for non-empty unrecognized names.
pub fn parse_galaxy_or(s: Option<&str>, default: Galaxy) -> wm_core::Result<Galaxy> {
    match s {
        None | Some("") => Ok(default),
        Some(s) => parse_galaxy(s),
    }
}

#[must_use]
pub const fn galaxy_name(g: Galaxy) -> &'static str {
    match g {
        Galaxy::Aria => "aria",
        Galaxy::Citta => "citta",
        Galaxy::Codex => "codex",
        Galaxy::Journals => "journals",
        Galaxy::Dreams => "dreams",
        Galaxy::Research => "research",
        Galaxy::Sessions => "sessions",
        Galaxy::Substrate => "substrate",
        Galaxy::Tutorial => "tutorial",
        Galaxy::Universal => "universal",
        Galaxy::Karma => "karma",
        Galaxy::Dharma => "dharma",
        Galaxy::Associations => "associations",
        Galaxy::Embeddings => "embeddings",
    }
}
