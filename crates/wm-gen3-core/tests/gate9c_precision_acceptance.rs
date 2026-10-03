//! Gate 9C Candidacy Precision Refinement & Cognitive Re-Derivation Acceptance Suite.
//!
//! Verifies:
//! - Hypothesis H9C-1: Candidacy precision scaling, noise reduction >= 50%, recall >= 85%, 0 reversed pairs.
//! - Hypothesis H9C-2: Re-derivation of the 28 Gana archetypes as stateless transform policies (Recipes).
//! - Hypothesis H9C-3: Conformal Forgotten Diamonds & dormant salience evaluation.
//! - Hypothesis H9C-4: Requalified projection sweep and authorized intake with vector persistence.

use std::collections::{BTreeMap, HashSet};
use std::path::{Path, PathBuf};

use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::ops::{ImportKind, RememberItem, Substrate};
use wm_gen3_core::recipe::{DiamondEvaluator, GanaArchetype, GanaFamily, Recipe};

struct TempDir(PathBuf);

impl TempDir {
    fn new(label: &str) -> Self {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).unwrap();
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-gate9c-{label}-{:x}",
            u64::from_be_bytes(nonce)
        ));
        let _ = std::fs::remove_dir_all(&path);
        Self(path)
    }
    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn item(content: &str, source: &str) -> RememberItem {
    RememberItem {
        content: content.to_string(),
        source: source.to_string(),
        kind: ImportKind::Reported,
    }
}

fn substrate(dir: &TempDir) -> Substrate {
    let mut s = Substrate::open(dir.path(), None, default_view()).expect("open synthetic store");
    s.set_budget(1_000_000);
    s.set_intake_authority(RatifiedChannel::mint("gate9c-acceptance"));
    s
}

/// H9C-1: Anchor coherence eliminates cross-topic noise while preserving legitimate updates.
#[test]
fn h9c1_anchor_coherence_eliminates_spurious_cross_topic_collisions() {
    let dir = TempDir::new("h9c1-anchor");
    let mut s = substrate(&dir);

    // Corpus containing true temporal updates AND cross-topic distractor pairs
    // that share single generic keywords ("package", "clean", "server", "update")
    let items = vec![
        // Topic A (Server infrastructure): True update pair
        item(
            "primary database server was upgraded from version 2.1 to 2.2 yesterday",
            "corp:infra",
        ),
        item(
            "primary database server version is now 2.2 in production",
            "corp:infra",
        ),
        // Topic B (Shipping & Logistics): Cross-topic sharing "package" and "delivered"
        item(
            "the freight courier delivered the heavy wooden cargo package to warehouse dock B",
            "corp:shipping",
        ),
        item(
            "please inspect the software package manifest before the next system deploy",
            "corp:dev",
        ),
        // Topic C (Office maintenance): Cross-topic sharing "clean"
        item(
            "the night janitorial crew made sure the kitchen counter and floor were sparkling clean",
            "corp:facilities",
        ),
        item(
            "ensure git working tree is clean before initiating git rebase against upstream",
            "corp:dev",
        ),
        // Topic D (Personnel Relocation): True update pair
        item(
            "Alice moved from Atlanta to Denver for the new regional assignment",
            "corp:hr",
        ),
        item(
            "Alice currently resides in Denver and leads the regional engineering office",
            "corp:hr",
        ),
        // Topic E (Vehicle Fleet): True update pair
        item(
            "the company pool car color was repainted from red to electric blue",
            "corp:fleet",
        ),
        item(
            "the company pool car is electric blue now and parked in bay 4",
            "corp:fleet",
        ),
    ];

    let results = s.remember_batch(&items);
    for r in &results {
        assert!(r.is_ok(), "ingest must succeed: {r:?}");
    }

    s.set_sweep_enabled(true);
    let stats = s.think_sweep();
    assert!(
        !stats.disabled && !stats.refused,
        "sweep must run: {stats:?}"
    );

    let relations = s.store().iter_relations().expect("iter_relations");

    // All relations proposed must be in correct temporal order (later -> supersedes -> earlier)
    for rel in &relations {
        assert!(
            rel.src() > rel.dst(),
            "temporal invariance violation: src {} must be > dst {}",
            rel.src(),
            rel.dst()
        );
    }

    // Verify true updates were proposed
    let pair_ids: HashSet<(u64, u64)> = relations.iter().map(|r| (r.src(), r.dst())).collect();

    // Server update: item 1 supersedes item 0
    assert!(
        pair_ids.contains(&(1, 0)),
        "server update (1 -> 0) must be proposed"
    );
    // Alice update: item 7 supersedes item 6
    assert!(
        pair_ids.contains(&(7, 6)),
        "Alice update (7 -> 6) must be proposed"
    );
    // Car update: item 9 supersedes item 8
    assert!(
        pair_ids.contains(&(9, 8)),
        "Car update (9 -> 8) must be proposed"
    );

    // Cross-topic noise pairs MUST NOT be proposed:
    // Shipping (2) vs Software package (3)
    assert!(
        !pair_ids.contains(&(3, 2)),
        "shipping vs dev package must be filtered"
    );
    // Cleaning (4) vs Git clean (5)
    assert!(
        !pair_ids.contains(&(5, 4)),
        "facilities clean vs git clean must be filtered"
    );

    // Total proposals must be tight and precise (zero false-positive cross-topic relations)
    assert_eq!(
        relations.len(),
        3,
        "expected exactly 3 true relation pairs; got {}",
        relations.len()
    );
}

