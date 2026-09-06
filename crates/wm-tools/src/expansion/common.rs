//! Shared helpers for expansion tools.

#![forbid(unsafe_code)]

use wm_core::{CoreError, Galaxy, Resource};
use wm_memory::{Memory, SearchEngine};

/// Effect-row writes covering every memory galaxy — for tools whose
/// mutation target is chosen at runtime (`galaxy` argument), so the
/// declaration honestly covers whatever galaxy the caller selects.
#[must_use]
pub fn memory_galaxy_writes() -> Vec<Resource> {
    Galaxy::memory_galaxies()
        .iter()
        .map(|g| Resource::Galaxy(g.db_name().to_string()))
        .collect()
}

/// Effect-row reads covering every memory galaxy — the paired declaration
/// for read-modify-write tools (scan → mutate → write) so the Satya
/// fabrication rule sees the evidence read before a citta write.
#[must_use]
pub fn memory_galaxy_reads() -> Vec<Resource> {
    Galaxy::memory_galaxies()
        .iter()
        .map(|g| Resource::Galaxy(g.db_name().to_string()))
        .collect()
}

/// Effect-row writes for pure-writer tools (e.g. `memory.create`) that
/// target a runtime galaxy but never read it.
///
/// Citta is excluded: a fresh write into the consciousness stream without
/// evidence is fabrication, refused by the pipeline's runtime Satya check.
#[must_use]
pub fn fresh_write_galaxies() -> Vec<Resource> {
    Galaxy::memory_galaxies()
        .iter()
        .filter(|g| **g != Galaxy::Citta)
        .map(|g| Resource::Galaxy(g.db_name().to_string()))
        .collect()
}

/// MCP visibility: memories flagged `is_private` never appear in MCP read,
/// search, list, query, or recall responses. Local maintenance paths
/// (export, doctor, reindex) may still see them.
#[must_use]
pub const fn mcp_visible(mem: &Memory) -> bool {
    !mem.metadata.is_private
}

/// Model visibility: memories flagged `model_exclude` never enter model
/// context windows or reasoning evidence.
#[must_use]
pub const fn model_visible(mem: &Memory) -> bool {
    !mem.metadata.model_exclude
}

/// Validity visibility (V8 Slice B, D1+D2): the third visibility predicate
/// beside [`mcp_visible`]/[`model_visible`].
///
/// True unless the memory carries a non-`Active` validity stamp AND the
/// `WM_VALIDITY_ENFORCE` knob is on. Knob-off (the default) the predicate
/// is identically true, so every wired call site is byte-identical with
/// or without validity stamps (the S8 doctrine).
#[must_use]
pub fn validity_visible(mem: &Memory) -> bool {
    if wm_memory::memory::validity_enforced() {
        mem.metadata.validity.is_current()
    } else {
        true
    }
}

// ── JSON-Schema helpers for `Tool::input_schema()` ─────────────────────

/// Build an object schema from properties and required keys.
#[must_use]
pub fn schema(properties: &serde_json::Value, required: &[&str]) -> serde_json::Value {
    serde_json::json!({
        "type": "object",
        "properties": properties,
        "required": required,
    })
}

/// A string property.
#[must_use]
pub fn str_prop(description: &str) -> serde_json::Value {
    serde_json::json!({"type": "string", "description": description})
}

/// A number property.
#[must_use]
pub fn num_prop(description: &str) -> serde_json::Value {
    serde_json::json!({"type": "number", "description": description})
}

/// An integer property.
#[must_use]
pub fn int_prop(description: &str) -> serde_json::Value {
    serde_json::json!({"type": "integer", "description": description})
}

/// A boolean property.
#[must_use]
pub fn bool_prop(description: &str) -> serde_json::Value {
    serde_json::json!({"type": "boolean", "description": description})
}

/// An array property with string items.
#[must_use]
pub fn str_array_prop(description: &str) -> serde_json::Value {
    serde_json::json!({"type": "array", "items": {"type": "string"}, "description": description})
}

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

#[cfg(test)]
mod tests {
    use super::*;

    // ── Validity visibility (V8 Slice B, D1+D2) ─────────────────────────

    #[test]
    fn validity_visible_defaults_true_even_when_stamped() {
        // Knob-off (the default) the predicate is identically true — even
        // for a stamped non-Active memory — so every wired call site is
        // byte-identical with or without validity stamps (S8 doctrine).
        // (The ON case needs env mutation, `unsafe` under edition-2024
        // `forbid(unsafe)` — covered by inspection, not here.)
        let mut mem = Memory::new(Galaxy::Codex, "old claim".into());
        assert!(validity_visible(&mem));
        let replacement = uuid::Uuid::new_v4();
        mem.transition_validity(wm_core::episodic::MemoryTransition::Supersede { replacement })
            .unwrap();
        assert!(!mem.metadata.validity.is_current());
        assert!(validity_visible(&mem));
    }
}
