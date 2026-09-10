//! Gratitude Ledger — hash-chained record of gratitude received.
//!
//! Rust port of the Python-era `whitemagic/gratitude/ledger.py` (the XRPL +
//! x402 gratitude ledger), reworked to the WMv5 governance conventions: a
//! SHA-256 hash chain persisted to LMDB in the Karma galaxy, keyed with a
//! `grat:` prefix so karma entries (8-byte BE keys) and write-audit journal
//! entries (`waj:` prefix) are never touched.
//!
//! Economic thesis (docs/PRICING_ETHICS.md §3-4): tips are pure patronage —
//! the core is free forever. This ledger is the record-keeper for the
//! `gratitude.tip` / `tip.send` economic surfaces listed in
//! `economic_firewall::ECONOMIC_TOOLS`: it stores every gratitude event in a
//! tamper-evident chain, computes supporter tiers for the gratitude benefits
//! (public listing, early access), and renders monthly digests for the
//! site/gratitude page.
//!
//! Hashing style follows `karma_ledger.rs` (SHA-256 over a canonical
//! serialization, genesis → linked entries), but stores every payload field,
//! so the full hash is recomputable at verify time — any mutated byte in any
//! field is detected at exactly the entry it was mutated in.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::sync::Arc;

use lmdb::{Cursor, Transaction};
use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};
use wm_core::{CoreError, Galaxy, Result};
use wm_memory::MemoryStore;

/// Genesis constant — the first entry's `prev_hash` links here.
pub const GENESIS_GRATITUDE: &str = "GENESIS_GRATITUDE";

/// LMDB key namespace for gratitude entries (Karma galaxy).
/// 5-byte prefix + 8-byte big-endian seq → lexicographic order == seq order,
/// and karma's 8-byte-key scan plus write-audit's `waj:` scan skip these.
const KEY_PREFIX: &[u8] = b"grat:";

/// LMDB metadata key for the persisted chain head.
const CHAIN_HEAD_KEY: &[u8] = b"__grat_head__";
/// LMDB metadata key for the persisted next-seq counter.
const NEXT_SEQ_KEY: &[u8] = b"__grat_next_seq__";

/// A single gratitude event in the hash chain.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GratitudeEntry {
    /// Sequential entry number (0-based).
    pub seq: u64,
    /// Unix epoch seconds of the event.
    pub at: i64,
    /// Donor identity. Empty string when `anonymous` — anonymous donors are
    /// never stored by id (PRICING_ETHICS §4 privacy rule).
    pub donor: String,
    /// Recipient identity (the recipient side of `tip.send`).
    pub recipient: String,
    /// Amount in currency units (caller normalizes to a common base before
    /// tiering; see [`tier_for`]).
    pub amount: f64,
    /// Currency / asset code, uppercased on record (e.g. "XRP", "USDC").
    pub currency: String,
    /// Optional donor note (may be empty).
    pub note: String,
    /// Whether the donor requested anonymity.
    pub anonymous: bool,
    /// Hash of the previous entry (genesis constant for seq 0).
    pub prev_hash: String,
    /// SHA-256 of this entry's canonical serialization (including prev_hash).
    pub hash: String,
}

/// Canonical hash-input projection of an entry — fixed field order, so the
/// serialization is byte-deterministic for identical values. `hash` itself is
/// excluded (it is the output, not the input).
#[derive(Serialize)]
struct HashInput<'a> {
    seq: u64,
    at: i64,
    donor: &'a str,
    recipient: &'a str,
    amount: f64,
    currency: &'a str,
    note: &'a str,
    anonymous: bool,
    prev_hash: &'a str,
}

/// Result of a chain integrity verification (ChainVerificationResult-style).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GratitudeVerification {
    /// Whether the chain is valid (all links intact, all hashes match).
    pub valid: bool,
    /// Number of entries verified.
    pub entries_verified: usize,
    /// First broken entry seq (if any).
    pub broken_at: Option<u64>,
    /// Description of the first violation (if any).
    pub violation: Option<String>,
    /// The persisted chain head hash.
    pub chain_head: String,
}

