use rusqlite::{Connection, params, Result};
use serde::{Deserialize, Serialize};
use crate::extractor::NormalizedTurn;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultNode {
    pub node_id: String,
    pub node_type: String, // 'directive' | 'problem' | 'breakthrough' | 'artifact' | 'concept'
    pub label: String,
    pub summary: String,
    pub session_id: String,
    pub chunk_id: Option<String>,
    pub time_created: i64,
    pub metadata: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultEdge {
    pub edge_id: String,
    pub src_id: String,
    pub dst_id: String,
    pub relation_kind: String, // 'causal' | 'supersedes' | 'associates'
    pub weight: f64,
    pub sign: i32,
    pub cost: f64,
    pub trust: f64,
    pub rule_id: String,
    pub created_at: i64,
}

pub struct CausalGraphBuilder;

impl CausalGraphBuilder {
    /// Mine nodes and causal relations from normalized session turns
    pub fn mine_session_graph(
        session_id: &str,
        turns: &[NormalizedTurn],
    ) -> (Vec<VaultNode>, Vec<VaultEdge>) {
        let mut nodes = Vec::new();
        let mut edges = Vec::new();

        let mut last_directive_id: Option<String> = None;
        let mut last_problem_id: Option<String> = None;

        for turn in turns {
            let lower = turn.clean_text.to_lowercase();

            // 1. Directives (Lucas's interventions and architectural goals)
            if turn.role == "user" && (
                lower.contains("let's") ||
                lower.contains("we need to") ||
                lower.contains("directive") ||
                lower.contains("implement") ||
                lower.contains("build") ||
                lower.contains("grand strategy")
            ) {
                let node_id = format!("dir-{}-{}", session_id, turn.seq);
                let label = extract_directive_title(&turn.clean_text);
                let summary = turn.clean_text.chars().take(280).collect();

                nodes.push(VaultNode {
                    node_id: node_id.clone(),
                    node_type: "directive".to_string(),
                    label,
                    summary,
                    session_id: session_id.to_string(),
                    chunk_id: Some(format!("{}-t0-{}", session_id, turn.seq)),
                    time_created: turn.time_created,
                    metadata: None,
                });
                last_directive_id = Some(node_id);
            }

            // 2. Problems (Errors, deadlocks, blocks)
            if turn.turn_type == "error" || lower.contains("deadlock") || lower.contains("panic") || lower.contains("failing") {
                let node_id = format!("prob-{}-{}", session_id, turn.seq);
                let label = extract_problem_title(&turn.clean_text);
                let summary = turn.clean_text.chars().take(280).collect();

                nodes.push(VaultNode {
                    node_id: node_id.clone(),
                    node_type: "problem".to_string(),
                    label,
                    summary,
                    session_id: session_id.to_string(),
                    chunk_id: Some(format!("{}-t0-{}", session_id, turn.seq)),
                    time_created: turn.time_created,
                    metadata: None,
                });

                if let Some(ref dir_id) = last_directive_id {
                    // Problem occurred during Directive
                    edges.push(VaultEdge {
                        edge_id: format!("e-dp-{}-{}", dir_id, node_id),
                        src_id: dir_id.clone(),
                        dst_id: node_id.clone(),
                        relation_kind: "causal".to_string(),
                        weight: 0.8,
                        sign: -1, // Conflict / blocker
                        cost: 0.2,
                        trust: 1.0,
                        rule_id: "RULE_DIRECTIVE_ENCOUNTERED_BLOCKER".to_string(),
                        created_at: turn.time_created,
                    });
                }
                last_problem_id = Some(node_id);
            }

            // 3. Breakthroughs (Passing tests, resolutions, ratifications)
            if turn.turn_type == "breakthrough" || lower.contains("test result: ok") || lower.contains("tests pass") || lower.contains("ratified") {
                let node_id = format!("bt-{}-{}", session_id, turn.seq);
                let label = extract_breakthrough_title(&turn.clean_text);
                let summary = turn.clean_text.chars().take(280).collect();

                nodes.push(VaultNode {
                    node_id: node_id.clone(),
                    node_type: "breakthrough".to_string(),
                    label,
                    summary,
                    session_id: session_id.to_string(),
                    chunk_id: Some(format!("{}-t0-{}", session_id, turn.seq)),
                    time_created: turn.time_created,
                    metadata: None,
                });

                // Link to active Problem (Resolution)
                if let Some(ref prob_id) = last_problem_id {
                    edges.push(VaultEdge {
                        edge_id: format!("e-pb-{}-{}", prob_id, node_id),
                        src_id: node_id.clone(),
                        dst_id: prob_id.clone(),
                        relation_kind: "supersedes".to_string(),
                        weight: 1.0,
                        sign: 1, // Positive resolution
                        cost: 0.1,
                        trust: 1.0,
                        rule_id: "RULE_BREAKTHROUGH_RESOLVES_PROBLEM".to_string(),
                        created_at: turn.time_created,
                    });
                    last_problem_id = None;
                }

                // Link to active Directive (Achievement)
                if let Some(ref dir_id) = last_directive_id {
                    edges.push(VaultEdge {
                        edge_id: format!("e-db-{}-{}", dir_id, node_id),
                        src_id: dir_id.clone(),
                        dst_id: node_id.clone(),
                        relation_kind: "causal".to_string(),
                        weight: 1.0,
                        sign: 1,
                        cost: 0.1,
                        trust: 1.0,
                        rule_id: "RULE_DIRECTIVE_YIELDS_BREAKTHROUGH".to_string(),
                        created_at: turn.time_created,
                    });
                }
            }

            // 4. Extract concept nodes
            mine_concept_associations(&turn, &mut nodes, &mut edges);
        }

        (nodes, edges)
    }

    /// Insert nodes and edges into the vault database in a transaction
    pub fn persist_graph(conn: &mut Connection, nodes: &[VaultNode], edges: &[VaultEdge]) -> Result<()> {
        let tx = conn.transaction()?;

        {
            let mut node_stmt = tx.prepare_cached(
                r#"
                INSERT OR REPLACE INTO vault_nodes (node_id, node_type, label, summary, session_id, chunk_id, time_created, metadata)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
                "#,
            )?;

            for n in nodes {
                node_stmt.execute(params![
                    n.node_id,
                    n.node_type,
                    n.label,
                    n.summary,
                    n.session_id,
                    n.chunk_id,
                    n.time_created,
                    n.metadata
                ])?;
            }
        }

        {
            let mut edge_stmt = tx.prepare_cached(
                r#"
                INSERT OR REPLACE INTO vault_edges (edge_id, src_id, dst_id, relation_kind, weight, sign, cost, trust, rule_id, created_at)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)
                "#,
            )?;

            for e in edges {
                edge_stmt.execute(params![
                    e.edge_id,
                    e.src_id,
                    e.dst_id,
                    e.relation_kind,
                    e.weight,
                    e.sign,
                    e.cost,
                    e.trust,
                    e.rule_id,
                    e.created_at
                ])?;
            }
        }

        tx.commit()?;
        Ok(())
    }
}

