#![no_main]

use libfuzzer_sys::fuzz_target;
use wm_gen3_core::transport::RepresentationTransport;

fuzz_target!(|data: &[u8]| {
    if let Ok(value) = RepresentationTransport::from_bytes(data) {
        let _ = value.to_bytes();
        let _ = value.digest();
    }
});
