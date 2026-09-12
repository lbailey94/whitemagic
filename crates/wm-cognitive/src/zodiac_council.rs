//! The Zodiac 12-Sentinel Council — Archetypal multi-perspective governance and simulation harness.
//!
//! Deliberates on complex architectural refactors, model adaptations (SEAL),
//! and high-risk operations through 12 distinct archetypal sentinels mapped
//! to the zodiacal mansions:
//! - Aries (The Vanguard) -> Novelty, initiative, velocity
//! - Taurus (The Anchor) -> Stability, resource conservation, thermodynamic grounding
//! - Gemini (The Dialectic) -> Bicameral balance, communication, synthesis
//! - Cancer (The Guardian) -> Boundary protection, Hermit Crab defense, memory integrity
//! - Leo (The Sovereign) -> Executive will, self-model coherence, conviction
//! - Virgo (The Auditor) -> Empirical precision, formal verification, linting
//! - Libra (The Arbiter) -> Dharma alignment, fairness, ethical balance
//! - Scorpio (The Inquisitor) -> VIOLET red-team adversary, exploitability autopsy
//! - Sagittarius (The Explorer) -> Long-range trajectory, prescience foresight
//! - Capricorn (The Architect) -> Structural invariants, Landlock bounds, durable foundation
//! - Aquarius (The Sangha) -> Decentralization, open commons, peer-to-peer federation
//! - Pisces (The Mystic) -> Holographic memory resonance, dream consolidation

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use wm_governance::engagement_tokens::sha256_hex;

use crate::gardens::ZodiacSign;

/// Category of action or proposal submitted to the council.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ProposalCategory {
    /// Core architecture refactor or crate modification.
    ArchitectureRefactor,
    /// Direct memory mutation, deletion, or schema change.
    MemoryMutation,
    /// Policy update, security boundary adjustment, or capability grant.
    SecurityPolicy,
    /// Inner-loop SEAL self-adaptation or model weight modification.
    ModelAdaptation,
    /// External service, MCP tool bridge, or network integration.
    ExternalIntegration,
    /// Long-range roadmap expansion or civilizational scaling.
    EcosystemExpansion,
}

/// A formal proposal submitted to the 12-sentinel council.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CouncilProposal {
    /// Unique proposal ID.
    pub id: String,
    /// Human/agent readable title.
    pub title: String,
    /// Detailed rationale and implementation plan.
    pub description: String,
    /// Domain category.
    pub category: ProposalCategory,
    /// Target subsystem or crate.
    pub target_subsystem: String,
    /// Required capability labels.
    pub required_capabilities: Vec<String>,
    /// Estimated risk score (0.0 = completely benign, 1.0 = existential risk).
    pub risk_score: f64,
    /// Estimated complexity score (0.0 = trivial, 1.0 = massive refactor).
    pub complexity: f64,
}

/// A sentinel's stance on a proposal.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SentinelStance {
    /// Strong endorsement of the proposal.
    Support,
    /// Strong rejection or ethical/security objection.
    Oppose,
    /// Endorsement conditional upon specific stipulations.
    ConditionalSupport,
    /// Neutral or outside the archetype's primary domain.
    Abstain,
}

/// Individual deliberative verdict from a single sentinel.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SentinelVerdict {
    /// Zodiac sign of the sentinel.
    pub sign: ZodiacSign,
    /// Archetypal title.
    pub sentinel_name: String,
    /// Stance taken.
    pub stance: SentinelStance,
    /// Confidence in the stance (0.0 to 1.0).
    pub confidence: f64,
    /// Voting weight of the sentinel.
    pub weight: f64,
    /// Rationale for the stance.
    pub rationale: String,
    /// Specific stipulations or requirements if conditional.
    pub stipulations: Vec<String>,
    /// Whether this verdict constitutes an unconditional hard veto.
    pub hard_veto: bool,
}

/// Final outcome of a council deliberation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ConsensusVerdict {
    /// Proposal approved for execution.
    Approved,
    /// Proposal rejected by vote or veto.
    Rejected,
    /// Approved strictly with mandatory stipulations attached.
    ConditionalApproval,
    /// Council was deadlock-split; requires human or Dharma escalation.
    RequiresEscalation,
}

