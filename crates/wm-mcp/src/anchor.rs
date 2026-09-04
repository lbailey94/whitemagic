//! Record-attestation anchoring (Track F Slice A, D5).
//!
//! [`anchor_report`] sweeps the store's `attestations` DBI, grades every
//! entry, and Merkle-anchors the validly-signed set. [`append_anchor_log`]
//! appends the report to a chained external JSONL log (the persistence —
//! place it somewhere versioned for out-of-band verifiability).
//!
//! Anchor rule: every validly-signed attestation commits a leaf — valid +
//! stale + missing-memory alike. Staleness is lifecycle (content updated
//! after creation; updates ride the revisions chain), not forgery; only a
//! bad signature excludes a leaf. Callers must treat `invalid > 0` as loud
//! tamper evidence (the CLI exits non-zero).

use serde_json::{Value, json};
use wm_core::CoreError;
use wm_memory::MemoryStore;

/// Sweep + anchor the store's record attestations.
///
/// Returns the report object, which doubles as the external-log record shape:
/// `{tool, v, root, leaf_count, attested, valid, stale, missing, invalid,
/// timestamp}`.
pub fn anchor_report(store: &MemoryStore) -> wm_core::Result<Value> {
    let sweep = store.attestation_sweep().map_err(|e| {
        // A sweep failure must never become an empty anchor: a root over
        // zero leaves would read as "nothing attested" instead of "store
        // unreadable".
        CoreError::Memory(format!("attestation sweep failed: {e}"))
    })?;
    let mut valid = 0u64;
    let mut stale = 0u64;
    let mut missing = 0u64;
    let mut invalid = 0u64;
    // (galaxy, memory_id, leaf) — sorted before hashing for determinism.
    let mut leaves: Vec<(String, String, String)> = Vec::new();
    for (att, report) in &sweep {
        if !report.signature_valid {
            invalid += 1;
            continue;
        }
        if !report.memory_present {
            missing += 1;
        } else if !report.matches_head {
            stale += 1;
        } else {
            valid += 1;
        }
        leaves.push((
            att.galaxy.clone(),
            att.memory_id.clone(),
            wm_memory::anchor_leaf_input(&att.record_hash, &att.signature_hex),
        ));
    }
    leaves.sort();
    let leaf_hashes: Vec<String> = leaves.into_iter().map(|(_, _, h)| h).collect();
    Ok(json!({
        "tool": "wm-anchor",
        "v": 1,
        "root": wm_memory::merkle_root_hex(&leaf_hashes),
        "leaf_count": leaf_hashes.len(),
        "attested": sweep.len(),
        "valid": valid,
        "stale": stale,
        "missing": missing,
        "invalid": invalid,
        "timestamp": wm_core::time::now_unix_secs(),
    }))
}

