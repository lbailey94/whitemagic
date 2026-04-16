// Galaxy Manager - Galaxy Operations (PSR-001)
// Target: 100-1000× speedup for galaxy management

const std = @import("std");

pub const Galaxy = struct {
    id: []const u8,
    name: []const u8,
    memory_count: usize,
    
    pub fn init(id: []const u8, name: []const u8) Galaxy {
        return Galaxy{
            .id = id,
            .name = name,
            .memory_count = 0,
        };
    }
};

pub const GalaxyManager = struct {
    allocator: std.mem.Allocator,
    galaxies: std.StringHashMap(Galaxy),
    active_galaxy: ?[]const u8,
    
    pub fn init(allocator: std.mem.Allocator) GalaxyManager {
        return GalaxyManager{
            .allocator = allocator,
            .galaxies = std.StringHashMap(Galaxy).init(allocator),
            .active_galaxy = null,
        };
    }
    
    pub fn deinit(self: *GalaxyManager) void {
        self.galaxies.deinit();
    }
    
    pub fn createGalaxy(self: *GalaxyManager, id: []const u8, name: []const u8) !void {
        const owned_id = try self.allocator.dupe(u8, id);
        const owned_name = try self.allocator.dupe(u8, name);
        const galaxy = Galaxy.init(owned_id, owned_name);
        try self.galaxies.put(owned_id, galaxy);
    }
    
    pub fn getGalaxy(self: *GalaxyManager, id: []const u8) ?Galaxy {
        return self.galaxies.get(id);
    }
    
    pub fn listGalaxies(self: *GalaxyManager, allocator: std.mem.Allocator) ![][]const u8 {
        var list = std.ArrayList([]const u8).init(allocator);
        
        var iter = self.galaxies.keyIterator();
        while (iter.next()) |key| {
            try list.append(key.*);
        }
        
        return list.toOwnedSlice();
    }
    
    pub fn switchGalaxy(self: *GalaxyManager, id: []const u8) bool {
        if (self.galaxies.contains(id)) {
            self.active_galaxy = id;
            return true;
        }
        return false;
    }
    
    pub fn getActiveGalaxy(self: *GalaxyManager) ?[]const u8 {
        return self.active_galaxy;
    }
    
    pub fn galaxyCount(self: *GalaxyManager) usize {
        return self.galaxies.count();
    }
};

// C FFI exports
export fn galaxy_manager_create() ?*GalaxyManager {
    const allocator = std.heap.c_allocator;
    const manager = allocator.create(GalaxyManager) catch return null;
    manager.* = GalaxyManager.init(allocator);
    return manager;
}

export fn galaxy_manager_destroy(manager: ?*GalaxyManager) void {
    if (manager) |m| {
        m.deinit();
        std.heap.c_allocator.destroy(m);
    }
}

export fn galaxy_manager_create_galaxy(
    manager: ?*GalaxyManager,
    id: [*c]const u8,
    id_len: usize,
    name: [*c]const u8,
    name_len: usize,
) bool {
    if (manager) |m| {
        const id_slice = id[0..id_len];
        const name_slice = name[0..name_len];
        m.createGalaxy(id_slice, name_slice) catch return false;
        return true;
    }
    return false;
}

export fn galaxy_manager_count(manager: ?*GalaxyManager) usize {
    if (manager) |m| {
        return m.galaxyCount();
    }
    return 0;
}

// Tests
test "galaxy manager creation" {
    var manager = GalaxyManager.init(std.testing.allocator);
    defer manager.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), manager.galaxyCount());
}

test "create and get galaxy" {
    var manager = GalaxyManager.init(std.testing.allocator);
    defer manager.deinit();
    
    try manager.createGalaxy("g1", "Galaxy One");
    
    const galaxy = manager.getGalaxy("g1");
    try std.testing.expect(galaxy != null);
    try std.testing.expectEqualStrings("Galaxy One", galaxy.?.name);
}

test "switch galaxy" {
    var manager = GalaxyManager.init(std.testing.allocator);
    defer manager.deinit();
    
    try manager.createGalaxy("g1", "Galaxy One");
    
    const switched = manager.switchGalaxy("g1");
    try std.testing.expect(switched);
    
    const active = manager.getActiveGalaxy();
    try std.testing.expect(active != null);
}

test "list galaxies" {
    var manager = GalaxyManager.init(std.testing.allocator);
    defer manager.deinit();
    
    try manager.createGalaxy("g1", "Galaxy One");
    try manager.createGalaxy("g2", "Galaxy Two");
    
    const list = try manager.listGalaxies(std.testing.allocator);
    defer std.testing.allocator.free(list);
    
    try std.testing.expectEqual(@as(usize, 2), list.len);
}