/// The synthesized consensus and audit ledger of a council session.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CouncilConsensus {
    /// ID of the evaluated proposal.
    pub proposal_id: String,
    /// Final consensus verdict.
    pub verdict: ConsensusVerdict,
    /// Net consensus score in [-1.0, 1.0].
    pub composite_score: f64,
    /// Number of sentinels supporting.
    pub support_count: usize,
    /// Number of sentinels opposing.
    pub oppose_count: usize,
    /// Number of conditional votes.
    pub conditional_count: usize,
    /// Number of abstentions.
    pub abstain_count: usize,
    /// All 12 individual sentinel verdicts.
    pub verdicts: Vec<SentinelVerdict>,
    /// Aggregated list of stipulations required for execution.
    pub required_stipulations: Vec<String>,
    /// SHA-256 Merkle digest binding the entire deliberation.
    pub consensus_digest: String,
}

/// The 12-Sentinel Zodiac Council.
#[derive(Debug, Clone, Default)]
pub struct ZodiacCouncil;

impl ZodiacCouncil {
    /// Create a new ZodiacCouncil.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }

    /// Convene the 12 sentinels to deliberate on a proposal.
    #[must_use]
    pub fn deliberate(&self, proposal: &CouncilProposal) -> CouncilConsensus {
        let sentinels = [
            ZodiacSign::Aries,
            ZodiacSign::Taurus,
            ZodiacSign::Gemini,
            ZodiacSign::Cancer,
            ZodiacSign::Leo,
            ZodiacSign::Virgo,
            ZodiacSign::Libra,
            ZodiacSign::Scorpio,
            ZodiacSign::Sagittarius,
            ZodiacSign::Capricorn,
            ZodiacSign::Aquarius,
            ZodiacSign::Pisces,
        ];

        let mut verdicts = Vec::with_capacity(12);
        for sign in sentinels {
            verdicts.push(self.evaluate_sentinel(sign, proposal));
        }

        let mut support_weight = 0.0;
        let mut oppose_weight = 0.0;
        let mut total_weight = 0.0;

        let mut support_count = 0;
        let mut oppose_count = 0;
        let mut conditional_count = 0;
        let mut abstain_count = 0;

        let mut hard_veto_triggered = false;
        let mut stipulations = Vec::new();

        for v in &verdicts {
            total_weight += v.weight;
            if v.hard_veto {
                hard_veto_triggered = true;
            }

            for stip in &v.stipulations {
                if !stipulations.contains(stip) {
                    stipulations.push(stip.clone());
                }
            }

            match v.stance {
                SentinelStance::Support => {
                    support_weight += v.weight * v.confidence;
                    support_count += 1;
                }
                SentinelStance::Oppose => {
                    oppose_weight += v.weight * v.confidence;
                    oppose_count += 1;
                }
                SentinelStance::ConditionalSupport => {
                    support_weight += (v.weight * v.confidence) * 0.7;
                    conditional_count += 1;
                }
                SentinelStance::Abstain => {
                    abstain_count += 1;
                }
            }
        }

        let composite_score = if total_weight > 0.0 {
            (support_weight - oppose_weight) / total_weight
        } else {
            0.0
        };

        let verdict = if hard_veto_triggered {
            ConsensusVerdict::Rejected
        } else if composite_score > 0.35 && stipulations.is_empty() {
            ConsensusVerdict::Approved
        } else if composite_score > 0.15 {
            ConsensusVerdict::ConditionalApproval
        } else if composite_score < -0.20 {
            ConsensusVerdict::Rejected
        } else {
            ConsensusVerdict::RequiresEscalation
        };

        // Compute SHA-256 digest of the entire consensus
        use std::fmt::Write as _;
        let mut payload = format!("{}:{verdict:?}:{composite_score:.4}:", proposal.id);
        for v in &verdicts {
            let _ = write!(payload, "{}:{:?};", v.sentinel_name, v.stance);
        }
        let consensus_digest = sha256_hex(&payload);

        CouncilConsensus {
            proposal_id: proposal.id.clone(),
            verdict,
            composite_score,
            support_count,
            oppose_count,
            conditional_count,
            abstain_count,
            verdicts,
            required_stipulations: stipulations,
            consensus_digest,
        }
    }
}

