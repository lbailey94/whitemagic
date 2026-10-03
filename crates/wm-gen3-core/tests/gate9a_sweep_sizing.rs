//! Bounded synthetic sizing for the planned Gate 9A sweep preflight.
//!
//! This is deliberately not `Substrate::think_sweep`: it makes no LMDB writes,
//! does not call models, and has no production effect.  It calls the actual Rust
//! tokenizer and supersession rule so that token and candidate measurements are
//! faithful to the current lexical algorithm.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::time::{Duration, Instant};

use wm_gen3_core::evidence::{EvidenceRecord, EvidenceStore};
use wm_gen3_core::field::{propose_supersedes, tokenize};

const REPETITIONS: usize = 3;
const MAX_FIXTURE_RECORDS: usize = 384;
const MAX_CONTENT_BYTES_PER_RECORD: usize = 2_048;
const MAX_FIXTURE_RELATIONS: usize = 512;
const MAX_FIXTURE_TOTAL_CONTENT_BYTES: usize = 786_432;
const MAX_FIXTURE_TOKEN_OCCURRENCES: usize = 20_000;
const MAX_FIXTURE_POSTING_BYTES: usize = 131_072;
const MAX_FIXTURE_PAIR_EXAMINATIONS: usize = 32_768;
const MAX_FIXTURE_EFFECTS: usize = 8_192;

#[derive(Debug, Clone, PartialEq, Eq)]
struct Observed {
    records_scanned: usize,
    raw_record_bytes: usize,
    max_raw_record_bytes: usize,
    token_occurrences: usize,
    unique_terms: usize,
    max_tokens_per_record: usize,
    postings_bytes: usize,
    posting_ids_examined: usize,
    relations_scanned: usize,
    pairs_lexical_candidates: usize,
    pair_examinations: usize,
    effects: usize,
    peak_token_ids: usize,
    peak_existing_pairs: usize,
    peak_by_id: usize,
}

#[derive(Debug, Clone)]
struct Run {
    observed: Observed,
    elapsed: Duration,
}

#[derive(Debug, Clone, Copy)]
struct Fixture {
    name: &'static str,
    records: usize,
    relation_count: usize,
    extra_bytes_on_first_record: usize,
}

fn fixture_records(fixture: Fixture) -> Vec<EvidenceRecord> {
    assert!(fixture.records <= MAX_FIXTURE_RECORDS);
    assert!(fixture.relation_count <= MAX_FIXTURE_RELATIONS);
    assert!(fixture.extra_bytes_on_first_record <= MAX_CONTENT_BYTES_PER_RECORD);

    let mut evidence = EvidenceStore::new();
    let group_size = (fixture.records / 20).max(2);
    for index in 0..fixture.records {
        let group = index / group_size;
        let mut content = format!(
            "subjectgroup{group} value{index} context{} evidence{}",
            index % 11,
            index % 17
        );
        if index == 0 && fixture.extra_bytes_on_first_record > 0 {
            // A single large token catches the exact failure mode where a token
            // count is small but the materialized raw input is large.
            content.push(' ');
            content.push_str(&"x".repeat(fixture.extra_bytes_on_first_record));
        }
        assert!(content.len() <= MAX_CONTENT_BYTES_PER_RECORD + 128);
        evidence.reported(&content, "synthetic:gate9a-sizing");
    }
    let records = (0..fixture.records as u64)
        .map(|id| evidence.get(id).expect("synthetic record").clone())
        .collect::<Vec<_>>();
    assert!(
        records
            .iter()
            .map(|record| record.content().len())
            .sum::<usize>()
            <= MAX_FIXTURE_TOTAL_CONTENT_BYTES
    );
    records
}

