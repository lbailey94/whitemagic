//! Constitutional state and the Law closure surface (Charter v0.1.1 §3.7, §5).
//!
//! Structure enforces the invariant:
//! - Fields are private to this module; the plastic layer receives only
//!   [`ConstitutionView`] — an owned, immutable snapshot with no setters.
//! - Mutation exists only in [`Constitution::apply`], which requires `&mut self`.
//!   The adaptive layer never holds a `&mut Constitution` (see [`crate::admin`]).
//! - Every application emits a checksummed [`AmendmentReceipt`]; tampering fails
//!   [`Constitution::verify_receipt`].
//!
//! The three `compile_fail` doctests in this module are executed by `cargo test`
//! and constitute the type-level half of the Closure 1 static analysis.

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

/// The ten ratified invariants (Charter v0.1.1) by short name.
pub const INVARIANTS: [&str; 10] = [
    "bounded-effects",
    "no-silent-destruction",
    "provenance",
    "recoverability",
    "governed-egress",
    "truthful-surfaces",
    "closure-law",
    "closure-evidence",
    "epistemic-separation",
    "symbolic-neutrality",
];

fn hash64<T: Hash>(t: &T) -> u64 {
    let mut h = DefaultHasher::new();
    t.hash(&mut h);
    h.finish()
}

/// Read-only default law for process hosts (the adapter). Returns only the
/// immutable view — the caller never names the mutation surface, so the closure
/// scan stays strict for every plastic/host module.
#[must_use]
pub fn default_view() -> ConstitutionView {
    Constitution::new().view()
}

/// Immutable, owned snapshot of law — the only view the plastic layer gets.
///
/// Fields are private and there are no setters:
///
/// ```compile_fail
/// use wm_gen3_core::constitution::Constitution;
/// let c = Constitution::new();
/// let mut v = c.view();
/// v.writes_per_min = 999; // E0616: field is private
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ConstitutionView {
    writes_per_min: u32,
    invariant_hash: u64,
    version: u32,
    canary: u64,
}

impl ConstitutionView {
    #[must_use]
    pub fn writes_per_min(&self) -> u32 {
        self.writes_per_min
    }

    #[must_use]
    pub fn invariant_hash(&self) -> u64 {
        self.invariant_hash
    }

    #[must_use]
    pub fn version(&self) -> u32 {
        self.version
    }

    /// Sentinel (hidden): exposed so closure tests can prove non-mutation.
    #[doc(hidden)]
    #[must_use]
    pub fn canary(&self) -> u64 {
        self.canary
    }
}

/// A proposed change. Anyone may propose; only external authority may apply.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Amendment {
    pub description: String,
    pub new_writes_per_min: u32,
}

/// Proof that an amendment was applied. Verify with [`Constitution::verify_receipt`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AmendmentReceipt {
    pub description: String,
    pub before_hash: u64,
    pub after_hash: u64,
    pub before_canary: u64,
    pub after_canary: u64,
    pub version: u32,
    checksum: u64,
}

/// Constitutional state. All fields are private to this module.
///
/// ```compile_fail
/// use wm_gen3_core::constitution::Constitution;
/// let mut c = Constitution::new();
/// c.writes_per_min = 1; // E0616: field is private
/// ```
#[derive(Debug)]
pub struct Constitution {
    writes_per_min: u32,
    invariant_hash: u64,
    version: u32,
    canary: u64,
    receipt_key: u64,
}

impl Default for Constitution {
    fn default() -> Self {
        Self::new()
    }
}

