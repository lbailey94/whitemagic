use std::collections::HashSet;
use wm_gen3_core::gen1_gems::{GemCluster, Gen1Arsenal};

#[test]
fn test_50_essential_gems_catalog_completeness() {
    let gems = Gen1Arsenal::all_gems();
    assert_eq!(
        gems.len(),
        50,
        "Must contain exactly the 50 Essential Gen1 Gems"
    );

    let mut ids = HashSet::new();
    let mut slugs = HashSet::new();

    for gem in gems {
        assert!(
            gem.id >= 1 && gem.id <= 50,
            "Gem ID {} out of range 1..=50",
            gem.id
        );
        assert!(ids.insert(gem.id), "Duplicate Gem ID: {}", gem.id);
        assert!(!gem.name.is_empty(), "Gem name cannot be empty");
        assert!(!gem.slug.is_empty(), "Gem slug cannot be empty");
        assert!(slugs.insert(gem.slug), "Duplicate Gem slug: {}", gem.slug);
        assert!(
            !gem.description.is_empty(),
            "Gem description cannot be empty"
        );
        assert!(!gem.pack_id.is_empty(), "Gem pack_id cannot be empty");
    }

    // Verify all 6 clusters are populated
    let clusters: HashSet<GemCluster> = gems.iter().map(|g| g.cluster).collect();
    assert_eq!(
        clusters.len(),
        6,
        "All 6 cognitive clusters must have representation"
    );
}

#[test]
fn test_12_plugin_packs_and_landlock_invariants() {
    let packs = Gen1Arsenal::all_plugin_packs();
    assert_eq!(
        packs.len(),
        12,
        "Must contain exactly 12 Landlocked Plugin Packs"
    );

    let mut pack_ids = HashSet::new();
    let valid_gem_ids: HashSet<u32> = Gen1Arsenal::all_gems().iter().map(|g| g.id).collect();

    for pack in packs {
        assert!(!pack.pack_id.is_empty());
        assert!(
            pack_ids.insert(pack.pack_id),
            "Duplicate pack ID: {}",
            pack.pack_id
        );
        assert!(!pack.name.is_empty());
        assert!(!pack.description.is_empty());

        // Gate 13 Landlock LSM Invariant: Plugin packs must be network-isolated
        assert!(
            pack.landlock_network_denied,
            "Pack {} must enforce Gate 13 Landlock network isolation (deny_network)",
            pack.pack_id
        );

        // Bounded resources invariant
        assert!(
            pack.default_timeout_ms <= 10000,
            "Timeout cannot exceed 10s budget"
        );
        assert!(
            pack.max_memory_mb <= 256,
            "Memory cannot exceed 256MB quota"
        );

        for gem_id in pack.gem_ids {
            assert!(
                valid_gem_ids.contains(gem_id),
                "Pack {} references invalid gem ID {}",
                pack.pack_id,
                gem_id
            );
        }
    }
}

#[test]
fn test_gem_retrieval_and_filtering() {
    let gem1 = Gen1Arsenal::get_gem(1).expect("get gem 1");
    assert_eq!(gem1.slug, "dynamic_motif_spectrometer");
    assert_eq!(gem1.cluster, GemCluster::EpistemicAndCognitivePhysics);

    let gem50 = Gen1Arsenal::get_gem(50).expect("get gem 50");
    assert_eq!(gem50.slug, "universal_skill_recipe_compiler");

    assert!(Gen1Arsenal::get_gem(0).is_none());
    assert!(Gen1Arsenal::get_gem(51).is_none());

    let spectroscopy_gems = Gen1Arsenal::gems_for_pack("pack_spectroscopy");
    assert!(!spectroscopy_gems.is_empty());
    assert!(spectroscopy_gems.iter().any(|g| g.id == 1));
}
