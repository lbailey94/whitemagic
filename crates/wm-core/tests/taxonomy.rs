//! Integration tests for the core taxonomy: Gana (28), Galaxy (14),
//! and `HolographicCoords` (6D).
//!
//! These tests verify structural invariants that must hold for the
// entire dispatch and memory systems to function correctly.

use proptest::prelude::*;
use wm_core::{Galaxy, Gana, HolographicCoords};

// ── Gana: 28 Lunar Mansions ───────────────────────────────────────────

#[test]
fn gana_has_exactly_28_variants() {
    assert_eq!(Gana::COUNT, 28);
    assert_eq!(Gana::all().len(), 28);
}

#[test]
fn gana_indices_are_contiguous_and_unique() {
    let mut seen = std::collections::HashSet::new();
    for (i, gana) in Gana::all().iter().enumerate() {
        let idx = *gana as u8;
        assert_eq!(
            idx as usize, i,
            "Gana {gana:?} has index {idx} but position {i}"
        );
        assert!(
            seen.insert(idx),
            "Duplicate u8 index {idx} for Gana {gana:?}"
        );
    }
}

#[test]
fn gana_from_index_roundtrips_all_variants() {
    for i in 0..28u8 {
        let gana = Gana::from_index(i).unwrap_or_else(|| panic!("index {i} should map to a Gana"));
        assert_eq!(gana as u8, i);
    }
    assert!(
        Gana::from_index(28).is_none(),
        "index 28 should be out of bounds"
    );
    assert!(Gana::from_index(255).is_none());
}

#[test]
fn gana_serialization_roundtrip_preserves_identity() {
    for gana in Gana::all() {
        let json = serde_json::to_string(&gana).unwrap();
        let back: Gana = serde_json::from_str(&json).unwrap();
        assert_eq!(gana, back, "Serialization roundtrip failed for {gana:?}");
    }
}

#[test]
fn gana_display_and_debug_are_non_empty() {
    for gana in Gana::all() {
        let display = format!("{gana}");
        let debug = format!("{gana:?}");
        assert!(!display.is_empty());
        assert!(!debug.is_empty());
    }
}

#[test]
fn gana_descriptions_are_non_empty_and_unique() {
    let mut descs: Vec<_> = Gana::all().iter().map(|g| g.description()).collect();
    let total = descs.len();
    descs.sort_unstable();
    descs.dedup();
    // Reserved Ganas share "Reserved" so we expect some duplicates,
    // but every description must be non-empty.
    for gana in Gana::all() {
        assert!(
            !gana.description().is_empty(),
            "Empty description for {gana:?}"
        );
    }
    // At least 25 unique descriptions (3 reserved Ganas share text)
    assert!(
        descs.len() >= 25,
        "Only {} unique descriptions, expected >= 25",
        descs.len()
    );
    let _ = total;
}

proptest! {
    /// Gana from_index ↔ as u8 is a bijection for valid indices.
    #[test]
    fn gana_index_bijection(idx in 0u8..28) {
        let gana = Gana::from_index(idx).unwrap();
        prop_assert_eq!(gana as u8, idx);
    }

    /// Serializing then deserializing any Gana preserves identity.
    #[test]
    fn gana_serde_roundtrip(idx in 0u8..28) {
        let gana = Gana::from_index(idx).unwrap();
        let json = serde_json::to_string(&gana).unwrap();
        let back: Gana = serde_json::from_str(&json).unwrap();
        prop_assert_eq!(gana, back);
    }
}

// ── Galaxy: 14 Memory Galaxies ────────────────────────────────────────

#[test]
fn galaxy_has_exactly_14_variants() {
    assert_eq!(Galaxy::COUNT, 14);
    assert_eq!(Galaxy::all().len(), 14);
}

#[test]
fn galaxy_db_names_are_all_unique() {
    let names: Vec<_> = Galaxy::all().iter().map(|g| g.db_name()).collect();
    let unique: std::collections::HashSet<_> = names.iter().collect();
    assert_eq!(names.len(), unique.len(), "Galaxy db_names must be unique");
}

#[test]
fn galaxy_db_names_are_non_empty_lowercase_ascii() {
    for galaxy in Galaxy::all() {
        let name = galaxy.db_name();
        assert!(!name.is_empty(), "Empty db_name for {galaxy:?}");
        assert!(
            name.chars()
                .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit()),
            "Non-lowercase-ascii db_name: {name} for {galaxy:?}"
        );
    }
}

#[test]
fn galaxy_display_matches_db_name() {
    for galaxy in Galaxy::all() {
        assert_eq!(format!("{galaxy}"), galaxy.db_name());
    }
}

// ── HolographicCoords: 6D Spatial-Temporal Addressing ─────────────────

#[test]
fn coords_encode_decode_roundtrip_preserves_all_fields() {
    let coords = HolographicCoords {
        galaxy: 7,
        sector: 1337,
        radial: 0.123,
        angular: std::f32::consts::PI,
        temporal: 1_700_000_000_000_000,
        consciousness: 0.777,
    };
    let key = coords.encode_key();
    let decoded = HolographicCoords::decode_key(&key).unwrap();
    assert_eq!(decoded.galaxy, coords.galaxy);
    assert_eq!(decoded.sector, coords.sector);
    assert_eq!(decoded.temporal, coords.temporal);
    assert!((decoded.radial - coords.radial).abs() < f32::EPSILON);
    assert!((decoded.angular - coords.angular).abs() < f32::EPSILON);
    assert!((decoded.consciousness - coords.consciousness).abs() < f32::EPSILON);
}