/// Supporter tier per PRICING_ETHICS §4 gratitude benefits.
///
/// Thresholds are USD-equivalent: Listed > 0, Patron >= 5, Sustainer >= 25.
/// Currency normalization to the USD-equivalent base is the caller's job for
/// now — the ledger stores amounts per currency and never converts.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum SupporterTier {
    /// No recorded gratitude yet.
    None,
    /// Listed in the public supporter listing.
    Listed,
    /// Patron: early access to experimental add-ons.
    Patron,
    /// Sustainer: badge on request, top listing.
    Sustainer,
}

impl SupporterTier {
    /// Human-readable label (for the supporter page).
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Listed => "listed",
            Self::Patron => "patron",
            Self::Sustainer => "sustainer",
        }
    }
}

/// Map a cumulative USD-equivalent gratitude total to a supporter tier.
///
/// Thresholds (PRICING_ETHICS §4): Listed > 0, Patron >= 5, Sustainer >= 25.
#[must_use]
pub const fn tier_for(cumulative_amount: f64) -> SupporterTier {
    if cumulative_amount >= 25.0 {
        SupporterTier::Sustainer
    } else if cumulative_amount >= 5.0 {
        SupporterTier::Patron
    } else if cumulative_amount > 0.0 {
        SupporterTier::Listed
    } else {
        SupporterTier::None
    }
}

/// Monthly digest for the site/gratitude page.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Digest {
    /// Number of gratitude entries in the month.
    pub entries_count: usize,
    /// Total received per currency (already-uppercased codes).
    pub total_by_currency: BTreeMap<String, f64>,
    /// Supporters whose first-ever entry landed in this month.
    pub new_supporters: usize,
    /// Most common non-empty note in the month (if any).
    pub top_note: Option<String>,
}

/// The gratitude ledger — append-only, LMDB-backed, hash-chained.
///
/// Unlike [`crate::karma_ledger::KarmaLedger`] this ledger owns its entries
/// in memory (for reference-returning queries) and persists each record
/// immediately in a single untracked LMDB batch (entry + chain head + next
/// seq), so a crash loses at most the entry being written. Reads for
/// verification always go to LMDB directly, so tampering with the store is
/// detected even while an instance holds cached copies.
pub struct GratitudeLedger {
    store: Arc<MemoryStore>,
    entries: Vec<GratitudeEntry>,
    chain_head: String,
    next_seq: u64,
}

impl GratitudeLedger {
    /// Open or create a gratitude ledger backed by the given LMDB store.
    pub fn new(store: Arc<MemoryStore>) -> Result<Self> {
        let mut ledger = Self {
            store,
            entries: Vec::new(),
            chain_head: GENESIS_GRATITUDE.to_string(),
            next_seq: 0,
        };
        ledger.load_state()?;
        Ok(ledger)
    }

    /// Load entries, chain head, and next seq from LMDB (if any).
    fn load_state(&mut self) -> Result<()> {
        let mut entries = Vec::new();
        for (key, val) in self.scan_cursor()? {
            if !key.starts_with(KEY_PREFIX) {
                continue;
            }
            match serde_json::from_slice::<GratitudeEntry>(&val) {
                Ok(entry) => entries.push(entry),
                Err(e) => {
                    // A corrupted entry must not silently truncate the chain:
                    // fail loud, the verify() path is the repair surface.
                    return Err(CoreError::Memory(format!(
                        "gratitude: corrupted entry in LMDB: {e}"
                    )));
                }
            }
        }
        entries.sort_by_key(|e| e.seq);
        if let Some(last) = entries.last() {
            self.chain_head.clone_from(&last.hash);
            self.next_seq = last.seq + 1;
        }
        self.entries = entries;
        Ok(())
    }

    /// Iterate all key-value pairs in the Karma galaxy under a read txn.
    fn scan_cursor(&self) -> Result<Vec<(Vec<u8>, Vec<u8>)>> {
        let db = self.store.galaxy_db(Galaxy::Karma)?;
        let tx = self
            .store
            .env()
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;
        let pairs: Vec<(Vec<u8>, Vec<u8>)> = cursor
            .iter()
            .map(|(k, v)| (k.to_vec(), v.to_vec()))
            .collect();
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(pairs)
    }

