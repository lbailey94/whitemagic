use rusqlite::{Connection, params};
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};
use tar::Archive as TarArchive;
use zstd::stream::Decoder as ZstdDecoder;

use wm_gen3_core::hologram::quantize_coords_6d;

pub const DEFAULT_SHM_CACHE_DIR: &str = "/dev/shm/whitemagic_cold_cache";
pub const MAX_SHM_CACHE_BYTES: u64 = 1024 * 1024 * 1024; // 1,024 MB (1 GB)

#[derive(Debug, Clone)]
pub struct ColdArchiveInfo {
    pub archive_id: String,
    pub archive_name: String,
    pub path: PathBuf,
    pub format: String,
    pub size_bytes: u64,
}

#[derive(Debug, Clone)]
pub struct ColdCatalogEntry {
    pub entry_id: String,
    pub archive_id: String,
    pub path_in_archive: String,
    pub size_bytes: u64,
    pub mtime: i64,
    pub is_cognitive: bool,
    pub content_hash: String,
    pub coords_6d: [i64; 6],
}

#[derive(Debug, Clone)]
pub struct ColdSearchResult {
    pub entry_id: String,
    pub archive_id: String,
    pub path_in_archive: String,
    pub size_bytes: u64,
    pub score: f32,
    pub snippet: String,
    pub coords_6d: [i64; 6],
}

/// Zero-Disk-Extraction Cold Storage Catalog and Shm Cache Manager
pub struct ColdStorageEngine {
    catalog_conn: Mutex<Connection>,
    cache_dir: PathBuf,
}

