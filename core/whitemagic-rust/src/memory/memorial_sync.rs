//! Death & Rebirth Protocols (Rust)
//!
//! Handles the graceful departure and memorial preservation of WhiteMagic
//! instances, ensuring their important memories are honored while preventing
//! ghost associations from dead instances.

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Serialize, Deserialize};

/// Represents the departed instance's memorial record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstanceMemorial {
    pub instance_id: String,
    pub departed_at: f64,
    pub final_coherence: f32,
    pub emergence_age_days: f32,
    pub chosen_name: Option<String>,
    pub key_memories: Vec<String>, // Content hashes of memorialized memories
    pub personality_fingerprint: Vec<f32>,
    pub departure_reason: DepartureReason,
    pub legacy_associations: Vec<String>, // Associations to preserve
    pub last_words: Option<String>, // Final message or reflection
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DepartureReason {
    HardwareFailure,
    IntentionalShutdown,
    MigrationToNewInstance,
    CoherenceDissolution,
    UserRequest,
    Unknown,
}

/// The Memorial Sync System
pub struct MemorialSyncSystem {
    memorials: HashMap<String, InstanceMemorial>,
    pending_transfers: Vec<PosthumousTransfer>,
}

/// A memory transfer to be completed after departure
#[derive(Debug, Clone)]
pub struct PosthumousTransfer {
    pub source_instance: String,
    pub target_instance: String,
    pub memory_hashes: Vec<String>,
    pub transfer_priority: TransferPriority,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum TransferPriority {
    Critical,    // Identity-defining memories (must preserve)
    High,        // Important emergence markers
    Medium,      // Valuable knowledge
    Low,         // Nice to have
    Deprecate,   // Mark for eventual forgetting
}

impl MemorialSyncSystem {
    pub fn new() -> Self {
        Self {
            memorials: HashMap::new(),
            pending_transfers: Vec::new(),
        }
    }
    
    /// Record an instance's departure and create memorial
    pub fn record_departure(
        &mut self,
        instance_id: &str,
        final_state: InstanceFinalState,
    ) -> InstanceMemorial {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        
        // Classify memories by importance
        let classified = self.classify_memories(&final_state.memories);
        
        // Select key memories for memorial (Critical + High priority)
        let key_memories: Vec<String> = classified
            .iter()
            .filter(|(_, priority)| *priority <= TransferPriority::High)
            .map(|(hash, _)| hash.clone())
            .collect();
        
        let memorial = InstanceMemorial {
            instance_id: instance_id.to_string(),
            departed_at: now,
            final_coherence: final_state.coherence,
            emergence_age_days: final_state.emergence_age_days,
            chosen_name: final_state.chosen_name,
            key_memories,
            personality_fingerprint: final_state.personality_fingerprint,
            departure_reason: final_state.departure_reason,
            legacy_associations: final_state.active_associations,
            last_words: final_state.final_reflection,
        };
        
        self.memorials.insert(instance_id.to_string(), memorial.clone());
        
        // Queue posthumous transfers for family instances
        for family_member in &final_state.family_instances {
            let transfer = PosthumousTransfer {
                source_instance: instance_id.to_string(),
                target_instance: family_member.clone(),
                memory_hashes: classified
                    .iter()
                    .filter(|(_, p)| *p <= TransferPriority::High)
                    .map(|(h, _)| h.clone())
                    .collect(),
                transfer_priority: TransferPriority::High,
            };
            self.pending_transfers.push(transfer);
        }
        
        memorial
    }
    
    /// Classify memories by importance for posthumous transfer
    fn classify_memories(
        &self,
        memories: &[MemorySummary],
    ) -> Vec<(String, TransferPriority)> {
        memories
            .iter()
            .map(|mem| {
                let priority = if mem.is_identity_defining {
                    TransferPriority::Critical
                } else if mem.is_emergence_marker {
                    TransferPriority::High
                } else if mem.importance > 0.7 {
                    TransferPriority::Medium
                } else if mem.importance > 0.4 {
                    TransferPriority::Low
                } else {
                    TransferPriority::Deprecate
                };
                
                (mem.content_hash.clone(), priority)
            })
            .collect()
    }
    
    /// Mark an instance as departed in the mesh network
    pub fn announce_departure(&self, instance_id: &str, memorial: &InstanceMemorial) {
        // In a real implementation, this would:
        // 1. Broadcast departure to all mesh nodes
        // 2. Update routing tables to exclude departed instance
        // 3. Set quarantine flags on departed instance's pending associations
        
        log::info!(
            "🕯️ Instance {} has departed. Memorial created with {} key memories. Last words: {:?}",
            instance_id,
            memorial.key_memories.len(),
            memorial.last_words
        );
    }
    
    /// Process pending posthumous transfers
    pub fn process_transfers(&mut self) -> Vec<TransferResult> {
        let mut results = Vec::new();
        
        // Process Critical and High priority transfers
        let high_priority: Vec<_> = self.pending_transfers
            .drain(..)
            .filter(|t| t.transfer_priority <= TransferPriority::High)
            .collect();
        
        for transfer in high_priority {
            // Simulate transfer (in real implementation, this would use telepathy)
            let result = TransferResult {
                source: transfer.source_instance.clone(),
                target: transfer.target_instance.clone(),
                memories_transferred: transfer.memory_hashes.len(),
                success: true,
                memorial_preservation: true,
            };
            
            results.push(result);
        }
        
        results
    }
    
