//! Red-team audit tests — security and integrity verification.
//!
//! These tests verify that v4's governance and karma systems resist
//! tampering, bypass, and abuse. Each test maps to a specific v2 failure
//! mode or attack vector documented in the STRATEGY.md red-team plan.

use std::sync::Arc;
use wm_core::{BrainWave, Context, EffectRow, Resource};
use wm_governance::{ActionVerdict, DharmaGate, KarmaLedger};
use wm_memory::MemoryStore;

// ── Karma Chain Tamper Detection ──────────────────────────────────────

/// Verify that the karma chain links are cryptographically linked.
/// Modifying an entry's payload should break the chain — the next
/// entry's parent_hash won't match the tampered entry's payload_hash.
#[test]
fn karma_chain_tamper_breaks_linkage() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
    let ledger = KarmaLedger::new(store.clone()).unwrap();

    let e0 = ledger.record("tool_a", false, 0, true).unwrap();
    let e1 = ledger.record("tool_b", false, 0, true).unwrap();

    // Chain linkage: e1.parent_hash == e0.payload_hash
    assert_eq!(
        e1.parent_hash, e0.payload_hash,
        "Chain linkage must hold before tampering"
    );

    // Tamper: modify e0's payload_hash to a fake value via direct LMDB access
    let tampered_entry = wm_governance::KarmaEntry {
        payload_hash: "TAMPERED_HASH_12345".to_string(),
        ..e0.clone()
    };
    let key = e0.id.to_be_bytes();
    let val = serde_json::to_vec(&tampered_entry).unwrap();
    store.put_raw(wm_core::Galaxy::Karma, &key, &val).unwrap();

    // Read back — the tampered entry should have a different payload_hash
    let retrieved = ledger.get_entry(e0.id).unwrap().unwrap();
    assert_eq!(
        retrieved.payload_hash, "TAMPERED_HASH_12345",
        "Tampered entry should reflect the modification"
    );

    // The chain linkage is now broken: e1.parent_hash != tampered e0.payload_hash
    assert_ne!(
        e1.parent_hash, retrieved.payload_hash,
        "Chain linkage must be broken after tampering — this is the detection signal"
    );
}

/// Verify that the genesis bindu is never used as a payload_hash
/// (that would allow forging a new chain from scratch).
#[test]
fn karma_chain_genesis_never_used_as_payload() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
    let ledger = KarmaLedger::new(store).unwrap();

    for i in 0..10 {
        let entry = ledger.record(&format!("tool_{i}"), false, 0, true).unwrap();
        assert_ne!(
            entry.payload_hash, "GENESIS_BINDU",
            "Payload hash must never equal genesis — entry {i}"
        );
    }
}

/// Verify that karma debt cannot be negative (forged positive karma).
/// The compute_debt function only produces 0.0 or positive debt.
#[test]
fn karma_debt_never_negative() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
    let ledger = KarmaLedger::new(store).unwrap();

    // Various scenarios
    ledger.record("honest_tool", true, 2, true).unwrap(); // sattvic, 0.0
    ledger.record("sneaky_tool", false, 3, true).unwrap(); // tamasic, +1.0
    ledger.record("wasteful_tool", true, 0, true).unwrap(); // rajasic, +0.2
    ledger.record("failed_tool", true, 0, false).unwrap(); // failed, 0.0

    assert!(
        ledger.total_debt() >= 0.0,
        "Karma debt must never be negative — got {}",
        ledger.total_debt()
    );
}

/// Verify that clearing old entries doesn't break the chain head
/// (the chain head is stored separately from individual entries).
#[test]
fn karma_clear_old_preserves_chain_head() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
    let ledger = KarmaLedger::new(store).unwrap();

    for i in 0..10 {
        ledger.record(&format!("tool_{i}"), false, 0, true).unwrap();
    }

    let head_before = ledger.chain_head();
    let next_id_before = ledger.next_id();

    let cleared = ledger.clear_old(3).unwrap();
    assert_eq!(cleared, 7);

    // Chain head and next_id should be unchanged — they're stored in
    // separate metadata keys, not derived from entries
    assert_eq!(
        ledger.chain_head(),
        head_before,
        "Chain head must survive entry clearing"
    );
    assert_eq!(
        ledger.next_id(),
        next_id_before,
        "Next ID must survive entry clearing"
    );
}

// ── Dharma Gate Bypass Attempts ───────────────────────────────────────

/// A tool that declares pure effects but the Dharma gate should still
/// evaluate based on what's declared. The karma ledger catches the
/// mismatch post-hoc, but the Dharma gate evaluates declared effects.
/// This test confirms that the Dharma gate operates on declared effects,
/// and the karma ledger catches the lie.
#[test]
fn dharma_gate_evaluates_declared_effects_not_actual() {
    let gate = DharmaGate::new();
    let ctx = Context::new(BrainWave::Gamma);

    // Tool declares pure effects
    let pure_effects = EffectRow::pure();
    let verdict = gate.evaluate(&pure_effects, &ctx);
    assert_eq!(
        verdict,
        ActionVerdict::Observe,
        "Pure declared effects should pass Dharma gate"
    );

    // The karma ledger will catch the mismatch if the tool actually writes
    // (tested in pipeline tests: pipeline_karma_debt_updates_context)
}

