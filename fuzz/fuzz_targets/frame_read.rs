#![no_main]

use libfuzzer_sys::fuzz_target;
use std::io::Cursor;
use std::time::{Duration, Instant};
use wm_gen3_core::transport::PhysicalFrameCodec;

fuzz_target!(|data: &[u8]| {
    let mut cursor = Cursor::new(data);
    let _ = PhysicalFrameCodec::read_frame(&mut cursor, Instant::now(), Duration::from_millis(25));
});
