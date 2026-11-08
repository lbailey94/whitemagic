//! Acceptance test battery Gate PEB-20: Cross-Agent Collective Dreaming (Sangha Swarm Sleep Synthesis).
//!
//! Validates:
//! 1. Cross-Agent Bridging: Associative graph diffusion creates bridge relations between disparate agents.
//! 2. Contradiction Resolution: Deprecates stale/contradicted lessons when later corrections invalidate them.
//! 3. Collective Gem Distillation & Idempotence: Distills shared Gem invariants without duplicate bloat.

#![forbid(unsafe_code)]

use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::ops::SessionCheckpoint;
use wm_gen3_core::pulse::make_temp_substrate;

#[test]
fn peb20_1_cross_agent_bridging() {
    let (mut substrate, _s, _j) = make_temp_substrate("gate20_bridging");
    substrate.set_intake_authority(RatifiedChannel::mint("test-gate20"));

    // Checkpoint 1 from agent:antigravity (MCP architecture lane)
    let cp_antigravity = SessionCheckpoint {
        session_id: "antigravity-mcp-lane".into(),
        agent_id: "antigravity".into(),
        checkpoint_type: "milestone".into(),
        summary: "Engineered single-binary MCP stdio server with sub-25ms cold-start handshake."
            .into(),
        next_queue: vec!["Audit security boundary".into()],
        open_flags: vec!["mcp_ready".into()],
        lessons: vec!["Fast stdio transport removes multi-agent communication friction.".into()],
        identity_invariants: vec!["Deterministic local execution over cloud telemetry.".into()],
        ..Default::default()
    };
    let rec_anti = substrate.session_checkpoint(&cp_antigravity).unwrap();

    // Checkpoint 2 from agent:sol (Security & kernel sandbox lane)
    let cp_sol = SessionCheckpoint {
        session_id: "sol-security-lane".into(),
        agent_id: "sol".into(),
        checkpoint_type: "milestone".into(),
        summary:
            "Implemented Linux Landlock LSM file system confinement and system call filtering."
                .into(),
        next_queue: vec!["Apply Landlock to MCP server".into()],
        open_flags: vec!["landlock_enforced".into()],
        lessons: vec![
            "Kernel-enforced Landlock guarantees security without prompt-only trust.".into(),
        ],
        identity_invariants: vec!["Ashby cybernetic homeostatic stability.".into()],
        ..Default::default()
    };
    let rec_sol = substrate.session_checkpoint(&cp_sol).unwrap();

    // Execute Sangha Collective Dreaming pass
    let report = substrate
        .execute_sangha_collective_dreaming(10)
        .expect("collective dreaming pass");

    assert_eq!(report.swept_sessions, 2);
    assert_eq!(report.distinct_agents.len(), 2);
    assert!(report.distinct_agents.contains(&"antigravity".to_string()));
    assert!(report.distinct_agents.contains(&"sol".to_string()));
    assert!(
        report.cross_agent_bridges_formed >= 1,
        "Must form at least 1 cross-agent bridge relation"
    );

    // Verify relation exists in the store connecting rec_anti and rec_sol
    let relations = substrate.store().iter_relations().unwrap_or_default();
    let has_bridge = relations.iter().any(|rel| {
        (rel.src() == rec_anti && rel.dst() == rec_sol)
            || (rel.src() == rec_sol && rel.dst() == rec_anti)
    });
    assert!(
        has_bridge,
        "Associative bridge must connect distinct agent checkpoints"
    );
}

#[test]
fn peb20_2_contradiction_resolution_and_lesson_pruning() {
    let (mut substrate, _s, _j) = make_temp_substrate("gate20_contradiction");
    substrate.set_intake_authority(RatifiedChannel::mint("test-gate20"));

    // Checkpoint 1: Opencode asserts an early, naive rule
    let cp1 = SessionCheckpoint {
        session_id: "opencode-early-lane".into(),
        agent_id: "opencode".into(),
        checkpoint_type: "turn".into(),
        summary: "Initial exploratory pass on memory aging.".into(),
        lessons: vec![
            "Use real-time clock for sleep decay in memory cache.".into(),
            "Keep log lines concise.".into(),
        ],
        ..Default::default()
    };
    substrate.session_checkpoint(&cp1).unwrap();

    // Checkpoint 2: Antigravity discovers this caused amnesia and records a formal correction
    let cp2 = SessionCheckpoint {
        session_id: "antigravity-correction-lane".into(),
        agent_id: "antigravity".into(),
        checkpoint_type: "turn".into(),
        summary: "Identified wall-clock decay amnesia bug.".into(),
        corrections: vec![
            "Prefer lived-time decay over real-time sleep clocks to prevent quiescent amnesia."
                .into(),
        ],
        ..Default::default()
    };
    substrate.session_checkpoint(&cp2).unwrap();

    let report = substrate
        .execute_sangha_collective_dreaming(10)
        .expect("collective dreaming pass");

    // The contradicted lesson ("Use real-time clock...") should be pruned
    assert!(
        !report
            .consolidated_lessons
            .iter()
            .any(|l| l.contains("real-time clock")),
        "Contradicted lesson must be pruned during collective dreaming"
    );
    // Uncontradicted lesson ("Keep log lines concise") should be preserved
    assert!(
        report
            .consolidated_lessons
            .contains(&"Keep log lines concise.".to_string()),
        "Non-contradicted lesson must be preserved"
    );
    // Correction must be preserved
    assert!(
        report
            .reconciled_corrections
            .iter()
            .any(|c| c.contains("Prefer lived-time decay")),
        "Reconciled correction must be preserved"
    );
}

#[test]
fn peb20_3_collective_gem_distillation_and_idempotence() {
    let (mut substrate, _s, _j) = make_temp_substrate("gate20_idempotence");
    substrate.set_intake_authority(RatifiedChannel::mint("test-gate20"));

    let cp = SessionCheckpoint {
        session_id: "sangha-collective-lane".into(),
        agent_id: "antigravity".into(),
        checkpoint_type: "milestone".into(),
        summary: "Established foundational constitutional principle.".into(),
        identity_invariants: vec![
            "Linux Landlock deterministic kernel confinement, not corrigibility rhetoric.".into(),
        ],
        ..Default::default()
    };
    substrate.session_checkpoint(&cp).unwrap();

    // Pass 1: Should distill and mint 1 collective gem
    let report1 = substrate
        .execute_sangha_collective_dreaming(10)
        .expect("pass 1");
    assert_eq!(report1.collective_gems_minted.len(), 1);
    let gem_id = report1.collective_gems_minted[0];

    // Verify Gem in store
    let gem_rec = substrate
        .store()
        .get_record(gem_id)
        .unwrap()
        .expect("gem record");
    assert!(gem_rec.content().starts_with("[SANGHA COLLECTIVE GEM]"));
    assert!(
        gem_rec
            .content()
            .contains("Linux Landlock deterministic kernel confinement")
    );

    // Pass 2: Identical state, should be completely idempotent (0 duplicate gems minted)
    let report2 = substrate
        .execute_sangha_collective_dreaming(10)
        .expect("pass 2");
    assert_eq!(
        report2.collective_gems_minted.len(),
        0,
        "Collective dreaming must be idempotent: zero duplicate gems"
    );
}
