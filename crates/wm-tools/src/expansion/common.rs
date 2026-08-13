//! Shared helpers for expansion tools.

#![forbid(unsafe_code)]

use wm_core::{CoreError, Galaxy};
use wm_memory::SearchEngine;

/// De-index a memory from the Tantivy full-text index.
///
/// Best-effort and non-fatal: an index failure is logged and ignored, so the
/// LMDB write (already committed or about to be committed by the caller) is
/// never rolled back because of a search-index problem.
///
/// Every path that deletes or replaces a memory in LMDB MUST de-index the old
/// document through this helper — otherwise full-text search keeps returning
/// deleted memories (index drift).
pub fn deindex(search: Option<&SearchEngine>, id_str: &str) {
    let Some(search) = search else { return };
    if let Err(e) = (|| {
        let mut writer = search.writer()?;
        search.delete_document(&mut writer, id_str)?;
        search.commit(&mut writer)?;
        Ok::<(), wm_core::CoreError>(())
    })() {
        tracing::warn!("Tantivy de-indexing failed for memory {id_str}: {e}");
    }
}

/// Index a memory into the Tantivy full-text index.
///
/// Best-effort and non-fatal, mirroring `deindex`. Every path that writes a
/// memory into LMDB outside `memory.create`/`memory.update` should index it
/// through this helper so full-text search stays consistent.
pub fn index_memory(search: Option<&SearchEngine>, mem: &wm_memory::Memory) {
    let Some(search) = search else { return };
    let id_str = mem.metadata.id.to_string();
    let galaxy_str = mem.metadata.galaxy.db_name().to_string();
    if let Err(e) = (|| {
        let mut writer = search.writer()?;
        search.add_document(
            &mut writer,
            &id_str,
            &galaxy_str,
            &mem.content,
            &mem.metadata.tags,
            mem.metadata.created_at.timestamp(),
        )?;
        search.commit(&mut writer)?;
        Ok::<(), wm_core::CoreError>(())
    })() {
        tracing::warn!("Tantivy indexing failed for memory {id_str}: {e}");
    }
}

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