/// Append a chained anchor record to an external JSONL log.
///
/// Each record carries `prev_hash` — the SHA-256 of the previous line — so
/// the log is itself a tamper-evident chain (same pattern as karma.anchor's
/// publish_path).
pub fn append_anchor_log(path: &std::path::Path, report: &Value) -> wm_core::Result<()> {
    use sha2::{Digest, Sha256};
    use std::io::Write;
    let prev_hash = std::fs::read_to_string(path)
        .ok()
        .and_then(|contents| {
            contents
                .lines()
                .last()
                .map(|line| format!("{:x}", Sha256::digest(line.as_bytes())))
        })
        .unwrap_or_else(|| "genesis".to_string());
    let mut entry = report.clone();
    entry["prev_hash"] = Value::String(prev_hash);
    let mut line = serde_json::to_string(&entry)
        .map_err(|e| CoreError::Memory(format!("anchor log serialize failed: {e}")))?;
    line.push('\n');
    std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .and_then(|mut f| f.write_all(line.as_bytes()))
        .map_err(|e| CoreError::Memory(format!("anchor log append failed: {e}")))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::Galaxy;
    use wm_memory::{Memory, attestation_payload, sign_attestation};

    const TEST_KEY: &str = "0bd1c44170ca3d916648a983dcdb8583d22f2da5b29fdd5ede4b38e805435577";

    fn test_store() -> MemoryStore {
        let dir = tempfile::tempdir().unwrap();
        MemoryStore::open_default(dir.path()).unwrap()
    }

    fn attest(store: &MemoryStore, galaxy: Galaxy, content: &str, agent: &str) -> uuid::Uuid {
        let memory = Memory::new(galaxy, content.to_string());
        store.put(galaxy, &memory).unwrap();
        let id = memory.metadata.id;
        let ts = wm_core::time::now_unix_secs();
        let payload = attestation_payload(
            galaxy.db_name(),
            &id.to_string(),
            &memory.metadata.content_hash,
            agent,
            ts,
        );
        let (pk, sig) = sign_attestation(&payload, TEST_KEY).unwrap();
        store
            .record_attestation(
                galaxy,
                id,
                &wm_memory::RecordAttestation {
                    domain: wm_memory::ATTESTATION_DOMAIN.to_string(),
                    galaxy: galaxy.db_name().to_string(),
                    memory_id: id.to_string(),
                    record_hash: memory.metadata.content_hash,
                    agent_id: agent.to_string(),
                    timestamp: ts,
                    public_key_hex: pk,
                    signature_hex: sig,
                },
            )
            .unwrap();
        id
    }

    #[test]
    fn anchor_over_valid_set() {
        let store = test_store();
        attest(&store, Galaxy::Codex, "alpha memory", "ses-1");
        attest(&store, Galaxy::Research, "beta memory", "ses-1");
        let report = anchor_report(&store).unwrap();
        assert_eq!(report["attested"], 2);
        assert_eq!(report["valid"], 2);
        assert_eq!(report["leaf_count"], 2);
        assert_eq!(report["invalid"], 0);
        assert_eq!(report["root"].as_str().unwrap().len(), 64);
        // Deterministic across runs.
        let again = anchor_report(&store).unwrap();
        assert_eq!(report["root"], again["root"]);
    }

    #[test]
    fn anchor_counts_stale_missing_and_invalid() {
        let store = test_store();
        let stale_id = attest(&store, Galaxy::Codex, "will be edited", "ses-1");
        let missing_id = attest(&store, Galaxy::Codex, "will be deleted", "ses-1");
        attest(&store, Galaxy::Codex, "stays valid", "ses-1");

        // Stale: rewrite content out from under the attestation.
        let mut memory = store.get(Galaxy::Codex, stale_id).unwrap().unwrap();
        memory.content = "edited".to_string();
        memory.metadata.content_hash = wm_memory::content_hash(&memory.content);
        store.put(Galaxy::Codex, &memory).unwrap();
        // Missing: delete the memory outright.
        assert!(store.delete(Galaxy::Codex, missing_id).unwrap());

        let report = anchor_report(&store).unwrap();
        assert_eq!(report["attested"], 3);
        assert_eq!(report["valid"], 1);
        assert_eq!(report["stale"], 1);
        assert_eq!(report["missing"], 1);
        assert_eq!(report["invalid"], 0);
        // Valid-sig stale + missing rows still commit leaves.
        assert_eq!(report["leaf_count"], 3);

        // Invalid: forge one signature in place.
        let mut forged = store.attestation(Galaxy::Codex, stale_id).unwrap().unwrap();
        forged.signature_hex = "00".repeat(64);
        store
            .record_attestation(Galaxy::Codex, stale_id, &forged)
            .unwrap();
        let report = anchor_report(&store).unwrap();
        assert_eq!(report["invalid"], 1);
        assert_eq!(report["leaf_count"], 2);
    }

    #[test]
    fn anchor_empty_store_is_honest_empty() {
        let store = test_store();
        let report = anchor_report(&store).unwrap();
        assert_eq!(report["attested"], 0);
        assert_eq!(report["leaf_count"], 0);
        assert_eq!(
            report["root"],
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn anchor_log_chains() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("anchors.jsonl");
        let store = test_store();
        attest(&store, Galaxy::Codex, "logged memory", "ses-1");
        let first = anchor_report(&store).unwrap();
        append_anchor_log(&path, &first).unwrap();
        let lines: Vec<String> = std::fs::read_to_string(&path)
            .unwrap()
            .lines()
            .map(str::to_string)
            .collect();
        assert_eq!(lines.len(), 1);
        let entry: Value = serde_json::from_str(&lines[0]).unwrap();
        assert_eq!(entry["prev_hash"], "genesis");

        attest(&store, Galaxy::Codex, "second memory", "ses-1");
        let second = anchor_report(&store).unwrap();
        append_anchor_log(&path, &second).unwrap();
        let lines: Vec<String> = std::fs::read_to_string(&path)
            .unwrap()
            .lines()
            .map(str::to_string)
            .collect();
        assert_eq!(lines.len(), 2);
        let entry: Value = serde_json::from_str(&lines[1]).unwrap();
        assert_ne!(entry["prev_hash"], "genesis");
        // prev_hash is the sha256 of the previous line.
        use sha2::{Digest, Sha256};
        assert_eq!(
            entry["prev_hash"],
            format!("{:x}", Sha256::digest(lines[0].as_bytes()))
        );
    }
}
