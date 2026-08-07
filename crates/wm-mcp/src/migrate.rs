//! v2 → v4 Migration tool — transfers SQLite memories to LMDB.

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use rusqlite::{Connection, Row};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use uuid::Uuid;
use wm_core::Galaxy;
use wm_memory::{Memory, MemoryType, SearchEngine};

/// v2 galaxy name → v4 Galaxy enum mapping.
fn map_galaxy(name: &str) -> Option<Galaxy> {
    match name.to_lowercase().as_str() {
        "codex" | "knowledge" | "openai_archives" => Some(Galaxy::Codex),
        "sessions" => Some(Galaxy::Sessions),
        "universal" | "main" | "archive" => Some(Galaxy::Universal),
        "aria" | "creative_solutions" => Some(Galaxy::Aria),
        "citta" | "self_discovery" => Some(Galaxy::Citta),
        "dreams" => Some(Galaxy::Dreams),
        "research" | "insight" => Some(Galaxy::Research),
        "substrate" | "meta" | "telemetry" => Some(Galaxy::Substrate),
        "tutorial" => Some(Galaxy::Tutorial),
        "journals" => Some(Galaxy::Journals),
        // Skip benchmark/quarantine galaxies — no cognitive value
        "benchmark"
        | "beam_bench"
        | "abstention_bench"
        | "longmemeval_bench"
        | "hologram_bench"
        | "quarantine"
        | "quarantine_universal"
        | "test"
        | "locomo_bench" => None,
        // Unknown galaxies → Universal
        _ => Some(Galaxy::Universal),
    }
}

/// v2 memory_type string → v4 MemoryType enum.
fn map_memory_type(v2_type: &str) -> MemoryType {
    match v2_type.to_uppercase().as_str() {
        "SHORT_TERM" => MemoryType::ShortTerm,
        "LONG_TERM" | "DOCUMENT" | "REFERENCE" => MemoryType::LongTerm,
        "EMOTIONAL" => MemoryType::Emotional,
        "NARRATIVE" => MemoryType::Narrative,
        "SYMBOLIC" => MemoryType::Symbolic,
        "PATTERN" => MemoryType::Pattern,
        "PROCEDURAL" => MemoryType::Procedural,
        "CITTA" => MemoryType::Citta,
        _ => MemoryType::LongTerm,
    }
}

/// Parse a v2 ID string into a UUID. If the string is a valid UUID, parse it.
/// Otherwise, generate a deterministic UUID v5 from the string.
fn parse_v2_id(id_str: &str) -> Uuid {
    if let Ok(uuid) = Uuid::parse_str(id_str) {
        return uuid;
    }
    // For non-UUID IDs (hex strings), generate a deterministic UUID v5
    Uuid::new_v5(&Uuid::NAMESPACE_URL, id_str.as_bytes())
}

/// Parse a v2 timestamp string into a DateTime<Utc>.
fn parse_timestamp(ts: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(ts).map_or_else(|_| Utc::now(), |dt| dt.with_timezone(&Utc))
}

/// Map v2 source_trust string to v4 f32 trust score.
fn map_source_trust(v2_trust: &str) -> f32 {
    match v2_trust.to_lowercase().as_str() {
        "user" => 1.0,
        "tool_output" | "tool" => 0.7,
        "inferred" => 0.5,
        "web" => 0.3,
        _ => 0.5,
    }
}

struct V2Memory {
    id: String,
    galaxy: String,
    content: String,
    memory_type: String,
    created_at: String,
    accessed_at: String,
    access_count: i64,
    emotional_valence: f64,
    importance: f64,
    neuro_score: f64,
    novelty_score: f64,
    recall_count: i64,
    half_life_days: f64,
    is_protected: bool,
    is_private: bool,
    model_exclude: bool,
    content_hash: String,
    source_trust: String,
    version: i64,
    agent_id: String,
}

