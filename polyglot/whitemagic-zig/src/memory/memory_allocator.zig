// Memory Allocator - Custom Allocator for Memory Objects (PSR-001)
// Target: 100-1000× speedup for memory allocation

const std = @import("std");

pub const MemoryPool = struct {
    allocator: std.mem.Allocator,
    pool: std.ArrayList([]u8),
    block_size: usize,
    free_list: std.ArrayList(usize),
    
    pub fn init(allocator: std.mem.Allocator, block_size: usize, initial_blocks: usize) !MemoryPool {
        var pool = std.ArrayList([]u8).init(allocator);
        var free_list = std.ArrayList(usize).init(allocator);
        
        for (0..initial_blocks) |i| {
            const block = try allocator.alloc(u8, block_size);
            try pool.append(allocator, block);
            try free_list.append(allocator, i);
        }
        
        return MemoryPool{
            .allocator = allocator,
            .pool = pool,
            .block_size = block_size,
            .free_list = free_list,
        };
    }
    
    pub fn deinit(self: *MemoryPool) void {
        for (self.pool.items) |block| {
            self.allocator.free(block);
        }
        self.pool.deinit(self.allocator);
        self.free_list.deinit(self.allocator);
    }
    
    pub fn allocate(self: *MemoryPool) ![]u8 {
        if (self.free_list.items.len > 0) {
            const idx = self.free_list.pop();
            return self.pool.items[idx];
        }
        
        // Expand pool
        const block = try self.allocator.alloc(u8, self.block_size);
        try self.pool.append(self.allocator, block);
        return block;
    }
    
    pub fn deallocate(self: *MemoryPool, block: []u8) !void {
        for (self.pool.items, 0..) |pool_block, i| {
            if (pool_block.ptr == block.ptr) {
                try self.free_list.append(self.allocator, i);
                return;
            }
        }
    }
    
    pub fn totalBlocks(self: *const MemoryPool) usize {
        return self.pool.items.len;
    }
    
    pub fn freeBlocks(self: *const MemoryPool) usize {
        return self.free_list.items.len;
    }
    
    pub fn usedBlocks(self: *const MemoryPool) usize {
        return self.totalBlocks() - self.freeBlocks();
    }
};

// C FFI exports
export fn memory_pool_create(block_size: usize, initial_blocks: usize) ?*MemoryPool {
    const allocator = std.heap.c_allocator;
    const pool = allocator.create(MemoryPool) catch return null;
    pool.* = MemoryPool.init(allocator, block_size, initial_blocks) catch return null;
    return pool;
}

export fn memory_pool_destroy(pool: ?*MemoryPool) void {
    if (pool) |p| {
        p.deinit();
        std.heap.c_allocator.destroy(p);
    }
}

export fn memory_pool_total_blocks(pool: ?*const MemoryPool) usize {
    if (pool) |p| {
        return p.totalBlocks();
    }
    return 0;
}

export fn memory_pool_free_blocks(pool: ?*const MemoryPool) usize {
    if (pool) |p| {
        return p.freeBlocks();
    }
    return 0;
}

// Tests
test "memory pool creation" {
    var pool = try MemoryPool.init(std.testing.allocator, 1024, 10);
    defer pool.deinit();
    
    try std.testing.expectEqual(@as(usize, 10), pool.totalBlocks());
    try std.testing.expectEqual(@as(usize, 10), pool.freeBlocks());
}

test "allocate and deallocate" {
    var pool = try MemoryPool.init(std.testing.allocator, 1024, 5);
    defer pool.deinit();
    
    const block = try pool.allocate();
    try std.testing.expectEqual(@as(usize, 4), pool.freeBlocks());
    
    try pool.deallocate(block);
    try std.testing.expectEqual(@as(usize, 5), pool.freeBlocks());
}

test "pool expansion" {
    var pool = try MemoryPool.init(std.testing.allocator, 1024, 2);
    defer pool.deinit();
    
    _ = try pool.allocate();
    _ = try pool.allocate();
    _ = try pool.allocate(); // Should expand
    
    try std.testing.expectEqual(@as(usize, 3), pool.totalBlocks());
}

test "used blocks count" {
    var pool = try MemoryPool.init(std.testing.allocator, 1024, 5);
    defer pool.deinit();
    
    _ = try pool.allocate();
    _ = try pool.allocate();
    
    try std.testing.expectEqual(@as(usize, 2), pool.usedBlocks());
}
