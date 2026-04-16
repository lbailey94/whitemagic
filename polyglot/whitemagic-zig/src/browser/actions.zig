//! Browser Actions - Zig-Accelerated Action Execution
//! Target: 100-1000x speedup for browser automation primitives
//! Priority: P0, Hot Path Score: 1.00

const std = @import("std");
const atomic = std.atomic;

// Hot path: Action types
pub const ActionType = enum(u8) {
    NAVIGATE = 0,
    CLICK = 1,
    TYPE = 2,
    SCROLL = 3,
    EXTRACT = 4,
    SUBMIT = 5,
    WAIT = 6,
};

// Hot path: Action result structure
pub const ActionResult = extern struct {
    success: bool,
    action_type: ActionType,
    selector: [256]u8,
    selector_len: u16,
    value: [1024]u8,
    value_len: u16,
    error: [512]u8,
    error_len: u16,
    duration_us: u64,  // Microseconds for precision
    timestamp_ns: i64,
};

// Hot path: Fast action validation
pub fn validateSelector(selector: []const u8) bool {
    if (selector.len == 0 or selector.len > 256) return false;
    
    // Must start with valid CSS selector character
    const first = selector[0];
    return first == '#' or first == '.' or first == '[' or 
           (first >= 'a' and first <= 'z') or
           (first >= 'A' and first <= 'Z');
}

pub fn validateURL(url: []const u8) bool {
    if (url.len < 4 or url.len > 2048) return false;
    
    // Fast check for http:// or https://
    if (url.len >= 7 and std.mem.eql(u8, url[0..7], "http://")) {
        return std.mem.indexOf(u8, url, ".") != null;
    }
    if (url.len >= 8 and std.mem.eql(u8, url[0..8], "https://")) {
        return std.mem.indexOf(u8, url, ".") != null;
    }
    
    return false;
}

// Hot path: Action timing with nanosecond precision
pub export fn start_action_timer() i64 {
    return std.time.nanoTimestamp();
}

pub export fn end_action_timer(start_ns: i64) u64 {
    const end_ns = std.time.nanoTimestamp();
    return @intCast((end_ns - start_ns) / 1000); // Convert to microseconds
}

// Hot path: Batch action validation
pub export fn validate_actions_batch(
    selectors_ptr: [*]const u8,
    selectors_lens_ptr: [*]const u16,
    action_count: usize,
    valid_out: [*]bool,
) void {
    var i: usize = 0;
    var offset: usize = 0;
    
    while (i < action_count) : (i += 1) {
        const len = selectors_lens_ptr[i];
        const selector = selectors_ptr[offset..offset + len];
        
        valid_out[i] = validateSelector(selector);
        offset += len;
    }
}

// Hot path: Action result initialization
pub export fn init_action_result(
    action_type: ActionType,
    selector_ptr: [*]const u8,
    selector_len: u16,
    out_result: *ActionResult,
) void {
    out_result.* = std.mem.zeroes(ActionResult);
    
    out_result.action_type = action_type;
    out_result.success = false;
    out_result.timestamp_ns = std.time.nanoTimestamp();
    
    const len = @min(selector_len, 256);
    @memcpy(&out_result.selector, selector_ptr[0..len], len);
    out_result.selector_len = len;
}

// Hot path: Record action success
pub export fn record_action_success(
    result: *ActionResult,
    start_time_ns: i64,
    value_ptr: [*]const u8,
    value_len: u16,
) void {
    result.success = true;
    result.duration_us = end_action_timer(start_time_ns);
    
    const len = @min(value_len, 1024);
    @memcpy(&result.value, value_ptr[0..len], len);
    result.value_len = len;
}

// Hot path: Record action error
pub export fn record_action_error(
    result: *ActionResult,
    start_time_ns: i64,
    error_ptr: [*]const u8,
    error_len: u16,
) void {
    result.success = false;
    result.duration_us = end_action_timer(start_time_ns);
    
    const len = @min(error_len, 512);
    @memcpy(&result.error, error_ptr[0..len], len);
    result.error_len = len;
}