fn row_to_v2_memory(row: &Row) -> rusqlite::Result<V2Memory> {
    Ok(V2Memory {
        id: row.get::<_, String>("id")?,
        galaxy: row
            .get::<_, String>("galaxy")
            .unwrap_or_else(|_| "universal".to_string()),
        content: row.get::<_, String>("content").unwrap_or_default(),
        memory_type: row
            .get::<_, String>("memory_type")
            .unwrap_or_else(|_| "LONG_TERM".to_string()),
        created_at: row
            .get::<_, String>("created_at")
            .unwrap_or_else(|_| Utc::now().to_rfc3339()),
        accessed_at: row
            .get::<_, String>("accessed_at")
            .unwrap_or_else(|_| Utc::now().to_rfc3339()),
        access_count: row.get::<_, i64>("access_count").unwrap_or(0),
        emotional_valence: row.get::<_, f64>("emotional_valence").unwrap_or(0.0),
        importance: row.get::<_, f64>("importance").unwrap_or(0.5),
        neuro_score: row.get::<_, f64>("neuro_score").unwrap_or(0.5),
        novelty_score: row.get::<_, f64>("novelty_score").unwrap_or(1.0),
        recall_count: row.get::<_, i64>("recall_count").unwrap_or(0),
        half_life_days: row.get::<_, f64>("half_life_days").unwrap_or(30.0),
        is_protected: row
            .get::<_, i64>("is_protected")
            .map(|v| v != 0)
            .unwrap_or(false),
        is_private: row
            .get::<_, i64>("is_private")
            .map(|v| v != 0)
            .unwrap_or(false),
        model_exclude: row
            .get::<_, i64>("model_exclude")
            .map(|v| v != 0)
            .unwrap_or(false),
        content_hash: row.get::<_, String>("content_hash").unwrap_or_default(),
        source_trust: row
            .get::<_, String>("source_trust")
            .unwrap_or_else(|_| "user".to_string()),
        version: row.get::<_, i64>("version").unwrap_or(1),
        agent_id: row.get::<_, String>("agent_id").unwrap_or_default(),
    })
}

/// Convert a v2 memory row into a v4 Memory.
fn v2_to_v4_memory(v2: &V2Memory, tags: &[String], galaxy: Galaxy) -> Memory {
    let id = parse_v2_id(&v2.id);
    let created_at = parse_timestamp(&v2.created_at);
    let accessed_at = parse_timestamp(&v2.accessed_at);

    let mut mem = Memory::new(galaxy, v2.content.clone());
    mem.metadata.id = id;
    mem.metadata.galaxy = galaxy;
    mem.metadata.content_hash = if v2.content_hash.is_empty() {
        wm_memory::content_hash(&v2.content)
    } else {
        v2.content_hash.clone()
    };
    mem.metadata.tags = tags.to_vec();
    mem.metadata.importance = v2.importance as f32;
    mem.metadata.created_at = created_at;
    mem.metadata.accessed_at = accessed_at;
    mem.metadata.access_count = v2.access_count.max(0) as u64;
    mem.metadata.memory_type = map_memory_type(&v2.memory_type);
    mem.metadata.neuro_score = v2.neuro_score as f32;
    mem.metadata.novelty_score = v2.novelty_score as f32;
    mem.metadata.emotional_valence = v2.emotional_valence as f32;
    mem.metadata.emotional_weight = (v2.emotional_valence.abs()) as f32;
    mem.metadata.is_protected = v2.is_protected;
    mem.metadata.is_private = v2.is_private;
    mem.metadata.model_exclude = v2.model_exclude;
    mem.metadata.source.clone_from(&v2.source_trust);
    mem.metadata.source_trust = map_source_trust(&v2.source_trust);
    mem.metadata.half_life_days = v2.half_life_days as f32;
    mem.metadata.recall_count = v2.recall_count.max(0) as u64;
    mem.metadata.version = v2.version.max(1) as u64;
    mem.metadata.agent_id = if v2.agent_id.is_empty() {
        "system".to_string()
    } else {
        v2.agent_id.clone()
    };
    // Set coords based on original creation time
    mem.metadata.coords = wm_core::HolographicCoords::new(galaxy, created_at.timestamp() as u64);
    mem
}

/// Load tags for all memories in a SQLite database.
fn load_tags(conn: &Connection) -> Result<HashMap<String, Vec<String>>> {
    let mut stmt = conn.prepare("SELECT memory_id, tag FROM tags")?;
    let mut tag_map: HashMap<String, Vec<String>> = HashMap::new();
    let rows = stmt.query_map([], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    })?;
    for row in rows {
        let (memory_id, tag) = row?;
        tag_map.entry(memory_id).or_default().push(tag);
    }
    Ok(tag_map)
}

