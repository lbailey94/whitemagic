// WhiteMagic Zig Library - Combined exports
// Combines all Zig modules for single library build

// Import modules
const galactic_map = @import("memory/galactic_map.zig");
const pattern_matcher = @import("memory/pattern_matcher.zig");

// Re-export C FFI functions (comptime to force inclusion)
comptime {
    _ = galactic_map.galactic_compute_distance;
    _ = galactic_map.galactic_classify_zone;
    _ = galactic_map.galactic_compute_batch;
    _ = pattern_matcher.pattern_detect;
    _ = pattern_matcher.pattern_detect_batch;
}
