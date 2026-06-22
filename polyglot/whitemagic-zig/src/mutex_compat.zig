const std = @import("std");

/// Mutex compatibility wrapper for Zig 0.16.
/// std.Thread.Mutex was removed in 0.16; we provide a spin-lock
/// around std.atomic.Mutex to maintain the same lock()/unlock() API.
pub const Mutex = struct {
    inner: std.atomic.Mutex = .unlocked,

    pub fn lock(self: *Mutex) void {
        while (!self.inner.tryLock()) {
            // Spin until lock acquired
        }
    }

    pub fn unlock(self: *Mutex) void {
        self.inner.unlock();
    }
};
