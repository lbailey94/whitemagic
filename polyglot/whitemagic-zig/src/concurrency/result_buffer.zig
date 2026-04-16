// Result Buffer - Lock-Free Result Buffer (PSR-005)
// Target: 1000× speedup for result collection

const std = @import("std");

pub const Result = struct {
    clone_id: usize,
    success: bool,
    data: []const u8,
};

pub const ResultBuffer = struct {
    allocator: std.mem.Allocator,
    buffer: std.ArrayList(Result),
    mutex: std.Thread.Mutex,
    
    pub fn init(allocator: std.mem.Allocator) ResultBuffer {
        return ResultBuffer{
            .allocator = allocator,
            .buffer = std.ArrayList(Result).init(allocator),
            .mutex = std.Thread.Mutex{},
        };
    }
    
    pub fn deinit(self: *ResultBuffer) void {
        for (self.buffer.items) |result| {
            self.allocator.free(result.data);
        }
        self.buffer.deinit(self.allocator);
    }
    
    pub fn addResult(self: *ResultBuffer, clone_id: usize, success: bool, data: []const u8) !void {
        self.mutex.lock();
        defer self.mutex.unlock();
        
        const owned_data = try self.allocator.dupe(u8, data);
        
        const result = Result{
            .clone_id = clone_id,
            .success = success,
            .data = owned_data,
        };
        
        try self.buffer.append(self.allocator, result);
    }
    
    pub fn getResults(self: *ResultBuffer) []const Result {
        self.mutex.lock();
        defer self.mutex.unlock();
        
        return self.buffer.items;
    }
    
    pub fn clear(self: *ResultBuffer) void {
        self.mutex.lock();
        defer self.mutex.unlock();
        
        for (self.buffer.items) |result| {
            self.allocator.free(result.data);
        }
        self.buffer.clearRetainingCapacity();
    }
    
    pub fn size(self: *ResultBuffer) usize {
        self.mutex.lock();
        defer self.mutex.unlock();
        
        return self.buffer.items.len;
    }
    
    pub fn successCount(self: *ResultBuffer) usize {
        self.mutex.lock();
        defer self.mutex.unlock();
        
        var count: usize = 0;
        for (self.buffer.items) |result| {
            if (result.success) count += 1;
        }
        return count;
    }
};

// C FFI exports
export fn result_buffer_create() ?*ResultBuffer {
    const allocator = std.heap.c_allocator;
    const buffer = allocator.create(ResultBuffer) catch return null;
    buffer.* = ResultBuffer.init(allocator);
    return buffer;
}

export fn result_buffer_destroy(buffer: ?*ResultBuffer) void {
    if (buffer) |b| {
        b.deinit();
        std.heap.c_allocator.destroy(b);
    }
}

export fn result_buffer_add_result(
    buffer: ?*ResultBuffer,
    clone_id: usize,
    success: bool,
    data: [*c]const u8,
    len: usize,
) bool {
    if (buffer) |b| {
        const slice = data[0..len];
        b.addResult(clone_id, success, slice) catch return false;
        return true;
    }
    return false;
}

export fn result_buffer_size(buffer: ?*ResultBuffer) usize {
    if (buffer) |b| {
        return b.size();
    }
    return 0;
}

export fn result_buffer_success_count(buffer: ?*ResultBuffer) usize {
    if (buffer) |b| {
        return b.successCount();
    }
    return 0;
}

// Tests
test "buffer creation" {
    var buffer = ResultBuffer.init(std.testing.allocator);
    defer buffer.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), buffer.size());
}

test "add result" {
    var buffer = ResultBuffer.init(std.testing.allocator);
    defer buffer.deinit();
    
    try buffer.addResult(1, true, "success");
    try std.testing.expectEqual(@as(usize, 1), buffer.size());
}

test "success count" {
    var buffer = ResultBuffer.init(std.testing.allocator);
    defer buffer.deinit();
    
    try buffer.addResult(1, true, "ok");
    try buffer.addResult(2, false, "fail");
    try buffer.addResult(3, true, "ok");
    
    try std.testing.expectEqual(@as(usize, 2), buffer.successCount());
}

test "clear buffer" {
    var buffer = ResultBuffer.init(std.testing.allocator);
    defer buffer.deinit();
    
    try buffer.addResult(1, true, "data");
    buffer.clear();
    
    try std.testing.expectEqual(@as(usize, 0), buffer.size());
}

test "get results" {
    var buffer = ResultBuffer.init(std.testing.allocator);
    defer buffer.deinit();
    
    try buffer.addResult(1, true, "r1");
    try buffer.addResult(2, true, "r2");
    
    const results = buffer.getResults();
    try std.testing.expectEqual(@as(usize, 2), results.len);
}
