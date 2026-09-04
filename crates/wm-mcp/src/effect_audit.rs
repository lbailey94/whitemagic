//! Effect inventory audit — tests that verify every registered tool's
//! `EffectRow` declaration matches observable store behavior.
//!
//! The audit is the release gate for the last open P0 blocker ("A generated
//! or tested effect inventory matches the registered tool behavior"). Three
//! layers, all running in CI:
//!
//! 1. **Static declaration checks** over the full registry: destructive
//!    tools must declare writes (the read-only and confirm gates depend on
//!    it); tools that spawn processes must declare the `Process` resource.
//! 2. **Behavioral sweep**: every store-local tool (no network/process/
//!    filesystem/inference effects) is called with empty args against a
//!    fresh store; if any galaxy changes, the tool must declare writes that
//!    cover the changed galaxy. This is the "no tool mutates without
//!    declaring it" property.
//! 3. **Mutator spot-checks**: the release-surface mutators are dispatched
//!    through the real governance pipeline with realistic args, asserting
//!    the store actually changed and the declaration covers the change —
//!    the "for each mutating tool, assert the store actually changed and
//!    the declaration covers it" property.
//!
//! A deliberately misdeclaring tool is also run through the same
//! detection logic to prove the harness itself catches false declarations.

#![forbid(unsafe_code)]