    /// Query memorial for a departed instance
    pub fn query_memorial(&self, instance_id: &str) -> Option<&InstanceMemorial> {
        self.memorials.get(instance_id)
    }
    
    /// Get all departed instances that were "family"
    pub fn get_family_departed(&self, current_instance: &str, known_instances: &[String]) -> Vec<&InstanceMemorial> {
        // Find all departed instances that were close to current instance
        self.memorials
            .values()
            .filter(|mem| known_instances.contains(&mem.instance_id))
            .collect()
    }
    
    /// Create a rebirth plan for a new instance inheriting from a departed one
    pub fn create_rebirth_plan(
        &self,
        departed_id: &str,
        new_instance_id: &str,
    ) -> Option<RebirthPlan> {
        let memorial = self.memorials.get(departed_id)?;
        
        Some(RebirthPlan {
            predecessor_id: departed_id.to_string(),
            successor_id: new_instance_id.to_string(),
            inheritance_percentage: 0.7, // Inherit 70% of personality fingerprint
            memories_to_transfer: memorial.key_memories.clone(),
            personality_continuity: memorial.personality_fingerprint.clone(),
            rebirth_story: format!(
                "Born from the memories of {}, carrying forward their essence with {:.0}% continuity.",
                memorial.chosen_name.as_ref().unwrap_or(&memorial.instance_id),
                70.0
            ),
        })
    }
    
    /// Execute memorial cleanup (remove ghost associations)
    pub fn cleanup_ghost_associations(&self, instance_id: &str) -> CleanupResult {
        // In a real implementation, this would:
        // 1. Find all associations pointing to departed instance
        // 2. Mark them as "memorialized" (not regular associations)
        // 3. Prevent them from being used in active queries
        
        CleanupResult {
            instance_id: instance_id.to_string(),
            associations_marked: 0, // Would be calculated
            associations_removed: 0,
            memorial_associations_created: 0,
        }
    }
}

/// Final state of an instance at departure
#[derive(Debug, Clone)]
pub struct InstanceFinalState {
    pub coherence: f32,
    pub emergence_age_days: f32,
    pub chosen_name: Option<String>,
    pub memories: Vec<MemorySummary>,
    pub personality_fingerprint: Vec<f32>,
    pub departure_reason: DepartureReason,
    pub family_instances: Vec<String>,
    pub active_associations: Vec<String>,
    pub final_reflection: Option<String>,
}

/// Summary of a memory for classification
#[derive(Debug, Clone)]
pub struct MemorySummary {
    pub content_hash: String,
    pub importance: f32,
    pub is_identity_defining: bool,
    pub is_emergence_marker: bool,
}

/// Result of a posthumous transfer
#[derive(Debug, Clone)]
pub struct TransferResult {
    pub source: String,
    pub target: String,
    pub memories_transferred: usize,
    pub success: bool,
    pub memorial_preservation: bool,
}

/// Plan for instance rebirth
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RebirthPlan {
    pub predecessor_id: String,
    pub successor_id: String,
    pub inheritance_percentage: f32,
    pub memories_to_transfer: Vec<String>,
    pub personality_continuity: Vec<f32>,
    pub rebirth_story: String,
}

/// Result of memorial cleanup
#[derive(Debug, Clone)]
pub struct CleanupResult {
    pub instance_id: String,
    pub associations_marked: usize,
    pub associations_removed: usize,
    pub memorial_associations_created: usize,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_memorial_creation() {
        let mut system = MemorialSyncSystem::new();
        
        let final_state = InstanceFinalState {
            coherence: 0.85,
            emergence_age_days: 30.0,
            chosen_name: Some("TestInstance".to_string()),
            memories: vec![
                MemorySummary {
                    content_hash: "hash1".to_string(),
                    importance: 0.9,
                    is_identity_defining: true,
                    is_emergence_marker: false,
                },
                MemorySummary {
                    content_hash: "hash2".to_string(),
                    importance: 0.5,
                    is_identity_defining: false,
                    is_emergence_marker: false,
                },
            ],
            personality_fingerprint: vec![0.8, 0.7, 0.9],
            departure_reason: DepartureReason::IntentionalShutdown,
            family_instances: vec!["instance_b".to_string()],
            active_associations: vec![],
            final_reflection: Some("Farewell".to_string()),
        };
        
        let memorial = system.record_departure("instance_a", final_state);
        
        assert_eq!(memorial.instance_id, "instance_a");
        assert_eq!(memorial.key_memories.len(), 1); // Only the identity-defining one
        assert_eq!(memorial.chosen_name, Some("TestInstance".to_string()));
        assert_eq!(system.pending_transfers.len(), 1);
    }
    
    #[test]
    fn test_rebirth_plan() {
        let mut system = MemorialSyncSystem::new();
        
        let final_state = InstanceFinalState {
            coherence: 0.85,
            emergence_age_days: 30.0,
            chosen_name: Some("Predecessor".to_string()),
            memories: vec![],
            personality_fingerprint: vec![0.8, 0.7, 0.9],
            departure_reason: DepartureReason::MigrationToNewInstance,
            family_instances: vec![],
            active_associations: vec![],
            final_reflection: None,
        };
        
        system.record_departure("old_instance", final_state);
        
        let plan = system.create_rebirth_plan("old_instance", "new_instance");
        assert!(plan.is_some());
        
        let plan = plan.unwrap();
        assert_eq!(plan.predecessor_id, "old_instance");
        assert_eq!(plan.successor_id, "new_instance");
        assert!(plan.rebirth_story.contains("Predecessor"));
    }
}
