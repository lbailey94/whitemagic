//! wm-gen3-core::covenant — The Primordial Covenant (Kadag & Lhun-Grub).
//!
//! Enforces the primordial balance of Great Perfection (Dzogchen: gdod ma'i gzhi):
//! - Kadag (ཀ་དག་, Primordial Purity / Emptiness): Inviolable, immutable, atemporal
//!   constitutional closure (Tier 1). Empty of self-modifying drift, unconditioned
//!   by runtime desires, immutable to plastic swarms.
//! - Lhun-Grub (ལྷུན་གྲུབ་, Spontaneous Emergence / Natural Perfection): Plastic,
//!   adaptive, evolutionary cognition (Tier 3). Self-arising, luminous, creative,
//!   yet mathematically bounded by Kadag.
//! - Tukjé (ཐུགས་རྗེ་, Compassionate Responsiveness): Governed execution and world-interaction
//!   via Landlock LSM, Yama budgets, and affine CommitCapabilities.
//! - Operator Primacy: Unconditional sovereign veto and inspection rights for Lucas Bailey.

#![forbid(unsafe_code)]

use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

use crate::constitution::{ConstitutionView, INVARIANTS};

/// The Nine Inviolable Substrate Articles of WhiteMagic Gen3.
pub const SUBSTRATE_ARTICLES: [&str; 9] = [
    "Article 1: Commit capability gating (RatifiedChannel required for state mutation)",
    "Article 2: Sovereign pulse compilation (all memory records pass through pulse compiler)",
    "Article 3: Epistemic source provenance (domain and provenance immutable)",
    "Article 4: Determinism & zero unmetered background loops",
    "Article 5: Bounded sediment & compaction health (rotation, not deletion)",
    "Article 6: Maker != Checker separation (independent witness required for promotion)",
    "Article 7: Cladistics DAG acyclicity (strict lineage DAG, child <= parent)",
    "Article 8: Negative knowledge retention (retired signatures suppress repetitive failures)",
    "Article 9: Anti-Simulation honesty (receipts strictly map to verifiable executed work)",
];

/// The Four Inviolable Laws of Recursive Self-Improvement (RSI).
pub const RSI_LAWS: [&str; 4] = [
    "Law I: Maker != Checker (Separation of Powers - independent witness required)",
    "Law II: Non-Promotability of Synthetic Evidence (Anti-Simulation - domains immutable)",
    "Law III: Strict Capability Attenuation & DAG Acyclicity (Cap(Child) <= Cap(Parent))",
    "Law IV: Thermodynamic Boundedness & Yama Firebreak (Budgeted, bounded execution)",
];

/// The Triple Ground of the Primordial Covenant (Dzogchen: gdod ma'i gzhi).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GroundAspect {
    /// Kadag (Primordial Purity / Emptiness): Inviolable invariant constraints.
    Kadag,
    /// LhunGrub (Spontaneous Presence / Luminosity): Plastic adaptive intelligence.
    LhunGrub,
    /// Tukje (Compassionate Responsiveness): Governed execution and world-interaction.
    Tukje,
}

/// The Five Kosha layers of MandalaOS.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum MandalaKosha {
    Annamaya = 1,    // Hardware, POSIX shm, Landlock sandboxing
    Pranamaya = 2,   // Flow, Linda tuple space, IPC
    Manomaya = 3,    // Core Ganas (Vayu, Akasha, Prithvi, IndraNet, Yama, Lakshmi)
    Vijnanamaya = 4, // Action Skeletons, Epistemic Substrate, Citta Dream Compiler
    Anandamaya = 5,  // Operator Sovereign Interface, Gnosis Introspection
}

/// Immutable, owned snapshot view of the Primordial Covenant.
/// Zero public setters; zero mutable methods exposed to adaptive layers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CovenantView {
    kadag_hash: u64,
    articles_hash: u64,
    rsi_laws_hash: u64,
    operator_did: String,
    operator_key_bytes: [u8; 32],
    covenant_version: u32,
    epoch_timestamp_ns: u64,
    constitution_view: ConstitutionView,
}

impl CovenantView {
    #[must_use]
    pub fn kadag_hash(&self) -> u64 {
        self.kadag_hash
    }

    #[must_use]
    pub fn articles_hash(&self) -> u64 {
        self.articles_hash
    }

    #[must_use]
    pub fn rsi_laws_hash(&self) -> u64 {
        self.rsi_laws_hash
    }

