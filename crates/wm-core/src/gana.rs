//! The 28 Gana (Lunar Mansion) Taxonomy
//!
//! Each Gana is a meta-tool category that groups related sub-tools.
//! The 28 Ganas map to the 28 Lunar Mansions of Vedic astrology,
//! providing a natural fractal taxonomy for the 800+ tools.

use serde::{Deserialize, Serialize};
use std::fmt;

/// The 28 Ganas (Lunar Mansions).
///
/// Each variant corresponds to a category of tools in the `WhiteMagic`
/// dispatch system. Tools declare their Gana affiliation at registration
/// time, enabling efficient routing and governance.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Gana {
    // ── Phase 1: Foundation (Ganas 1-7) ──────────────────────────────
    /// Horn — System building, pipelines, invocation, status
    Horn = 0,
    /// Neck — Galaxy synchronization
    Neck = 1,
    /// Root — Cache management, flushing, status, tuning
    Root = 2,
    /// Room — Agent management, registration, heartbeat, capabilities
    Room = 3,
    /// Heart — Anomaly detection, state management
    Heart = 4,
    /// Tail — (Reserved)
    Tail = 5,
    /// Winnowing Basket — Memory recall, search, hybrid recall
    WinnowingBasket = 6,

    // ── Phase 2: Consciousness (Ganas 8-14) ──────────────────────────
    /// Ghost — Citta cycle, consciousness, coherence, smarana
    Ghost = 7,
    /// Willow — Karma verification, recording, reporting
    Willow = 8,
    /// Star — Capabilities, dream, serendipity, entity resolve
    Star = 9,
    /// Extended Net — Ethics evaluation, governor, dharma validation
    ExtendedNet = 10,
    /// Wings — (Reserved)
    Wings = 11,
    /// Chariot — Code explanation, fix generation
    Chariot = 12,
    /// Abundance — Dream cycle, lifecycle, narrative compress, gratitude
    Abundance = 13,

    // ── Phase 3: Intelligence (Ganas 15-21) ──────────────────────────
    /// Straddling Legs — Session management, context packing, checkpoint
    StraddlingLegs = 14,
    /// Mound — Foresight, simulation, convergence
    Mound = 15,
    /// Stomach — (Reserved)
    Stomach = 16,
    /// Hairy Head — Code communities, correlation, god nodes
    HairyHead = 17,
    /// Net — Association mining, emergence scan
    Net = 18,
    /// Turtle Beak — Task distribution
    TurtleBeak = 19,
    /// Three Stars — Explanation, bicameral reasoning, think
    ThreeStars = 20,

    // ── Phase 4: Harmony (Ganas 22-28) ───────────────────────────────
    /// Dipper — Cognitive action loop, mode, homeostasis
    Dipper = 21,
    /// Ox — Archaeology search, learning, pattern learning
    Ox = 22,
    /// Girl — Consciousness token economy
    Girl = 23,
    /// Void — Galaxy dashboard, backup, taxonomy, export
    Void = 24,
    /// Roof — Mandala creation, shelter
    Roof = 25,
    /// Encampment — Memory creation, fast write, consolidation
    Encampment = 26,
    /// Wall — Anti-loop, boundary check, dharma audit
    Wall = 27,
}

impl Gana {
    /// Total number of Ganas (always 28).
    pub const COUNT: usize = 28;

    /// Returns all 28 Ganas in order.
    #[must_use]
    pub const fn all() -> [Self; 28] {
        [
            Self::Horn,
            Self::Neck,
            Self::Root,
            Self::Room,
            Self::Heart,
            Self::Tail,
            Self::WinnowingBasket,
            Self::Ghost,
            Self::Willow,
            Self::Star,
            Self::ExtendedNet,
            Self::Wings,
            Self::Chariot,
            Self::Abundance,
            Self::StraddlingLegs,
            Self::Mound,
            Self::Stomach,
            Self::HairyHead,
            Self::Net,
            Self::TurtleBeak,
            Self::ThreeStars,
            Self::Dipper,
            Self::Ox,
            Self::Girl,
            Self::Void,
            Self::Roof,
            Self::Encampment,
            Self::Wall,
        ]
    }

