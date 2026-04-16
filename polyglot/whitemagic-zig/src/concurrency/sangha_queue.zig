// Lock-Free Sangha Signal Queue (PSR-005)
// Target: <1μs message passing between agents
const std = @import("std");

pub const SanghaSignal = struct {
    id_ptr: [*c]const u8,
    sender_id_ptr: [*c]const u8,
    content_ptr: [*c]const u8,
    channel_ptr: [*c]const u8,
    timestamp: i64,
    x: f32,
    y: f32,
    z: f32,
    w: f32,
    v: f32,
};

pub const SignalQueue = struct {
    allocator: std.mem.Allocator,
    buffer: []?*SanghaSignal,
    capacity: usize,
    head: std.atomic.Value(usize),
    tail: std.atomic.Value(usize),

    pub fn init(allocator: std.mem.Allocator, capacity: usize) !SignalQueue {
        const buffer = try allocator.alloc(?*SanghaSignal, capacity);
        @memset(buffer, null);
        return SignalQueue{
            .allocator = allocator,
            .buffer = buffer,
            .capacity = capacity,
            .head = std.atomic.Value(usize).init(0),
            .tail = std.atomic.Value(usize).init(0),
        };
    }

    pub fn deinit(self: *SignalQueue) void {
        self.allocator.free(self.buffer);
    }

    pub fn push(self: *SignalQueue, signal: *SanghaSignal) bool {
        const tail = self.tail.load(.monotonic);
        const next_tail = (tail + 1) % self.capacity;
        const head = self.head.load(.monotonic);

        if (next_tail == head) return false;

        self.buffer[tail] = signal;
        _ = self.tail.cmpxchgStrong(tail, next_tail, .release, .monotonic);
        return true;
    }

    pub fn pop(self: *SignalQueue) ?*SanghaSignal {
        const head = self.head.load(.monotonic);
        const tail = self.tail.load(.monotonic);

        if (head == tail) return null;

        const signal = self.buffer[head];
        self.buffer[head] = null;
        const next_head = (head + 1) % self.capacity;
        _ = self.head.cmpxchgStrong(head, next_head, .release, .monotonic);
        return signal;
    }
};

// C FFI Exports
export fn sangha_queue_create(capacity: usize) ?*SignalQueue {
    const allocator = std.heap.c_allocator;
    const queue = allocator.create(SignalQueue) catch return null;
    queue.* = SignalQueue.init(allocator, capacity) catch return null;
    return queue;
}

export fn sangha_queue_push(queue: ?*SignalQueue, signal: ?*SanghaSignal) bool {
    if (queue) |q| {
        if (signal) |s| {
            return q.push(s);
        }
    }
    return false;
}

export fn sangha_queue_pop(queue: ?*SignalQueue) ?*SanghaSignal {
    if (queue) |q| {
        return q.pop();
    }
    return null;
}