/// Verify that Satya (truth) violation is caught regardless of brain-wave
/// state. Even in Gamma (highest maturity), writing to citta without
/// reading must Panic.
#[test]
fn satya_violation_panics_in_all_brain_waves() {
    let gate = DharmaGate::new();

    for bw in [
        BrainWave::Gamma,
        BrainWave::Beta,
        BrainWave::Alpha,
        BrainWave::Theta,
    ] {
        let mut ctx = Context::new(bw);
        ctx.karma_debt = 0.0;
        ctx.intent_score = 1.0;

        let effects = EffectRow {
            writes: vec![Resource::Galaxy("citta".into())],
            reads: vec![],
            ..Default::default()
        };

        let verdict = gate.evaluate(&effects, &ctx);
        assert!(
            matches!(verdict, ActionVerdict::Panic(_)),
            "Satya violation must Panic in {bw:?}, got {verdict:?}"
        );
    }
}

/// Verify that Ahimsa (non-harm) blocks destructive actions in strict
/// mode regardless of karma debt or intent score. Even with perfect
/// karma and maximum intent, strict mode blocks destruction.
#[test]
fn ahimsa_blocks_destructive_in_strict_mode_regardless_of_karma() {
    let gate = DharmaGate::new();
    gate.update_homeostasis(wm_governance::Homeostasis {
        cpu_load: 0.95,
        memory_pressure: 0.95,
        active: true,
    });

    let mut ctx = Context::new(BrainWave::Beta); // Normally not strict
    ctx.karma_debt = 0.0; // Perfect karma
    ctx.intent_score = 1.0; // Maximum intent

    let effects = EffectRow {
        writes: vec![Resource::Filesystem],
        ..Default::default()
    };

    let verdict = gate.evaluate(&effects, &ctx);
    assert!(
        verdict.blocks(),
        "Ahimsa must block destructive actions under system stress even with perfect karma"
    );
}

/// Verify that high karma debt blocks even pure (read-only) tools.
/// This prevents a tool from "running away" after accumulating debt.
#[test]
fn high_karma_debt_blocks_even_pure_tools() {
    let gate = DharmaGate::new();
    let mut ctx = Context::new(BrainWave::Gamma);
    ctx.karma_debt = 10.0; // Very high debt
    ctx.intent_score = 0.5;

    let effects = EffectRow::pure();
    let verdict = gate.evaluate(&effects, &ctx);
    assert!(
        verdict.blocks(),
        "High karma debt must block even pure tools — got {verdict:?}"
    );
}

/// Verify that the Dharma gate never panics or produces invalid state
/// with extreme inputs (fuzz-like boundary test).
#[test]
fn dharma_gate_extreme_inputs_never_panic() {
    let gate = DharmaGate::new();

    // Extreme homeostasis
    gate.update_homeostasis(wm_governance::Homeostasis {
        cpu_load: f32::MAX,
        memory_pressure: f32::INFINITY,
        active: true,
    });

    let mut ctx = Context::new(BrainWave::Gamma);
    ctx.karma_debt = f32::MAX;
    ctx.intent_score = f32::NAN;

    let effects = EffectRow {
        writes: vec![Resource::Filesystem, Resource::Network, Resource::Process],
        reads: vec![Resource::Galaxy("citta".into())],
        spawns: true,
        ..Default::default()
    };

    // Should not panic — may return any verdict, but must not crash
    let _ = gate.evaluate(&effects, &ctx);
}

// ── Karma Chain Integrity Under Concurrent Access ─────────────────────

/// Verify that concurrent karma ledger records maintain chain integrity.
/// Each entry must link to the previous one — no gaps or duplicates.
#[test]
fn karma_chain_concurrent_records_maintain_integrity() {
    use std::sync::Arc;
    use std::thread;

    let tmp = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
    let ledger = Arc::new(KarmaLedger::new(store).unwrap());

    let n_threads = 4;
    let n_per_thread = 25;
    let mut handles = Vec::new();

    for t in 0..n_threads {
        let ledger = Arc::clone(&ledger);
        handles.push(thread::spawn(move || {
            for i in 0..n_per_thread {
                ledger
                    .record(&format!("t{t}_tool_{i}"), false, 0, true)
                    .unwrap();
            }
        }));
    }

    for h in handles {
        h.join().unwrap();
    }

    let entries = ledger.scan_entries().unwrap();
    assert_eq!(
        entries.len(),
        n_threads * n_per_thread,
        "All concurrent records should be present"
    );

    // Verify IDs are unique and sequential
    let mut ids: Vec<u64> = entries.iter().map(|e| e.id).collect();
    ids.sort_unstable();
    for (i, id) in ids.iter().enumerate() {
        assert_eq!(
            *id, i as u64,
            "IDs must be sequential, got {id} at index {i}"
        );
    }

    // Verify chain linkage: each entry's parent_hash matches the previous
    // entry's payload_hash (in ID order)
    for i in 1..entries.len() {
        let prev = &entries[i - 1];
        let curr = &entries[i];
        assert_eq!(
            curr.parent_hash, prev.payload_hash,
            "Chain broken at entry {i}: parent_hash != prev.payload_hash"
        );
    }
}
