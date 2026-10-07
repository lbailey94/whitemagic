//! Read-only migration census over the live v9 stores on this host.
//!
//! This test never writes to the legacy stores: it opens them with the
//! read-only, lock-free [`Gen2Reader`] and reports the "before" (legacy
//! `session_turn`-only) and "after" (all accepted session lanes + galaxy-DBI
//! decode) accounting.
//!
//! Run explicitly (ignored by default so CI does not depend on host stores):
//!
//! ```text
//! cargo test -p wm-gen3-core --test migration_census_ro -- --ignored --nocapture
//! ```

use std::collections::BTreeMap;
use std::path::Path;

use wm_gen3_core::compat::{
    GEN2_GALAXY_DBS, Gen2Reader, gen3_galaxy_for_gen2_db, is_memory_galaxy_db,
};

const STORES: &[(&str, &str)] = &[
    (
        "heritage",
        "/home/lucas/wm-data/WMdata/projects/heritage/lmdb",
    ),
    ("vault", "/home/lucas/wm-data/WMdata/projects/vault/lmdb"),
    (
        "opencode",
        "/home/lucas/wm-data/WMdata/projects/opencode/lmdb",
    ),
    ("wmv9", "/home/lucas/wm-data/WMdata/projects/wmv9/lmdb"),
];

#[test]
#[ignore = "read-only live-store census; requires local v9 stores"]
fn census_live_stores() {
    for (name, store) in STORES {
        let path = Path::new(store);
        if !path.join("data.mdb").is_file() {
            println!("[{name}] skipped: {store} not present");
            continue;
        }
        let reader = Gen2Reader::open(path).expect("open legacy store read-only");

        // BEFORE: legacy turn-only reader.
        let (old_turns, old_skipped) = reader.session_turns().expect("legacy session scan");

        // AFTER: every accepted session lane + explicit skip accounting.
        let (records, quarantine) = reader.session_records().expect("extended session scan");
        let mut by_type: BTreeMap<String, usize> = BTreeMap::new();
        for record in &records {
            *by_type.entry(record.record_type.clone()).or_default() += 1;
        }

        println!(
            "[{name}] sessions BEFORE: turns={} skipped={}",
            old_turns.len(),
            old_skipped
        );
        println!(
            "[{name}] sessions AFTER:  accepted={} by_type={by_type:?} decode_skipped={}",
            records.len(),
            quarantine.len()
        );

        for db in GEN2_GALAXY_DBS {
            if !is_memory_galaxy_db(db) {
                let count = reader.count_galaxy_db(db).expect("count lane").unwrap_or(0);
                if count > 0 {
                    println!(
                        "[{name}] galaxy:{db} non_memory_lane={count} (mapped to {})",
                        gen3_galaxy_for_gen2_db(db)
                    );
                }
                continue;
            }
            match reader.scan_galaxy_db(db, None) {
                Ok(scan) => {
                    if scan.records.is_empty() && scan.decode_skipped == 0 {
                        continue;
                    }
                    println!(
                        "[{name}] galaxy:{db} decoded={} decode_skipped={} -> {}",
                        scan.records.len(),
                        scan.decode_skipped,
                        gen3_galaxy_for_gen2_db(db)
                    );
                }
                Err(e) => println!("[{name}] galaxy:{db} scan refused: {e}"),
            }
        }
    }
}