fn extract_directive_title(text: &str) -> String {
    let first = text.lines().next().unwrap_or("Directive").trim();
    if first.len() > 60 {
        let truncated = crate::safe_truncate(first, 57);
        format!("{}...", truncated)
    } else {
        first.to_string()
    }
}

fn extract_problem_title(text: &str) -> String {
    for line in text.lines() {
        if line.contains("error:") || line.contains("panic:") || line.contains("failed") {
            return line.trim().chars().take(60).collect();
        }
    }
    "Problem / Blocker".to_string()
}

fn extract_breakthrough_title(text: &str) -> String {
    for line in text.lines() {
        if line.contains("test result: ok") || line.contains("passed") || line.contains("ratified") {
            return line.trim().chars().take(60).collect();
        }
    }
    "Verified Breakthrough".to_string()
}

fn mine_concept_associations(
    turn: &NormalizedTurn,
    nodes: &mut Vec<VaultNode>,
    edges: &mut Vec<VaultEdge>,
) {
    let lower = turn.clean_text.to_lowercase();
    let concepts = [
        ("c_landlock", "kernel_and_sandboxing", &["landlock", "sandbox", "kekkai", "containment"][..]),
        ("c_shm", "substrate_and_tuples", &["shm", "posix", "linda", "tuple", "shared memory"][..]),
        ("c_covenant", "epistemology_and_philosophy", &["covenant", "charter", "kadag", "lhun-grub"][..]),
        ("c_mesh", "mesh_and_p2p", &["mesh", "ganying", "port 7369", "p2p"][..]),
        ("c_continuity", "memory_and_continuity", &["continuity", "vault", "opencode.db", "gestalt"][..]),
    ];

    for (cid, cname, patterns) in &concepts {
        if patterns.iter().any(|p| lower.contains(p)) {
            let cnode = VaultNode {
                node_id: cid.to_string(),
                node_type: "concept".to_string(),
                label: cname.to_string(),
                summary: format!("Core WhiteMagic Concept: {cname}"),
                session_id: turn.session_id.clone(),
                chunk_id: None,
                time_created: turn.time_created,
                metadata: None,
            };
            if !nodes.iter().any(|n| n.node_id == *cid) {
                nodes.push(cnode);
            }

            // Associate turn chunk with concept
            let chunk_id = format!("{}-t0-{}", turn.session_id, turn.seq);
            edges.push(VaultEdge {
                edge_id: format!("e-assoc-{}-{}", chunk_id, cid),
                src_id: cid.to_string(),
                dst_id: cid.to_string(), // Self/concept anchor
                relation_kind: "associates".to_string(),
                weight: 0.7,
                sign: 1,
                cost: 0.05,
                trust: 0.95,
                rule_id: "RULE_CONCEPT_ASSOCIATION".to_string(),
                created_at: turn.time_created,
            });
        }
    }
}