    /// Record a gratitude event (timestamped now).
    ///
    /// When `anonymous` is true the donor id is never stored — the entry's
    /// donor field is blanked before hashing and persistence.
    pub fn record(
        &mut self,
        donor: &str,
        recipient: &str,
        amount: f64,
        currency: &str,
        note: &str,
        anonymous: bool,
    ) -> Result<&GratitudeEntry> {
        let at = i64::try_from(wm_core::time::now_unix_secs()).unwrap_or(i64::MAX);
        self.record_at(donor, recipient, amount, currency, note, anonymous, at)
    }

    /// Record a gratitude event at an explicit timestamp (for imports and
    /// tests). See [`Self::record`] for the anonymity rule.
    #[allow(clippy::too_many_arguments)]
    pub fn record_at(
        &mut self,
        donor: &str,
        recipient: &str,
        amount: f64,
        currency: &str,
        note: &str,
        anonymous: bool,
        at: i64,
    ) -> Result<&GratitudeEntry> {
        if !amount.is_finite() || amount < 0.0 {
            return Err(CoreError::Tool(format!(
                "gratitude: amount must be finite and non-negative, got {amount}"
            )));
        }
        let seq = self.next_seq;
        let prev_hash = self.chain_head.clone();
        let currency = currency.trim().to_uppercase();
        let donor_stored = if anonymous { "" } else { donor };
        let hash = canonical_hash(&HashInput {
            seq,
            at,
            donor: donor_stored,
            recipient,
            amount,
            currency: &currency,
            note,
            anonymous,
            prev_hash: &prev_hash,
        });
        let entry = GratitudeEntry {
            seq,
            at,
            donor: donor_stored.to_string(),
            recipient: recipient.to_string(),
            amount,
            currency,
            note: note.to_string(),
            anonymous,
            prev_hash,
            hash,
        };

        let key = entry_key(seq);
        let val = serde_json::to_vec(&entry)
            .map_err(|e| CoreError::Memory(format!("gratitude serialize failed: {e}")))?;
        // Governance bookkeeping — untracked, like karma/write-audit flushes.
        self.store.put_raw_batch_untracked(
            Galaxy::Karma,
            &[
                (&key, val.as_slice()),
                (CHAIN_HEAD_KEY, entry.hash.as_bytes()),
                (NEXT_SEQ_KEY, &(seq + 1).to_be_bytes()),
            ],
        )?;

        self.chain_head.clone_from(&entry.hash);
        self.next_seq = seq + 1;
        self.entries.push(entry);
        Ok(self.entries.last().expect("entry was just pushed"))
    }

