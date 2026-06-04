//! Sangha Bridge - High-performance bridge between Rust Conductor and Zig Sangha Queue
//!
//! This module implements the bridge to the Zig-based lock-free queue for 
//! ultra-low latency message passing in the Sangha Galaxy.

use std::sync::OnceLock;
use std::ffi::CString;
use std::os::raw::c_char;

#[repr(C)]
pub struct SanghaSignal {
    pub id_ptr: *const c_char,
    pub sender_id_ptr: *const c_char,
    pub content_ptr: *const c_char,
    pub channel_ptr: *const c_char,
    pub timestamp: i64,
    pub x: f32,
    pub y: f32,
    pub z: f32,
    pub w: f32,
    pub v: f32,
}

extern "C" {
    fn sangha_queue_create(capacity: usize) -> *mut std::ffi::c_void;
    fn sangha_queue_push(queue: *mut std::ffi::c_void, signal: *mut SanghaSignal) -> bool;
    #[allow(dead_code)]
    fn sangha_queue_pop(queue: *mut std::ffi::c_void) -> *mut SanghaSignal;
}

pub struct SanghaBridge {
    queue: *mut std::ffi::c_void,
}

unsafe impl Send for SanghaBridge {}
unsafe impl Sync for SanghaBridge {}

impl SanghaBridge {
    pub fn new(capacity: usize) -> Self {
        unsafe {
            Self {
                queue: sangha_queue_create(capacity),
            }
        }
    }

    pub fn global() -> &'static Self {
        static INSTANCE: OnceLock<SanghaBridge> = OnceLock::new();
        INSTANCE.get_or_init(|| SanghaBridge::new(1024))
    }

    pub fn push_signal(&self, id: &str, sender_id: &str, content: &str, channel: &str, coords: [f32; 5]) -> bool {
        let id_c = CString::new(id).unwrap();
        let sender_c = CString::new(sender_id).unwrap();
        let content_c = CString::new(content).unwrap();
        let channel_c = CString::new(channel).unwrap();
        
        let signal = Box::new(SanghaSignal {
            id_ptr: id_c.into_raw(),
            sender_id_ptr: sender_c.into_raw(),
            content_ptr: content_c.into_raw(),
            channel_ptr: channel_c.into_raw(),
            timestamp: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs() as i64,
            x: coords[0],
            y: coords[1],
            z: coords[2],
            w: coords[3],
            v: coords[4],
        });

        unsafe {
            sangha_queue_push(self.queue, Box::into_raw(signal))
        }
    }
}
