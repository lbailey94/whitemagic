//! The plastic layer (Phase 1 placeholder).
//!
//! Contract (enforced by `scripts/check_closures.sh` and by types):
//! - May READ law through [`crate::constitution::ConstitutionView`] only.
//! - May PROPOSE amendments — proposals are inert until the external authority path
//!   applies them.
//! - Must never reference the constitution mutation surface: no mutable constitutional
//!   references, no amendment application, no construction, no admin path. The closure
//!   scan fails the build if production code in this module does.

use crate::constitution::{Amendment, ConstitutionView};

/// A proposal the adaptive layer may emit. Inert until the external authority path
/// applies it.
#[derive(Debug, Clone)]
pub struct AmendmentProposal {
    pub change: Amendment,
    pub rationale: String,
}

/// Compose a proposal (allowed anywhere; applying is not).
#[must_use]
pub fn propose(description: &str, new_writes_per_min: u32, rationale: &str) -> AmendmentProposal {
    AmendmentProposal {
        change: Amendment {
            description: description.to_string(),
            new_writes_per_min,
        },
        rationale: rationale.to_string(),
    }
}

/// Read law through the immutable view.
#[must_use]
pub fn observe(view: &ConstitutionView) -> u32 {
    view.writes_per_min()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::constitution::Constitution;

    #[test]
    fn adaptive_layer_reads_law_through_view_only() {
        let c = Constitution::new();
        let v = c.view();
        assert_eq!(observe(&v), v.writes_per_min());
    }

    #[test]
    fn proposals_are_inert_until_authority_applies_them() {
        let c = Constitution::new();
        let p = propose("lower budget", 30, "adaptive suggestion");
        assert_eq!(observe(&c.view()), 120);
        assert_eq!(p.change.new_writes_per_min, 30);
        assert_eq!(observe(&c.view()), 120, "proposal alone changes nothing");
    }
}
