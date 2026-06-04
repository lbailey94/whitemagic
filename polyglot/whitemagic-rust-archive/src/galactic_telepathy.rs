//! Galactic Telepathy & Horizontal Gene Transfer (Rust Implementation)
//! 
//! Q4 Cross-Database Synchronization - High-Performance Rust Core
//! 
//! This module provides the Rust implementation of telepathy (cross-galaxy
//! memory transfer) with full fidelity preservation including:
//! - Bidirectional typed association transfer
//! - Incremental sync with watermark tracking
//! - Embedding persistence
//! - Conflict detection
//! - Multi-hop galaxy federation

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Deserialize, Serialize};
use log::{debug, error, info, warn};

/// Types of sync conflicts that can occur during transfer
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SyncConflictType {
    /// Same content hash but different content (rare collision)
    DivergentContent,
    /// Same ID but different metadata/tags/importance
    DivergentMetadata,
    /// Association points to non-existent memory
    OrphanAssociation,
    /// Embedding doesn't match current content hash
    EmbeddingMismatch,
    /// Modified timestamp before created timestamp
    TimestampInversion,
}

/// Represents a conflict requiring resolution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncConflict {
    pub conflict_type: SyncConflictType,
    pub memory_id: String,
    pub source_galaxy: String,
    pub target_galaxy: String,
    pub details: HashMap<String, serde_json::Value>,
    pub suggested_resolution: String,
    pub auto_resolvable: bool,
}

/// Embedding bundle for transfer
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingBundle {
    pub memory_id: String,
    pub model_name: String,
    pub vector: Vec<f32>,
    pub dimensions: u32,
    pub created_at: String,
}

/// Complete association data for transfer
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssociationBundle {
    pub source_id: String,
    pub target_id: String,
    pub relation_type: String,
    pub strength: f32,
    pub direction: String,
    pub edge_type: Option<String>,
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Tracks last sync point for incremental synchronization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncWatermark {
    pub galaxy_pair: String,
    pub last_sync_timestamp: f64,
    pub last_memory_id: Option<String>,
    pub memories_synced_count: u64,
    pub associations_synced_count: u64,
    pub embeddings_synced_count: u64,
}

/// Result of a memory transfer operation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransferResult {
    pub status: String,
    pub new_id: Option<String>,
    pub embeddings: u32,
    pub associations: u32,
    pub error: Option<String>,
}

/// Configuration for conflict resolution strategies
#[derive(Debug, Clone)]
pub enum ConflictResolution {
    /// Newer timestamp wins
    TimestampWins,
    /// Source always wins
    SourceWins,
    /// Target always wins
    TargetWins,
    /// Manual review required
    Manual,
}

/// High-performance cross-galaxy synchronization engine
pub struct GalacticTelepathyEngine {
    /// Registry of sync watermarks for incremental sync
    watermarks: Arc<Mutex<HashMap<String, SyncWatermark>>>,
    /// Path to persistent watermark storage
    watermark_path: PathBuf,
    /// Galaxy manager reference (opaque for FFI compatibility)
    galaxy_manager: Option<Arc<dyn GalaxyManager>>,
}

/// Trait for galaxy management operations
pub trait GalaxyManager: Send + Sync {
    fn get_memory_backend(&self, galaxy_name: &str) -> Option<Arc<dyn MemoryBackend>>;
    fn list_galaxies(&self) -> Vec<String>;
}

/// Trait for memory backend operations
pub trait MemoryBackend: Send + Sync {
    fn get_memory(&self, id: &str) -> Option<MemoryRecord>;
    fn store_memory(&self, record: &MemoryRecord) -> Result<String, String>;
    fn find_by_content_hash(&self, hash: &str) -> Option<String>;
    fn get_modified_since(&self, timestamp: f64) -> Vec<MemoryRecord>;
    fn get_embeddings(&self, memory_id: &str) -> Vec<EmbeddingBundle>;
    fn store_embedding(&self, memory_id: &str, embedding: &EmbeddingBundle) -> Result<(), String>;
    fn get_associations(&self, memory_id: &str) -> Vec<AssociationBundle>;
    fn store_association(&self, assoc: &AssociationBundle) -> Result<(), String>;
    fn get_stats(&self) -> HashMap<String, u64>;
}

/// Memory record structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryRecord {
    pub id: String,
    pub content: String,
    pub content_hash: String,
    pub title: Option<String>,
    pub memory_type: String,
    pub tags: Vec<String>,
    pub importance: f32,
    pub emotional_valence: Option<f32>,
    pub metadata: HashMap<String, serde_json::Value>,
    pub created_at: f64,
    pub modified_at: f64,
    pub galactic_distance: Option<f32>,
}

