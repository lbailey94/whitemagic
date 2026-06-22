// Work Queue - Lock-Free Work Queue (PSR-005)
// Target: 1000× faster than Python queue

const std = @import("std");

pub const WorkQueue = struct {
    capacity: usize,
    head: std.atomic.Value(usize),
    tail: std.atomic.Value(usize),
    buffer: []?[]const u8,
    allocator: std.mem.Allocator,

    pub fn init(allocator: std.mem.Allocator, capacity: usize) !*WorkQueue {
        const queue = try allocator.create(WorkQueue);
        const buffer = try allocator.alloc(?[]const u8, capacity);
        
        for (buffer) |*slot| {
            slot.* = null;
        }
        
        queue.* = WorkQueue{
            .capacity = capacity,
            .head = std.atomic.Value(usize).init(0),
            .tail = std.atomic.Value(usize).init(0),
            .buffer = buffer,
            .allocator = allocator,
        };
        
        return queue;
    }

    pub fn deinit(self: *WorkQueue) void {
        self.allocator.free(self.buffer);
        self.allocator.destroy(self);
    }

    pub fn push(self: *WorkQueue, task: []const u8) bool {
        const tail = self.tail.load(.acquire);
        const next_tail = (tail + 1) % self.capacity;
        const head = self.head.load(.acquire);
        
        if (next_tail == head) {
            return false; // Queue full
        }
        
        self.buffer[tail] = task;
        _ = self.tail.store(next_tail, .release);
        
        return true;
    }

    pub fn pop(self: *WorkQueue) ?[]const u8 {
        const head = self.head.load(.acquire);
        const tail = self.tail.load(.acquire);
        
        if (head == tail) {
            return null; // Queue empty
        }
        
        const task = self.buffer[head];
        self.buffer[head] = null;
        _ = self.head.store((head + 1) % self.capacity, .release);
        
        return task;
    }

    pub fn size(self: *WorkQueue) usize {
        const head = self.head.load(.acquire);
        const tail = self.tail.load(.acquire);
        
        if (tail >= head) {
            return tail - head;
        } else {
            return self.capacity - head + tail;
        }
    }

    pub fn is_empty(self: *WorkQueue) bool {
        return self.head.load(.acquire) == self.tail.load(.acquire);
    }

    pub fn is_full(self: *WorkQueue) bool {
        const tail = self.tail.load(.acquire);
        const next_tail = (tail + 1) % self.capacity;
        return next_tail == self.head.load(.acquire);
    }
};

// C FFI exports
export fn work_queue_create(capacity: usize) ?*WorkQueue {
    const allocator = std.heap.c_allocator;
    return WorkQueue.init(allocator, capacity) catch null;
}

export fn work_queue_destroy(queue: *WorkQueue) void {
    queue.deinit();
}

export fn work_queue_push(queue: *WorkQueue, task: [*:0]const u8) bool {
    const task_slice = std.mem.span(task);
    return queue.push(task_slice);
}

export fn work_queue_pop(queue: *WorkQueue, buffer: [*]u8, buffer_len: usize) bool {
    if (queue.pop()) |task| {
        const copy_len = @min(task.len, buffer_len - 1);
        @memcpy(buffer[0..copy_len], task[0..copy_len]);
        buffer[copy_len] = 0;
        return true;
    }
    return false;
}

export fn work_queue_size(queue: *WorkQueue) usize {
    return queue.size();
}

test "work queue basic operations" {
    const allocator = std.testing.allocator;
    const queue = try WorkQueue.init(allocator, 10);
    defer queue.deinit();

    try std.testing.expect(queue.is_empty());
    try std.testing.expect(queue.push("task1"));
    try std.testing.expect(!queue.is_empty());
    try std.testing.expect(queue.size() == 1);

    const task = queue.pop();
    try std.testing.expect(task != null);
    try std.testing.expect(queue.is_empty());
}

test "work queue full capacity" {
    const allocator = std.testing.allocator;
    const queue = try WorkQueue.init(allocator, 3);
    defer queue.deinit();

    try std.testing.expect(queue.push("task1"));
    try std.testing.expect(queue.push("task2"));
    try std.testing.expect(!queue.is_full());
    try std.testing.expect(!queue.push("task3")); // Should fail, capacity is 3 but one slot reserved
}
