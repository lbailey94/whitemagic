//! Trusted bounded sweep planner (Gate 9A Slice 1).
//!
//! Pure planning over a coherent, already-bounded read snapshot produced by
//! `Store::sweep_preflight`. This module is the single planner truth: the
//! synthetic sizing test's in-memory reconstruction is not consulted here, and
//! production callers cannot construct a sealed plan any other way.
//!
//! Planning is deterministic: records are ordered by logical ingest time, tokens
//! are visited in sorted order, effects are canonically ordered before digests
//! are taken, and every statutory limit refuses (never truncates) before any
//! canonical mutation.

use std::collections::{BTreeMap, HashSet};

use crate::evidence::EvidenceRecord;
use crate::field::{self, RULE_ID, Relation, RelationState};
use crate::intake::OperationId;
use crate::sweep::{
    SweepEffect, SweepError, SweepLimits, SweepObserved, SweepRequest, VolatileUsageSnapshot,
};

/// Coherent read snapshot: every field is read inside one LMDB read transaction
/// and every collection is already bounded by [`SweepLimits`].
#[derive(Debug)]
pub(crate) struct SweepPreflightData {
    pub(crate) realm_id: [u8; 16],
    pub(crate) epoch: u64,
    /// Current sweep counter value; the commit transaction assigns this id.
    pub(crate) next_sweep_id: u64,
    pub(crate) records: Vec<EvidenceRecord>,
    pub(crate) relations: Vec<Relation>,
    pub(crate) df: BTreeMap<String, u64>,
    pub(crate) vectors: BTreeMap<u64, Vec<f32>>,
    pub(crate) observed: SweepObserved,
}

/// Caller-supplied planning inputs.
pub(crate) struct SweepPlanInputs<'a> {
    pub(crate) operation_id: OperationId,
    pub(crate) issuer_label: &'a str,
    pub(crate) limits: SweepLimits,
    pub(crate) rare_df_divisor: u64,
    pub(crate) rare_df_floor: u64,
    pub(crate) lifecycle_age_sweeps: u64,
    pub(crate) usage: VolatileUsageSnapshot,
}

/// Counts that explain a plan; they mirror the legacy sweep statistics without
/// changing what is planned.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub(crate) struct SweepPlanReport {
    pub(crate) pairs_lexical_candidates: u64,
    pub(crate) pairs_pruned_by_projection: u64,
    pub(crate) pairs_considered: u64,
    pub(crate) pairs_examined: u64,
    pub(crate) pairs_skipped_existing: u64,
    pub(crate) pairs_rejected_rule: u64,
    pub(crate) proposals: u64,
    pub(crate) promotions: u64,
    pub(crate) demotions: u64,
}

fn limit_error(dimension: &'static str, observed: u64, limit: u64) -> SweepError {
    SweepError::LimitExceeded {
        dimension,
        observed,
        limit,
    }
}

fn checked_add(value: u64, add: u64) -> Result<u64, SweepError> {
    value.checked_add(add).ok_or(SweepError::LengthOverflow)
}

