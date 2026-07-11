// Galaxy Storage - Binary format storage with compaction
// Phase 8: Galaxy Semantics + Storage (Zig)

const std = @import("std");

// Binary format magic: WMGS (WhiteMagic Galaxy Storage)
const MAGIC = [4]u8{ 0x57, 0x4D, 0x47, 0x53 };
const VERSION: u16 = 1;

pub const GalaxyRecord = struct {
    id: []const u8,
    galaxy: []const u8,
    content: []const u8,
    importance: f64,
    timestamp: []const u8,
};

pub const GalaxyStorage = struct {
    allocator: std.mem.Allocator,
    file_path: []const u8,
    records: std.ArrayList(GalaxyRecord),

    pub fn init(allocator: std.mem.Allocator, file_path: []const u8) GalaxyStorage {
        return GalaxyStorage{
            .allocator = allocator,
            .file_path = file_path,
            .records = std.ArrayList(GalaxyRecord).init(allocator),
        };
    }

    pub fn deinit(self: *GalaxyStorage) void {
        for (self.records.items) |rec| {
            self.allocator.free(rec.id);
            self.allocator.free(rec.galaxy);
            self.allocator.free(rec.content);
            self.allocator.free(rec.timestamp);
        }
        self.records.deinit();
    }

    /// Write records to disk in binary format
    pub fn flush(self: *GalaxyStorage) !void {
        const file = try std.fs.cwd().createFile(self.file_path, .{ .truncate = true });
        defer file.close();

        var writer = file.writer();
        try writer.writeAll(&MAGIC);
        try writer.writeInt(u16, VERSION, .little);
        try writer.writeInt(u32, @intCast(self.records.items.len), .little);

        for (self.records.items) |rec| {
            try writeString(writer, rec.id);
            try writeString(writer, rec.galaxy);
            try writeBytes(writer, rec.content);
            try writer.writeAll(std.mem.asBytes(&rec.importance));
            try writeString(writer, rec.timestamp);
        }
    }

    /// Load records from binary file
    pub fn load(self: *GalaxyStorage) !void {
        const file = std.fs.cwd().openFile(self.file_path, .{}) catch return;
        defer file.close();

        var reader = file.reader();

        var magic: [4]u8 = undefined;
        const n = try reader.readAll(&magic);
        if (n != 4 or !std.mem.eql(u8, &magic, &MAGIC)) {
            return error.InvalidFormat;
        }

        const version = try reader.readInt(u16, .little);
        if (version != VERSION) return error.UnsupportedVersion;

        const record_count = try reader.readInt(u32, .little);

        for (self.records.items) |rec| {
            self.allocator.free(rec.id);
            self.allocator.free(rec.galaxy);
            self.allocator.free(rec.content);
            self.allocator.free(rec.timestamp);
        }
        self.records.clearRetainingCapacity();

        var i: u32 = 0;
        while (i < record_count) : (i += 1) {
            const id = try readString(self.allocator, reader);
            const galaxy = try readString(self.allocator, reader);
            const content = try readBytes(self.allocator, reader);
            var importance: f64 = undefined;
            _ = try reader.readAll(std.mem.asBytes(&importance));
            const timestamp = try readString(self.allocator, reader);

            try self.records.append(.{
                .id = id,
                .galaxy = galaxy,
                .content = content,
                .importance = importance,
                .timestamp = timestamp,
            });
        }
    }

    /// Add a record to storage
    pub fn add(self: *GalaxyStorage, rec: GalaxyRecord) !void {
        const id = try self.allocator.dupe(u8, rec.id);
        const galaxy = try self.allocator.dupe(u8, rec.galaxy);
        const content = try self.allocator.dupe(u8, rec.content);
        const timestamp = try self.allocator.dupe(u8, rec.timestamp);

        try self.records.append(.{
            .id = id,
            .galaxy = galaxy,
            .content = content,
            .importance = rec.importance,
            .timestamp = timestamp,
        });
    }

    /// Get records for a specific galaxy
    pub fn getGalaxyRecords(self: *GalaxyStorage, galaxy: []const u8, allocator: std.mem.Allocator) ![]GalaxyRecord {
        var result = std.ArrayList(GalaxyRecord).init(allocator);
        for (self.records.items) |rec| {
            if (std.mem.eql(u8, rec.galaxy, galaxy)) {
                try result.append(rec);
            }
        }
        return result.toOwnedSlice();
    }

    /// Compact storage by removing records below importance threshold
    pub fn compact(self: *GalaxyStorage, min_importance: f64) usize {
        var removed: usize = 0;
        var i: usize = 0;
        while (i < self.records.items.len) {
            if (self.records.items[i].importance < min_importance) {
                const rec = self.records.swapRemove(i);
                self.allocator.free(rec.id);
                self.allocator.free(rec.galaxy);
                self.allocator.free(rec.content);
                self.allocator.free(rec.timestamp);
                removed += 1;
            } else {
                i += 1;
            }
        }
        return removed;
    }

    /// Get total record count
    pub fn count(self: *GalaxyStorage) usize {
        return self.records.items.len;
    }

    /// Get total bytes used by all records
    pub fn totalBytes(self: *GalaxyStorage) usize {
        var total: usize = 0;
        for (self.records.items) |rec| {
            total += rec.id.len + rec.galaxy.len + rec.content.len + rec.timestamp.len + 8;
        }
        return total;
    }
};

