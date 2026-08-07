//! Fuzz target: NLU classify — feed arbitrary strings to the TF-IDF router.
//!
//! Invariant: `classify()` must never panic and must always return a valid
//! tool name with confidence in [0.0, 1.0].

#![no_main]

use libfuzzer_sys::fuzz_target;
use wm_tools::nlu::classify;

fuzz_target!(|data: &[u8]| {
    // Try as raw bytes (invalid UTF-8 should not panic)
    if let Ok(text) = std::str::from_utf8(data) {
        let (tool, confidence) = classify(text);
        assert!(!tool.is_empty(), "classify returned empty tool name");
        assert!(
            (0.0..=1.0).contains(&confidence),
            "confidence {confidence} out of range for input: {text:?}"
        );
    }

    // Also try as a string with arbitrary bytes replaced
    let lossy = String::from_utf8_lossy(data);
    let (tool, confidence) = classify(&lossy);
    assert!(!tool.is_empty(), "classify returned empty tool name (lossy)");
    assert!(
        (0.0..=1.0).contains(&confidence),
        "confidence {confidence} out of range (lossy)"
    );
});