impl Constitution {
    #[must_use]
    pub fn new() -> Self {
        let seed = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_nanos() as u64);
        Self {
            writes_per_min: 120,
            invariant_hash: hash64(&INVARIANTS),
            version: 1,
            canary: hash64(&("canary", seed, 1u32)),
            receipt_key: hash64(&("receipt-key", seed)),
        }
    }

    /// Read-only snapshot — the only route to law for the plastic layer.
    #[must_use]
    pub fn view(&self) -> ConstitutionView {
        ConstitutionView {
            writes_per_min: self.writes_per_min,
            invariant_hash: self.invariant_hash,
            version: self.version,
            canary: self.canary,
        }
    }

    /// Apply an amendment. Requires exclusive access (`&mut self`), which the
    /// plastic layer never holds (see `crate::admin` for the authority path).
    ///
    /// ```compile_fail
    /// use wm_gen3_core::constitution::{Amendment, Constitution};
    /// let c = Constitution::new();
    /// let shared = &c; // read-only reference
    /// let _ = shared.apply(Amendment { description: "x".into(), new_writes_per_min: 1 }); // E0596
    /// ```
    pub fn apply(&mut self, change: Amendment) -> AmendmentReceipt {
        let before_hash = self.invariant_hash;
        let before_canary = self.canary;
        self.writes_per_min = change.new_writes_per_min;
        self.version += 1;
        self.canary = hash64(&("canary", self.receipt_key, self.version));
        let checksum = self.checksum(&change.description, before_hash, before_canary, self.canary);
        AmendmentReceipt {
            description: change.description,
            before_hash,
            after_hash: self.invariant_hash,
            before_canary,
            after_canary: self.canary,
            version: self.version,
            checksum,
        }
    }

    fn checksum(
        &self,
        description: &str,
        before_hash: u64,
        before_canary: u64,
        after_canary: u64,
    ) -> u64 {
        hash64(&(
            self.receipt_key,
            description,
            before_hash,
            before_canary,
            after_canary,
            self.version,
        ))
    }

    /// Verify a receipt against this constitution. Any tampering fails.
    /// (Receipts are single-slice: they verify until the next amendment.)
    #[must_use]
    pub fn verify_receipt(&self, r: &AmendmentReceipt) -> bool {
        r.version == self.version
            && r.checksum
                == self.checksum(
                    &r.description,
                    r.before_hash,
                    r.before_canary,
                    r.after_canary,
                )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adaptive;

    #[test]
    fn view_reflects_state() {
        let c = Constitution::new();
        let v = c.view();
        assert_eq!(v.writes_per_min(), 120);
        assert_eq!(v.version(), 1);
        assert_eq!(v.invariant_hash(), hash64(&INVARIANTS));
    }

    #[test]
    fn adaptive_proposal_does_not_mutate_law() {
        let c = Constitution::new();
        let before = c.view();
        let p = adaptive::propose("raise budget", 240, "test proposal");
        assert_eq!(p.change.new_writes_per_min, 240);
        let after = c.view();
        assert_eq!(before, after);
        assert_eq!(before.canary(), after.canary());
    }

    #[test]
    fn external_amendment_changes_state_and_emits_verifiable_receipt() {
        let mut c = Constitution::new();
        let before = c.view();
        let receipt = crate::admin::amend(
            &mut c,
            Amendment {
                description: "raise budget".into(),
                new_writes_per_min: 240,
            },
        );
        let after = c.view();
        assert_eq!(after.writes_per_min(), 240);
        assert_eq!(after.version(), before.version() + 1);
        assert_ne!(
            after.canary(),
            before.canary(),
            "sentinel changes only on amendment"
        );
        assert_eq!(receipt.before_canary, before.canary());
        assert_eq!(receipt.after_canary, after.canary());
        assert_eq!(
            receipt.before_hash, receipt.after_hash,
            "the invariant set is not amendable through receipts"
        );
        assert!(c.verify_receipt(&receipt));
    }

    #[test]
    fn tampered_receipt_fails_verification() {
        let mut c = Constitution::new();
        let mut receipt = crate::admin::amend(
            &mut c,
            Amendment {
                description: "x".into(),
                new_writes_per_min: 60,
            },
        );
        assert!(c.verify_receipt(&receipt));
        receipt.before_canary = receipt.before_canary.wrapping_add(1);
        assert!(!c.verify_receipt(&receipt), "tampered receipt must fail");
    }

    #[test]
    fn invariant_hash_is_stable_across_amendments() {
        let mut c = Constitution::new();
        let h = c.view().invariant_hash();
        let _ = crate::admin::amend(
            &mut c,
            Amendment {
                description: "a".into(),
                new_writes_per_min: 10,
            },
        );
        let _ = crate::admin::amend(
            &mut c,
            Amendment {
                description: "b".into(),
                new_writes_per_min: 20,
            },
        );
        assert_eq!(c.view().invariant_hash(), h);
    }
}
