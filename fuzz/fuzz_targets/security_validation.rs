#![no_main]

use libfuzzer_sys::fuzz_target;
use wm_core::security::{is_url_safe, is_path_safe, is_description_safe, sanitize_path};

fuzz_target!(|data: &[u8]| {
    if let Ok(s) = std::str::from_utf8(data) {
        // SSRF validation must never panic
        let _ = is_url_safe(s);

        // Path traversal validation must never panic
        let _ = is_path_safe(s);
        let _ = sanitize_path(s);

        // Description sanitization must never panic
        let _ = is_description_safe(s);
    }
});