fn measure(records: &[EvidenceRecord], relation_count: usize) -> Run {
    let started = Instant::now();
    let mut token_ids: BTreeMap<String, Vec<u64>> = BTreeMap::new();
    let mut raw_record_bytes = 0;
    let mut max_raw_record_bytes = 0;
    let mut token_occurrences = 0;
    let mut max_tokens_per_record = 0;
    for record in records {
        // This is raw input payload size (content + source), intentionally not
        // a guessed MessagePack size. The eventual Store preflight must count
        // actual serialized reads separately when it reads LMDB.
        let raw_bytes = record.content().len() + record.source().len();
        raw_record_bytes += raw_bytes;
        max_raw_record_bytes = max_raw_record_bytes.max(raw_bytes);
        let terms = tokenize(record.content());
        token_occurrences += terms.len();
        max_tokens_per_record = max_tokens_per_record.max(terms.len());
        for term in terms {
            token_ids.entry(term).or_default().push(record.id());
        }
    }

    // Match the current `df` inputs by encoding exactly the Vec<u64> posting
    // shape used by Store, while keeping this harness read-only and in-memory.
    let mut postings_bytes = 0;
    let mut posting_ids_examined = 0;
    let mut df = HashMap::new();
    for (term, ids) in &token_ids {
        postings_bytes += rmp_serde::to_vec(ids)
            .expect("synthetic posting encode")
            .len();
        posting_ids_examined += ids.len();
        df.insert(term.clone(), ids.len());
    }
    assert!(token_occurrences <= MAX_FIXTURE_TOKEN_OCCURRENCES);
    assert!(postings_bytes <= MAX_FIXTURE_POSTING_BYTES);

    let by_id = records
        .iter()
        .map(|record| (record.id(), record))
        .collect::<HashMap<_, _>>();
    // Model a preexisting relations scan as actual pair keys. Additional rows are
    // deliberately unrelated; they measure materialization without changing
    // current candidate behavior.
    let mut existing = HashSet::new();
    for ids in token_ids.values() {
        for (offset, &a) in ids.iter().enumerate() {
            for &b in ids.iter().skip(offset + 1) {
                if (a.wrapping_add(b)) % 7 == 0 {
                    existing.insert((a.max(b), a.min(b)));
                }
            }
        }
    }
    let base_existing = existing.len();
    for extra in base_existing..relation_count {
        existing.insert((u64::MAX - extra as u64, extra as u64));
    }

    let rare_max = (records.len() / 20).max(2);
    let mut pairs_lexical_candidates = 0;
    let mut pair_examinations = 0;
    let mut effects = 0;
    for ids in token_ids.values() {
        if ids.len() < 2 {
            continue;
        }
        for (offset, &a) in ids.iter().enumerate() {
            for &b in ids.iter().skip(offset + 1) {
                assert!(
                    pair_examinations < MAX_FIXTURE_PAIR_EXAMINATIONS,
                    "synthetic sizing fixture exceeded pair safety cap"
                );
                pairs_lexical_candidates += 1;
                let (record_a, record_b) = (
                    by_id.get(&a).expect("id from token index"),
                    by_id.get(&b).expect("id from token index"),
                );
                let (earlier, later) = if record_a.created_at() <= record_b.created_at() {
                    (record_a, record_b)
                } else {
                    (record_b, record_a)
                };
                pair_examinations += 1;
                if existing.contains(&(later.id(), earlier.id())) {
                    continue;
                }
                if propose_supersedes(later, earlier, rare_max, &|term| {
                    df.get(term).copied().unwrap_or(0)
                })
                .is_some()
                {
                    effects += 1;
                    assert!(
                        effects <= MAX_FIXTURE_EFFECTS,
                        "synthetic sizing fixture exceeded effect safety cap"
                    );
                }
            }
        }
    }

    Run {
        observed: Observed {
            records_scanned: records.len(),
            raw_record_bytes,
            max_raw_record_bytes,
            token_occurrences,
            unique_terms: token_ids.len(),
            max_tokens_per_record,
            postings_bytes,
            posting_ids_examined,
            relations_scanned: relation_count,
            pairs_lexical_candidates,
            pair_examinations,
            effects,
            peak_token_ids: token_ids.values().map(Vec::len).sum(),
            peak_existing_pairs: existing.len(),
            peak_by_id: by_id.len(),
        },
        elapsed: started.elapsed(),
    }
}

#[test]
fn bounded_synthetic_sweep_preflight_sizing_is_repeatable() {
    let fixtures = [
        Fixture {
            name: "small",
            records: 32,
            relation_count: 32,
            extra_bytes_on_first_record: 0,
        },
        Fixture {
            name: "medium",
            records: 160,
            relation_count: 192,
            extra_bytes_on_first_record: 0,
        },
        Fixture {
            name: "stress",
            records: 384,
            relation_count: 512,
            extra_bytes_on_first_record: 2_048,
        },
    ];

    println!(
        "fixture,repetition,records,raw_bytes,max_raw_bytes,tokens,unique_terms,posting_bytes,posting_ids,relations,pairs,effects,peak_token_ids,peak_existing,peak_by_id,elapsed_us"
    );
    for fixture in fixtures {
        let records = fixture_records(fixture);
        let runs = (0..REPETITIONS)
            .map(|_| measure(&records, fixture.relation_count))
            .collect::<Vec<_>>();
        let baseline = &runs[0].observed;
        assert!(runs.iter().all(|run| run.observed == *baseline));
        assert!(baseline.records_scanned <= MAX_FIXTURE_RECORDS);
        assert!(baseline.relations_scanned <= MAX_FIXTURE_RELATIONS);
        assert!(baseline.raw_record_bytes <= MAX_FIXTURE_TOTAL_CONTENT_BYTES);
        assert!(baseline.token_occurrences <= MAX_FIXTURE_TOKEN_OCCURRENCES);
        assert!(baseline.postings_bytes <= MAX_FIXTURE_POSTING_BYTES);
        assert!(baseline.pair_examinations <= MAX_FIXTURE_PAIR_EXAMINATIONS);
        assert!(baseline.effects <= MAX_FIXTURE_EFFECTS);
        for (repetition, run) in runs.iter().enumerate() {
            println!(
                "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}",
                fixture.name,
                repetition + 1,
                run.observed.records_scanned,
                run.observed.raw_record_bytes,
                run.observed.max_raw_record_bytes,
                run.observed.token_occurrences,
                run.observed.unique_terms,
                run.observed.postings_bytes,
                run.observed.posting_ids_examined,
                run.observed.relations_scanned,
                run.observed.pair_examinations,
                run.observed.effects,
                run.observed.peak_token_ids,
                run.observed.peak_existing_pairs,
                run.observed.peak_by_id,
                run.elapsed.as_micros(),
            );
        }
    }
}
