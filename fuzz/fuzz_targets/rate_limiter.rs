//! Fuzz target: Rate limiter — feed arbitrary tool names to try_acquire.
//!
//! Invariant: `try_acquire()` must never panic with arbitrary tool names,
//! including empty strings, very long strings, and non-UTF-8-ish patterns.

#![no_main]

use libfuzzer_sys::fuzz_target;
use wm_dispatch::RateLimiter;

fuzz_target!(|data: &[u8]| {
    let limiter = RateLimiter::new(100_000, 10_000, 1_000);

    // Use the data as a tool name (lossy UTF-8)
    let tool_name = String::from_utf8_lossy(data);
    let _ = limiter.try_acquire(&tool_name);

    // Also try with common tool name patterns
    if !data.is_empty() {
        let tool = format!("tool_{}", data[0]);
        let _ = limiter.try_acquire(&tool);
    }

    // Empty string
    let _ = limiter.try_acquire("");

    // Repeated calls with the same name should be consistent
    for _ in 0..10 {
        let _ = limiter.try_acquire("fuzz_tool");
    }
});
