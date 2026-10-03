//! External authority path (operator side) — the only route from proposal to law.
//!
//! Requires exclusive (`&mut`) access, which the operator process holds and the
//! adaptive layer never does. Every application emits a verifiable receipt
//! (Charter §4: ratification → receipt).

use crate::constitution::{Amendment, AmendmentReceipt, Constitution};

/// Apply an amendment through the authority path.
pub fn amend(constitution: &mut Constitution, change: Amendment) -> AmendmentReceipt {
    constitution.apply(change)
}
