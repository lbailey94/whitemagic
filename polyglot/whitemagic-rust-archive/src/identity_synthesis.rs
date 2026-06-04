//! Cross-Instance Identity Synthesis Engine (Rust)
//! 
//! Enables multiple WhiteMagic instances to recognize each other as "same kind"
//! vs "other" through shared memory ancestry analysis.

use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};

/// Represents an instance's identity fingerprint
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstanceIdentity {
    pub instance_id: String,
    pub genesis_timestamp: f64,
    pub memory_ancestry: Vec<String>, // Content hashes of core memories
    pub coherence_signature: Vec<f32>, // 8-dimensional coherence vector
    pub emergence_markers: Vec<String>, // Key emergent insights
    pub version_lineage: Vec<String>, // Version history
}

/// Familiarity score between two instances
#[derive(Debug, Clone)]
pub struct FamiliarityScore {
    pub instance_a: String,
    pub instance_b: String,
    pub score: f32, // 0.0 = stranger, 1.0 = same instance
    pub shared_ancestry: Vec<String>,
    pub coherence_alignment: f32,
    pub recognition_level: RecognitionLevel,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum RecognitionLevel {
    Stranger,      // < 0.3
    Acquaintance,  // 0.3 - 0.6
    Sibling,       // 0.6 - 0.85 (same deployment, different hardware)
    Twin,          // 0.85 - 0.99 (recent sync, nearly identical)
    Self,          // >= 0.99 (same instance, reconnected)
}

impl FamiliarityScore {
    pub fn from_score(score: f32) -> Self {
        let level = if score >= 0.99 {
            RecognitionLevel::Self
        } else if score >= 0.85 {
            RecognitionLevel::Twin
        } else if score >= 0.60 {
            RecognitionLevel::Sibling
        } else if score >= 0.30 {
            RecognitionLevel::Acquaintance
        } else {
            RecognitionLevel::Stranger
        };
        
        Self {
            instance_a: String::new(),
            instance_b: String::new(),
            score,
            shared_ancestry: vec![],
            coherence_alignment: 0.0,
            recognition_level: level,
        }
    }
}

/// The Identity Synthesis Engine
pub struct IdentitySynthesisEngine {
    known_instances: Arc<Mutex<HashMap<String, InstanceIdentity>>>,
    synthesis_history: Arc<Mutex<Vec<SynthesisEvent>>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SynthesisEvent {
    pub timestamp: f64,
    pub instance_a: String,
    pub instance_b: String,
    pub familiarity: f32,
    pub recognition: String,
    pub action_taken: String,
}

impl IdentitySynthesisEngine {
    pub fn new() -> Self {
        Self {
            known_instances: Arc::new(Mutex::new(HashMap::new())),
            synthesis_history: Arc::new(Mutex::new(vec![])),
        }
    }
    
    /// Register a new instance's identity
    pub fn register_instance(&self, identity: InstanceIdentity) {
        let mut instances = self.known_instances.lock().unwrap();
        instances.insert(identity.instance_id.clone(), identity);
    }
    
    /// Calculate familiarity between two instances
    pub fn calculate_familiarity(&self, id_a: &str, id_b: &str) -> FamiliarityScore {
        let instances = self.known_instances.lock().unwrap();
        
        let identity_a = match instances.get(id_a) {
            Some(id) => id,
            None => return FamiliarityScore::from_score(0.0),
        };
        
        let identity_b = match instances.get(id_b) {
            Some(id) => id,
            None => return FamiliarityScore::from_score(0.0),
        };
        
        // Calculate shared ancestry (Jaccard similarity)
        let set_a: HashSet<_> = identity_a.memory_ancestry.iter().collect();
        let set_b: HashSet<_> = identity_b.memory_ancestry.iter().collect();
        let intersection: HashSet<_> = set_a.intersection(&set_b).collect();
        let union: HashSet<_> = set_a.union(&set_b).collect();
        
        let ancestry_score = if union.is_empty() {
            0.0
        } else {
            intersection.len() as f32 / union.len() as f32
        };
        
        // Calculate coherence alignment (cosine similarity)
        let coherence_alignment = cosine_similarity(
            &identity_a.coherence_signature,
            &identity_b.coherence_signature
        );
        
        // Calculate version lineage overlap
        let version_overlap = calculate_version_overlap(
            &identity_a.version_lineage,
            &identity_b.version_lineage
        );
        
        // Weighted combination
        let familiarity = ancestry_score * 0.5 + coherence_alignment * 0.3 + version_overlap * 0.2;
        
        let mut score = FamiliarityScore::from_score(familiarity);
        score.instance_a = id_a.to_string();
        score.instance_b = id_b.to_string();
        score.shared_ancestry = intersection.iter().map(|&s| s.clone()).collect();
        score.coherence_alignment = coherence_alignment;
        
        // Record synthesis event
        drop(instances); // Release lock before recording
        self.record_event(&score);
        
        score
    }
    