    /// Returns the Sanskrit name for this Gana.
    #[must_use]
    pub const fn sanskrit(self) -> &'static str {
        match self {
            Self::Horn => "Rohini",
            Self::Neck => "Krittika",
            Self::Root => "Bharani",
            Self::Room => "Anuradha",
            Self::Heart => "Magha",
            Self::Tail => "Mula",
            Self::WinnowingBasket => "Purva Phalguni",
            Self::Ghost => "Pushya",
            Self::Willow => "Purva Ashadha",
            Self::Star => "Dhanishta",
            Self::ExtendedNet => "Uttara Phalguni",
            Self::Wings => "Hasta",
            Self::Chariot => "Revati",
            Self::Abundance => "Rohini",
            Self::StraddlingLegs => "Ardra",
            Self::Mound => "Mrigashira",
            Self::Stomach => "Purva Bhadrapada",
            Self::HairyHead => "Krittika",
            Self::Net => "Rohini",
            Self::TurtleBeak => "Punarvasu",
            Self::ThreeStars => "Mrigashira",
            Self::Dipper => "Uttara Ashadha",
            Self::Ox => "Rohini",
            Self::Girl => "Rohini",
            Self::Void => "Shatabhisha",
            Self::Roof => "Dhanishta",
            Self::Encampment => "Rohini",
            Self::Wall => "Rohini",
        }
    }

    /// Returns a human-readable description of this Gana's domain.
    #[must_use]
    pub const fn description(self) -> &'static str {
        match self {
            Self::Horn => "System building, pipelines, invocation, status",
            Self::Neck => "Galaxy synchronization",
            Self::Root => "Cache management, flushing, status, tuning",
            Self::Room => "Agent management, registration, heartbeat",
            Self::Heart => "Anomaly detection, state management",
            Self::Tail => "Reserved",
            Self::WinnowingBasket => "Memory recall, search, hybrid recall",
            Self::Ghost => "Citta cycle, consciousness, coherence, smarana",
            Self::Willow => "Karma verification, recording, reporting",
            Self::Star => "Capabilities, dream, serendipity, entity resolve",
            Self::ExtendedNet => "Ethics evaluation, governor, dharma validation",
            Self::Wings => "Reserved",
            Self::Chariot => "Code explanation, fix generation",
            Self::Abundance => "Dream cycle, lifecycle, narrative compress, gratitude",
            Self::StraddlingLegs => "Session management, context packing, checkpoint",
            Self::Mound => "Foresight, simulation, convergence",
            Self::Stomach => "Reserved",
            Self::HairyHead => "Code communities, correlation, god nodes",
            Self::Net => "Association mining, emergence scan",
            Self::TurtleBeak => "Task distribution",
            Self::ThreeStars => "Explanation, bicameral reasoning, think",
            Self::Dipper => "Cognitive action loop, mode, homeostasis",
            Self::Ox => "Archaeology search, learning, pattern learning",
            Self::Girl => "Consciousness token economy",
            Self::Void => "Galaxy dashboard, backup, taxonomy, export",
            Self::Roof => "Mandala creation, shelter",
            Self::Encampment => "Memory creation, fast write, consolidation",
            Self::Wall => "Anti-loop, boundary check, dharma audit",
        }
    }

    /// Convert from u8 index.
    #[must_use]
    pub const fn from_index(idx: u8) -> Option<Self> {
        if idx < 28 {
            Some(Self::all()[idx as usize])
        } else {
            None
        }
    }
}

impl fmt::Display for Gana {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gana_count_is_28() {
        assert_eq!(Gana::COUNT, 28);
        assert_eq!(Gana::all().len(), 28);
    }

    #[test]
    fn gana_roundtrip_index() {
        for (i, gana) in Gana::all().iter().enumerate() {
            assert_eq!(Gana::from_index(i as u8), Some(*gana));
        }
    }

    #[test]
    fn gana_serializes_as_enum() {
        let json = serde_json::to_string(&Gana::Horn).unwrap();
        assert_eq!(json, "\"Horn\"");
        let back: Gana = serde_json::from_str(&json).unwrap();
        assert_eq!(back, Gana::Horn);
    }

    #[test]
    fn gana_repr_u8() {
        assert_eq!(Gana::Horn as u8, 0);
        assert_eq!(Gana::Wall as u8, 27);
    }
}