/// Plan one sweep operation from a bounded coherent snapshot.
pub(crate) fn plan_sweep(
    data: &SweepPreflightData,
    inputs: SweepPlanInputs<'_>,
) -> Result<(SweepRequest, SweepPlanReport), SweepError> {
    let limits = inputs.limits;
    let mut report = SweepPlanReport::default();

    let mut records: Vec<&EvidenceRecord> = data.records.iter().collect();
    records.sort_by_key(|record| record.created_at());
    let n = records.len();
    let rare_max = (n as u64 / inputs.rare_df_divisor.max(1)).max(inputs.rare_df_floor);

    // Token index in declared sorted order (deterministic pair stream).
    let mut token_ids: BTreeMap<String, Vec<u64>> = BTreeMap::new();
    for record in &records {
        for token in field::tokenize(record.content()) {
            token_ids.entry(token).or_default().push(record.id());
        }
    }
    let df = |token: &str| -> u64 { data.df.get(token).copied().unwrap_or(0) };

    let existing: HashSet<(u64, u64)> = data
        .relations
        .iter()
        .map(|relation| (relation.src(), relation.dst()))
        .collect();
    let by_id: BTreeMap<u64, &EvidenceRecord> = records
        .iter()
        .map(|record| (record.id(), *record))
        .collect();

    let mut proposed: HashSet<(u64, u64)> = HashSet::new();
    let mut creates: Vec<SweepEffect> = Vec::new();
    let mut states: Vec<SweepEffect> = Vec::new();

    let mut effects_total = 0u64;
    for ids in token_ids.values() {
        if ids.len() < 2 {
            continue;
        }
        for (index, &a) in ids.iter().enumerate() {
            for &b in ids.iter().skip(index + 1) {
                report.pairs_lexical_candidates += 1;
                let (Some(&ra), Some(&rb)) = (by_id.get(&a), by_id.get(&b)) else {
                    continue;
                };
                let (earlier, later) = if ra.created_at() <= rb.created_at() {
                    (ra, rb)
                } else {
                    (rb, ra)
                };
                report.pairs_considered += 1;
                if report.pairs_examined >= limits.max_pair_examinations {
                    return Err(limit_error(
                        "pair_examinations",
                        report.pairs_examined + 1,
                        limits.max_pair_examinations,
                    ));
                }
                report.pairs_examined += 1;
                if existing.contains(&(later.id(), earlier.id())) {
                    report.pairs_skipped_existing += 1;
                    continue;
                }
                if !data.vectors.is_empty() {
                    let gate = match (
                        data.vectors.get(&later.id()),
                        data.vectors.get(&earlier.id()),
                    ) {
                        (Some(lv), Some(ev)) => {
                            crate::projection::cosine(lv, ev) >= crate::projection::TAU_SWEEP
                        }
                        _ => true,
                    };
                    if !gate {
                        report.pairs_pruned_by_projection += 1;
                        continue;
                    }
                }
                if let Some((src, dst, confidence)) =
                    field::propose_supersedes(later, earlier, rare_max as usize, &|term: &str| {
                        df(term) as usize
                    })
                {
                    // A pair can share several rare tokens; the canonical effect
                    // set keeps one create per ordered pair.
                    if !proposed.insert((src, dst)) {
                        report.pairs_skipped_existing += 1;
                        continue;
                    }
                    if effects_total >= limits.max_effects {
                        return Err(limit_error(
                            "effects",
                            effects_total + 1,
                            limits.max_effects,
                        ));
                    }
                    effects_total = checked_add(effects_total, 1)?;
                    report.proposals += 1;
                    creates.push(SweepEffect::CreateSupersedes {
                        src,
                        dst,
                        confidence_bits: confidence.to_bits(),
                        rule_id: RULE_ID.into(),
                    });
                } else {
                    report.pairs_rejected_rule += 1;
                }
            }
        }
    }

    let sweep = data.next_sweep_id;
    for relation in &data.relations {
        if relation.created_sweep() >= sweep {
            continue;
        }
        let used = inputs
            .usage
            .entries()
            .iter()
            .any(|entry| entry.relation_id == relation.id() && entry.count > 0);
        let transition = match relation.state() {
            RelationState::Candidate if used => Some(RelationState::Persistent),
            RelationState::Persistent
                if !used
                    && sweep.saturating_sub(relation.created_sweep())
                        >= inputs.lifecycle_age_sweeps =>
            {
                Some(RelationState::Cold)
            }
            _ => None,
        };
        if let Some(next_state) = transition {
            if effects_total >= limits.max_effects {
                return Err(limit_error(
                    "effects",
                    effects_total + 1,
                    limits.max_effects,
                ));
            }
            effects_total = checked_add(effects_total, 1)?;
            match next_state {
                RelationState::Persistent => report.promotions += 1,
                RelationState::Cold => report.demotions += 1,
                RelationState::Candidate => {}
            }
            states.push(SweepEffect::SetRelationState {
                relation_id: relation.id(),
                expected_prior_state: relation.state(),
                next_state,
            });
        }
    }

    // Canonical effect order required by the contract: creates sorted by
    // (src, dst) before state transitions sorted by relation id.
    creates.sort_by_key(|effect| match effect {
        SweepEffect::CreateSupersedes { src, dst, .. } => (*src, *dst),
        SweepEffect::SetRelationState { relation_id, .. } => (*relation_id, 0),
    });
    states.sort_by_key(|effect| match effect {
        SweepEffect::SetRelationState { relation_id, .. } => (*relation_id, 0),
        SweepEffect::CreateSupersedes { src, dst, .. } => (*src, *dst),
    });
    let mut effects = creates;
    effects.extend(states);

    let effects_len = u64::try_from(effects.len()).map_err(|_| SweepError::LengthOverflow)?;
    if effects_len != effects_total {
        return Err(SweepError::EffectCountMismatch);
    }
    let observed = SweepObserved {
        effects: effects_total,
        pair_examinations: report.pairs_examined,
        ..data.observed
    };

    let policy_digest = crate::sweep::sweep_policy_digest(
        crate::sweep::SweepPolicyInputs {
            rare_df_divisor: inputs.rare_df_divisor,
            rare_df_floor: inputs.rare_df_floor,
            lifecycle_age_sweeps: inputs.lifecycle_age_sweeps,
        },
        limits,
    );
    let request = SweepRequest::production(
        inputs.issuer_label,
        inputs.operation_id,
        data.realm_id,
        data.epoch,
        limits,
        observed,
        policy_digest,
        inputs.usage,
        effects,
    )?;
    Ok((request, report))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::evidence::{Class, Domain, RecordStatus};
    use crate::sweep::{LIFECYCLE_AGE_SWEEPS, SWEEP_PROFILE_V1, VolatileUsageSnapshot};

    fn record(id: u64, content: &str) -> EvidenceRecord {
        EvidenceRecord::from_wire(
            id,
            Domain::Reported,
            Class::Evidence,
            content.to_string(),
            format!("fixture:{id}"),
            1.0,
            RecordStatus::Persistent,
            id,
        )
    }

    fn data(records: Vec<EvidenceRecord>, relations: Vec<Relation>) -> SweepPreflightData {
        let raw: u64 = records
            .iter()
            .map(|r| (r.content().len() + r.source().len()) as u64)
            .sum();
        let largest = records
            .iter()
            .map(|r| (r.content().len() + r.source().len()) as u64)
            .max()
            .unwrap_or(0);
        let tokens: u64 = records
            .iter()
            .map(|r| field::tokenize(r.content()).len() as u64)
            .sum();
        let mut df = BTreeMap::new();
        for r in &records {
            for token in field::tokenize(r.content()) {
                *df.entry(token).or_insert(0_u64) += 1;
            }
        }
        SweepPreflightData {
            realm_id: [4; 16],
            epoch: 2,
            next_sweep_id: 0,
            observed: SweepObserved {
                records_scanned: records.len() as u64,
                raw_record_bytes: raw,
                largest_record_bytes: largest,
                postings_bytes: 0,
                token_occurrences: tokens,
                relations_scanned: relations.len() as u64,
                pair_examinations: 0,
                effects: 0,
            },
            records,
            relations,
            df,
            vectors: BTreeMap::new(),
        }
    }

    fn usage(entries: Vec<(u64, u64)>) -> VolatileUsageSnapshot {
        VolatileUsageSnapshot::synthetic(
            [9; 16],
            1,
            entries
                .into_iter()
                .map(|(relation_id, count)| crate::sweep::UsageEntry { relation_id, count })
                .collect(),
        )
    }

    fn inputs<'a>(limits: SweepLimits, usage: &'a VolatileUsageSnapshot) -> SweepPlanInputs<'a> {
        SweepPlanInputs {
            operation_id: OperationId::from_bytes([7; 16]),
            issuer_label: "sweep-planner-test",
            limits,
            rare_df_divisor: 20,
            rare_df_floor: 2,
            lifecycle_age_sweeps: LIFECYCLE_AGE_SWEEPS,
            usage: usage.clone(),
        }
    }

    #[test]
    fn plan_is_deterministic_and_effect_bound() {
        let records = vec![
            record(0, "color red shared"),
            record(1, "color blue shared"),
            record(2, "color green shared"),
        ];
        let preflight = data(records, Vec::new());
        let usage = usage(Vec::new());
        let (first, report) = plan_sweep(&preflight, inputs(SWEEP_PROFILE_V1, &usage)).unwrap();
        let (second, _) = plan_sweep(&preflight, inputs(SWEEP_PROFILE_V1, &usage)).unwrap();
        assert_eq!(first.digest(), second.digest());
        assert_eq!(first.effects(), second.effects());
        assert_eq!(report.proposals as usize, first.effects().len());
        assert_eq!(report.pairs_examined, first.observed().pair_examinations);
        assert_eq!(first.observed().effects, first.effects().len() as u64);
    }

    #[test]
    fn duplicate_pair_across_tokens_produces_one_effect() {
        // Two rare tokens (df = 2) shared by the same pair visit it twice.
        let records = vec![
            record(0, "tokA tokB value zero"),
            record(1, "tokA tokB value one"),
        ];
        let preflight = data(records, Vec::new());
        let usage = usage(Vec::new());
        let (request, report) = plan_sweep(&preflight, inputs(SWEEP_PROFILE_V1, &usage)).unwrap();
        // tokA, tokB and the shared "value" token each visit the pair once.
        assert_eq!(report.pairs_examined, 3);
        assert_eq!(request.effects().len(), 1);
        assert_eq!(report.pairs_skipped_existing, 2);
    }

    #[test]
    fn pair_cap_refuses_instead_of_truncating() {
        let records: Vec<EvidenceRecord> = (0..130)
            .map(|id| record(id, &format!("sh common unique{id}")))
            .collect();
        let preflight = data(records, Vec::new());
        let usage = usage(Vec::new());
        let mut limits = SWEEP_PROFILE_V1;
        limits.max_pair_examinations = 100;
        let error = plan_sweep(&preflight, inputs(limits, &usage)).unwrap_err();
        assert!(matches!(
            error,
            SweepError::LimitExceeded {
                dimension: "pair_examinations",
                ..
            }
        ));
    }

    #[test]
    fn effect_cap_refuses_instead_of_truncating() {
        // Five rare shared tokens (df = 2) each link one pair; every pair proposes.
        let mut records = Vec::new();
        for pair in 0..5_u64 {
            let base = pair * 2;
            records.push(record(base, &format!("tok{pair} valuea{base}")));
            records.push(record(base + 1, &format!("tok{pair} valueb{base}")));
        }
        let preflight = data(records, Vec::new());
        let usage = usage(Vec::new());
        let mut limits = SWEEP_PROFILE_V1;
        limits.max_effects = 3;
        let error = plan_sweep(&preflight, inputs(limits, &usage)).unwrap_err();
        assert!(matches!(
            error,
            SweepError::LimitExceeded {
                dimension: "effects",
                ..
            }
        ));
    }

    #[test]
    fn lifecycle_uses_volatile_usage_and_expected_prior_state() {
        let relation = Relation::new(0, 2, 1, 0.9, 0);
        let mut preflight = data(
            vec![record(0, "x"), record(1, "y"), record(2, "z")],
            vec![relation],
        );
        // The relation was created by sweep 0; this plan is for sweep 1.
        preflight.next_sweep_id = 1;
        let usage = usage(vec![(0, 3)]);
        let (request, report) = plan_sweep(&preflight, inputs(SWEEP_PROFILE_V1, &usage)).unwrap();
        assert_eq!(report.promotions, 1);
        assert_eq!(
            request.effects(),
            &[SweepEffect::SetRelationState {
                relation_id: 0,
                expected_prior_state: RelationState::Candidate,
                next_state: RelationState::Persistent,
            }]
        );
    }

    #[test]
    fn usage_snapshot_is_bounded_by_the_relations_limit() {
        let preflight = data(vec![record(0, "x")], Vec::new());
        let usage = usage(vec![(0, 1), (1, 1), (2, 1)]);
        let mut limits = SWEEP_PROFILE_V1;
        limits.max_relations_scanned = 2;
        let error = plan_sweep(&preflight, inputs(limits, &usage)).unwrap_err();
        assert!(matches!(error, SweepError::InvalidUsage(_)));
    }

    #[test]
    fn profile_v1_matches_ratified_values() {
        assert_eq!(
            SWEEP_PROFILE_V1,
            SweepLimits {
                max_records_scanned: 256,
                max_raw_record_bytes: 16 * 1024,
                max_single_record_bytes: 1024,
                max_postings_bytes: 2 * 1024,
                max_token_occurrences: 1024,
                max_relations_scanned: 256,
                max_pair_examinations: 8192,
                max_effects: 1024,
            }
        );
    }
}