/// Migrate a single v2 SQLite database to v4 LMDB.
fn migrate_database(
    db_path: &Path,
    store: &wm_memory::MemoryStore,
    search: &SearchEngine,
    galaxy_override: Option<Galaxy>,
    dry_run: bool,
) -> Result<(usize, usize, usize)> {
    let db_name = db_path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown");
    let parent_name = db_path
        .parent()
        .and_then(|p| p.file_name())
        .and_then(|n| n.to_str())
        .unwrap_or("unknown");

    let conn = Connection::open(db_path)
        .with_context(|| format!("Opening SQLite DB: {}", db_path.display()))?;

    // Load tags
    let tag_map = load_tags(&conn).unwrap_or_default();

    // Query all memories
    let mut stmt = conn.prepare(
        "SELECT id, galaxy, content, memory_type, created_at, accessed_at, access_count, \
         emotional_valence, importance, neuro_score, novelty_score, recall_count, \
         half_life_days, is_protected, is_private, model_exclude, content_hash, \
         source_trust, version, agent_id FROM memories",
    )?;

    let rows = stmt.query_map([], row_to_v2_memory)?;

    // Group memories by v4 galaxy for batch writing
    let mut by_galaxy: HashMap<Galaxy, Vec<Memory>> = HashMap::new();
    let mut total_read = 0usize;
    let mut total_skipped = 0usize;

    for row in rows {
        let v2 = row?;
        total_read += 1;

        // Determine target galaxy
        let galaxy = if let Some(g) = galaxy_override {
            g
        } else if let Some(g) = map_galaxy(&v2.galaxy) {
            g
        } else {
            total_skipped += 1;
            continue;
        };

        let tags = tag_map.get(&v2.id).cloned().unwrap_or_default();
        let mem = v2_to_v4_memory(&v2, &tags, galaxy);
        by_galaxy.entry(galaxy).or_default().push(mem);
    }

    let mut total_written = 0usize;

    if dry_run {
        for (galaxy, memories) in &by_galaxy {
            println!(
                "  [DRY RUN] {} → {}: {} memories would be written",
                parent_name,
                galaxy.db_name(),
                memories.len()
            );
            total_written += memories.len();
        }
    } else {
        let mut writer = search.writer()?;
        for (galaxy, memories) in &by_galaxy {
            // Batch write in chunks of 500 to keep transactions reasonable
            for chunk in memories.chunks(500) {
                store.put_batch(*galaxy, chunk)?;
                // Index each memory into Tantivy
                for mem in chunk {
                    search.add_document(
                        &mut writer,
                        &mem.metadata.id.to_string(),
                        galaxy.db_name(),
                        &mem.content,
                        &mem.metadata.tags,
                        mem.metadata.created_at.timestamp(),
                    )?;
                }
            }
            println!(
                "  {} → {}: {} memories written",
                parent_name,
                galaxy.db_name(),
                memories.len()
            );
            total_written += memories.len();
        }
        search.commit(&mut writer)?;
    }

    println!(
        "  {parent_name} ({db_name}): read={total_read}, written={total_written}, skipped={total_skipped}"
    );

    Ok((total_read, total_written, total_skipped))
}

/// Discover all v2 galaxy databases in a directory.
fn discover_v2_databases(galaxies_dir: &Path) -> Result<Vec<PathBuf>> {
    let mut dbs = Vec::new();
    if !galaxies_dir.is_dir() {
        return Ok(dbs);
    }

    for entry in std::fs::read_dir(galaxies_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            let db_path = path.join("whitemagic.db");
            if db_path.exists() {
                dbs.push(db_path);
            }
        }
    }

    dbs.sort();
    Ok(dbs)
}

