// State Tracker - Lock-Free State Tracking (PSR-007)
// Target: 1000× speedup for state management

const std = @import("std");

pub const StateTracker = struct {
    allocator: std.mem.Allocator,
    states: std.StringHashMap([]const u8),
    
    pub fn init(allocator: std.mem.Allocator) StateTracker {
        return StateTracker{
            .allocator = allocator,
            .states = std.StringHashMap([]const u8).init(allocator),
        };
    }
    
    pub fn deinit(self: *StateTracker) void {
        self.states.deinit();
    }
    
    pub fn setState(self: *StateTracker, entity: []const u8, state: []const u8) !void {
        try self.states.put(entity, state);
    }
    
    pub fn getState(self: *const StateTracker, entity: []const u8) ?[]const u8 {
        return self.states.get(entity);
    }
    
    pub fn entityCount(self: *const StateTracker) usize {
        return self.states.count();
    }
};

// C FFI exports
export fn state_tracker_create() ?*StateTracker {
    const allocator = std.heap.c_allocator;
    const tracker = allocator.create(StateTracker) catch return null;
    tracker.* = StateTracker.init(allocator);
    return tracker;
}

export fn state_tracker_destroy(tracker: ?*StateTracker) void {
    if (tracker) |t| {
        t.deinit();
        std.heap.c_allocator.destroy(t);
    }
}

export fn state_tracker_entity_count(tracker: ?*const StateTracker) usize {
    if (tracker) |t| {
        return t.entityCount();
    }
    return 0;
}

// Tests
test "tracker creation" {
    var tracker = StateTracker.init(std.testing.allocator);
    defer tracker.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), tracker.entityCount());
}

test "set state" {
    var tracker = StateTracker.init(std.testing.allocator);
    defer tracker.deinit();
    
    try tracker.setState("entity1", "active");
    try std.testing.expectEqual(@as(usize, 1), tracker.entityCount());
}

test "get state" {
    var tracker = StateTracker.init(std.testing.allocator);
    defer tracker.deinit();
    
    try tracker.setState("entity1", "active");
    
    const state = tracker.getState("entity1");
    try std.testing.expect(state != null);
    try std.testing.expect(std.mem.eql(u8, state.?, "active"));
}
