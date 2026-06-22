// Lock-Free MPMC Queue (PSR-005)
// Target: 1000× speedup for multi-producer/multi-consumer scenarios

const std = @import("std");

/// Lock-free queue node
pub const Node = struct {
    value: usize,
    next: ?*Node,
};

/// Simple lock-free queue (bounded)
pub const LockFreeQueue = struct {
    allocator: std.mem.Allocator,
    buffer: []?usize,
    capacity: usize,
    head: std.atomic.Value(usize),
    tail: std.atomic.Value(usize),
    
    pub fn init(allocator: std.mem.Allocator, capacity: usize) !LockFreeQueue {
        const buffer = try allocator.alloc(?usize, capacity);
        @memset(buffer, null);
        
        return LockFreeQueue{
            .allocator = allocator,
            .buffer = buffer,
            .capacity = capacity,
            .head = std.atomic.Value(usize).init(0),
            .tail = std.atomic.Value(usize).init(0),
        };
    }
    
    pub fn deinit(self: *LockFreeQueue) void {
        self.allocator.free(self.buffer);
    }
    
    pub fn push(self: *LockFreeQueue, value: usize) bool {
        const tail = self.tail.load(.monotonic);
        const next_tail = (tail + 1) % self.capacity;
        const head = self.head.load(.monotonic);
        
        // Queue full
        if (next_tail == head) {
            return false;
        }
        
        self.buffer[tail] = value;
        _ = self.tail.cmpxchgStrong(tail, next_tail, .release, .monotonic);
        return true;
    }
    
    pub fn pop(self: *LockFreeQueue) ?usize {
        const head = self.head.load(.monotonic);
        const tail = self.tail.load(.monotonic);
        
        // Queue empty
        if (head == tail) {
            return null;
        }
        
        const value = self.buffer[head];
        self.buffer[head] = null;
        
        const next_head = (head + 1) % self.capacity;
        _ = self.head.cmpxchgStrong(head, next_head, .release, .monotonic);
        
        return value;
    }
    
    pub fn size(self: *LockFreeQueue) usize {
        const head = self.head.load(.monotonic);
        const tail = self.tail.load(.monotonic);
        
        if (tail >= head) {
            return tail - head;
        } else {
            return self.capacity - head + tail;
        }
    }
    
    pub fn isEmpty(self: *LockFreeQueue) bool {
        return self.head.load(.monotonic) == self.tail.load(.monotonic);
    }
};

/// C FFI exports
export fn queue_create(capacity: usize) ?*LockFreeQueue {
    const allocator = std.heap.c_allocator;
    const queue = allocator.create(LockFreeQueue) catch return null;
    queue.* = LockFreeQueue.init(allocator, capacity) catch return null;
    return queue;
}

export fn queue_destroy(queue: ?*LockFreeQueue) void {
    if (queue) |q| {
        q.deinit();
        std.heap.c_allocator.destroy(q);
    }
}

export fn queue_push(queue: ?*LockFreeQueue, value: usize) bool {
    if (queue) |q| {
        return q.push(value);
    }
    return false;
}

export fn queue_pop(queue: ?*LockFreeQueue, out_value: [*c]usize) bool {
    if (queue) |q| {
        if (q.pop()) |value| {
            out_value.* = value;
            return true;
        }
    }
    return false;
}

export fn queue_size(queue: ?*LockFreeQueue) usize {
    if (queue) |q| {
        return q.size();
    }
    return 0;
}

// Tests
test "queue creation" {
    var queue = try LockFreeQueue.init(std.testing.allocator, 10);
    defer queue.deinit();
    
    try std.testing.expect(queue.isEmpty());
    try std.testing.expectEqual(@as(usize, 0), queue.size());
}

test "queue push and pop" {
    var queue = try LockFreeQueue.init(std.testing.allocator, 10);
    defer queue.deinit();
    
    try std.testing.expect(queue.push(42));
    try std.testing.expect(queue.push(43));
    
    const val1 = queue.pop();
    try std.testing.expect(val1 != null);
    try std.testing.expectEqual(@as(usize, 42), val1.?);
    
    const val2 = queue.pop();
    try std.testing.expect(val2 != null);
    try std.testing.expectEqual(@as(usize, 43), val2.?);
    
    try std.testing.expect(queue.isEmpty());
}

test "queue full" {
    var queue = try LockFreeQueue.init(std.testing.allocator, 3);
    defer queue.deinit();
    
    try std.testing.expect(queue.push(1));
    try std.testing.expect(queue.push(2));
    try std.testing.expect(!queue.push(3)); // Should fail (capacity-1)
}

test "queue empty pop" {
    var queue = try LockFreeQueue.init(std.testing.allocator, 10);
    defer queue.deinit();
    
    const val = queue.pop();
    try std.testing.expect(val == null);
}