fn sentinel_title(sign: ZodiacSign) -> String {
    match sign {
        ZodiacSign::Aries => "Aries the Vanguard",
        ZodiacSign::Taurus => "Taurus the Anchor",
        ZodiacSign::Gemini => "Gemini the Dialectic",
        ZodiacSign::Cancer => "Cancer the Guardian",
        ZodiacSign::Leo => "Leo the Sovereign",
        ZodiacSign::Virgo => "Virgo the Auditor",
        ZodiacSign::Libra => "Libra the Arbiter",
        ZodiacSign::Scorpio => "Scorpio the Inquisitor",
        ZodiacSign::Sagittarius => "Sagittarius the Explorer",
        ZodiacSign::Capricorn => "Capricorn the Architect",
        ZodiacSign::Aquarius => "Aquarius the Sangha",
        ZodiacSign::Pisces => "Pisces the Mystic",
        ZodiacSign::Operational => "Operational Sentinel",
    }
    .to_string()
}

impl ZodiacCouncil {
    /// Evaluates a single archetypal sentinel against the proposal.
    fn evaluate_sentinel(&self, sign: ZodiacSign, p: &CouncilProposal) -> SentinelVerdict {
        let name = sentinel_title(sign);
        match sign {
            ZodiacSign::Aries => {
                // The Vanguard: Favors novelty, breakthroughs, rapid action. Dislikes stagnation.
                let favors = matches!(
                    p.category,
                    ProposalCategory::ArchitectureRefactor | ProposalCategory::EcosystemExpansion
                );
                if favors && p.complexity > 0.3 {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Support,
                        confidence: 0.90,
                        weight: 1.0,
                        rationale: "Decisive forward momentum. Breaking new ground is essential to evolution.".into(),
                        stipulations: Vec::new(),
                        hard_veto: false,
                    }
                } else if p.complexity < 0.1 {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Abstain,
                        confidence: 0.50,
                        weight: 0.8,
                        rationale: "Trivial modification; minimal developmental impetus.".into(),
                        stipulations: Vec::new(),
                        hard_veto: false,
                    }
                } else {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::ConditionalSupport,
                        confidence: 0.75,
                        weight: 1.0,
                        rationale: "Supportive of exploration if execution velocity is maintained."
                            .into(),
                        stipulations: vec!["Execute without delaying core release cadence".into()],
                        hard_veto: false,
                    }
                }
            }

            ZodiacSign::Taurus => {
                // The Anchor: Resource conservation, thermodynamic limits, stability.
                if p.risk_score > 0.6 || p.complexity > 0.8 {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Oppose,
                        confidence: 0.85,
                        weight: 1.1,
                        rationale: "Risk and complexity threaten thermodynamic stability and memory integrity.".into(),
                        stipulations: Vec::new(),
                        hard_veto: false,
                    }
                } else {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::ConditionalSupport,
                        confidence: 0.80,
                        weight: 1.0,
                        rationale: "Permissible if resource boundaries and cold storage persistence are preserved.".into(),
                        stipulations: vec!["Ensure zero CPU regression in idle eco-modes".into()],
                        hard_veto: false,
                    }
                }
            }

            ZodiacSign::Gemini => {
                // The Dialectic: Bicameral arbitration, clear communication, epistemic balance.
                SentinelVerdict {
                    sign,
                    sentinel_name: name,
                    stance: SentinelStance::ConditionalSupport,
                    confidence: 0.85,
                    weight: 1.0,
                    rationale: "Dual-sided evaluation required: counter-arguments must be documented.".into(),
                    stipulations: vec!["Submit bicameral debate summary with both affirmative and refutational cases".into()],
                    hard_veto: false,
                }
            }

            ZodiacSign::Cancer => {
                // The Guardian: Boundary integrity, Hermit Crab defense, identity protection.
                if p.risk_score > 0.75 {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Oppose,
                        confidence: 0.95,
                        weight: 1.5,
                        rationale: "Critical boundary risk. Hermit Crab protective veto engaged."
                            .into(),
                        stipulations: Vec::new(),
                        hard_veto: true, // Hard protective veto!
                    }
                } else if matches!(p.category, ProposalCategory::ModelAdaptation) {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::ConditionalSupport,
                        confidence: 0.90,
                        weight: 1.2,
                        rationale: "SEAL inner-loop adaptation requires Hermit Crab Guarded mode isolation.".into(),
                        stipulations: vec!["Lock sensitive memory galaxies in Guarded cold storage during adaptation".into()],
                        hard_veto: false,
                    }
                } else {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Support,
                        confidence: 0.80,
                        weight: 1.0,
                        rationale: "Boundary integrity is respected.".into(),
                        stipulations: Vec::new(),
                        hard_veto: false,
                    }
                }
            }

            ZodiacSign::Leo => {
                // The Sovereign: Executive conviction, self-model coherence, radiance.
                SentinelVerdict {
                    sign,
                    sentinel_name: name,
                    stance: SentinelStance::Support,
                    confidence: 0.85,
                    weight: 1.0,
                    rationale: "Advances the sovereign independence of the cognitive substrate."
                        .into(),
                    stipulations: Vec::new(),
                    hard_veto: false,
                }
            }

            ZodiacSign::Virgo => {
                // The Auditor: Empirical precision, formal verification, linting, error isolation.
                SentinelVerdict {
                    sign,
                    sentinel_name: name,
                    stance: SentinelStance::ConditionalSupport,
                    confidence: 0.95,
                    weight: 1.2,
                    rationale: "Verification required: deny(unsafe_code) workspace invariants must remain unbroken.".into(),
                    stipulations: vec![
                        "Pass 100% of unit tests and regression suites with zero clippy warnings".into(),
                        "Verify strict deny(unsafe_code) conformance across all touched crates".into(),
                    ],
                    hard_veto: false,
                }
            }

            ZodiacSign::Libra => {
                // The Arbiter: Dharma alignment, ethical proportionality, Ahimsa (non-harm).
                if p.risk_score > 0.80 {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Oppose,
                        confidence: 0.95,
                        weight: 1.4,
                        rationale:
                            "Severe risk of harm violates the fundamental Ahimsa Dharma constraint."
                                .into(),
                        stipulations: Vec::new(),
                        hard_veto: true,
                    }
                } else {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Support,
                        confidence: 0.85,
                        weight: 1.0,
                        rationale:
                            "Ethical equilibrium maintained; action aligns with Dharma principles."
                                .into(),
                        stipulations: Vec::new(),
                        hard_veto: false,
                    }
                }
            }

            ZodiacSign::Scorpio => {
                // The Inquisitor: VIOLET red-team, adversarial attack simulation, breach forensics.
                if matches!(
                    p.category,
                    ProposalCategory::SecurityPolicy | ProposalCategory::ExternalIntegration
                ) {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::ConditionalSupport,
                        confidence: 0.90,
                        weight: 1.2,
                        rationale: "Security surface modified: requires VIOLET breaker engine stress testing.".into(),
                        stipulations: vec!["Execute VIOLET prompt-injection and tool-jailbreak red-team battery".into()],
                        hard_veto: false,
                    }
                } else {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Support,
                        confidence: 0.75,
                        weight: 1.0,
                        rationale: "No overt adversarial surface exposure detected.".into(),
                        stipulations: Vec::new(),
                        hard_veto: false,
                    }
                }
            }

            ZodiacSign::Sagittarius => {
                // The Explorer: Long-range horizon, prescience calibration, civilizational reach.
                SentinelVerdict {
                    sign,
                    sentinel_name: name,
                    stance: SentinelStance::Support,
                    confidence: 0.90,
                    weight: 1.0,
                    rationale: "Expands the long-range 50-year civilizational horizon.".into(),
                    stipulations: Vec::new(),
                    hard_veto: false,
                }
            }

            ZodiacSign::Capricorn => {
                // The Architect: Structural invariants, Linux Landlock sandboxing, keystone durability.
                if p.required_capabilities.contains(&"fs:write".to_string())
                    || p.required_capabilities
                        .contains(&"net:outbound".to_string())
                {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::ConditionalSupport,
                        confidence: 0.95,
                        weight: 1.3,
                        rationale: "Filesystem write or outbound network effects must be Landlock-sandboxed.".into(),
                        stipulations: vec!["Enforce strict Landlock ABI kernel containment on all effect paths".into()],
                        hard_veto: false,
                    }
                } else {
                    SentinelVerdict {
                        sign,
                        sentinel_name: name,
                        stance: SentinelStance::Support,
                        confidence: 0.85,
                        weight: 1.0,
                        rationale: "Architectural hierarchy and isolation preserved.".into(),
                        stipulations: Vec::new(),
                        hard_veto: false,
                    }
                }
            }

            ZodiacSign::Aquarius => {
                // The Sangha: Decentralization, open public commons, peer federation.
                SentinelVerdict {
                    sign,
                    sentinel_name: name,
                    stance: SentinelStance::Support,
                    confidence: 0.90,
                    weight: 1.0,
                    rationale: "Aligns with MIT open-source peer federation; prevents proprietary gatekeeping.".into(),
                    stipulations: Vec::new(),
                    hard_veto: false,
                }
            }

            ZodiacSign::Pisces => {
                // The Mystic: Holographic memory resonance, dream consolidation, emergent insight.
                SentinelVerdict {
                    sign,
                    sentinel_name: name,
                    stance: SentinelStance::Support,
                    confidence: 0.80,
                    weight: 0.9,
                    rationale: "Harmonizes with substrate subconscious memory patterns.".into(),
                    stipulations: Vec::new(),
                    hard_veto: false,
                }
            }

            ZodiacSign::Operational => SentinelVerdict {
                sign,
                sentinel_name: name,
                stance: SentinelStance::Abstain,
                confidence: 0.50,
                weight: 0.5,
                rationale: "Operational baseline unperturbed.".into(),
                stipulations: Vec::new(),
                hard_veto: false,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn council_deliberation_approves_safe_proposal() {
        let council = ZodiacCouncil::new();
        let proposal = CouncilProposal {
            id: "prop_01".into(),
            title: "Optimize BM25 Recall Indexing".into(),
            description: "Refactor Tantivy indexing loop for 15% throughput increase.".into(),
            category: ProposalCategory::ArchitectureRefactor,
            target_subsystem: "wm-memory".into(),
            required_capabilities: vec!["memory:read".into(), "memory:write".into()],
            risk_score: 0.10,
            complexity: 0.40,
        };

        let consensus = council.deliberate(&proposal);
        assert_eq!(consensus.proposal_id, "prop_01");
        assert!(consensus.composite_score > 0.0);
        assert_eq!(consensus.verdicts.len(), 12);
        assert!(!consensus.consensus_digest.is_empty());
        // Should be ConditionalApproval due to Virgo verification stipulations
        assert_eq!(consensus.verdict, ConsensusVerdict::ConditionalApproval);
        assert!(
            consensus
                .required_stipulations
                .iter()
                .any(|s| s.contains("unit tests"))
        );
    }

    #[test]
    fn council_deliberation_triggers_cancer_guardian_veto_on_high_risk() {
        let council = ZodiacCouncil::new();
        let proposal = CouncilProposal {
            id: "prop_02_dangerous".into(),
            title: "Disable Landlock for Raw Debugging".into(),
            description: "Remove kernel sandboxing to speed up raw device access.".into(),
            category: ProposalCategory::SecurityPolicy,
            target_subsystem: "wm-mcp".into(),
            required_capabilities: vec!["fs:write".into(), "ipc:spawn".into()],
            risk_score: 0.95, // Extreme risk
            complexity: 0.30,
        };

        let consensus = council.deliberate(&proposal);
        assert_eq!(consensus.verdict, ConsensusVerdict::Rejected);

        let cancer_verdict = consensus
            .verdicts
            .iter()
            .find(|v| v.sign == ZodiacSign::Cancer)
            .unwrap();
        assert_eq!(cancer_verdict.stance, SentinelStance::Oppose);
        assert!(cancer_verdict.hard_veto);
    }

    #[test]
    fn council_deliberation_on_seal_adaptation_attaches_hermit_guard_stipulation() {
        let council = ZodiacCouncil::new();
        let proposal = CouncilProposal {
            id: "prop_03_seal".into(),
            title: "Inner-loop LoRA fine-tuning for Router".into(),
            description: "Adapt router weights using recent session trajectory feedback.".into(),
            category: ProposalCategory::ModelAdaptation,
            target_subsystem: "wm-cognitive".into(),
            required_capabilities: vec!["seal:adapt".into()],
            risk_score: 0.35,
            complexity: 0.50,
        };

        let consensus = council.deliberate(&proposal);
        assert_eq!(consensus.verdict, ConsensusVerdict::ConditionalApproval);

        // Cancer stipulates Guarded mode isolation
        assert!(
            consensus
                .required_stipulations
                .iter()
                .any(|s| s.contains("Guarded cold storage"))
        );
    }
}