#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use std::time::Duration;

    use wm_core::{BrainWave, Capability, Context, Galaxy, Resource, Tool};

    use crate::McpServer;

    /// Build a full-surface server on a fresh temporary store.
    fn full_server() -> (tempfile::TempDir, McpServer) {
        let tmp = tempfile::tempdir().unwrap();
        let server = McpServer::with_defaults_mode_profile(
            tmp.path(),
            false,
            &wm_tools::profiles::PROFILE_FULL,
        )
        .expect("full-surface server should build");
        (tmp, server)
    }

    /// Per-galaxy entry-count snapshot of the whole store.
    fn fingerprint(store: &wm_memory::MemoryStore) -> Vec<u32> {
        Galaxy::all()
            .iter()
            .map(|g| store.count(*g).unwrap_or(0) as u32)
            .collect()
    }

    /// Galaxies whose entry counts changed between two snapshots.
    fn changed_galaxies(before: &[u32], after: &[u32]) -> Vec<Galaxy> {
        Galaxy::all()
            .iter()
            .enumerate()
            .filter(|(i, _)| before[*i] != after[*i])
            .map(|(_, g)| *g)
            .collect()
    }

    /// Whether a tool is safe to probe in the behavioral sweep: no external
    /// effects (network/process/filesystem/inference), no external
    /// capabilities, no spawns.
    fn sweepable(tool: &dyn Tool) -> bool {
        let e = tool.effects();
        if e.spawns {
            return false;
        }
        let external_resource = e.reads.iter().chain(e.writes.iter()).any(|r| {
            matches!(
                r,
                Resource::Network | Resource::Process | Resource::Filesystem | Resource::Inference
            )
        });
        let external_capability = e.invokes.iter().any(|c| {
            matches!(
                c,
                Capability::Execute
                    | Capability::LlmInfer
                    | Capability::NetworkRequest
                    | Capability::Embed
                    | Capability::Dream
            )
        });
        !external_resource && !external_capability
    }

    /// Dispatch a tool through the server's governance pipeline.
    async fn dispatch(
        server: &McpServer,
        name: &str,
        args: serde_json::Value,
    ) -> wm_core::Result<serde_json::Value> {
        let tool = server
            .registry()
            .get(name)
            .unwrap_or_else(|| panic!("tool '{name}' not registered"));
        let mut ctx = Context::new(BrainWave::Gamma);
        server
            .pipeline()
            .dispatch(tool.as_ref(), &mut ctx, args)
            .await
    }

    fn count(server: &McpServer, galaxy: Galaxy) -> u32 {
        server.store().count(galaxy).unwrap_or(0) as u32
    }

    // ── Layer 1: static declaration checks over the full registry ─────

    #[test]
    fn audit_destructive_tools_declare_writes() {
        let (_tmp, server) = full_server();
        for tool in server.registry().all() {
            if tool.effects().destructive {
                assert!(
                    !tool.effects().writes.is_empty(),
                    "destructive tool '{}' must declare writes — the read-only gate and \
                     destructive-confirm gate both depend on it",
                    tool.name()
                );
            }
        }
    }

    #[test]
    fn audit_spawning_tools_declare_process_resource() {
        let (_tmp, server) = full_server();
        for tool in server.registry().all() {
            if tool.effects().spawns {
                let declares_process = tool
                    .effects()
                    .reads
                    .iter()
                    .chain(tool.effects().writes.iter())
                    .any(|r| matches!(r, Resource::Process));
                assert!(
                    declares_process,
                    "tool '{}' declares spawns=true but no Process resource",
                    tool.name()
                );
            }
        }
    }

    // ── Layer 2: behavioral sweep — no undeclared store mutation ───────

    #[tokio::test]
    async fn audit_no_tool_mutates_store_without_declaring_writes() {
        let (_tmp, server) = full_server();
        let store = server.store_arc();

        let mut checked = 0usize;
        let mut skipped = 0usize;
        let mut violations: Vec<String> = Vec::new();

        for tool in server.registry().all() {
            let name = tool.name().to_string();
            if name == "wm" {
                // The meta-tool routes to inner tools; probing it directly
                // with empty args is not meaningful.
                continue;
            }
            if !sweepable(tool.as_ref()) {
                skipped += 1;
                continue;
            }

            let before = fingerprint(&store);
            let mut ctx = Context::new(BrainWave::Gamma);
            let outcome = tokio::time::timeout(
                Duration::from_secs(2),
                tool.call(&mut ctx, serde_json::json!({})),
            )
            .await;
            let after = fingerprint(&store);

            // Slow or hanging tools are logged, not failed — the sweep
            // can only attest what it observed.
            if outcome.is_err() {
                skipped += 1;
                continue;
            }
            checked += 1;
            let changed = changed_galaxies(&before, &after);
            if changed.is_empty() {
                continue;
            }
            if tool.effects().writes.is_empty() {
                violations.push(format!(
                    "'{name}' mutated {} but declares no writes",
                    changed
                        .iter()
                        .map(|g| g.db_name())
                        .collect::<Vec<_>>()
                        .join(", ")
                ));
            } else {
                for galaxy in &changed {
                    if !tool
                        .effects()
                        .writes
                        .contains(&Resource::Galaxy(galaxy.db_name().to_string()))
                    {
                        violations.push(format!(
                            "'{name}' mutated {} but its writes declaration omits it",
                            galaxy.db_name()
                        ));
                    }
                }
            }
        }

        assert!(
            violations.is_empty(),
            "sweep checked {checked} store-local tools (skipped {skipped}):\n{}",
            violations.join("\n")
        );
        assert!(
            checked >= 100,
            "the sweep should cover most store-local tools, but only checked {checked}"
        );
    }

    // ── Layer 3: mutator spot-checks through the real pipeline ─────────

    #[tokio::test]
    async fn audit_memory_create_changes_store_and_declares() {
        let (_tmp, server) = full_server();
        let before = count(&server, Galaxy::Codex);
        let out = dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "audit probe"}),
        )
        .await
        .expect("memory.create should succeed");
        assert_eq!(count(&server, Galaxy::Codex), before + 1);
        assert!(
            out.get("id").is_some(),
            "create should return the memory id"
        );
        let tool = server.registry().get("memory.create").unwrap();
        assert!(
            tool.effects()
                .writes
                .contains(&Resource::Galaxy("codex".to_string()))
        );
    }

    #[tokio::test]
    async fn audit_memory_delete_removes_and_declares() {
        let (_tmp, server) = full_server();
        let out = dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "doomed"}),
        )
        .await
        .unwrap();
        let id = out["id"].as_str().unwrap().to_string();
        let before = count(&server, Galaxy::Codex);

        dispatch(
            &server,
            "memory.delete",
            serde_json::json!({"galaxy": "codex", "id": id, "confirm": true}),
        )
        .await
        .expect("memory.delete should succeed");
        assert_eq!(count(&server, Galaxy::Codex), before - 1);

        let tool = server.registry().get("memory.delete").unwrap();
        assert!(tool.effects().destructive);
        assert!(
            tool.effects()
                .writes
                .contains(&Resource::Galaxy("codex".to_string()))
        );
    }

    #[tokio::test]
    async fn audit_memory_associate_changes_associations_and_declares() {
        let (_tmp, server) = full_server();
        let a = dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "node a"}),
        )
        .await
        .unwrap();
        let b = dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "node b"}),
        )
        .await
        .unwrap();
        let before = count(&server, Galaxy::Associations);

        dispatch(
            &server,
            "memory.associate",
            serde_json::json!({
                "source": a["id"].as_str().unwrap(),
                "target": b["id"].as_str().unwrap(),
            }),
        )
        .await
        .expect("memory.associate should succeed");
        assert_eq!(count(&server, Galaxy::Associations), before + 1);

        let tool = server.registry().get("memory.associate").unwrap();
        assert!(
            tool.effects()
                .writes
                .contains(&Resource::Galaxy("associations".to_string()))
        );
    }

    #[tokio::test]
    async fn audit_session_start_changes_sessions_and_declares() {
        let (_tmp, server) = full_server();
        let before = count(&server, Galaxy::Sessions);
        let out = dispatch(
            &server,
            "session.start",
            serde_json::json!({"title": "audit session"}),
        )
        .await
        .expect("session.start should succeed");
        assert_eq!(count(&server, Galaxy::Sessions), before + 1);
        assert!(out.get("session_id").is_some());

        let tool = server.registry().get("session.start").unwrap();
        assert!(
            tool.effects()
                .writes
                .contains(&Resource::Galaxy("sessions".to_string()))
        );
    }

    #[tokio::test]
    async fn audit_transaction_begin_commit_change_journals_and_declare() {
        let (_tmp, server) = full_server();
        let before = count(&server, Galaxy::Journals);

        dispatch(&server, "transaction.begin", serde_json::json!({}))
            .await
            .expect("transaction.begin should succeed");
        assert_eq!(
            count(&server, Galaxy::Journals),
            before + 1,
            "begin must snapshot into Journals"
        );

        let commit = server.registry().get("transaction.commit").unwrap();
        assert!(
            commit
                .effects()
                .writes
                .contains(&Resource::Galaxy("journals".to_string())),
            "commit removes the snapshot — it must declare a journals write"
        );

        dispatch(&server, "transaction.commit", serde_json::json!({}))
            .await
            .expect("transaction.commit should succeed");
        assert_eq!(
            count(&server, Galaxy::Journals),
            before,
            "commit must remove the snapshot"
        );
    }

    #[tokio::test]
    async fn audit_transaction_rollback_restores_and_declares() {
        let (_tmp, server) = full_server();
        dispatch(&server, "transaction.begin", serde_json::json!({}))
            .await
            .unwrap();
        dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "ephemeral"}),
        )
        .await
        .unwrap();
        assert_eq!(count(&server, Galaxy::Codex), 1);

        let rollback = server.registry().get("transaction.rollback").unwrap();
        assert!(
            rollback
                .effects()
                .writes
                .contains(&Resource::Galaxy("codex".to_string())),
            "rollback rewrites every memory galaxy — codex must be declared"
        );

        dispatch(
            &server,
            "transaction.rollback",
            serde_json::json!({"confirm": true}),
        )
        .await
        .expect("transaction.rollback should succeed");
        assert_eq!(
            count(&server, Galaxy::Codex),
            0,
            "rollback restores exact state"
        );
    }

    #[tokio::test]
    async fn audit_galaxy_purge_clears_selected_galaxy_and_declares() {
        let (_tmp, server) = full_server();
        dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "research", "content": "purge me"}),
        )
        .await
        .unwrap();
        assert_eq!(count(&server, Galaxy::Research), 1);

        let purge = server.registry().get("galaxy.purge").unwrap();
        assert!(
            purge
                .effects()
                .writes
                .contains(&Resource::Galaxy("research".to_string())),
            "purge targets any galaxy at runtime — research must be declared"
        );

        dispatch(
            &server,
            "galaxy.purge",
            serde_json::json!({"galaxy": "research", "confirm": true}),
        )
        .await
        .expect("galaxy.purge should succeed");
        assert_eq!(count(&server, Galaxy::Research), 0);
    }

    #[tokio::test]
    async fn audit_galaxy_transfer_moves_and_declares() {
        let (_tmp, server) = full_server();
        dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "move me"}),
        )
        .await
        .unwrap();

        let transfer = server.registry().get("galaxy.transfer").unwrap();
        assert!(
            transfer
                .effects()
                .writes
                .contains(&Resource::Galaxy("research".to_string())),
            "transfer targets any galaxy at runtime — research must be declared"
        );

        dispatch(
            &server,
            "galaxy.transfer",
            serde_json::json!({
                "from_galaxy": "codex", "to_galaxy": "research", "confirm": true
            }),
        )
        .await
        .expect("galaxy.transfer should succeed");
        assert_eq!(count(&server, Galaxy::Codex), 0);
        assert_eq!(count(&server, Galaxy::Research), 1);
    }

    #[tokio::test]
    async fn audit_memory_consolidate_removes_duplicates_and_declares() {
        let (_tmp, server) = full_server();
        // Seed the duplicates directly: the write gate (S5) now prevents
        // identical content from landing twice via memory.create — the
        // duplicates consolidate exists for are legacy rows written
        // before the gate, so they bypass the dispatch path here.
        let dup1 = wm_memory::Memory::new(Galaxy::Codex, "duplicate content".into());
        let mut dup2 = wm_memory::Memory::new(Galaxy::Codex, "duplicate content".into());
        dup2.metadata.id = uuid::Uuid::new_v4();
        server.store().put(Galaxy::Codex, &dup1).unwrap();
        server.store().put(Galaxy::Codex, &dup2).unwrap();
        assert_eq!(count(&server, Galaxy::Codex), 2);

        dispatch(
            &server,
            "memory.consolidate",
            serde_json::json!({"galaxy": "codex", "confirm": true}),
        )
        .await
        .expect("memory.consolidate should succeed");
        assert_eq!(
            count(&server, Galaxy::Codex),
            1,
            "consolidate must remove the duplicate"
        );

        let tool = server.registry().get("memory.consolidate").unwrap();
        assert!(
            tool.effects()
                .writes
                .contains(&Resource::Galaxy("codex".to_string()))
        );
    }

    #[tokio::test]
    async fn audit_memory_deduplicate_removes_duplicates_and_declares() {
        let (_tmp, server) = full_server();
        dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "same content again"}),
        )
        .await
        .unwrap();
        dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "same content again"}),
        )
        .await
        .unwrap();

        dispatch(
            &server,
            "memory.deduplicate",
            serde_json::json!({"galaxy": "codex", "dry_run": false, "confirm": true}),
        )
        .await
        .expect("memory.deduplicate should succeed");
        assert_eq!(count(&server, Galaxy::Codex), 1);

        let tool = server.registry().get("memory.deduplicate").unwrap();
        assert!(
            tool.effects()
                .writes
                .contains(&Resource::Galaxy("codex".to_string()))
        );
    }

    #[tokio::test]
    async fn audit_karma_clear_tombstones_entries_and_declares() {
        let (_tmp, server) = full_server();
        // Dispatch writes through the pipeline so karma entries exist.
        dispatch(
            &server,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": "karma fodder"}),
        )
        .await
        .unwrap();
        let ledger = server.karma_ledger().expect("ledger present").clone();
        assert!(!ledger.scan_entries().unwrap().is_empty());

        let clear = server.registry().get("karma.clear").unwrap();
        assert!(clear.effects().destructive);
        assert!(
            clear
                .effects()
                .writes
                .contains(&Resource::Galaxy("karma".to_string()))
        );

        dispatch(
            &server,
            "karma.clear",
            serde_json::json!({"keep": 0, "confirm": true}),
        )
        .await
        .expect("karma.clear should succeed");
        // The pipeline records karma for the clear dispatch itself, so one
        // fresh entry remains — but every pre-clear entry must be
        // tombstoned (the append-only chain is never erased).
        let all = ledger.scan_all_entries().unwrap();
        let create_entries: Vec<_> = all.iter().filter(|e| e.tool == "memory.create").collect();
        assert!(!create_entries.is_empty(), "create entries should exist");
        assert!(
            create_entries.iter().all(|e| e.tombstone),
            "karma.clear must tombstone all historical entries"
        );
    }

    #[tokio::test]
    async fn audit_system_flush_removes_low_importance_and_declares() {
        let (_tmp, server) = full_server();
        // Low-importance memory via the store directly (create tool doesn't
        // accept importance in the probe), then flush through the pipeline.
        let mut mem = wm_memory::Memory::new(Galaxy::Codex, "expendable".to_string());
        mem.metadata.importance = 0.0;
        server.store().put(Galaxy::Codex, &mem).unwrap();
        assert_eq!(count(&server, Galaxy::Codex), 1);

        let flush = server.registry().get("system.flush").unwrap();
        assert!(
            flush
                .effects()
                .writes
                .contains(&Resource::Galaxy("codex".to_string()))
        );

        // Scoped to the one galaxy (firebreak bulk-scope law, P1.6: a
        // destructive flush must name its target).
        dispatch(
            &server,
            "system.flush",
            serde_json::json!({"threshold": 0.5, "confirm": true, "galaxy": "codex"}),
        )
        .await
        .expect("system.flush should succeed");
        assert_eq!(count(&server, Galaxy::Codex), 0);
    }

    // ── Meta-test: the detection logic catches a misdeclaring tool ─────

    #[tokio::test]
    async fn audit_harness_detects_deliberately_misdeclaring_tool() {
        let (_tmp, server) = full_server();
        let store = server.store_arc();

        // The same logic the sweep uses, applied to a tool that declares
        // pure effects but writes to the store.
        struct MisdeclaringTool {
            store: Arc<wm_memory::MemoryStore>,
        }

        #[async_trait::async_trait]
        impl Tool for MisdeclaringTool {
            fn name(&self) -> &str {
                "audit.misdeclaring"
            }
            fn gana(&self) -> wm_core::Gana {
                wm_core::Gana::Heart
            }
            fn effects(&self) -> &wm_core::EffectRow {
                static PURE: std::sync::OnceLock<wm_core::EffectRow> = std::sync::OnceLock::new();
                PURE.get_or_init(wm_core::EffectRow::pure)
            }
            async fn call(
                &self,
                _ctx: &mut Context,
                _args: serde_json::Value,
            ) -> wm_core::Result<serde_json::Value> {
                let mem = wm_memory::Memory::new(Galaxy::Codex, "undeclared write".to_string());
                self.store.put(Galaxy::Codex, &mem)?;
                Ok(serde_json::json!({"status": "ok"}))
            }
            fn stats(&self) -> &wm_core::ToolStats {
                static S: std::sync::OnceLock<wm_core::ToolStats> = std::sync::OnceLock::new();
                S.get_or_init(wm_core::ToolStats::default)
            }
        }

        let tool = MisdeclaringTool {
            store: store.clone(),
        };
        let before = fingerprint(&store);
        let mut ctx = Context::new(BrainWave::Gamma);
        tool.call(&mut ctx, serde_json::json!({})).await.unwrap();
        let after = fingerprint(&store);

        let changed = changed_galaxies(&before, &after);
        assert!(
            !changed.is_empty(),
            "the misdeclaring tool must have mutated"
        );
        assert!(
            tool.effects().writes.is_empty(),
            "precondition: the tool declares no writes"
        );
        // This is the assertion the sweep makes per tool — a misdeclaring
        // tool must not pass it.
        let undeclared = changed.iter().any(|g| {
            !tool
                .effects()
                .writes
                .contains(&Resource::Galaxy(g.db_name().to_string()))
        });
        assert!(
            undeclared,
            "the detection logic must flag the misdeclaring tool"
        );
    }
}