    /// Verify the whole chain against LMDB (not the in-memory cache).
    ///
    /// Walks genesis → head, checking for each entry:
    /// 1. `prev_hash` linkage (first entry links to [`GENESIS_GRATITUDE`])
    /// 2. stored `hash` equals the recomputed canonical hash of all fields
    /// 3. the persisted chain head equals the last entry's hash
    pub fn verify(&self) -> Result<GratitudeVerification> {
        let mut entries = Vec::new();
        for (key, val) in self.scan_cursor()? {
            if !key.starts_with(KEY_PREFIX) {
                continue;
            }
            match serde_json::from_slice::<GratitudeEntry>(&val) {
                Ok(entry) => entries.push(entry),
                Err(e) => {
                    return Ok(GratitudeVerification {
                        valid: false,
                        entries_verified: entries.len(),
                        broken_at: parse_seq(&key),
                        violation: Some(format!("undecodable entry in LMDB: {e}")),
                        chain_head: self.persisted_head(),
                    });
                }
            }
        }
        entries.sort_by_key(|e| e.seq);

        let chain_head = self.persisted_head();
        let fail =
            |entries_verified: usize, seq: Option<u64>, violation: String| GratitudeVerification {
                valid: false,
                entries_verified,
                broken_at: seq,
                violation: Some(violation),
                chain_head: chain_head.clone(),
            };

        if entries.is_empty() {
            return Ok(GratitudeVerification {
                valid: chain_head == GENESIS_GRATITUDE,
                entries_verified: 0,
                broken_at: None,
                violation: (chain_head != GENESIS_GRATITUDE)
                    .then(|| format!("chain head is {chain_head} but no entries exist")),
                chain_head,
            });
        }

        if entries[0].prev_hash != GENESIS_GRATITUDE {
            return Ok(fail(
                0,
                Some(entries[0].seq),
                format!(
                    "first entry seq {} prev_hash is not GENESIS_GRATITUDE (got {})",
                    entries[0].seq, entries[0].prev_hash
                ),
            ));
        }

        let mut prev: Option<&GratitudeEntry> = None;
        for (i, entry) in entries.iter().enumerate() {
            let expected = prev.map_or(GENESIS_GRATITUDE, |p| p.hash.as_str());
            if entry.prev_hash != expected {
                return Ok(fail(
                    i,
                    Some(entry.seq),
                    format!(
                        "entry seq {} prev_hash {} does not match the previous hash",
                        entry.seq, entry.prev_hash
                    ),
                ));
            }
            let recomputed = canonical_hash(&HashInput {
                seq: entry.seq,
                at: entry.at,
                donor: &entry.donor,
                recipient: &entry.recipient,
                amount: entry.amount,
                currency: &entry.currency,
                note: &entry.note,
                anonymous: entry.anonymous,
                prev_hash: &entry.prev_hash,
            });
            if recomputed != entry.hash {
                return Ok(fail(
                    i,
                    Some(entry.seq),
                    format!(
                        "entry seq {} stored hash {} does not match recomputed hash {recomputed}",
                        entry.seq, entry.hash
                    ),
                ));
            }
            prev = Some(entry);
        }

        if let Some(last) = entries.last() {
            if last.hash != chain_head {
                return Ok(fail(
                    entries.len(),
                    Some(last.seq),
                    format!(
                        "chain head {chain_head} does not match last entry hash {}",
                        last.hash
                    ),
                ));
            }
        }

        Ok(GratitudeVerification {
            valid: true,
            entries_verified: entries.len(),
            broken_at: None,
            violation: None,
            chain_head,
        })
    }

    fn persisted_head(&self) -> String {
        match self.store.get_raw(Galaxy::Karma, CHAIN_HEAD_KEY) {
            Ok(Some(data)) => String::from_utf8_lossy(&data).into_owned(),
            _ => GENESIS_GRATITUDE.to_string(),
        }
    }

    /// Total received across all entries, optionally restricted to one
    /// currency code (exact match, uppercased).
    #[must_use]
    pub fn total_received(&self, currency: Option<&str>) -> f64 {
        self.entries
            .iter()
            .filter(|e| currency.is_none_or(|c| e.currency == c.trim().to_uppercase()))
            .map(|e| e.amount)
            .sum()
    }

    /// All entries where the identity is the donor or the recipient.
    #[must_use]
    pub fn entries_for(&self, donor_or_recipient: &str) -> Vec<&GratitudeEntry> {
        self.entries
            .iter()
            .filter(|e| e.donor == donor_or_recipient || e.recipient == donor_or_recipient)
            .collect()
    }

