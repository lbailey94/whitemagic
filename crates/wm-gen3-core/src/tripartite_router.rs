//! wm-gen3-core::tripartite_router — The Tripartite Cognitive Router (2027 Post-Transformer Architecture).
//!
//! Enforces:
//! 1. Sub-microsecond System 0 dispatch for canonical Sutra glyphs and exact patterns (<1 µs, 0 tokens).
//! 2. System 0.5 Model2Vec static vector similarity routing (~25 µs, 0 cloud tokens).
//! 3. System 1 local typed decision organ (<10 ms).
//! 4. System 2 frontier cloud deliberation (only when open-ended complexity warrants).
//! 5. Bioelectric setpoint modulation: In `Stressed` or `Critical` homeostatic regimes,
//!    cloud escalation is suspended to preserve thermal, power, and memory invariants.

use serde::{Deserialize, Serialize};
use std::time::Instant;

use crate::catuskoti::Corner;
use crate::hexagram::Hexagram;
use crate::homeostasis::{BioelectricState, HomeostaticRegime};
use crate::sutra::SutraGlyph;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum CognitiveTier {
    /// System 0: Sub-microsecond Sutra Logoglyphic Canon dispatch (<1 µs, 0 tokens).
    System0Sutra,
    /// System 0.5: Local static Model2Vec embedding vector match (~25 µs, 0 tokens).
    System05Vector,
    /// System 1: Local typed decision organ / Small Language Model (<10 ms, 0 cloud tokens).
    System1LocalOrgan,
    /// System 2: Frontier Cloud Deliberation (only for complex open-ended reasoning).
    System2FrontierCloud,
}

impl CognitiveTier {
    /// Stable ordinal used as the `ValkyrieSample.target_class` label when training
    /// routing organs (S0=0, S0.5=1, S1=2, S2=3).
    #[must_use]
    pub fn index(self) -> usize {
        match self {
            Self::System0Sutra => 0,
            Self::System05Vector => 1,
            Self::System1LocalOrgan => 2,
            Self::System2FrontierCloud => 3,
        }
    }