/// Run the migration from v2 SQLite to v4 LMDB.
///
/// # Arguments
/// * `v2_galaxies_dir` - Path to v2's `galaxies/` directory (containing per-galaxy subdirs with whitemagic.db)
/// * `v2_single_db` - Optional path to a single v2 SQLite database
/// * `v4_store_path` - Path to v4's LMDB store directory
/// * `dry_run` - If true, only report what would be migrated without writing
/// * `galaxy_filter` - Optional galaxy name filter (only migrate memories from this v2 galaxy)
pub fn run_migration(
    v2_galaxies_dir: Option<&Path>,
    v2_single_db: Option<&Path>,
    v4_store_path: &Path,
    dry_run: bool,
    galaxy_filter: Option<&str>,
) -> Result<()> {
    println!("=== WhiteMagic v4 Migration Tool ===");
    println!();
    println!("Target v4 store: {}", v4_store_path.display());
    if dry_run {
        println!("Mode: DRY RUN (no writes)");
    }
    println!();

    // Collect databases to migrate
    let dbs: Vec<PathBuf> = if let Some(single) = v2_single_db {
        vec![single.to_path_buf()]
    } else if let Some(dir) = v2_galaxies_dir {
        discover_v2_databases(dir)?
    } else {
        anyhow::bail!("Either --v2-dir or --v2-db must be specified");
    };

    if dbs.is_empty() {
        println!("No v2 databases found to migrate.");
        return Ok(());
    }

    println!("Found {} v2 database(s) to migrate:", dbs.len());
    for db in &dbs {
        let galaxy_name = db
            .parent()
            .and_then(|p| p.file_name())
            .and_then(|n| n.to_str())
            .unwrap_or("?");
        println!("  - {} ({})", galaxy_name, db.display());
    }
    println!();

    // Open v4 store — use 4GB map size for migration (v2 data can be large)
    // Write to lmdb/ subdirectory for consistency with wm serve/doctor
    let lmdb_path = v4_store_path.join("lmdb");
    std::fs::create_dir_all(&lmdb_path)?;
    let store = wm_memory::MemoryStore::open(&lmdb_path, 4 * 1024 * 1024 * 1024)?;

    // Open Tantivy search index alongside LMDB
    let tantivy_path = lmdb_path.join("tantivy");
    std::fs::create_dir_all(&tantivy_path)?;
    let search = SearchEngine::open(&tantivy_path)?;

    // Galaxy filter override
    let galaxy_override = galaxy_filter.and_then(map_galaxy);

    let mut grand_total_read = 0usize;
    let mut grand_total_written = 0usize;
    let mut grand_total_skipped = 0usize;

    for db in &dbs {
        let (read, written, skipped) =
            migrate_database(db, &store, &search, galaxy_override, dry_run)?;
        grand_total_read += read;
        grand_total_written += written;
        grand_total_skipped += skipped;
    }

    println!();
    println!("=== Migration Summary ===");
    println!("Total memories read:    {grand_total_read}");
    println!("Total memories written: {grand_total_written}");
    println!("Total memories skipped: {grand_total_skipped}");
    println!();

    // Verify by counting memories in v4 store
    if !dry_run {
        println!("=== v4 Store Verification ===");
        let mut total = 0usize;
        for galaxy in Galaxy::all() {
            let count = store.count(galaxy).unwrap_or(0);
            if count > 0 {
                println!("  {}: {} memories", galaxy.db_name(), count);
                total += count;
            }
        }
        println!("  Total in v4: {total} memories");
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;
    use tempfile::TempDir;
    use wm_core::Galaxy;

    /// Create a v2-compatible SQLite database with the memories and tags schema.
    fn create_v2_db(path: &Path) -> Connection {
        let conn = Connection::open(path).unwrap();
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                memory_type TEXT,
                created_at TEXT,
                updated_at TEXT,
                accessed_at TEXT,
                access_count INTEGER,
                emotional_valence REAL,
                importance REAL,
                neuro_score REAL DEFAULT 1.0,
                novelty_score REAL DEFAULT 1.0,
                recall_count INTEGER DEFAULT 0,
                half_life_days REAL DEFAULT 30.0,
                is_protected INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                title TEXT,
                content_hash TEXT,
                is_private INTEGER DEFAULT 0,
                model_exclude INTEGER DEFAULT 0,
                galaxy TEXT DEFAULT 'universal',
                source_trust TEXT DEFAULT 'user',
                version INTEGER DEFAULT 0,
                agent_id TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS tags (
                memory_id TEXT,
                tag TEXT,
                PRIMARY KEY (memory_id, tag)
            );",
        )
        .unwrap();
        conn
    }

    /// Insert a v2 memory row into the SQLite database.
    fn insert_v2_memory(
        conn: &Connection,
        id: &str,
        galaxy: &str,
        content: &str,
        memory_type: &str,
        source_trust: &str,
    ) {
        conn.execute(
            "INSERT INTO memories (id, galaxy, content, memory_type, created_at, accessed_at, \
             access_count, emotional_valence, importance, neuro_score, novelty_score, \
             recall_count, half_life_days, is_protected, is_private, model_exclude, \
             content_hash, source_trust, version, agent_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20)",
            rusqlite::params![
                id,
                galaxy,
                content,
                memory_type,
                "2026-01-01T00:00:00Z",
                "2026-01-02T00:00:00Z",
                5i64,
                0.5f64,
                0.8f64,
                0.7f64,
                0.9f64,
                3i64,
                30.0f64,
                0i64,
                0i64,
                0i64,
                "",
                source_trust,
                1i64,
                "test-agent",
            ],
        )
        .unwrap();
    }

    fn insert_tag(conn: &Connection, memory_id: &str, tag: &str) {
        conn.execute(
            "INSERT INTO tags (memory_id, tag) VALUES (?1, ?2)",
            rusqlite::params![memory_id, tag],
        )
        .unwrap();
    }

    #[test]
    fn map_galaxy_known_names() {
        assert_eq!(map_galaxy("codex"), Some(Galaxy::Codex));
        assert_eq!(map_galaxy("knowledge"), Some(Galaxy::Codex));
        assert_eq!(map_galaxy("sessions"), Some(Galaxy::Sessions));
        assert_eq!(map_galaxy("universal"), Some(Galaxy::Universal));
        assert_eq!(map_galaxy("main"), Some(Galaxy::Universal));
        assert_eq!(map_galaxy("aria"), Some(Galaxy::Aria));
        assert_eq!(map_galaxy("citta"), Some(Galaxy::Citta));
        assert_eq!(map_galaxy("dreams"), Some(Galaxy::Dreams));
        assert_eq!(map_galaxy("research"), Some(Galaxy::Research));
        assert_eq!(map_galaxy("substrate"), Some(Galaxy::Substrate));
        assert_eq!(map_galaxy("tutorial"), Some(Galaxy::Tutorial));
        assert_eq!(map_galaxy("journals"), Some(Galaxy::Journals));
    }

    #[test]
    fn map_galaxy_case_insensitive() {
        assert_eq!(map_galaxy("CODEX"), Some(Galaxy::Codex));
        assert_eq!(map_galaxy("Sessions"), Some(Galaxy::Sessions));
        assert_eq!(map_galaxy("DREAMS"), Some(Galaxy::Dreams));
    }

    #[test]
    fn map_galaxy_skips_benchmark() {
        assert_eq!(map_galaxy("benchmark"), None);
        assert_eq!(map_galaxy("quarantine"), None);
        assert_eq!(map_galaxy("test"), None);
        assert_eq!(map_galaxy("beam_bench"), None);
    }

    #[test]
    fn map_galaxy_unknown_defaults_to_universal() {
        assert_eq!(map_galaxy("unknown_galaxy"), Some(Galaxy::Universal));
        assert_eq!(map_galaxy("custom"), Some(Galaxy::Universal));
    }

    #[test]
    fn map_memory_type_all_variants() {
        assert_eq!(map_memory_type("SHORT_TERM"), MemoryType::ShortTerm);
        assert_eq!(map_memory_type("LONG_TERM"), MemoryType::LongTerm);
        assert_eq!(map_memory_type("DOCUMENT"), MemoryType::LongTerm);
        assert_eq!(map_memory_type("REFERENCE"), MemoryType::LongTerm);
        assert_eq!(map_memory_type("EMOTIONAL"), MemoryType::Emotional);
        assert_eq!(map_memory_type("NARRATIVE"), MemoryType::Narrative);
        assert_eq!(map_memory_type("SYMBOLIC"), MemoryType::Symbolic);
        assert_eq!(map_memory_type("PATTERN"), MemoryType::Pattern);
        assert_eq!(map_memory_type("PROCEDURAL"), MemoryType::Procedural);
        assert_eq!(map_memory_type("CITTA"), MemoryType::Citta);
    }

    #[test]
    fn map_memory_type_unknown_defaults_to_long_term() {
        assert_eq!(map_memory_type("UNKNOWN"), MemoryType::LongTerm);
        assert_eq!(map_memory_type(""), MemoryType::LongTerm);
    }

    #[test]
    fn parse_v2_id_valid_uuid() {
        let uuid_str = "550e8400-e29b-41d4-a716-446655440000";
        let parsed = parse_v2_id(uuid_str);
        assert_eq!(parsed.to_string(), uuid_str);
    }

    #[test]
    fn parse_v2_id_non_uuid_generates_deterministic() {
        let id_str = "abc123hex";
        let parsed1 = parse_v2_id(id_str);
        let parsed2 = parse_v2_id(id_str);
        assert_eq!(parsed1, parsed2, "Same input should produce same UUID");
        assert_ne!(parsed1.to_string(), id_str, "Should not be the raw string");
    }

    #[test]
    fn parse_timestamp_valid_rfc3339() {
        let ts = "2026-01-01T12:00:00Z";
        let parsed = parse_timestamp(ts);
        assert_eq!(parsed.to_rfc3339(), "2026-01-01T12:00:00+00:00");
    }

    #[test]
    fn parse_timestamp_invalid_returns_now() {
        let ts = "not a timestamp";
        let parsed = parse_timestamp(ts);
        let now = Utc::now();
        let diff = now - parsed;
        assert!(diff.num_seconds() < 5, "Should be close to now");
    }

    #[test]
    fn map_source_trust_known_values() {
        assert!((map_source_trust("user") - 1.0).abs() < f32::EPSILON);
        assert!((map_source_trust("tool_output") - 0.7).abs() < f32::EPSILON);
        assert!((map_source_trust("tool") - 0.7).abs() < f32::EPSILON);
        assert!((map_source_trust("inferred") - 0.5).abs() < f32::EPSILON);
        assert!((map_source_trust("web") - 0.3).abs() < f32::EPSILON);
    }

    #[test]
    fn map_source_trust_unknown_defaults_to_0_5() {
        assert!((map_source_trust("unknown") - 0.5).abs() < f32::EPSILON);
    }

    #[test]
    fn v2_to_v4_memory_preserves_fields() {
        let v2 = V2Memory {
            id: "550e8400-e29b-41d4-a716-446655440000".to_string(),
            galaxy: "codex".to_string(),
            content: "test content".to_string(),
            memory_type: "LONG_TERM".to_string(),
            created_at: "2026-01-01T00:00:00Z".to_string(),
            accessed_at: "2026-01-02T00:00:00Z".to_string(),
            access_count: 5,
            emotional_valence: 0.5,
            importance: 0.8,
            neuro_score: 0.7,
            novelty_score: 0.9,
            recall_count: 3,
            half_life_days: 30.0,
            is_protected: false,
            is_private: false,
            model_exclude: false,
            content_hash: "abc123".to_string(),
            source_trust: "user".to_string(),
            version: 2,
            agent_id: "test-agent".to_string(),
        };
        let tags = vec!["rust".to_string(), "memory".to_string()];
        let mem = v2_to_v4_memory(&v2, &tags, Galaxy::Codex);

        assert_eq!(mem.metadata.galaxy, Galaxy::Codex);
        assert_eq!(mem.content, "test content");
        assert_eq!(mem.metadata.memory_type, MemoryType::LongTerm);
        assert_eq!(mem.metadata.tags, tags);
        assert!((mem.metadata.importance - 0.8).abs() < f32::EPSILON);
        assert!((mem.metadata.neuro_score - 0.7).abs() < f32::EPSILON);
        assert!((mem.metadata.novelty_score - 0.9).abs() < f32::EPSILON);
        assert!((mem.metadata.emotional_valence - 0.5).abs() < f32::EPSILON);
        assert!((mem.metadata.emotional_weight - 0.5).abs() < f32::EPSILON);
        assert_eq!(mem.metadata.access_count, 5);
        assert_eq!(mem.metadata.recall_count, 3);
        assert_eq!(mem.metadata.version, 2);
        assert_eq!(mem.metadata.agent_id, "test-agent");
        assert!((mem.metadata.source_trust - 1.0).abs() < f32::EPSILON);
        assert_eq!(mem.metadata.content_hash, "abc123");
    }

    #[test]
    fn v2_to_v4_memory_empty_agent_id_defaults_to_system() {
        let v2 = V2Memory {
            id: "550e8400-e29b-41d4-a716-446655440000".to_string(),
            galaxy: "universal".to_string(),
            content: "test".to_string(),
            memory_type: "SHORT_TERM".to_string(),
            created_at: "2026-01-01T00:00:00Z".to_string(),
            accessed_at: "2026-01-01T00:00:00Z".to_string(),
            access_count: 0,
            emotional_valence: 0.0,
            importance: 0.5,
            neuro_score: 0.5,
            novelty_score: 1.0,
            recall_count: 0,
            half_life_days: 30.0,
            is_protected: false,
            is_private: false,
            model_exclude: false,
            content_hash: String::new(),
            source_trust: "user".to_string(),
            version: 1,
            agent_id: String::new(),
        };
        let mem = v2_to_v4_memory(&v2, &[], Galaxy::Universal);
        assert_eq!(mem.metadata.agent_id, "system");
        assert_ne!(
            mem.metadata.content_hash, "",
            "Empty hash should be computed"
        );
    }

    #[test]
    fn v2_to_v4_memory_negative_access_count_clamped() {
        let v2 = V2Memory {
            id: "550e8400-e29b-41d4-a716-446655440000".to_string(),
            galaxy: "universal".to_string(),
            content: "test".to_string(),
            memory_type: "SHORT_TERM".to_string(),
            created_at: "2026-01-01T00:00:00Z".to_string(),
            accessed_at: "2026-01-01T00:00:00Z".to_string(),
            access_count: -5,
            emotional_valence: 0.0,
            importance: 0.5,
            neuro_score: 0.5,
            novelty_score: 1.0,
            recall_count: -3,
            half_life_days: 30.0,
            is_protected: false,
            is_private: false,
            model_exclude: false,
            content_hash: String::new(),
            source_trust: "user".to_string(),
            version: 0,
            agent_id: String::new(),
        };
        let mem = v2_to_v4_memory(&v2, &[], Galaxy::Universal);
        assert_eq!(
            mem.metadata.access_count, 0,
            "Negative access_count should be clamped to 0"
        );
        assert_eq!(
            mem.metadata.recall_count, 0,
            "Negative recall_count should be clamped to 0"
        );
        assert_eq!(mem.metadata.version, 1, "Version 0 should be clamped to 1");
    }

    #[test]
    fn migrate_database_basic() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);

        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440000",
            "codex",
            "Rust memory",
            "LONG_TERM",
            "user",
        );
        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440001",
            "dreams",
            "Dream content",
            "NARRATIVE",
            "tool",
        );
        insert_tag(&conn, "550e8400-e29b-41d4-a716-446655440000", "rust");
        insert_tag(&conn, "550e8400-e29b-41d4-a716-446655440000", "memory");
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        let lmdb_path = store_dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb_path).unwrap();
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        let tantivy_path = lmdb_path.join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = SearchEngine::open(&tantivy_path).unwrap();

        let (read, written, skipped) =
            migrate_database(&db_path, &store, &search, None, false).unwrap();

        assert_eq!(read, 2);
        assert_eq!(written, 2);
        assert_eq!(skipped, 0);
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 1);
        assert_eq!(store.count(Galaxy::Dreams).unwrap(), 1);
    }

    #[test]
    fn migrate_database_skips_benchmark_galaxy() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);

        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440000",
            "benchmark",
            "bench data",
            "LONG_TERM",
            "user",
        );
        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440001",
            "codex",
            "real data",
            "LONG_TERM",
            "user",
        );
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        let lmdb_path = store_dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb_path).unwrap();
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        let tantivy_path = lmdb_path.join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = SearchEngine::open(&tantivy_path).unwrap();

        let (read, written, skipped) =
            migrate_database(&db_path, &store, &search, None, false).unwrap();

        assert_eq!(read, 2);
        assert_eq!(written, 1);
        assert_eq!(skipped, 1);
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 1);
    }

    #[test]
    fn migrate_database_dry_run_does_not_write() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);

        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440000",
            "codex",
            "test",
            "LONG_TERM",
            "user",
        );
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        let lmdb_path = store_dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb_path).unwrap();
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        let tantivy_path = lmdb_path.join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = SearchEngine::open(&tantivy_path).unwrap();

        let (read, written, skipped) =
            migrate_database(&db_path, &store, &search, None, true).unwrap();

        assert_eq!(read, 1);
        assert_eq!(written, 1, "Dry run should count what would be written");
        assert_eq!(skipped, 0);
        assert_eq!(
            store.count(Galaxy::Codex).unwrap(),
            0,
            "Dry run should not write anything"
        );
    }

    #[test]
    fn migrate_database_galaxy_override() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);

        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440000",
            "codex",
            "test",
            "LONG_TERM",
            "user",
        );
        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440001",
            "dreams",
            "test2",
            "LONG_TERM",
            "user",
        );
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        let lmdb_path = store_dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb_path).unwrap();
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        let tantivy_path = lmdb_path.join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = SearchEngine::open(&tantivy_path).unwrap();

        let (read, written, skipped) =
            migrate_database(&db_path, &store, &search, Some(Galaxy::Research), false).unwrap();

        assert_eq!(read, 2);
        assert_eq!(written, 2);
        assert_eq!(skipped, 0);
        assert_eq!(store.count(Galaxy::Research).unwrap(), 2);
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 0);
        assert_eq!(store.count(Galaxy::Dreams).unwrap(), 0);
    }

    #[test]
    fn migrate_database_with_tags() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);

        let mem_id = "550e8400-e29b-41d4-a716-446655440000";
        insert_v2_memory(
            &conn,
            mem_id,
            "codex",
            "tagged content",
            "LONG_TERM",
            "user",
        );
        insert_tag(&conn, mem_id, "rust");
        insert_tag(&conn, mem_id, "memory");
        insert_tag(&conn, mem_id, "migration");
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        let lmdb_path = store_dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb_path).unwrap();
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        let tantivy_path = lmdb_path.join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = SearchEngine::open(&tantivy_path).unwrap();

        let (read, written, skipped) =
            migrate_database(&db_path, &store, &search, None, false).unwrap();

        assert_eq!(read, 1);
        assert_eq!(written, 1);
        assert_eq!(skipped, 0);

        let memories = store.scan(Galaxy::Codex, 100).unwrap();
        assert_eq!(memories.len(), 1);
        assert_eq!(memories[0].metadata.tags.len(), 3);
        assert!(memories[0].metadata.tags.contains(&"rust".to_string()));
        assert!(memories[0].metadata.tags.contains(&"memory".to_string()));
        assert!(memories[0].metadata.tags.contains(&"migration".to_string()));
    }

    #[test]
    fn migrate_database_empty_db() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        let lmdb_path = store_dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb_path).unwrap();
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        let tantivy_path = lmdb_path.join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = SearchEngine::open(&tantivy_path).unwrap();

        let (read, written, skipped) =
            migrate_database(&db_path, &store, &search, None, false).unwrap();

        assert_eq!(read, 0);
        assert_eq!(written, 0);
        assert_eq!(skipped, 0);
    }

    #[test]
    fn discover_v2_databases_finds_dbs() {
        let tmp = TempDir::new().unwrap();
        let galaxies_dir = tmp.path().join("galaxies");

        let codex_dir = galaxies_dir.join("codex");
        std::fs::create_dir_all(&codex_dir).unwrap();
        std::fs::write(codex_dir.join("whitemagic.db"), b"dummy").unwrap();

        let dreams_dir = galaxies_dir.join("dreams");
        std::fs::create_dir_all(&dreams_dir).unwrap();
        std::fs::write(dreams_dir.join("whitemagic.db"), b"dummy").unwrap();

        let empty_dir = galaxies_dir.join("empty");
        std::fs::create_dir_all(&empty_dir).unwrap();

        let dbs = discover_v2_databases(&galaxies_dir).unwrap();
        assert_eq!(
            dbs.len(),
            2,
            "Should find 2 databases (empty dir has no db)"
        );
        assert!(dbs.iter().any(|p| p.to_string_lossy().contains("codex")));
        assert!(dbs.iter().any(|p| p.to_string_lossy().contains("dreams")));
    }

    #[test]
    fn discover_v2_databases_nonexistent_dir() {
        let dbs = discover_v2_databases(Path::new("/nonexistent/path")).unwrap();
        assert!(dbs.is_empty());
    }

    #[test]
    fn run_migration_single_db() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);
        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440000",
            "codex",
            "test",
            "LONG_TERM",
            "user",
        );
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        run_migration(None, Some(&db_path), store_dir.path(), false, None).unwrap();

        let lmdb_path = store_dir.path().join("lmdb");
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 1);
    }

    #[test]
    fn run_migration_dry_run() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);
        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440000",
            "codex",
            "test",
            "LONG_TERM",
            "user",
        );
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        run_migration(None, Some(&db_path), store_dir.path(), true, None).unwrap();

        let lmdb_path = store_dir.path().join("lmdb");
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        assert_eq!(
            store.count(Galaxy::Codex).unwrap(),
            0,
            "Dry run should not write"
        );
    }

    #[test]
    fn run_migration_galaxy_filter() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("whitemagic.db");
        let conn = create_v2_db(&db_path);
        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440000",
            "codex",
            "codex data",
            "LONG_TERM",
            "user",
        );
        insert_v2_memory(
            &conn,
            "550e8400-e29b-41d4-a716-446655440001",
            "dreams",
            "dream data",
            "LONG_TERM",
            "user",
        );
        drop(conn);

        let store_dir = TempDir::new().unwrap();
        run_migration(None, Some(&db_path), store_dir.path(), false, Some("codex")).unwrap();

        let lmdb_path = store_dir.path().join("lmdb");
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        assert_eq!(
            store.count(Galaxy::Codex).unwrap(),
            2,
            "Galaxy filter should override all memories to Codex"
        );
        assert_eq!(store.count(Galaxy::Dreams).unwrap(), 0);
    }

    #[test]
    fn run_migration_no_dbs_specified_errors() {
        let tmp = TempDir::new().unwrap();
        let result = run_migration(None, None, tmp.path(), false, None);
        assert!(result.is_err());
    }

    #[test]
    fn run_migration_multiple_galaxies() {
        let tmp = TempDir::new().unwrap();
        let galaxies_dir = tmp.path().join("galaxies");

        let codex_dir = galaxies_dir.join("codex");
        std::fs::create_dir_all(&codex_dir).unwrap();
        let conn1 = create_v2_db(&codex_dir.join("whitemagic.db"));
        insert_v2_memory(
            &conn1,
            "550e8400-e29b-41d4-a716-446655440000",
            "codex",
            "codex 1",
            "LONG_TERM",
            "user",
        );
        insert_v2_memory(
            &conn1,
            "550e8400-e29b-41d4-a716-446655440001",
            "codex",
            "codex 2",
            "LONG_TERM",
            "user",
        );
        drop(conn1);

        let dreams_dir = galaxies_dir.join("dreams");
        std::fs::create_dir_all(&dreams_dir).unwrap();
        let conn2 = create_v2_db(&dreams_dir.join("whitemagic.db"));
        insert_v2_memory(
            &conn2,
            "550e8400-e29b-41d4-a716-446655440002",
            "dreams",
            "dream 1",
            "NARRATIVE",
            "tool",
        );
        drop(conn2);

        let store_dir = TempDir::new().unwrap();
        run_migration(Some(&galaxies_dir), None, store_dir.path(), false, None).unwrap();

        let lmdb_path = store_dir.path().join("lmdb");
        let store = wm_memory::MemoryStore::open(&lmdb_path, 1024 * 1024).unwrap();
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 2);
        assert_eq!(store.count(Galaxy::Dreams).unwrap(), 1);
    }
}