fn writeString(writer: anytype, s: []const u8) !void {
    try writer.writeInt(u16, @intCast(s.len), .little);
    try writer.writeAll(s);
}

fn writeBytes(writer: anytype, b: []const u8) !void {
    try writer.writeInt(u32, @intCast(b.len), .little);
    try writer.writeAll(b);
}

fn readString(allocator: std.mem.Allocator, reader: anytype) ![]u8 {
    const len = try reader.readInt(u16, .little);
    const buf = try allocator.alloc(u8, len);
    const n = try reader.readAll(buf);
    if (n != len) return error.Truncated;
    return buf;
}

fn readBytes(allocator: std.mem.Allocator, reader: anytype) ![]u8 {
    const len = try reader.readInt(u32, .little);
    const buf = try allocator.alloc(u8, len);
    const n = try reader.readAll(buf);
    if (n != len) return error.Truncated;
    return buf;
}

test "galaxy storage add and count" {
    const path = ".zig-cache/test_galaxy_storage.wmg";

    var storage = GalaxyStorage.init(std.testing.allocator, path);
    defer storage.deinit();

    try std.testing.expectEqual(@as(usize, 0), storage.count());

    try storage.add(.{
        .id = "m1",
        .galaxy = "oracle",
        .content = "test content",
        .importance = 0.8,
        .timestamp = "2026-01-01T00:00:00Z",
    });

    try std.testing.expectEqual(@as(usize, 1), storage.count());
}

test "galaxy storage flush and load" {
    var storage = GalaxyStorage.init(std.testing.allocator, ".zig-cache/test_galaxy_flush.wmg");
    defer storage.deinit();

    try storage.add(.{
        .id = "m1",
        .galaxy = "universal",
        .content = "hello world",
        .importance = 0.5,
        .timestamp = "2026-01-01",
    });
    try storage.add(.{
        .id = "m2",
        .galaxy = "oracle",
        .content = "prediction data",
        .importance = 0.9,
        .timestamp = "2026-01-02",
    });

    try storage.flush();

    var storage2 = GalaxyStorage.init(std.testing.allocator, ".zig-cache/test_galaxy_flush.wmg");
    defer storage2.deinit();

    try storage2.load();
    try std.testing.expectEqual(@as(usize, 2), storage2.count());

    try std.testing.expectEqualStrings("m1", storage2.records.items[0].id);
    try std.testing.expectEqualStrings("universal", storage2.records.items[0].galaxy);
    try std.testing.expectEqualStrings("hello world", storage2.records.items[0].content);
    try std.testing.expectEqual(@as(f64, 0.5), storage2.records.items[0].importance);
}

test "galaxy storage filter by galaxy" {
    var storage = GalaxyStorage.init(std.testing.allocator, ".zig-cache/test_galaxy_filter.wmg");
    defer storage.deinit();

    try storage.add(.{ .id = "m1", .galaxy = "oracle", .content = "a", .importance = 0.5, .timestamp = "t1" });
    try storage.add(.{ .id = "m2", .galaxy = "universal", .content = "b", .importance = 0.3, .timestamp = "t2" });
    try storage.add(.{ .id = "m3", .galaxy = "oracle", .content = "c", .importance = 0.7, .timestamp = "t3" });

    const oracle_records = try storage.getGalaxyRecords("oracle", std.testing.allocator);
    defer std.testing.allocator.free(oracle_records);

    try std.testing.expectEqual(@as(usize, 2), oracle_records.len);
}

test "galaxy storage compact" {
    var storage = GalaxyStorage.init(std.testing.allocator, ".zig-cache/test_galaxy_compact.wmg");
    defer storage.deinit();

    try storage.add(.{ .id = "m1", .galaxy = "test", .content = "keep", .importance = 0.8, .timestamp = "t1" });
    try storage.add(.{ .id = "m2", .galaxy = "test", .content = "remove", .importance = 0.1, .timestamp = "t2" });
    try storage.add(.{ .id = "m3", .galaxy = "test", .content = "keep2", .importance = 0.6, .timestamp = "t3" });

    const removed = storage.compact(0.5);
    try std.testing.expectEqual(@as(usize, 1), removed);
    try std.testing.expectEqual(@as(usize, 2), storage.count());
}

test "galaxy storage total bytes" {
    var storage = GalaxyStorage.init(std.testing.allocator, ".zig-cache/test_galaxy_bytes.wmg");
    defer storage.deinit();

    try storage.add(.{ .id = "m1", .galaxy = "g", .content = "abc", .importance = 0.5, .timestamp = "t" });

    // id(2) + galaxy(1) + content(3) + timestamp(1) + importance(8) = 15
    try std.testing.expectEqual(@as(usize, 15), storage.totalBytes());
}