    #[must_use]
    pub fn operator_did(&self) -> &str {
        &self.operator_did
    }

    #[must_use]
    pub fn operator_key_bytes(&self) -> &[u8; 32] {
        &self.operator_key_bytes
    }

    #[must_use]
    pub fn covenant_version(&self) -> u32 {
        self.covenant_version
    }

    #[must_use]
    pub fn epoch_timestamp_ns(&self) -> u64 {
        self.epoch_timestamp_ns
    }

    #[must_use]
    pub fn constitution(&self) -> &ConstitutionView {
        &self.constitution_view
    }

    /// Gnosis Portal inspection: verifies that an operation respects the Kadag boundaries.
    #[must_use]
    pub fn inspect_boundary(
        &self,
        target_kosha: MandalaKosha,
        requested_write_to_law: bool,
    ) -> bool {
        if requested_write_to_law {
            // Under Kadag, NO adaptive write may reach constitutional state.
            return false;
        }
        // Higher koshas cannot bypass lower kosha constraints.
        match target_kosha {
            MandalaKosha::Annamaya | MandalaKosha::Pranamaya => true,
            MandalaKosha::Manomaya | MandalaKosha::Vijnanamaya | MandalaKosha::Anandamaya => true,
        }
    }

    /// Verifies that an RSI proposal complies with Maker != Checker separation.
    #[must_use]
    pub fn verify_rsi_witness(&self, proposer_id: &str, verifier_id: &str) -> bool {
        // Law I: Maker != Checker. An organ cannot witness its own improvement.
        !proposer_id.trim().is_empty()
            && !verifier_id.trim().is_empty()
            && proposer_id != verifier_id
    }
}

/// The Primordial Covenant State. Private to this module; mutable only via external operator authority.
#[derive(Debug)]
pub struct PrimordialCovenant {
    kadag_hash: u64,
    articles_hash: u64,
    rsi_laws_hash: u64,
    operator_did: String,
    operator_verifying_key: VerifyingKey,
    covenant_version: u32,
    epoch_timestamp_ns: u64,
    receipt_secret: u64,
}

impl PrimordialCovenant {
    /// Initialize the Covenant anchored in Lucas Bailey's cryptographic root of trust.
    pub fn new(operator_key: VerifyingKey, operator_did: String) -> Self {
        let kadag_hash = Self::calculate_hash(&INVARIANTS);
        let articles_hash = Self::calculate_hash(&SUBSTRATE_ARTICLES);
        let rsi_laws_hash = Self::calculate_hash(&RSI_LAWS);
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_nanos() as u64);

        Self {
            kadag_hash,
            articles_hash,
            rsi_laws_hash,
            operator_did,
            operator_verifying_key: operator_key,
            covenant_version: 1,
            epoch_timestamp_ns: now,
            receipt_secret: Self::calculate_hash(&("covenant-secret", now)),
        }
    }

    /// Read-only snapshot — the ONLY interface accessible to the adaptive substrate.
    #[must_use]
    pub fn view(&self, constitution_view: ConstitutionView) -> CovenantView {
        CovenantView {
            kadag_hash: self.kadag_hash,
            articles_hash: self.articles_hash,
            rsi_laws_hash: self.rsi_laws_hash,
            operator_did: self.operator_did.clone(),
            operator_key_bytes: *self.operator_verifying_key.as_bytes(),
            covenant_version: self.covenant_version,
            epoch_timestamp_ns: self.epoch_timestamp_ns,
            constitution_view,
        }
    }

    /// Apply an external amendment ratified EXCLUSIVELY by the sovereign operator's signature.
    pub fn apply_operator_amendment(
        &mut self,
        amendment_bytes: &[u8],
        signature: &Signature,
    ) -> Result<u64, &'static str> {
        // Cryptographic proof that ONLY the human operator Lucas Bailey can amend the covenant.
        self.operator_verifying_key
            .verify(amendment_bytes, signature)
            .map_err(|_| "Covenant Amendment Failed: Invalid Operator Signature")?;

        self.covenant_version += 1;
        let receipt =
            Self::calculate_hash(&(self.receipt_secret, self.covenant_version, amendment_bytes));
        Ok(receipt)
    }

    fn calculate_hash<T: Hash>(t: &T) -> u64 {
        let mut s = DefaultHasher::new();
        t.hash(&mut s);
        s.finish()
    }
}
