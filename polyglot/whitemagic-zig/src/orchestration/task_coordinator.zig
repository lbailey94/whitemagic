// Task Coordinator - Zero-Overhead Task Coordination (PSR-007)
// Target: 1000× speedup for task coordination

const std = @import("std");

pub const Task = struct {
    id: []const u8,
    priority: i32,
    status: []const u8,
};

pub const TaskCoordinator = struct {
    allocator: std.mem.Allocator,
    tasks: std.ArrayList(Task),
    
    pub fn init(allocator: std.mem.Allocator) TaskCoordinator {
        return TaskCoordinator{
            .allocator = allocator,
            .tasks = std.ArrayList(Task).init(allocator),
        };
    }
    
    pub fn deinit(self: *TaskCoordinator) void {
        self.tasks.deinit();
    }
    
    pub fn addTask(self: *TaskCoordinator, task: Task) !void {
        try self.tasks.append(task);
    }
    
    pub fn getNextTask(self: *TaskCoordinator) ?Task {
        for (self.tasks.items) |task| {
            if (std.mem.eql(u8, task.status, "pending")) {
                return task;
            }
        }
        return null;
    }
    
    pub fn taskCount(self: *const TaskCoordinator) usize {
        return self.tasks.items.len;
    }
};

// C FFI exports
export fn task_coordinator_create() ?*TaskCoordinator {
    const allocator = std.heap.c_allocator;
    const coordinator = allocator.create(TaskCoordinator) catch return null;
    coordinator.* = TaskCoordinator.init(allocator);
    return coordinator;
}

export fn task_coordinator_destroy(coordinator: ?*TaskCoordinator) void {
    if (coordinator) |c| {
        c.deinit();
        std.heap.c_allocator.destroy(c);
    }
}

export fn task_coordinator_task_count(coordinator: ?*const TaskCoordinator) usize {
    if (coordinator) |c| {
        return c.taskCount();
    }
    return 0;
}

// Tests
test "coordinator creation" {
    var coordinator = TaskCoordinator.init(std.testing.allocator);
    defer coordinator.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), coordinator.taskCount());
}

test "add task" {
    var coordinator = TaskCoordinator.init(std.testing.allocator);
    defer coordinator.deinit();
    
    try coordinator.addTask(Task{
        .id = "t1",
        .priority = 1,
        .status = "pending",
    });
    
    try std.testing.expectEqual(@as(usize, 1), coordinator.taskCount());
}

test "get next task" {
    var coordinator = TaskCoordinator.init(std.testing.allocator);
    defer coordinator.deinit();
    
    try coordinator.addTask(Task{
        .id = "t1",
        .priority = 1,
        .status = "pending",
    });
    
    const next = coordinator.getNextTask();
    try std.testing.expect(next != null);
}
