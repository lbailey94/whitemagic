//! Linux sys_futex wake and wait primitives for zero-spin sleeping.

use std::sync::atomic::AtomicU32;
#[cfg(not(target_os = "linux"))]
use std::sync::atomic::Ordering;

#[cfg(target_os = "linux")]
const FUTEX_WAIT: libc::c_int = 0;
#[cfg(target_os = "linux")]
const FUTEX_WAKE: libc::c_int = 1;

/// Wait until futex value changes from expected.
pub fn futex_wait(addr: &AtomicU32, expected: u32, timeout_ms: Option<u64>) {
    #[cfg(target_os = "linux")]
    {
        let timespec = timeout_ms.map(|ms| libc::timespec {
            tv_sec: (ms / 1000) as libc::time_t,
            tv_nsec: ((ms % 1000) * 1_000_000) as libc::c_long,
        });
        let timeout_ptr = timespec
            .as_ref()
            .map_or(std::ptr::null(), |ts| ts as *const _);

        unsafe {
            libc::syscall(
                libc::SYS_futex,
                addr as *const AtomicU32 as *const u32,
                FUTEX_WAIT,
                expected,
                timeout_ptr,
                std::ptr::null::<u32>(),
                0u32,
            );
        }
    }

    #[cfg(not(target_os = "linux"))]
    {
        // Portable fallback: spin with yield
        let mut spins = 0;
        while addr.load(Ordering::Acquire) == expected {
            if spins < 100 {
                std::hint::spin_loop();
            } else {
                std::thread::yield_now();
            }
            spins += 1;
            if let Some(t) = timeout_ms {
                if spins > (t * 1000) {
                    break;
                }
            }
        }
    }
}

/// Wake up to `count` waiters waiting on addr.
pub fn futex_wake(addr: &AtomicU32, count: i32) -> i32 {
    #[cfg(target_os = "linux")]
    {
        let res = unsafe {
            libc::syscall(
                libc::SYS_futex,
                addr as *const AtomicU32 as *const u32,
                FUTEX_WAKE,
                count,
                std::ptr::null::<libc::timespec>(),
                std::ptr::null::<u32>(),
                0u32,
            )
        };
        if res < 0 { 0 } else { res as i32 }
    }

    #[cfg(not(target_os = "linux"))]
    {
        let _ = addr;
        let _ = count;
        0
    }
}