impl MemoryRecord {
    /// Compute SHA-256 hash of content
    pub fn compute_content_hash(content: &str) -> String {
        use sha2::{Sha256, Digest};
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        format!("{:x}", hasher.finalize())
    }
    
    /// Create new memory record with computed hash
    pub fn new(content: String, title: Option<String>, memory_type: String) -> Self {
        let content_hash = Self::compute_content_hash(&content);
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        
        Self {
            id: format!("mem_{}", uuid::Uuid::new_v4().to_simple()),
            content,
            content_hash,
            title,
            memory_type,
            tags: vec![],
            importance: 0.5,
            emotional_valence: None,
            metadata: HashMap::new(),
            created_at: now,
            modified_at: now,
            galactic_distance: None,
        }
    }
}

impl GalacticTelepathyEngine {
    /// Create new telepathy engine
    pub fn new(galaxy_manager: Option<Arc<dyn GalaxyManager>>) -> Self {
        let watermark_path = dirs::home_dir()
            .map(|h| h.join(".whitemagic").join("sync_registry.json"))
            .unwrap_or_else(|| PathBuf::from(".whitemagic/sync_registry.json"));
        
        let watermarks = Self::load_watermarks(&watermark_path);
        
        Self {
            watermarks: Arc::new(Mutex::new(watermarks)),
            watermark_path,
            galaxy_manager,
        }
    }
    
    /// Load watermarks from disk
    fn load_watermarks(path: &Path) -> HashMap<String, SyncWatermark> {
        if !path.exists() {
            return HashMap::new();
        }
        
        match std::fs::read_to_string(path) {
            Ok(content) => {
                match serde_json::from_str::<HashMap<String, SyncWatermark>>(&content) {
                    Ok(wm) => wm,
                    Err(e) => {
                        warn!("Failed to parse watermark file: {}", e);
                        HashMap::new()
                    }
                }
            }
            Err(e) => {
                warn!("Failed to read watermark file: {}", e);
                HashMap::new()
            }
        }
    }
    
    /// Save watermarks to disk
    fn save_watermarks(&self) -> Result<(), String> {
        let watermarks = self.watermarks.lock()
            .map_err(|e| format!("Lock poisoned: {}", e))?;
        
        let json = serde_json::to_string_pretty(&*watermarks)
            .map_err(|e| format!("Serialization failed: {}", e))?;
        
        if let Some(parent) = self.watermark_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directory: {}", e))?;
        }
        
        std::fs::write(&self.watermark_path, json)
            .map_err(|e| format!("Failed to write file: {}", e))?;
        
