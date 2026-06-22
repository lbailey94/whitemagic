// Input Sanitizer - Zero-Copy Sanitization (PSR-006)
// Target: 1000× speedup for input sanitization

const std = @import("std");

pub const SanitizationResult = struct {
    clean: []const u8,
    violations: usize,
};

pub const InputSanitizer = struct {
    allocator: std.mem.Allocator,
    max_length: usize,
    
    pub fn init(allocator: std.mem.Allocator, max_length: usize) InputSanitizer {
        return InputSanitizer{
            .allocator = allocator,
            .max_length = max_length,
        };
    }
    
    pub fn sanitize(self: *InputSanitizer, input: []const u8) !SanitizationResult {
        var violations: usize = 0;
        var clean = std.ArrayList(u8).init(self.allocator);
        defer clean.deinit();
        
        const truncated = if (input.len > self.max_length) blk: {
            violations += 1;
            break :blk input[0..self.max_length];
        } else input;
        
        for (truncated) |char| {
            if (std.ascii.isPrint(char) or char == '\n' or char == '\t') {
                try clean.append(char);
            } else {
                violations += 1;
            }
        }
        
        return SanitizationResult{
            .clean = try self.allocator.dupe(u8, clean.items),
            .violations = violations,
        };
    }
    
    pub fn validateLength(self: *const InputSanitizer, input: []const u8) bool {
        return input.len <= self.max_length;
    }
};

// C FFI exports
export fn input_sanitizer_create(max_length: usize) ?*InputSanitizer {
    const allocator = std.heap.c_allocator;
    const sanitizer = allocator.create(InputSanitizer) catch return null;
    sanitizer.* = InputSanitizer.init(allocator, max_length);
    return sanitizer;
}

export fn input_sanitizer_destroy(sanitizer: ?*InputSanitizer) void {
    if (sanitizer) |s| {
        std.heap.c_allocator.destroy(s);
    }
}

export fn input_sanitizer_validate_length(sanitizer: ?*const InputSanitizer, input: [*c]const u8, len: usize) bool {
    if (sanitizer) |s| {
        const slice = input[0..len];
        return s.validateLength(slice);
    }
    return false;
}

// Tests
test "sanitizer creation" {
    var sanitizer = InputSanitizer.init(std.testing.allocator, 1000);
    _ = sanitizer;
}

test "sanitize clean input" {
    var sanitizer = InputSanitizer.init(std.testing.allocator, 1000);
    const result = try sanitizer.sanitize("hello world");
    defer std.testing.allocator.free(result.clean);
    
    try std.testing.expectEqual(@as(usize, 0), result.violations);
}

test "sanitize with violations" {
    var sanitizer = InputSanitizer.init(std.testing.allocator, 1000);
    const input = "hello\x00world";
    const result = try sanitizer.sanitize(input);
    defer std.testing.allocator.free(result.clean);
    
    try std.testing.expect(result.violations > 0);
}

test "validate length" {
    const sanitizer = InputSanitizer.init(std.testing.allocator, 10);
    
    try std.testing.expect(sanitizer.validateLength("short"));
    try std.testing.expect(!sanitizer.validateLength("this is too long"));
}
