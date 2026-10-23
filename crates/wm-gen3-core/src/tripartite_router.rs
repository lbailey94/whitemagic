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

pub struct TripartiteRouter;

impl TripartiteRouter {
    /// Evaluate a user task or instruction against the tripartite hierarchy.
    #[must_use]
    pub fn route(prompt: &str, bio_state: Option<&BioelectricState>) -> RoutingDecision {
        let t0 = Instant::now();
        let trimmed = prompt.trim();

        // 1. System 0: Direct Logoglyphic Canon Detection (<1 µs)
        for glyph in SutraGlyph::ALL {
            let c = glyph.as_char();
            let a = glyph.alchemical_char();
            if trimmed.contains(c) || trimmed.contains(a) {
                let matched = if trimmed.contains(c) { c } else { a };
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

        // Detect potential thesis / antithesis pairs
        let wants_exec = lower.contains("execute")
            || lower.contains("commit")
            || lower.contains("dispatch")
            || lower.contains("run");
        let wants_sim = lower.contains("simulate")
            || lower.contains("shadow")
            || lower.contains("dry-run")
            || lower.contains("dryrun");
        let wants_verify = lower.contains("verify")
            || lower.contains("test")
            || lower.contains("proof")
            || lower.contains("check");
        let wants_fuzz = lower.contains("fuzz")
            || lower.contains("redteam")
            || lower.contains("discriminate")
            || lower.contains("adversarial");

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

        let keyword_match = if wants_verify {
            Some(SutraGlyph::Zheng)
        } else if wants_exec {
            Some(SutraGlyph::Xing)
        } else if lower.contains("survey")
            || lower.contains("inspect")
            || lower.contains("lookup")
            || lower.contains("status")
        {
            Some(SutraGlyph::Guan)
        } else if lower.contains("probe") || lower.contains("telemetry") {
            Some(SutraGlyph::Cha)
        } else if wants_fuzz {
            Some(SutraGlyph::Bian)
        } else if wants_sim {
            Some(SutraGlyph::Ni)
        } else if lower.contains("clean") || lower.contains("prune") || lower.contains("compact") {
            Some(SutraGlyph::Qing)
        } else if lower.contains("dream") || lower.contains("sleep") || lower.contains("quiesce") {
            Some(SutraGlyph::Xi)
        } else if lower.contains("sync")
            || lower.contains("resonate")
            || lower.contains("mesh")
            || lower.contains("peer")
        {
            Some(SutraGlyph::Ying)
        } else if lower.contains("sandbox") || lower.contains("kekkai") || lower.contains("confine")
        {
            Some(SutraGlyph::Jie)
        } else if lower.contains("synthesize") || lower.contains("unify") {
            Some(SutraGlyph::He)
        } else if lower.contains("decompose") || lower.contains("decouple") {
            Some(SutraGlyph::Fen)
        } else if lower.contains("diff") || lower.contains("illuminate") {
            Some(SutraGlyph::Zhao)
        } else if lower.contains("clarify") || lower.contains("settle") {
            Some(SutraGlyph::Cheng)
        } else if lower.contains("fork") || lower.contains("sprout") {
            Some(SutraGlyph::Ya)
        } else if lower.contains("transmute") || lower.contains("dissolve") {
            Some(SutraGlyph::Hua)
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
}