impl ColdStorageEngine {
    /// Initialize or open the cold storage catalog database
    pub fn new<P: AsRef<Path>>(
        catalog_db_path: P,
        cache_dir: Option<PathBuf>,
    ) -> Result<Self, String> {
        let conn = Connection::open(catalog_db_path)
            .map_err(|e| format!("Failed to open cold catalog db: {e}"))?;

        conn.execute_batch(
            r#"
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            PRAGMA mmap_size = 268435456;

            CREATE TABLE IF NOT EXISTS cold_archives (
                archive_id TEXT PRIMARY KEY,
                archive_name TEXT NOT NULL,
                path TEXT NOT NULL,
                format TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                indexed_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cold_entries (
                entry_id TEXT PRIMARY KEY,
                archive_id TEXT NOT NULL,
                path_in_archive TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mtime INTEGER NOT NULL,
                is_cognitive INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                bin_x INTEGER NOT NULL,
                bin_y INTEGER NOT NULL,
                bin_z INTEGER NOT NULL,
                bin_tau INTEGER NOT NULL,
                bin_sigma INTEGER NOT NULL,
                bin_omega INTEGER NOT NULL,
                FOREIGN KEY(archive_id) REFERENCES cold_archives(archive_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_cold_archive ON cold_entries(archive_id);
            CREATE INDEX IF NOT EXISTS idx_cold_path ON cold_entries(path_in_archive);
            CREATE INDEX IF NOT EXISTS idx_cold_spatial ON cold_entries(bin_x, bin_y, bin_z);

            CREATE VIRTUAL TABLE IF NOT EXISTS cold_fts USING fts5(
                entry_id UNINDEXED,
                archive_id UNINDEXED,
                path_in_archive,
                content_text,
                tokenize='unicode61 remove_diacritics 2'
            );
            "#,
        )
        .map_err(|e| format!("Catalog schema init error: {e}"))?;

        let cache_path = cache_dir.unwrap_or_else(|| PathBuf::from(DEFAULT_SHM_CACHE_DIR));
        let _ = fs::create_dir_all(&cache_path);

        Ok(Self {
            catalog_conn: Mutex::new(conn),
            cache_dir: cache_path,
        })
    }

    /// Stream index a `.tar.zst` or `.tar` archive directly without extracting to NVMe disk
    pub fn index_archive_stream<P: AsRef<Path>>(
        &self,
        archive_path: P,
        max_entries: Option<usize>,
    ) -> Result<usize, String> {
        let path = archive_path.as_ref();
        if !path.exists() {
            return Err(format!("Archive path does not exist: {}", path.display()));
        }

        let archive_name = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown_archive")
            .to_string();

        let archive_id = format!("arc_{}", compute_fnv1a(archive_name.as_bytes()));
        let file_meta = fs::metadata(path).map_err(|e| format!("Failed to read metadata: {e}"))?;
        let size_bytes = file_meta.len();

        let is_zstd = archive_name.ends_with(".zst") || archive_name.ends_with(".tar.zst");
        let format = if is_zstd { "tar.zst" } else { "tar" };

        let now_sec = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0);

        let file = File::open(path).map_err(|e| format!("Failed to open archive file: {e}"))?;

        let mut conn = self
            .catalog_conn
            .lock()
            .map_err(|e| format!("Catalog lock failed: {e}"))?;

        conn.execute(
            r#"
            INSERT OR REPLACE INTO cold_archives (archive_id, archive_name, path, format, size_bytes, indexed_at)
            VALUES (?1, ?2, ?3, ?4, ?5, ?6)
            "#,
            params![archive_id, archive_name, path.display().to_string(), format, size_bytes as i64, now_sec],
        ).map_err(|e| format!("Insert archive record failed: {e}"))?;

        let count = if is_zstd {
            let decoder =
                ZstdDecoder::new(file).map_err(|e| format!("Zstd decoder init failed: {e}"))?;
            let mut tar = TarArchive::new(decoder);
            self.process_tar_entries(&mut tar, &archive_id, &mut conn, max_entries)?
        } else {
            let mut tar = TarArchive::new(file);
            self.process_tar_entries(&mut tar, &archive_id, &mut conn, max_entries)?
        };

        Ok(count)
    }

    fn process_tar_entries<R: Read>(
        &self,
        tar: &mut TarArchive<R>,
        archive_id: &str,
        conn: &mut Connection,
        max_entries: Option<usize>,
    ) -> Result<usize, String> {
        let entries = tar
            .entries()
            .map_err(|e| format!("Failed to read TAR entries: {e}"))?;

        let mut indexed_count = 0;
        let tx = conn.transaction().map_err(|e| format!("TX error: {e}"))?;

        {
            let mut entry_stmt = tx.prepare_cached(
                r#"
                INSERT OR REPLACE INTO cold_entries
                (entry_id, archive_id, path_in_archive, size_bytes, mtime, is_cognitive, content_hash,
                 bin_x, bin_y, bin_z, bin_tau, bin_sigma, bin_omega)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)
                "#,
            ).map_err(|e| format!("Prepare entry stmt failed: {e}"))?;

            let mut fts_stmt = tx
                .prepare_cached(
                    r#"
                INSERT INTO cold_fts (entry_id, archive_id, path_in_archive, content_text)
                VALUES (?1, ?2, ?3, ?4)
                "#,
                )
                .map_err(|e| format!("Prepare fts stmt failed: {e}"))?;

            for entry_res in entries {
                if let Some(limit) = max_entries {
                    if indexed_count >= limit {
                        break;
                    }
                }

                let mut entry = match entry_res {
                    Ok(e) => e,
                    Err(_) => continue, // Skip corrupt headers gracefully
                };

                let header = entry.header();
                let entry_type = header.entry_type();
                if !entry_type.is_file() {
                    continue;
                }

                let path_str = match entry.path() {
                    Ok(p) => p.display().to_string(),
                    Err(_) => continue,
                };

                let size = entry.size();
                let mtime = header.mtime().unwrap_or(0) as i64;
                let is_cognitive = is_cognitive_file(&path_str, size);

                let mut content_text: Option<String> = None;
                let content_hash: String;
                let coords: [i64; 6];

                if is_cognitive && size <= 1024 * 1024 {
                    // Read text in memory strictly (NEVER write to NVMe!)
                    let mut buf = Vec::with_capacity(size as usize);
                    if entry.read_to_end(&mut buf).is_ok() {
                        let hash_bytes = Sha256::digest(&buf);
                        content_hash = format!("{:x}", hash_bytes);
                        coords = compute_6d_coords(&hash_bytes, mtime, &path_str);
                        if let Ok(text) = String::from_utf8(buf) {
                            content_text = Some(text);
                        }
                    } else {
                        content_hash = format!("{:x}", Sha256::digest(path_str.as_bytes()));
                        coords = compute_6d_coords(
                            &Sha256::digest(path_str.as_bytes()),
                            mtime,
                            &path_str,
                        );
                    }
                } else {
                    // Binary or bulk payload: derive coordinate from path + size + mtime
                    let mut hasher = Sha256::new();
                    hasher.update(path_str.as_bytes());
                    hasher.update(size.to_le_bytes());
                    let hash_bytes = hasher.finalize();
                    content_hash = format!("{:x}", hash_bytes);
                    coords = compute_6d_coords(&hash_bytes, mtime, &path_str);
                }

                let entry_id = format!("{}_{}", archive_id, compute_fnv1a(path_str.as_bytes()));

                entry_stmt
                    .execute(params![
                        entry_id,
                        archive_id,
                        path_str,
                        size as i64,
                        mtime,
                        if is_cognitive { 1 } else { 0 },
                        content_hash,
                        coords[0],
                        coords[1],
                        coords[2],
                        coords[3],
                        coords[4],
                        coords[5],
                    ])
                    .map_err(|e| format!("Execute entry insert: {e}"))?;

                if let Some(ref text) = content_text {
                    let preview = crate::safe_truncate(text, 8000);
                    let _ = fts_stmt.execute(params![entry_id, archive_id, path_str, preview]);
                }

                indexed_count += 1;
            }
        }

        tx.commit().map_err(|e| format!("Commit failed: {e}"))?;
        Ok(indexed_count)
    }

    /// Search cold catalog using FTS5 cognitive text match
    pub fn search_cognitive_text(
        &self,
        query: &str,
        limit: usize,
    ) -> Result<Vec<ColdSearchResult>, String> {
        let conn = self
            .catalog_conn
            .lock()
            .map_err(|e| format!("Catalog lock failed: {e}"))?;

        let sanitized: String = query
            .chars()
            .filter(|c| c.is_alphanumeric() || c.is_whitespace())
            .collect();
        let terms: Vec<&str> = sanitized.split_whitespace().collect();
        if terms.is_empty() {
            return Ok(Vec::new());
        }
        let fts_query = terms.join(" OR ");

        let mut stmt = conn
            .prepare_cached(
                r#"
            SELECT c.entry_id, c.archive_id, c.path_in_archive, c.size_bytes,
                   f.rank, snippet(cold_fts, 3, '[', ']', '...', 16),
                   c.bin_x, c.bin_y, c.bin_z, c.bin_tau, c.bin_sigma, c.bin_omega
            FROM cold_fts f
            JOIN cold_entries c ON c.entry_id = f.entry_id
            WHERE cold_fts MATCH ?1
            ORDER BY f.rank
            LIMIT ?2
            "#,
            )
            .map_err(|e| format!("Prepare cold search failed: {e}"))?;

        let rows = stmt
            .query_map(params![fts_query, limit as i64], |row| {
                let entry_id: String = row.get(0)?;
                let archive_id: String = row.get(1)?;
                let path_in_archive: String = row.get(2)?;
                let size_bytes: i64 = row.get(3)?;
                let rank: f64 = row.get(4)?;
                let snippet: String = row.get(5)?;
                let coords = [
                    row.get(6)?,
                    row.get(7)?,
                    row.get(8)?,
                    row.get(9)?,
                    row.get(10)?,
                    row.get(11)?,
                ];

                Ok(ColdSearchResult {
                    entry_id,
                    archive_id,
                    path_in_archive,
                    size_bytes: size_bytes as u64,
                    score: (-rank) as f32,
                    snippet,
                    coords_6d: coords,
                })
            })
            .map_err(|e| format!("Query cold search failed: {e}"))?;

        let mut out = Vec::new();
        for r in rows {
            out.push(r.map_err(|e| format!("Row error: {e}"))?);
        }
        Ok(out)
    }

    /// Read an entry from /dev/shm LRU cache or extract on-demand into RAM
    pub fn fetch_payload<P: AsRef<Path>>(
        &self,
        archive_path: P,
        path_in_archive: &str,
    ) -> Result<Vec<u8>, String> {
        let cache_key = format!("{:x}", Sha256::digest(path_in_archive.as_bytes()));
        let cached_file = self.cache_dir.join(&cache_key);

        // 1. Check /dev/shm LRU cache (< 0.02ms hit!)
        if cached_file.exists() {
            if let Ok(bytes) = fs::read(&cached_file) {
                return Ok(bytes);
            }
        }

        // 2. Cache miss: stream decompressed archive until matching entry is found
        let path = archive_path.as_ref();
        let file = File::open(path).map_err(|e| format!("Failed to open archive: {e}"))?;

        let is_zstd = path.to_string_lossy().ends_with(".zst");
        let mut target_bytes = None;

        if is_zstd {
            let decoder =
                ZstdDecoder::new(file).map_err(|e| format!("Zstd decoder init failed: {e}"))?;
            let mut tar = TarArchive::new(decoder);
            for mut entry in tar
                .entries()
                .map_err(|e| format!("Tar error: {e}"))?
                .flatten()
            {
                if let Ok(p) = entry.path() {
                    if p.display().to_string() == path_in_archive {
                        let mut buf = Vec::new();
                        entry
                            .read_to_end(&mut buf)
                            .map_err(|e| format!("Read entry: {e}"))?;
                        target_bytes = Some(buf);
                        break;
                    }
                }
            }
        } else {
            let mut tar = TarArchive::new(file);
            for mut entry in tar
                .entries()
                .map_err(|e| format!("Tar error: {e}"))?
                .flatten()
            {
                if let Ok(p) = entry.path() {
                    if p.display().to_string() == path_in_archive {
                        let mut buf = Vec::new();
                        entry
                            .read_to_end(&mut buf)
                            .map_err(|e| format!("Read entry: {e}"))?;
                        target_bytes = Some(buf);
                        break;
                    }
                }
            }
        }

        let bytes = target_bytes.ok_or_else(|| {
            format!(
                "Path '{path_in_archive}' not found in archive {}",
                path.display()
            )
        })?;

        // 3. Write into /dev/shm LRU cache (RAM tmpfs, never touches host NVMe!)
        self.enforce_shm_cache_limits();
        let _ = fs::write(&cached_file, &bytes);

        Ok(bytes)
    }

    /// Enforce LRU eviction if /dev/shm cache exceeds quota
    fn enforce_shm_cache_limits(&self) {
        let entries = match fs::read_dir(&self.cache_dir) {
            Ok(iter) => iter,
            Err(_) => return,
        };

        let mut files: Vec<(PathBuf, u64, SystemTime)> = Vec::new();
        let mut total_size: u64 = 0;

        for entry in entries.flatten() {
            if let Ok(meta) = entry.metadata() {
                if meta.is_file() {
                    let size = meta.len();
                    let mtime = meta.modified().unwrap_or(UNIX_EPOCH);
                    total_size += size;
                    files.push((entry.path(), size, mtime));
                }
            }
        }

        if total_size > MAX_SHM_CACHE_BYTES {
            // Sort by mtime ascending (oldest first)
            files.sort_by_key(|f| f.2);
            for (path, size, _) in files {
                let _ = fs::remove_file(path);
                total_size = total_size.saturating_sub(size);
                if total_size < (MAX_SHM_CACHE_BYTES * 3 / 4) {
                    break;
                }
            }
        }
    }
}

fn is_cognitive_file(path: &str, size: u64) -> bool {
    if size > 1024 * 1024 {
        return false;
    }
    let lower = path.to_lowercase();
    lower.ends_with(".md")
        || lower.ends_with(".txt")
        || lower.ends_with(".json")
        || lower.ends_with(".rs")
        || lower.ends_with(".py")
        || lower.ends_with(".toml")
        || lower.ends_with(".yaml")
        || lower.ends_with(".yml")
        || lower.ends_with(".sh")
}

fn compute_6d_coords(hash_bytes: &[u8], mtime: i64, path: &str) -> [i64; 6] {
    // 1. Spatial coordinates x, y, z derived from hash bytes
    let b0 = hash_bytes[0] as f64 / 255.0;
    let b1 = hash_bytes[1] as f64 / 255.0;
    let b2 = hash_bytes[2] as f64 / 255.0;

    let x = (b0 - 0.5) * 200.0;
    let y = (b1 - 0.5) * 200.0;
    let z = (b2 - 0.5) * 200.0;

    // 2. Temporal dimension tau normalized relative to WhiteMagic epoch (2025-10-01)
    let epoch_2025_10_01 = 1759276800i64;
    let tau = ((mtime - epoch_2025_10_01) as f64) / 86400.0; // days since epoch

    // 3. Epistemic Salience sigma
    let lower = path.to_lowercase();
    let sigma =
        if lower.contains("receipt") || lower.contains("covenant") || lower.contains("charter") {
            0.98
        } else if lower.ends_with(".rs") || lower.ends_with(".md") {
            0.85
        } else if lower.ends_with(".json") || lower.ends_with(".toml") {
            0.75
        } else {
            0.50
        };

    // 4. Harmonic cluster omega (28 Ganas / Lunar Mansions)
    let omega = (hash_bytes[3] % 28) as f64;

    quantize_coords_6d([x, y, z, tau, sigma, omega])
}

fn compute_fnv1a(bytes: &[u8]) -> u64 {
    let mut hash: u64 = 0xcbf29ce484222325;
    for &b in bytes {
        hash ^= b as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}