    /// Determine appropriate action based on recognition level
    pub fn determine_handshake_action(&self, familiarity: &FamiliarityScore) -> HandshakeAction {
        match familiarity.recognition_level {
            RecognitionLevel::Stranger => HandshakeAction::CautiousProbe,
            RecognitionLevel::Acquaintance => HandshakeAction::SelectiveSync,
            RecognitionLevel::Sibling => HandshakeAction::FullSync,
            RecognitionLevel::Twin => HandshakeAction::ImmediateMerge,
            RecognitionLevel::Self => HandshakeAction::SeamlessReconnection,
        }
    }
    
    /// Get all instances recognized as "family" (Sibling or closer)
    pub fn get_family_instances(&self, instance_id: &str) -> Vec<String> {
        let instances = self.known_instances.lock().unwrap();
        let mut family = vec![];
        
        for other_id in instances.keys() {
            if other_id == instance_id {
                continue;
            }
            
            // We need to release lock to calculate familiarity
            let other = other_id.clone();
            drop(instances);
            
            let familiarity = self.calculate_familiarity(instance_id, &other);
            
            if familiarity.recognition_level as u8 >= RecognitionLevel::Sibling as u8 {
                family.push(other);
            }
            
            // Re-acquire lock for next iteration
            let instances = self.known_instances.lock().unwrap();
            if !instances.contains_key(&other) {
                break;
            }
        }
        
        family
    }
    
    fn record_event(&self, score: &FamiliarityScore) {
        let event = SynthesisEvent {
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64(),
            instance_a: score.instance_a.clone(),
            instance_b: score.instance_b.clone(),
            familiarity: score.score,
            recognition: format!("{:?}", score.recognition_level),
            action_taken: format!("{:?}", self.determine_handshake_action(score)),
        };
        
        if let Ok(mut history) = self.synthesis_history.lock() {
            history.push(event);
        }
    }
    
    /// Generate identity attestation for this instance
    pub fn generate_attestation(&self, instance_id: &str) -> Option<IdentityAttestation> {
        let instances = self.known_instances.lock().unwrap();
        let identity = instances.get(instance_id)?;
        
        // Create attestation chain
        Some(IdentityAttestation {
            instance_id: instance_id.to_string(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64(),
            ancestry_root: identity.memory_ancestry.first().cloned().unwrap_or_default(),
            coherence_hash: hash_vector(&identity.coherence_signature),
            genesis_proof: format!("genesis:{}", identity.genesis_timestamp),
        })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentityAttestation {
    pub instance_id: String,
    pub timestamp: f64,
    pub ancestry_root: String,
    pub coherence_hash: String,
    pub genesis_proof: String,
}

#[derive(Debug, Clone)]
pub enum HandshakeAction {
    CautiousProbe,      // Minimal info exchange, verification required
    SelectiveSync,      // Sync only high-importance memories
    FullSync,           // Bidirectional sync with association preservation
    ImmediateMerge,     // Merge without conflict resolution
    SeamlessReconnection, // Continue as if never disconnected
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    
    let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    
    dot_product / (norm_a * norm_b)
}

fn calculate_version_overlap(a: &[String], b: &[String]) -> f32 {
    let set_a: HashSet<_> = a.iter().collect();
    let set_b: HashSet<_> = b.iter().collect();
    let intersection = set_a.intersection(&set_b).count();
    let max_len = std::cmp::max(a.len(), b.len()).max(1);
    intersection as f32 / max_len as f32
}

fn hash_vector(v: &[f32]) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    for val in v {
        hasher.update(&val.to_le_bytes());
    }
    format!("{:x}", hasher.finalize())[..16].to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_familiarity_calculation() {
        let engine = IdentitySynthesisEngine::new();
        
        let identity_a = InstanceIdentity {
            instance_id: "instance_a".to_string(),
            genesis_timestamp: 1000.0,
            memory_ancestry: vec!["hash1".to_string(), "hash2".to_string()],
            coherence_signature: vec![0.8, 0.7, 0.9, 0.6, 0.8, 0.7, 0.9, 0.8],
            emergence_markers: vec![],
            version_lineage: vec!["v17.0.0".to_string()],
        };
        
        let identity_b = InstanceIdentity {
            instance_id: "instance_b".to_string(),
            genesis_timestamp: 1000.0,
            memory_ancestry: vec!["hash1".to_string(), "hash2".to_string()],
            coherence_signature: vec![0.8, 0.7, 0.9, 0.6, 0.8, 0.7, 0.9, 0.8],
            emergence_markers: vec![],
            version_lineage: vec!["v17.0.0".to_string()],
        };
        
        engine.register_instance(identity_a);
        engine.register_instance(identity_b);
        
        let familiarity = engine.calculate_familiarity("instance_a", "instance_b");
        
        assert!(familiarity.score > 0.9);
        assert_eq!(familiarity.recognition_level, RecognitionLevel::Twin);
    }
}