#[test]
fn coords_encode_produces_23_byte_key() {
    let coords = HolographicCoords {
        galaxy: 0,
        sector: 0,
        radial: 0.0,
        angular: 0.0,
        temporal: 0,
        consciousness: 0.0,
    };
    assert_eq!(coords.encode_key().len(), 23);
}

#[test]
fn coords_decode_rejects_short_keys() {
    assert!(HolographicCoords::decode_key(&[0; 22]).is_none());
    assert!(HolographicCoords::decode_key(&[]).is_none());
}

#[test]
fn coords_distance_to_self_is_zero() {
    let coords = HolographicCoords {
        galaxy: 3,
        sector: 42,
        radial: 0.75,
        angular: 1.5,
        temporal: 1700000000,
        consciousness: 0.8,
    };
    assert_eq!(coords.distance_to(&coords), 0.0);
}

#[test]
fn coords_distance_is_symmetric() {
    let a = HolographicCoords {
        galaxy: 0,
        sector: 10,
        radial: 0.3,
        angular: 0.5,
        temporal: 1000,
        consciousness: 0.4,
    };
    let b = HolographicCoords {
        galaxy: 1,
        sector: 20,
        radial: 0.9,
        angular: 2.0,
        temporal: 5000,
        consciousness: 0.9,
    };
    assert!((a.distance_to(&b) - b.distance_to(&a)).abs() < f32::EPSILON);
}

#[test]
fn coords_distance_bounded_in_zero_to_one() {
    let a = HolographicCoords {
        galaxy: 0,
        sector: 0,
        radial: 0.0,
        angular: 0.0,
        temporal: 0,
        consciousness: 0.0,
    };
    let b = HolographicCoords {
        galaxy: 0,
        sector: 0,
        radial: 1.0,
        angular: std::f32::consts::TAU,
        temporal: u64::MAX,
        consciousness: 1.0,
    };
    let d = a.distance_to(&b);
    assert!((0.0..=1.0).contains(&d), "Distance {d} should be in [0, 1]");
}

#[test]
fn coords_new_uses_given_galaxy_index() {
    let coords = HolographicCoords::new(Galaxy::Citta, 1000);
    assert_eq!(coords.galaxy, Galaxy::Citta as u8);
}

proptest! {
    /// Encode/decode roundtrip for arbitrary valid coordinates.
    #[test]
    fn coords_roundtrip(
        galaxy in 0u8..14,
        sector in 0u16..,
        radial in 0.0f32..1.0,
        angular in 0.0f32..std::f32::consts::TAU,
        temporal in 0u64..u64::MAX / 2,
        consciousness in 0.0f32..1.0,
    ) {
        let coords = HolographicCoords {
            galaxy, sector, radial, angular, temporal, consciousness,
        };
        let key = coords.encode_key();
        let decoded = HolographicCoords::decode_key(&key).unwrap();
        prop_assert_eq!(decoded.galaxy, galaxy);
        prop_assert_eq!(decoded.sector, sector);
        prop_assert_eq!(decoded.temporal, temporal);
        prop_assert!((decoded.radial - radial).abs() < f32::EPSILON);
        prop_assert!((decoded.angular - angular).abs() < f32::EPSILON);
        prop_assert!((decoded.consciousness - consciousness).abs() < f32::EPSILON);
    }

    /// Distance to self is always zero.
    #[test]
    fn coords_distance_self_zero(
        galaxy in 0u8..14,
        sector in 0u16..,
        radial in 0.0f32..1.0,
        angular in 0.0f32..std::f32::consts::TAU,
        temporal in 0u64..,
        consciousness in 0.0f32..1.0,
    ) {
        let coords = HolographicCoords {
            galaxy, sector, radial, angular, temporal, consciousness,
        };
        prop_assert_eq!(coords.distance_to(&coords), 0.0);
    }

    /// Distance is symmetric.
    #[test]
    fn coords_distance_symmetric(
        a_galaxy in 0u8..14, b_galaxy in 0u8..14,
        a_sector in 0u16.., b_sector in 0u16..,
        a_radial in 0.0f32..1.0, b_radial in 0.0f32..1.0,
        a_angular in 0.0f32..std::f32::consts::TAU, b_angular in 0.0f32..std::f32::consts::TAU,
        a_temporal in 0u64..u64::MAX/2, b_temporal in 0u64..u64::MAX/2,
        a_consc in 0.0f32..1.0, b_consc in 0.0f32..1.0,
    ) {
        let a = HolographicCoords {
            galaxy: a_galaxy, sector: a_sector, radial: a_radial,
            angular: a_angular, temporal: a_temporal, consciousness: a_consc,
        };
        let b = HolographicCoords {
            galaxy: b_galaxy, sector: b_sector, radial: b_radial,
            angular: b_angular, temporal: b_temporal, consciousness: b_consc,
        };
        let d_ab = a.distance_to(&b);
        let d_ba = b.distance_to(&a);
        prop_assert!((d_ab - d_ba).abs() < 0.001);
    }
}