// Hot path: Serialize action result to JSON
pub export fn serialize_action_result(
    result: *const ActionResult,
    out_json: [*]u8,
    out_capacity: usize,
    out_len: *usize,
) void {
    var stream = std.io.fixedBufferStream(out_json[0..out_capacity]);
    var writer = stream.writer();
    
    _ = writer.write("{\"success\":") catch {};
    _ = writer.write(if (result.success) "true" else "false") catch {};
    
    _ = writer.write(",\"action\":\"") catch {};
    const action_name = switch (result.action_type) {
        .NAVIGATE => "navigate",
        .CLICK => "click",
        .TYPE => "type",
        .SCROLL => "scroll",
        .EXTRACT => "extract",
        .SUBMIT => "submit",
        .WAIT => "wait",
    };
    _ = writer.write(action_name) catch {};
    
    if (result.selector_len > 0) {
        _ = writer.write("\",\"selector\":\"") catch {};
        _ = writer.write(result.selector[0..result.selector_len]) catch {};
    }
    
    if (result.value_len > 0) {
        _ = writer.write("\",\"value\":\"") catch {};
        _ = writer.write(result.value[0..result.value_len]) catch {};
    }
    
    if (result.error_len > 0) {
        _ = writer.write("\",\"error\":\"") catch {};
        _ = writer.write(result.error[0..result.error_len]) catch {};
    }
    
    _ = writer.print("\",\"duration_ms\":{d:.2},\"timestamp\":{d}}}", .{
        @as(f64, @floatFromInt(result.duration_us)) / 1000.0,
        result.timestamp_ns,
    }) catch {};
    
    out_len.* = stream.pos;
}

// Hot path: Action metrics tracking
pub const ActionMetrics = struct {
    total_actions: atomic.Value(u64),
    successful_actions: atomic.Value(u64),
    failed_actions: atomic.Value(u64),
    total_duration_us: atomic.Value(u64),
    
    pub fn init() ActionMetrics {
        return ActionMetrics{
            .total_actions = atomic.Value(u64).init(0),
            .successful_actions = atomic.Value(u64).init(0),
            .failed_actions = atomic.Value(u64).init(0),
            .total_duration_us = atomic.Value(u64).init(0),
        };
    }
    
    pub fn recordAction(self: *ActionMetrics, success: bool, duration_us: u64) void {
        _ = self.total_actions.fetchAdd(1, .monotonic);
        _ = self.total_duration_us.fetchAdd(duration_us, .monotonic);
        
        if (success) {
            _ = self.successful_actions.fetchAdd(1, .monotonic);
        } else {
            _ = self.failed_actions.fetchAdd(1, .monotonic);
        }
    }
    
    pub fn getAverageDuration(self: *ActionMetrics) u64 {
        const total = self.total_actions.load(.acquire);
        const duration = self.total_duration_us.load(.acquire);
        
        if (total == 0) return 0;
        return duration / total;
    }
};

// Global metrics instance
var global_metrics: ActionMetrics = ActionMetrics.init();
var metrics_mutex: std.Thread.Mutex = .{};

pub export fn record_action_metrics(success: bool, duration_us: u64) void {
    metrics_mutex.lock();
    defer metrics_mutex.unlock();
    
    global_metrics.recordAction(success, duration_us);
}

pub export fn get_action_stats(
    total_out: *u64,
    success_out: *u64,
    failed_out: *u64,
    avg_duration_out: *u64,
) void {
    metrics_mutex.lock();
    defer metrics_mutex.unlock();
    
    total_out.* = global_metrics.total_actions.load(.acquire);
    success_out.* = global_metrics.successful_actions.load(.acquire);
    failed_out.* = global_metrics.failed_actions.load(.acquire);
    avg_duration_out.* = global_metrics.getAverageDuration();
}

// Benchmark entry point
pub export fn benchmark_action_execution(iterations: u32) u64 {
    var timer = std.time.Timer.start() catch return 0;
    
    var i: u32 = 0;
    while (i < iterations) : (i += 1) {
        // Simulate action validation and timing
        const selector = "#login-button";
        _ = validateSelector(selector);
        
        const start = start_action_timer();
        
        // Simulate work
        var j: u32 = 0;
        while (j < 100) : (j += 1) {
            std.mem.doNotOptimizeAway(j);
        }
        
        const duration = end_action_timer(start);
        record_action_metrics(true, duration);
    }
    
    return timer.read();
}