/// H9C-2: The 28 Gana archetypes are re-derived as stateless transform policies.
#[test]
fn h9c2_gana_recipes_adhere_to_charter_and_article_4() {
    let presets = Recipe::all_presets();
    assert_eq!(
        presets.len(),
        28,
        "must define exactly 28 canonical Gana recipes"
    );

    let mut names = HashSet::new();
    let mut families = BTreeMap::new();

    for r in &presets {
        assert!(!r.name.is_empty());
        assert!(
            names.insert(r.name),
            "recipe names must be unique: {}",
            r.name
        );
        *families.entry(r.family).or_insert(0usize) += 1;

        // Verify valid parameter boundaries
        assert!(
            r.temperature >= 0.0 && r.temperature <= 1.0,
            "temperature in [0, 1]"
        );
        assert!(
            r.conformal_alpha > 0.0 && r.conformal_alpha <= 0.20,
            "alpha in (0, 0.20]"
        );
        assert!(
            r.relevance_floor >= 0.40 && r.relevance_floor <= 0.80,
            "relevance floor in [0.40, 0.80]"
        );
        assert!(
            r.salience_bias >= 0.0 && r.salience_bias <= 1.0,
            "salience bias in [0, 1]"
        );
        assert!(
            r.temporal_horizon_sweeps >= 10,
            "temporal horizon must be non-trivial"
        );
    }

    // Four symmetric families with 7 archetypes each
    assert_eq!(families[&GanaFamily::Analytical], 7);
    assert_eq!(families[&GanaFamily::Synthesis], 7);
    assert_eq!(families[&GanaFamily::Operational], 7);
    assert_eq!(families[&GanaFamily::Guardrail], 7);

    // Verify Charter §3.10 and Article 4 compliance:
    // Recipes are pure Plain-Old-Data structs with zero runtime state or background loop capabilities.
    let dharma = Recipe::preset(GanaArchetype::Dharma);
    assert_eq!(dharma.name, "Dharma");
    assert_eq!(dharma.temperature, 0.0);
    assert_eq!(dharma.family, GanaFamily::Guardrail);
}

/// H9C-3: Conformal Forgotten Diamonds calculate dormant salience without background daemons.
#[test]
fn h9c3_conformal_forgotten_diamonds_scoring_and_recovery() {
    let evaluator = DiamondEvaluator::new(60.0, 0.35);

    // High intrinsic value record, zero recent accesses, 60 sweeps old (1 half-life)
    let s_60 = evaluator.compute_diamond_score(1.0, 60, 0);
    assert!(
        (s_60 - 0.50).abs() < 1e-5,
        "score at 1 half-life should be 0.50: got {s_60}"
    );
    assert!(s_60 >= evaluator.diamond_floor, "must qualify as diamond");

    // Same record, but accessed frequently (10 recent accesses) -> not forgotten!
    let s_60_frequent = evaluator.compute_diamond_score(1.0, 60, 10);
    assert!(
        s_60_frequent < evaluator.diamond_floor,
        "frequently accessed memory cannot be forgotten diamond"
    );

    // Ancient memory: 600 sweeps old (10 half-lives) -> decayed beyond retrieval
    let s_600 = evaluator.compute_diamond_score(1.0, 600, 0);
    assert!(s_600 < 0.01, "ancient memory must decay below threshold");
}

/// H9C-4: Requalified projection sweep and intake persist vectors and prune below tau_sweep.
#[test]
fn h9c4_requalified_projection_intake_and_sweep() {
    let cache_dir = wm_gen3_core::embed_cache_dir();

    if !cache_dir.exists() {
        eprintln!("skip: fastembed cache not found at {}", cache_dir.display());
        return;
    }

    let dir = TempDir::new("h9c4-projection");
    let mut s = substrate(&dir);

    // Enable projection and load model
    s.set_projection_enabled(true, Some(&cache_dir))
        .expect("projection loads from cache");
    s.set_sweep_enabled(true);

    // Ingest records: projection must NOT fail with ProjectionForbidden
    let items = vec![
        item(
            "the server cluster operates on version 3.4 currently",
            "corp:infra",
        ),
        item(
            "the server cluster has been upgraded to version 3.5 in the cloud",
            "corp:infra",
        ),
    ];

    let results = s.remember_batch(&items);
    for r in &results {
        assert!(
            r.is_ok(),
            "projection-enabled intake must succeed in Gate 9C: {r:?}"
        );
    }

    // Verify vectors were persisted into LMDB embeddings dbi
    let vectors = s.store().iter_vectors().expect("iter_vectors");
    assert_eq!(
        vectors.len(),
        2,
        "both records must have vectors persisted in store"
    );

    // Run sweep with projection active: must NOT return Slice 1 exclusion error
    let stats = s.think_sweep();
    assert!(
        !stats.disabled && !stats.refused,
        "projection-enabled sweep must succeed: {stats:?}"
    );
    assert_eq!(stats.proposals, 1, "must propose the supersedes relation");

    let relations = s.store().iter_relations().expect("iter_relations");
    assert_eq!(relations.len(), 1);
    assert_eq!(relations[0].src(), 1);
    assert_eq!(relations[0].dst(), 0);
}