    /// Supporter accounting: one row per donor (anonymous entries aggregate
    /// into a single `anonymous N` row — ids are never shown), sorted by
    /// total descending. Tiers are USD-equivalent; see [`tier_for`].
    #[must_use]
    pub fn supporters(&self) -> Vec<(String, SupporterTier, f64)> {
        let mut named: HashMap<String, f64> = HashMap::new();
        let mut anon_total = 0.0;
        let mut anon_count = 0usize;
        for entry in &self.entries {
            if entry.anonymous {
                anon_total += entry.amount;
                anon_count += 1;
            } else {
                *named.entry(entry.donor.clone()).or_insert(0.0) += entry.amount;
            }
        }
        let mut rows: Vec<(String, SupporterTier, f64)> = named
            .into_iter()
            .map(|(donor, total)| (donor, tier_for(total), total))
            .collect();
        if anon_count > 0 {
            rows.push((
                format!("anonymous {anon_count}"),
                tier_for(anon_total),
                anon_total,
            ));
        }
        rows.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));
        rows
    }

    /// Monthly digest for the site/gratitude page.
    ///
    /// `month` is 1-12 (UTC); invalid months yield an error. Ties for
    /// `top_note` resolve to the first-encountered note.
    pub fn monthly_digest(&self, year: i32, month: u32) -> Result<Digest> {
        let (start, end) = month_bounds(year, month)?;
        let mut totals: BTreeMap<String, f64> = BTreeMap::new();
        let mut note_counts: HashMap<&str, usize> = HashMap::new();
        let mut entries_count = 0usize;
        let mut month_donors: BTreeSet<&str> = BTreeSet::new();
        for entry in &self.entries {
            if entry.at < start || entry.at >= end {
                continue;
            }
            entries_count += 1;
            *totals.entry(entry.currency.clone()).or_insert(0.0) += entry.amount;
            if !entry.note.is_empty() {
                *note_counts.entry(entry.note.as_str()).or_insert(0) += 1;
            }
            month_donors.insert(if entry.anonymous {
                ""
            } else {
                entry.donor.as_str()
            });
        }

        // A donor is "new" this month if their first-ever entry is in it.
        // (The set dedups donors so one gift per donor counts once.)
        let mut new_supporters = 0usize;
        for donor in month_donors {
            let first_at = self
                .entries
                .iter()
                .filter(|e| e.donor == donor)
                .map(|e| e.at)
                .min();
            if first_at.is_some_and(|first| first >= start && first < end) {
                new_supporters += 1;
            }
        }

        let top_note = note_counts
            .into_iter()
            .max_by_key(|(note, count)| (*count, std::cmp::Reverse(*note)))
            .map(|(note, _)| note.to_string());

        Ok(Digest {
            entries_count,
            total_by_currency: totals,
            new_supporters,
            top_note,
        })
    }

    /// Current chain head hash (genesis constant for an empty ledger).
    #[must_use]
    pub fn chain_head(&self) -> &str {
        &self.chain_head
    }

    /// Next sequence number to be assigned (diagnostics).
    #[must_use]
    pub const fn next_seq(&self) -> u64 {
        self.next_seq
    }

    /// All entries, in seq order.
    #[must_use]
    pub fn entries(&self) -> &[GratitudeEntry] {
        &self.entries
    }
}

/// Entry LMDB key: `grat:` + 8-byte big-endian seq (sorts in seq order).
fn entry_key(seq: u64) -> Vec<u8> {
    let mut key = KEY_PREFIX.to_vec();
    key.extend_from_slice(&seq.to_be_bytes());
    key
}

/// Recover a seq from an entry-shaped key (best effort, for error reports).
fn parse_seq(key: &[u8]) -> Option<u64> {
    if key.len() == KEY_PREFIX.len() + 8 {
        Some(u64::from_be_bytes(key[KEY_PREFIX.len()..].try_into().ok()?))
    } else {
        None
    }
}

/// SHA-256 hex digest of a string (karma_ledger's helper style).
fn sha256_hex(input: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    format!("{:x}", hasher.finalize())
}

/// Compute an entry's chain hash: SHA-256 over the canonical JSON
/// serialization of every payload field **including `prev_hash`** (fixed
/// field order, ryu float formatting — byte-deterministic). Because every
/// stored field participates, verify() can recompute the full hash and pin
/// any single-byte tamper to its entry.
fn canonical_hash(input: &HashInput<'_>) -> String {
    let canonical = serde_json::to_string(input).unwrap_or_default();
    sha256_hex(&canonical)
}