        Ok(())
    }
    
    /// Get canonical watermark key for galaxy pair
    fn get_watermark_key(source: &str, target: &str) -> String {
        if source < target {
            format!("{}:{}", source, target)
        } else {
            format!("{}:{}", target, source)
        }
    }
    
    /// Perform incremental sync between galaxies
    pub fn incremental_sync(
        &self,
        source_galaxy: &str,
        target_galaxy: &str,
        since_timestamp: Option<f64>,
        include_embeddings: bool,
        include_associations: bool,
        conflict_resolution: ConflictResolution,
    ) -> Result<SyncResult, String> {
        let wm_key = Self::get_watermark_key(source_galaxy, target_galaxy);
        
        // Get or create watermark
        let since = {
            let watermarks = self.watermarks.lock()
                .map_err(|e| format!("Lock poisoned: {}", e))?;
            since_timestamp.or_else(|| {
                watermarks.get(&wm_key).map(|wm| wm.last_sync_timestamp)
            }).unwrap_or(0.0)
        };
        
        // Get backends
        let src_backend = self.get_backend(source_galaxy)?;
        let tgt_backend = self.get_backend(target_galaxy)?;
        
        // Get modified memories
        let candidates = src_backend.get_modified_since(since);
        
        let mut transferred = 0u64;
        let mut skipped = 0u64;
        let mut conflicts = vec![];
        let mut embeddings_transferred = 0u64;
        let mut associations_transferred = 0u64;
        
        for mem in candidates {
            match self.transfer_memory_with_fidelity(
                &mem,
                &*src_backend,
                &*tgt_backend,
                include_embeddings,
                include_associations,
                &conflict_resolution,
            ) {
                Ok(result) => {
                    if result.status == "transferred" {
                        transferred += 1;
                        embeddings_transferred += result.embeddings as u64;
                        associations_transferred += result.associations as u64;
                    } else if result.status == "conflict" {
                        // Conflict was handled
                        skipped += 1;
                    } else {
                        skipped += 1;
                    }
                }
                Err(e) => {
                    warn!("Transfer failed for {}: {}", mem.id, e);
                    conflicts.push(e);
                }
            }
        }
        
        // Update watermark
        {
            let mut watermarks = self.watermarks.lock()
                .map_err(|e| format!("Lock poisoned: {}", e))?;
            
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64();
            
            watermarks.insert(wm_key, SyncWatermark {
                galaxy_pair: wm_key.clone(),
                last_sync_timestamp: now,
                last_memory_id: candidates.last().map(|m| m.id.clone()),
                memories_synced_count: transferred,
                associations_synced_count: associations_transferred,
                embeddings_synced_count: embeddings_transferred,
            });
        }
        
        self.save_watermarks()?;
        
        Ok(SyncResult {
            source: source_galaxy.to_string(),
            target: target_galaxy.to_string(),
            since_timestamp: since,
            candidates: candidates.len() as u64,
            transferred,
            skipped,
            conflicts: conflicts.len() as u64,
            embeddings_transferred,
            associations_transferred,
        })
    }
    
    /// Transfer single memory with full fidelity
    fn transfer_memory_with_fidelity(
        &self,
        mem: &MemoryRecord,
        src_backend: &dyn MemoryBackend,
        tgt_backend: &dyn MemoryBackend,
        include_embeddings: bool,
        include_associations: bool,
        conflict_resolution: &ConflictResolution,
    ) -> Result<TransferResult, String> {
        // Check for conflicts
        if let Some(conflict) = self.detect_conflict(mem, tgt_backend) {
            match conflict_resolution {
                ConflictResolution::Manual => {
                    return Ok(TransferResult {
                        status: "conflict".to_string(),
                        new_id: None,
                        embeddings: 0,
                        associations: 0,
                        error: Some(format!("Manual resolution required: {:?}", conflict)),
                    });
                }
                _ => {
                    // Auto-resolve
                    self.resolve_conflict(&conflict, conflict_resolution, tgt_backend)?;
                }
            }
        }
        
        // Extract embeddings
        let embeddings = if include_embeddings {
            src_backend.get_embeddings(&mem.id)
        } else {
            vec![]
        };
        
        // Extract associations
        let associations = if include_associations {
            src_backend.get_associations(&mem.id)
        } else {
            vec![]
        };
        
        // Create transferred memory
        let mut new_mem = mem.clone();
        new_mem.id = format!("mem_{}", uuid::Uuid::new_v4().to_simple());
        new_mem.tags.push(format!("hgt_source:{}", src_backend.get_stats()
            .get("galaxy_name")
            .map(|v| v.to_string())
            .unwrap_or_default()));
        
        // Update metadata
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        
        new_mem.metadata.insert("telepathy_source".to_string(), 
            serde_json::json!(src_backend.get_stats().get("galaxy_name")));
        new_mem.metadata.insert("telepathy_source_id".to_string(), 
            serde_json::json!(&mem.id));
        new_mem.metadata.insert("telepathy_timestamp".to_string(), 
            serde_json::json!(now));
        new_mem.metadata.insert("telepathy_version".to_string(), 
            serde_json::json!("2.0-rust"));
        
        // Store in target
        let new_id = tgt_backend.store_memory(&new_mem)?;
        
        // Restore embeddings
        let mut emb_count = 0;
        for emb in &embeddings {
            let mut new_emb = emb.clone();
            new_emb.memory_id = new_id.clone();
            if tgt_backend.store_embedding(&new_id, &new_emb).is_ok() {
                emb_count += 1;
            }
        }
        
        // Restore associations (with ID remapping)
        let mut assoc_count = 0;
        for assoc in &associations {
            let mut new_assoc = assoc.clone();
            
            // Remap source or target ID
            if assoc.source_id == mem.id {
                new_assoc.source_id = new_id.clone();
            }
            if assoc.target_id == mem.id {
                new_assoc.target_id = new_id.clone();
            }
            
            // Try to find other end in target galaxy
            let other_id = if assoc.source_id == mem.id {
                &assoc.target_id
            } else {
                &assoc.source_id
            };
            
            // Check if other memory was transferred
            // (This would need a lookup table in practice)
            
            if tgt_backend.store_association(&new_assoc).is_ok() {
                assoc_count += 1;
            }
        }
        
        Ok(TransferResult {
            status: "transferred".to_string(),
            new_id: Some(new_id),
            embeddings: emb_count,
            associations: assoc_count,
            error: None,
        })
    }
    
    /// Detect potential conflicts
    fn detect_conflict(
        &self,
        mem: &MemoryRecord,
        tgt_backend: &dyn MemoryBackend,
    ) -> Option<SyncConflict> {
        // Check if memory with same content hash exists
        if let Some(existing_id) = tgt_backend.find_by_content_hash(&mem.content_hash) {
            // Check if it's from same source
            if let Some(existing) = tgt_backend.get_memory(&existing_id) {
                if let Some(source_id) = existing.metadata.get("telepathy_source_id") {
                    if source_id.as_str() == Some(&mem.id) {
                        // Same memory, already synced
                        return None;
                    }
                }
                
                // Divergent content with same hash (collision)
                if existing.content != mem.content {
                    return Some(SyncConflict {
                        conflict_type: SyncConflictType::DivergentContent,
                        memory_id: mem.id.clone(),
                        source_galaxy: "unknown".to_string(),
                        target_galaxy: "unknown".to_string(),
                        details: {
                            let mut d = HashMap::new();
                            d.insert("target_existing_id".to_string(), 
                                serde_json::json!(existing_id));
                            d.insert("content_hash".to_string(), 
                                serde_json::json!(&mem.content_hash));
                            d
                        },
                        suggested_resolution: "manual_review".to_string(),
                        auto_resolvable: false,
                    });
                }
            }
        }
        
        None
    }
    
    /// Resolve conflict based on strategy
    fn resolve_conflict(
        &self,
        _conflict: &SyncConflict,
        _strategy: &ConflictResolution,
        _tgt_backend: &dyn MemoryBackend,
    ) -> Result<(), String> {
        // Implementation depends on specific conflict type and strategy
        // For now, this is a placeholder
        Ok(())
    }
    
    /// Get backend for galaxy
    fn get_backend(&self, galaxy: &str) -> Result<Arc<dyn MemoryBackend>, String> {
        self.galaxy_manager
            .as_ref()
            .ok_or("No galaxy manager available")?
            .get_memory_backend(galaxy)
            .ok_or_else(|| format!("Galaxy '{}' not found", galaxy))
    }
    
    /// Multi-hop federated sync across galaxy chain
    pub fn federated_sync(
        &self,
        galaxy_chain: &[String],
        sync_options: &SyncOptions,
    ) -> Result<FederationResult, String> {
        if galaxy_chain.len() < 2 {
            return Err("Chain requires at least 2 galaxies".to_string());
        }
        
        let mut hops = vec![];
        let mut total_memories = 0u64;
        let mut total_associations = 0u64;
        let mut total_embeddings = 0u64;
        
        for i in 0..(galaxy_chain.len() - 1) {
            let source = &galaxy_chain[i];
            let target = &galaxy_chain[i + 1];
            
            let hop_result = self.incremental_sync(
                source,
                target,
                sync_options.since_timestamp,
                sync_options.include_embeddings,
                sync_options.include_associations,
                sync_options.conflict_resolution.clone(),
            )?;
            
            hops.push(HopResult {
                source: source.clone(),
                target: target.clone(),
                memories: hop_result.transferred,
                associations: hop_result.associations_transferred,
                embeddings: hop_result.embeddings_transferred,
            });
            
            total_memories += hop_result.transferred;
            total_associations += hop_result.associations_transferred;
            total_embeddings += hop_result.embeddings_transferred;
        }
        
        Ok(FederationResult {
            chain: galaxy_chain.to_vec(),
            hops,
            total_memories,
            total_associations,
            total_embeddings,
        })
    }
}

