// Task Pool - Zero-Overhead Task Pool (PSR-005)
// Target: 1000× speedup for task pooling

const std = @import("std");

pub const Task = struct {
    id: usize,
    priority: i32,
    data: []const u8,
};

pub const TaskPool = struct {
    allocator: std.mem.Allocator,
    tasks: std.ArrayList(Task),
    next_id: usize,
    
    pub fn init(allocator: std.mem.Allocator) TaskPool {
        return TaskPool{
            .allocator = allocator,
            .tasks = std.ArrayList(Task).init(allocator),
            .next_id = 0,
        };
    }
    
    pub fn deinit(self: *TaskPool) void {
        for (self.tasks.items) |task| {
            self.allocator.free(task.data);
        }
        self.tasks.deinit(self.allocator);
    }
    
    pub fn addTask(self: *TaskPool, priority: i32, data: []const u8) !usize {
        const id = self.next_id;
        self.next_id += 1;
        
        const owned_data = try self.allocator.dupe(u8, data);
        
        const task = Task{
            .id = id,
            .priority = priority,
            .data = owned_data,
        };
        
        try self.tasks.append(self.allocator, task);
        return id;
    }
    
    pub fn getTask(self: *TaskPool) ?Task {
        if (self.tasks.items.len == 0) return null;
        
        // Find highest priority task
        var max_priority: i32 = std.math.minInt(i32);
        var max_idx: usize = 0;
        
        for (self.tasks.items, 0..) |task, i| {
            if (task.priority > max_priority) {
                max_priority = task.priority;
                max_idx = i;
            }
        }
        
        return self.tasks.orderedRemove(max_idx);
    }
    
    pub fn size(self: *const TaskPool) usize {
        return self.tasks.items.len;
    }
    
    pub fn clear(self: *TaskPool) void {
        for (self.tasks.items) |task| {
            self.allocator.free(task.data);
        }
        self.tasks.clearRetainingCapacity();
    }
};

// C FFI exports
export fn task_pool_create() ?*TaskPool {
    const allocator = std.heap.c_allocator;
    const pool = allocator.create(TaskPool) catch return null;
    pool.* = TaskPool.init(allocator);
    return pool;
}

export fn task_pool_destroy(pool: ?*TaskPool) void {
    if (pool) |p| {
        p.deinit();
        std.heap.c_allocator.destroy(p);
    }
}

export fn task_pool_add_task(pool: ?*TaskPool, priority: i32, data: [*c]const u8, len: usize) usize {
    if (pool) |p| {
        const slice = data[0..len];
        return p.addTask(priority, slice) catch return std.math.maxInt(usize);
    }
    return std.math.maxInt(usize);
}

export fn task_pool_size(pool: ?*const TaskPool) usize {
    if (pool) |p| {
        return p.size();
    }
    return 0;
}

// Tests
test "pool creation" {
    var pool = TaskPool.init(std.testing.allocator);
    defer pool.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), pool.size());
}

test "add task" {
    var pool = TaskPool.init(std.testing.allocator);
    defer pool.deinit();
    
    const data = "test data";
    const id = try pool.addTask(1, data);
    
    try std.testing.expectEqual(@as(usize, 0), id);
    try std.testing.expectEqual(@as(usize, 1), pool.size());
}

test "get task priority" {
    var pool = TaskPool.init(std.testing.allocator);
    defer pool.deinit();
    
    _ = try pool.addTask(1, "low");
    _ = try pool.addTask(5, "high");
    _ = try pool.addTask(3, "med");
    
    const task = pool.getTask();
    try std.testing.expect(task != null);
    try std.testing.expectEqual(@as(i32, 5), task.?.priority);
}

test "clear pool" {
    var pool = TaskPool.init(std.testing.allocator);
    defer pool.deinit();
    
    _ = try pool.addTask(1, "task1");
    _ = try pool.addTask(2, "task2");
    
    pool.clear();
    try std.testing.expectEqual(@as(usize, 0), pool.size());
}