/// UTC epoch-seconds bounds `[start, end)` of a calendar month.
fn month_bounds(year: i32, month: u32) -> Result<(i64, i64)> {
    let start_date = chrono::NaiveDate::from_ymd_opt(year, month, 1)
        .ok_or_else(|| CoreError::Tool(format!("gratitude: invalid month {year}-{month:02}")))?;
    let (next_year, next_month) = if month == 12 {
        (year + 1, 1)
    } else {
        (year, month + 1)
    };
    let end_date = chrono::NaiveDate::from_ymd_opt(next_year, next_month, 1)
        .ok_or_else(|| CoreError::Tool("gratitude: month rollover failed".to_string()))?;
    let to_secs = |d: chrono::NaiveDate| {
        d.and_hms_opt(0, 0, 0)
            .ok_or_else(|| CoreError::Tool("gratitude: midnight overflow".to_string()))
            .map(|dt| dt.and_utc().timestamp())
    };
    Ok((to_secs(start_date)?, to_secs(end_date)?))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_store() -> Arc<MemoryStore> {
        let tmp = tempfile::tempdir().unwrap();
        Arc::new(MemoryStore::open_default(tmp.path()).unwrap())
    }

    /// Epoch seconds for a UTC date (test helper).
    fn secs(year: i32, month: u32, day: u32) -> i64 {
        chrono::NaiveDate::from_ymd_opt(year, month, day)
            .unwrap()
            .and_hms_opt(0, 0, 0)
            .unwrap()
            .and_utc()
            .timestamp()
    }

    #[test]
    fn record_and_chain_verify_ok() {
        let store = make_store();
        let mut ledger = GratitudeLedger::new(store).unwrap();

        let e0 = ledger
            .record_at(
                "alice",
                "wm",
                3.0,
                "usd",
                "for the essays",
                false,
                secs(2026, 1, 15),
            )
            .unwrap()
            .clone();
        let e1 = ledger
            .record_at("bob", "wm", 0.5, "xrp", "", false, secs(2026, 1, 20))
            .unwrap()
            .clone();

        assert_eq!(e0.seq, 0);
        assert_eq!(e0.prev_hash, GENESIS_GRATITUDE);
        assert_eq!(e0.currency, "USD", "currency is uppercased on record");
        assert_eq!(e1.prev_hash, e0.hash, "entry 1 links to entry 0");

        let v = ledger.verify().unwrap();
        assert!(v.valid, "chain should verify: {:?}", v.violation);
        assert_eq!(v.entries_verified, 2);
        assert_eq!(v.broken_at, None);
        assert_eq!(v.chain_head, e1.hash);
    }

    #[test]
    fn tamper_detection_pins_the_right_seq() {
        let store = make_store();
        let mut ledger = GratitudeLedger::new(store.clone()).unwrap();
        ledger
            .record_at("alice", "wm", 1.0, "usd", "", false, secs(2026, 1, 1))
            .unwrap();
        let e1 = ledger
            .record_at("bob", "wm", 2.0, "usd", "", false, secs(2026, 1, 2))
            .unwrap()
            .clone();
        ledger
            .record_at("carol", "wm", 3.0, "usd", "", false, secs(2026, 1, 3))
            .unwrap();

        // Mutate one byte of entry seq 1's amount directly in LMDB.
        let tampered = GratitudeEntry {
            amount: 9_999.0,
            ..e1.clone()
        };
        let key = entry_key(e1.seq);
        let val = serde_json::to_vec(&tampered).unwrap();
        store.put_raw(Galaxy::Karma, &key, &val).unwrap();

        let v = ledger.verify().unwrap();
        assert!(!v.valid, "tampered chain must fail verification");
        assert_eq!(v.broken_at, Some(1), "must pin the mutated entry");
        assert!(v.violation.is_some());
    }

    #[test]
    fn totals_per_currency() {
        let store = make_store();
        let mut ledger = GratitudeLedger::new(store).unwrap();
        ledger
            .record_at("alice", "wm", 10.0, "USD", "", false, secs(2026, 2, 1))
            .unwrap();
        ledger
            .record_at("bob", "wm", 5.0, "usd", "", false, secs(2026, 2, 2))
            .unwrap();
        ledger
            .record_at("carol", "wm", 100.0, "XRP", "", false, secs(2026, 2, 3))
            .unwrap();

        assert_eq!(ledger.total_received(None), 115.0);
        assert_eq!(ledger.total_received(Some("USD")), 15.0);
        assert_eq!(ledger.total_received(Some("XRP")), 100.0);
        assert_eq!(ledger.total_received(Some("EUR")), 0.0);
    }

    #[test]
    fn tier_thresholds() {
        assert_eq!(tier_for(0.0), SupporterTier::None);
        assert_eq!(tier_for(0.03), SupporterTier::Listed);
        assert_eq!(tier_for(4.99), SupporterTier::Listed);
        assert_eq!(tier_for(5.0), SupporterTier::Patron);
        assert_eq!(tier_for(24.99), SupporterTier::Patron);
        assert_eq!(tier_for(25.0), SupporterTier::Sustainer);
        assert_eq!(tier_for(1_000.0), SupporterTier::Sustainer);
    }

    #[test]
    fn supporters_aggregate_and_anonymous_ids_are_hidden() {
        let store = make_store();
        let mut ledger = GratitudeLedger::new(store).unwrap();
        ledger
            .record_at("alice", "wm", 6.0, "USD", "", false, secs(2026, 1, 1))
            .unwrap();
        ledger
            .record_at("bob", "wm", 0.5, "USD", "", false, secs(2026, 1, 2))
            .unwrap();
        // Three separate anonymous donors — one aggregate row, no ids.
        ledger
            .record_at("secret1", "wm", 10.0, "USD", "", true, secs(2026, 1, 3))
            .unwrap();
        ledger
            .record_at("secret2", "wm", 10.0, "USD", "", true, secs(2026, 1, 4))
            .unwrap();
        ledger
            .record_at("secret3", "wm", 10.0, "USD", "", true, secs(2026, 1, 5))
            .unwrap();

        // Anonymous entries never carry a donor id, even in storage.
        for entry in ledger.entries() {
            if entry.anonymous {
                assert!(entry.donor.is_empty());
            }
        }

        let rows = ledger.supporters();
        assert_eq!(rows.len(), 3, "3 anonymous entries → one aggregate row");
        assert_eq!(rows[0].0, "anonymous 3");
        assert_eq!(rows[0].1, SupporterTier::Sustainer);
        assert_eq!(rows[0].2, 30.0);
        assert_eq!(rows[1].0, "alice");
        assert_eq!(rows[1].1, SupporterTier::Patron);
        assert_eq!(rows[2].0, "bob");
        assert_eq!(rows[2].1, SupporterTier::Listed);
    }

    #[test]
    fn monthly_digest_correctness() {
        let store = make_store();
        let mut ledger = GratitudeLedger::new(store).unwrap();

        // January: alice's first-ever gift, a note, an anonymous gift.
        ledger
            .record_at(
                "alice",
                "wm",
                10.0,
                "USD",
                "for the essays",
                false,
                secs(2026, 1, 15),
            )
            .unwrap();
        ledger
            .record_at("secret", "wm", 2.0, "XRP", "", true, secs(2026, 1, 20))
            .unwrap();
        // February: alice again (not new), carol is new, top note repeats.
        ledger
            .record_at("alice", "wm", 1.0, "USD", "", false, secs(2026, 2, 5))
            .unwrap();
        ledger
            .record_at(
                "carol",
                "wm",
                3.0,
                "USD",
                "for the essays",
                false,
                secs(2026, 2, 6),
            )
            .unwrap();
        ledger
            .record_at(
                "carol",
                "wm",
                4.0,
                "USD",
                "keep going",
                false,
                secs(2026, 2, 7),
            )
            .unwrap();
        // March noise outside the digest window.
        ledger
            .record_at("dave", "wm", 9.0, "USD", "", false, secs(2026, 3, 1))
            .unwrap();

        let jan = ledger.monthly_digest(2026, 1).unwrap();
        assert_eq!(jan.entries_count, 2);
        assert_eq!(jan.total_by_currency.get("USD"), Some(&10.0));
        assert_eq!(jan.total_by_currency.get("XRP"), Some(&2.0));
        assert_eq!(jan.new_supporters, 2, "alice (first-ever) + anonymous");
        assert_eq!(jan.top_note.as_deref(), Some("for the essays"));

        let feb = ledger.monthly_digest(2026, 2).unwrap();
        assert_eq!(feb.entries_count, 3);
        assert_eq!(feb.total_by_currency.get("USD"), Some(&8.0));
        assert_eq!(feb.new_supporters, 1, "only carol is new");
        assert_eq!(feb.top_note.as_deref(), Some("for the essays"));

        let mar = ledger.monthly_digest(2026, 3).unwrap();
        assert_eq!(mar.entries_count, 1);
        assert_eq!(mar.new_supporters, 1);
        assert_eq!(mar.top_note, None);
    }

    #[test]
    fn monthly_digest_rejects_invalid_month() {
        let store = make_store();
        let ledger = GratitudeLedger::new(store).unwrap();
        assert!(ledger.monthly_digest(2026, 0).is_err());
        assert!(ledger.monthly_digest(2026, 13).is_err());
    }

    #[test]
    fn persistence_roundtrip_across_instances() {
        let store = make_store();
        let mut ledger1 = GratitudeLedger::new(store.clone()).unwrap();
        let e0 = ledger1
            .record_at(
                "alice",
                "wm",
                5.0,
                "USD",
                "roundtrip",
                false,
                secs(2026, 1, 1),
            )
            .unwrap()
            .clone();

        let mut ledger2 = GratitudeLedger::new(store).unwrap();
        assert_eq!(ledger2.next_seq(), 1, "next seq persists");
        assert_eq!(ledger2.chain_head(), e0.hash, "chain head persists");
        assert_eq!(ledger2.total_received(Some("USD")), 5.0);

        // New records chain onto the persisted head.
        let e1 = ledger2
            .record_at("bob", "wm", 1.0, "XRP", "", false, secs(2026, 1, 2))
            .unwrap()
            .clone();
        assert_eq!(e1.prev_hash, e0.hash);

        let v = ledger2.verify().unwrap();
        assert!(v.valid, "cross-instance chain verifies: {:?}", v.violation);
        assert_eq!(v.entries_verified, 2);
    }

    #[test]
    fn empty_ledger_zero_state() {
        let store = make_store();
        let ledger = GratitudeLedger::new(store).unwrap();

        assert_eq!(ledger.chain_head(), GENESIS_GRATITUDE);
        assert_eq!(ledger.next_seq(), 0);
        assert_eq!(ledger.total_received(None), 0.0);
        assert!(ledger.supporters().is_empty());

        let v = ledger.verify().unwrap();
        assert!(v.valid, "empty ledger verifies as the defined zero state");
        assert_eq!(v.entries_verified, 0);

        let digest = ledger.monthly_digest(2026, 1).unwrap();
        assert_eq!(digest, Digest::default());
    }

    #[test]
    fn entries_for_matches_donor_and_recipient() {
        let store = make_store();
        let mut ledger = GratitudeLedger::new(store).unwrap();
        ledger
            .record_at("alice", "wm", 1.0, "USD", "", false, secs(2026, 1, 1))
            .unwrap();
        ledger
            .record_at("bob", "alice", 2.0, "USD", "", false, secs(2026, 1, 2))
            .unwrap();
        ledger
            .record_at("carol", "wm", 3.0, "USD", "", false, secs(2026, 1, 3))
            .unwrap();

        let alice = ledger.entries_for("alice");
        assert_eq!(alice.len(), 2, "alice as donor and as recipient");
        assert_eq!(alice[0].seq, 0);
        assert_eq!(alice[1].seq, 1);

        let nobody = ledger.entries_for("nobody");
        assert!(nobody.is_empty());
    }

    #[test]
    fn rejects_non_finite_and_negative_amounts() {
        let store = make_store();
        let mut ledger = GratitudeLedger::new(store).unwrap();
        assert!(
            ledger
                .record_at("alice", "wm", f64::NAN, "USD", "", false, 0)
                .is_err()
        );
        assert!(
            ledger
                .record_at("alice", "wm", f64::INFINITY, "USD", "", false, 0)
                .is_err()
        );
        assert!(
            ledger
                .record_at("alice", "wm", -1.0, "USD", "", false, 0)
                .is_err()
        );
        assert_eq!(ledger.next_seq(), 0, "rejected records consume no seq");
    }

    #[test]
    fn hash_is_canonical_and_deterministic() {
        let input = HashInput {
            seq: 0,
            at: 100,
            donor: "a",
            recipient: "wm",
            amount: 3.0,
            currency: "USD",
            note: "note",
            anonymous: false,
            prev_hash: GENESIS_GRATITUDE,
        };
        let h1 = canonical_hash(&input);
        let h2 = canonical_hash(&input);
        assert_eq!(h1, h2, "identical fields → identical hash");
        assert_eq!(h1.len(), 64, "SHA-256 hex");

        // Any payload change (including prev_hash) changes the hash.
        let h3 = canonical_hash(&HashInput {
            prev_hash: "OTHER",
            ..input
        });
        let h4 = canonical_hash(&HashInput {
            amount: 3.01,
            ..input
        });
        assert_ne!(h1, h3, "prev_hash participates in the hash");
        assert_ne!(h1, h4, "amount participates in the hash");
    }
}