    /// Inverse of [`CognitiveTier::index`]; out-of-range classes fold via `% 4`.
    #[must_use]
    pub fn from_index(class: usize) -> Self {
        match class % 4 {
            0 => Self::System0Sutra,
            1 => Self::System05Vector,
            2 => Self::System1LocalOrgan,
            _ => Self::System2FrontierCloud,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RoutingDecision {
    pub tier: CognitiveTier,
    pub selected_glyph: Option<char>,
    pub skeleton_id: Option<String>,
    pub confidence: f32,
    pub rationale: String,
    pub routing_latency_ns: u64,
    pub catuskoti: Option<Corner>,
}

#[inline]
fn has_word(text: &str, word: &str) -> bool {
    text.split(|c: char| !c.is_alphanumeric() && c != '_' && c != '-')
        .any(|w| w.eq_ignore_ascii_case(word))
}

fn match_system0_explicit(trimmed: &str) -> Option<(SutraGlyph, char)> {
    // 1. Raw alchemical glyph seals (unambiguous, never in natural prose)
    for glyph in SutraGlyph::ALL {
        let a = glyph.alchemical_char();
        if trimmed.contains(a) {
            return Some((glyph, a));
        }
    }

    // 2. Exact single character or sigiled/bracketed logoglyph (e.g. "行", "§行", "[行]", "`行`")
    let clean = trimmed.trim_matches(|c: char| {
        c == '§' || c == '[' || c == ']' || c == '`' || c == '(' || c == ')' || c == '{' || c == '}'
    });
    if clean.chars().count() == 1 {
        let c = clean.chars().next().unwrap();
        for glyph in SutraGlyph::ALL {
            if glyph.as_char() == c {
                return Some((glyph, c));
            }
        }
    }

    // 3. Explicit "sutra:<name>" or "#sutra:<name>" or "sutra:<glyph>"
    if let Some(rest) = trimmed
        .strip_prefix("sutra:")
        .or_else(|| trimmed.strip_prefix("#sutra:"))
    {
        let sub = rest.trim();
        if let Some(glyph) = SutraGlyph::from_token(sub) {
            return Some((glyph, glyph.as_char()));
        }
    }

    // 4. Pure codon pipeline (e.g. "行 觀 證", "行; 觀")
    let glyph_candidates: Vec<char> = clean
        .chars()
        .filter(|c| !c.is_whitespace() && *c != ';' && *c != '·' && *c != '-' && *c != '>')
        .collect();
    if !glyph_candidates.is_empty() && glyph_candidates.len() <= 4 {
        let all_glyphs = glyph_candidates
            .iter()
            .all(|&c| SutraGlyph::from_char(c).is_some());
        if all_glyphs {
            let first_glyph = SutraGlyph::from_char(glyph_candidates[0]).unwrap();
            return Some((first_glyph, glyph_candidates[0]));
        }
    }

    None
}

pub struct TripartiteRouter;

impl TripartiteRouter {
    /// Evaluate a user task or instruction against the tripartite hierarchy.
    #[must_use]
    pub fn route(prompt: &str, bio_state: Option<&BioelectricState>) -> RoutingDecision {
        let t0 = Instant::now();
        let trimmed = prompt.trim();

        // 1. System 0: Direct Logoglyphic Canon Detection (<1 µs)
        if let Some((glyph, matched)) = match_system0_explicit(trimmed) {
            return RoutingDecision {
                tier: CognitiveTier::System0Sutra,
                selected_glyph: Some(matched),
                skeleton_id: Some(glyph.bound_skeleton_id().to_string()),
                confidence: 0.99,
                rationale: format!(
                    "Exact canonical logoglyph '{}' ({}) matched; dispatching System 0 organelle reflex",
                    matched,
                    glyph.taoist_seal()
                ),
                routing_latency_ns: t0.elapsed().as_nanos() as u64,
                catuskoti: Some(Corner::K1Affirmed),
            };
        }

        // 2. Direct 64-Hexagram Macro-Action Recognition
        if let Some(hex) = Hexagram::parse(trimmed) {
            let lower_glyph = hex.lower_trigram().bound_sutra_glyph();
            return RoutingDecision {
                tier: CognitiveTier::System0Sutra,
                selected_glyph: Some(lower_glyph.as_char()),
                skeleton_id: Some(lower_glyph.bound_skeleton_id().to_string()),
                confidence: 0.96,
                rationale: format!(
                    "Hexagram #{} '{}' ({}, Upper:{}, Lower:{}) matched; dispatching System 0 macro-action",
                    hex.king_wen_id(),
                    hex.name_zh(),
                    hex.name_en(),
                    hex.upper_trigram().name_zh(),
                    hex.lower_trigram().name_zh()
                ),
                routing_latency_ns: t0.elapsed().as_nanos() as u64,
                catuskoti: Some(Corner::K1Affirmed),
            };
        }

        // 3. Catuṣkoṭi K3 Dialectical Tension Detection & Keyword Matching
        let lower = trimmed.to_lowercase();
        let word_count = trimmed.split_whitespace().count();
        let is_interrogative = trimmed.contains('?')
            || trimmed.starts_with("why ")
            || trimmed.starts_with("how ")
            || trimmed.starts_with("what ")
            || trimmed.starts_with("can you")
            || trimmed.starts_with("could you");

        // Detect potential thesis / antithesis pairs
        let wants_exec = has_word(&lower, "execute")
            || has_word(&lower, "commit")
            || has_word(&lower, "dispatch")
            || has_word(&lower, "ship")
            || (has_word(&lower, "run")
                && !has_word(&lower, "dry-run")
                && !has_word(&lower, "dryrun"));
        let wants_sim = has_word(&lower, "simulate")
            || has_word(&lower, "shadow")
            || has_word(&lower, "dry-run")
            || has_word(&lower, "dryrun");
        let wants_verify = has_word(&lower, "verify")
            || has_word(&lower, "test")
            || has_word(&lower, "proof")
            || (has_word(&lower, "check") && !has_word(&lower, "checkpoint"))
            || has_word(&lower, "audit");
        let wants_fuzz = has_word(&lower, "fuzz")
            || has_word(&lower, "redteam")
            || has_word(&lower, "discriminate")
            || has_word(&lower, "adversarial");

        if (wants_exec && wants_sim) || (wants_verify && wants_fuzz) {
            // K3 Dialectical tension: Both thesis and antithesis are affirmed
            let (glyph, skel) = if wants_verify && wants_fuzz {
                (SutraGlyph::Bian, "skel-adversarial-redteam")
            } else {
                (SutraGlyph::Ni, "skel-shadow-dryrun")
            };
            return RoutingDecision {
                tier: CognitiveTier::System0Sutra,
                selected_glyph: Some(glyph.as_char()),
                skeleton_id: Some(skel.to_string()),
                confidence: 0.93,
                rationale: "Catuṣkoṭi K3 dialectical tension detected (Both Affirmed): dual-layer paraconsistent synthesis dispatched".to_string(),
                routing_latency_ns: t0.elapsed().as_nanos() as u64,
                catuskoti: Some(Corner::K3DialecticalContradiction),
            };
        }

        // Explicit snapshot/quiescence intent
        if has_word(&lower, "checkpoint") {
            return RoutingDecision {
                tier: CognitiveTier::System0Sutra,
                selected_glyph: Some(SutraGlyph::Xi.as_char()),
                skeleton_id: Some(SutraGlyph::Xi.bound_skeleton_id().to_string()),
                confidence: 0.95,
                rationale: "Explicit snapshot/quiescence intent matched to Xi (息)".to_string(),
                routing_latency_ns: t0.elapsed().as_nanos() as u64,
                catuskoti: Some(Corner::K1Affirmed),
            };
        }

        let is_short_directive = !is_interrogative && word_count <= 8;
        let keyword_match = if is_short_directive {
            if wants_verify {
                Some(SutraGlyph::Zheng)
            } else if wants_exec {
                Some(SutraGlyph::Xing)
            } else if has_word(&lower, "survey")
                || has_word(&lower, "inspect")
                || has_word(&lower, "lookup")
                || has_word(&lower, "status")
            {
                Some(SutraGlyph::Guan)
            } else if has_word(&lower, "probe") || has_word(&lower, "telemetry") {
                Some(SutraGlyph::Cha)
            } else if wants_fuzz {
                Some(SutraGlyph::Bian)
            } else if wants_sim {
                Some(SutraGlyph::Ni)
            } else if has_word(&lower, "clean")
                || has_word(&lower, "prune")
                || has_word(&lower, "compact")
            {
                Some(SutraGlyph::Qing)
            } else if has_word(&lower, "dream")
                || has_word(&lower, "sleep")
                || has_word(&lower, "quiesce")
            {
                Some(SutraGlyph::Xi)
            } else if has_word(&lower, "sync")
                || has_word(&lower, "resonate")
                || has_word(&lower, "mesh")
                || has_word(&lower, "peer")
            {
                Some(SutraGlyph::Ying)
            } else if has_word(&lower, "sandbox")
                || has_word(&lower, "kekkai")
                || has_word(&lower, "confine")
            {
                Some(SutraGlyph::Jie)
            } else if has_word(&lower, "synthesize") || has_word(&lower, "unify") {
                Some(SutraGlyph::He)
            } else if has_word(&lower, "decompose") || has_word(&lower, "decouple") {
                Some(SutraGlyph::Fen)
            } else if has_word(&lower, "diff") || has_word(&lower, "illuminate") {
                Some(SutraGlyph::Zhao)
            } else if has_word(&lower, "clarify") || has_word(&lower, "settle") {
                Some(SutraGlyph::Cheng)
            } else if has_word(&lower, "fork") || has_word(&lower, "sprout") {
                Some(SutraGlyph::Ya)
            } else if has_word(&lower, "transmute") || has_word(&lower, "dissolve") {
                Some(SutraGlyph::Hua)
            } else {
                None
            }
        } else {
            None
        };

        if let Some(glyph) = keyword_match {
            return RoutingDecision {
                tier: CognitiveTier::System0Sutra,
                selected_glyph: Some(glyph.as_char()),
                skeleton_id: Some(glyph.bound_skeleton_id().to_string()),
                confidence: 0.88,
                rationale: format!(
                    "Keyword match to canonical intent '{}' ({}); dispatching System 0",
                    glyph.english(),
                    glyph.as_char()
                ),
                routing_latency_ns: t0.elapsed().as_nanos() as u64,
                catuskoti: Some(Corner::K1Affirmed),
            };
        }

        // Check bioelectric homeostatic override:
        // In Critical or Stressed mode, strictly avoid System 2 cloud token churn.
        let under_stress = bio_state
            .map(|b| b.regime >= HomeostaticRegime::Stressed)
            .unwrap_or(false);

        // 4. System 0.5: Local Semantic Pattern Routing (~25 µs)
        let word_count = trimmed.split_whitespace().count();
        if word_count <= 8 && !trimmed.contains('?') {
            return RoutingDecision {
                tier: CognitiveTier::System05Vector,
                selected_glyph: Some('觀'),
                skeleton_id: Some("skel-fast-lookup".to_string()),
                confidence: 0.78,
                rationale:
                    "Short operational command routed to System 0.5 semantic vector matching"
                        .to_string(),
                routing_latency_ns: t0.elapsed().as_nanos() as u64,
                catuskoti: Some(Corner::K1Affirmed),
            };
        }

        // Determine if query is high-complexity open-ended reasoning
        let is_complex_reasoning =
            word_count >= 15 || trimmed.contains("analyz") || trimmed.contains("research");

        if is_complex_reasoning && !under_stress {
            return RoutingDecision {
                tier: CognitiveTier::System2FrontierCloud,
                selected_glyph: Some('遠'),
                skeleton_id: Some("skel-deliberate-horizon".to_string()),
                confidence: 0.90,
                rationale: "Complex open-ended query requiring multi-hop frontier deliberative reasoning (System 2)".to_string(),
                routing_latency_ns: t0.elapsed().as_nanos() as u64,
                catuskoti: Some(Corner::K4NeutralAgnostic),
            };
        }

        // 5. System 1: Local Typed Decision / Classifier (<10 ms)
        let rationale = if under_stress {
            "Homeostatic stress active: System 2 cloud invocation suspended; routed to local System 1".to_string()
        } else {
            "Standard structured query handled by local System 1 decision organ".to_string()
        };
        RoutingDecision {
            tier: CognitiveTier::System1LocalOrgan,
            selected_glyph: Some('合'),
            skeleton_id: None,
            confidence: 0.72,
            rationale,
            routing_latency_ns: t0.elapsed().as_nanos() as u64,
            catuskoti: Some(Corner::K1Affirmed),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tripartite_router_system0_glyph_match() {
        let dec = TripartiteRouter::route("行", None);
        assert_eq!(dec.tier, CognitiveTier::System0Sutra);
        assert_eq!(dec.selected_glyph, Some('行'));
        assert_eq!(
            dec.skeleton_id.as_deref(),
            Some("skel-verify-commit-vanguard")
        );
        assert!(
            dec.routing_latency_ns < 100_000,
            "System 0 routing must complete in sub-100µs"
        );
    }

    #[test]
    fn test_tripartite_router_system0_keyword_match() {
        let dec = TripartiteRouter::route("please verify the tests", None);
        assert_eq!(dec.tier, CognitiveTier::System0Sutra);
        assert_eq!(dec.selected_glyph, Some('證'));
    }

    #[test]
    fn test_tripartite_router_system05_short_command() {
        let dec = TripartiteRouter::route("browse candidate memory nodes", None);
        assert_eq!(dec.tier, CognitiveTier::System05Vector);
    }

    #[test]
    fn test_tripartite_router_homeostatic_cloud_suppression() {
        let stressed_bio = BioelectricState {
            v_rest_mv: -20.0,
            regime: HomeostaticRegime::Critical,
            cpu_temp_c: 90.0,
            battery_pct: Some(15.0),
            on_ac_power: false,
            load_avg_1m: 6.0,
            mem_available_mb: 2048.0,
            nvme_free_gb: 30.0,
            metabolism_mode: crate::homeostasis::MetabolismMode::CriticalHibernation,
            probe_latency_ns: 500.0,
        };

        // Long query that would normally escalate to System 2:
        let long_query = "Can you write an extensive research report analyzing sixty distinct micro-architectures for distributed multi-agent swarm consensus across mobile networks in thirty years?";
        let dec_stressed = TripartiteRouter::route(long_query, Some(&stressed_bio));
        assert_eq!(dec_stressed.tier, CognitiveTier::System1LocalOrgan);
        assert!(dec_stressed.rationale.contains("Homeostatic stress active"));

        let dec_calm = TripartiteRouter::route(long_query, None);
        assert_eq!(dec_calm.tier, CognitiveTier::System2FrontierCloud);
    }

    #[test]
    fn test_tripartite_router_hexagram_recognition() {
        let dec = TripartiteRouter::route("既济", None);
        assert_eq!(dec.tier, CognitiveTier::System0Sutra);
        assert_eq!(dec.selected_glyph, Some('證'));
        assert!(dec.rationale.contains("Hexagram #63 '既济'"));
        assert_eq!(dec.catuskoti, Some(Corner::K1Affirmed));

        let dec_qian = TripartiteRouter::route("乾", None);
        assert_eq!(dec_qian.tier, CognitiveTier::System0Sutra);
        assert_eq!(dec_qian.selected_glyph, Some('行'));
        assert!(dec_qian.rationale.contains("Hexagram #1 '乾'"));
    }

    #[test]
    fn test_tripartite_router_catuskoti_dialectical_contradiction() {
        // Query has both execution and simulation
        let dec = TripartiteRouter::route("execute this simulation dry-run now", None);
        assert_eq!(dec.tier, CognitiveTier::System0Sutra);
        assert_eq!(dec.selected_glyph, Some('擬'));
        assert_eq!(dec.skeleton_id.as_deref(), Some("skel-shadow-dryrun"));
        assert_eq!(dec.catuskoti, Some(Corner::K3DialecticalContradiction));
        assert!(
            dec.rationale
                .contains("Catuṣkoṭi K3 dialectical tension detected")
        );

        // Query has both verification and adversarial fuzzing
        let dec_fuzz =
            TripartiteRouter::route("verify invariants with adversarial fuzz test", None);
        assert_eq!(dec_fuzz.tier, CognitiveTier::System0Sutra);
        assert_eq!(dec_fuzz.selected_glyph, Some('辨'));
        assert_eq!(
            dec_fuzz.skeleton_id.as_deref(),
            Some("skel-adversarial-redteam")
        );
        assert_eq!(dec_fuzz.catuskoti, Some(Corner::K3DialecticalContradiction));
    }

    #[test]
    fn test_tripartite_router_strict_delimitation_and_no_false_positives() {
        // Explicit sigiled / bracketed / alchemical glyphs match System 0
        assert_eq!(
            TripartiteRouter::route("§行", None).tier,
            CognitiveTier::System0Sutra
        );
        assert_eq!(
            TripartiteRouter::route("[行]", None).tier,
            CognitiveTier::System0Sutra
        );
        assert_eq!(
            TripartiteRouter::route("`行`", None).tier,
            CognitiveTier::System0Sutra
        );
        assert_eq!(
            TripartiteRouter::route("🜂", None).tier,
            CognitiveTier::System0Sutra
        );
        assert_eq!(
            TripartiteRouter::route("sutra:xing", None).tier,
            CognitiveTier::System0Sutra
        );

        // Natural language prose containing Hanzi characters must NOT be hijacked into System 0
        let chinese_prose = "我们在进行分布式系统测试和架构研究";
        assert_ne!(
            TripartiteRouter::route(chinese_prose, None).tier,
            CognitiveTier::System0Sutra
        );

        // Substring collision prevention: "prune" must not trigger "run"
        let prune_cmd = "prune old logs";
        let dec_prune = TripartiteRouter::route(prune_cmd, None);
        assert_eq!(dec_prune.tier, CognitiveTier::System0Sutra);
        assert_eq!(dec_prune.selected_glyph, Some('清')); // Qing = clean / prune

        // Explicit "checkpoint" routes to Xi (quiescence / snapshot)
        let ckpt_cmd = "trigger session checkpoint";
        let dec_ckpt = TripartiteRouter::route(ckpt_cmd, None);
        assert_eq!(dec_ckpt.tier, CognitiveTier::System0Sutra);
        assert_eq!(dec_ckpt.selected_glyph, Some('息'));

        // Conversational query with "check" must NOT hijack to System 0
        let convo_query =
            "Can you check why the memory crystals are not syncing across nodes in the cluster?";
        let dec_convo = TripartiteRouter::route(convo_query, None);
        assert_ne!(dec_convo.tier, CognitiveTier::System0Sutra);
    }
}