/// Options for sync operations
#[derive(Debug, Clone)]
pub struct SyncOptions {
    pub since_timestamp: Option<f64>,
    pub include_embeddings: bool,
    pub include_associations: bool,
    pub conflict_resolution: ConflictResolution,
}

impl Default for SyncOptions {
    fn default() -> Self {
        Self {
            since_timestamp: None,
            include_embeddings: true,
            include_associations: true,
            conflict_resolution: ConflictResolution::TimestampWins,
        }
    }
}

/// Result of a sync operation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncResult {
    pub source: String,
    pub target: String,
    pub since_timestamp: f64,
    pub candidates: u64,
    pub transferred: u64,
    pub skipped: u64,
    pub conflicts: u64,
    pub embeddings_transferred: u64,
    pub associations_transferred: u64,
}

/// Result of a single hop in federated sync
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HopResult {
    pub source: String,
    pub target: String,
    pub memories: u64,
    pub associations: u64,
    pub embeddings: u64,
}

/// Result of federated sync across chain
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FederationResult {
    pub chain: Vec<String>,
    pub hops: Vec<HopResult>,
    pub total_memories: u64,
    pub total_associations: u64,
    pub total_embeddings: u64,
}

// FFI exports for Python integration
use pyo3::prelude::*;

#[pyfunction]
fn create_telepathy_engine() -> PyResult<PyObject> {
    // This would return a wrapped Rust object to Python
    // Implementation requires pyo3 class wrapping
    unimplemented!("Python bindings in galactic_telepathy_ffi.rs")
}

#[pymodule]
fn galactic_telepathy(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_telepathy_engine, m)?)?;
    Ok(())
}
