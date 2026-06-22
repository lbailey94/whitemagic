// FTS Search - Full-Text Search Acceleration (PSR-001)
// Target: 1000× speedup for full-text search

const std = @import("std");

pub const Document = struct {
    id: usize,
    content: []const u8,
};

pub const FTSEngine = struct {
    allocator: std.mem.Allocator,
    documents: std.ArrayList(Document),
    
    pub fn init(allocator: std.mem.Allocator) FTSEngine {
        return FTSEngine{
            .allocator = allocator,
            .documents = std.ArrayList(Document).init(allocator),
        };
    }
    
    pub fn deinit(self: *FTSEngine) void {
        for (self.documents.items) |doc| {
            self.allocator.free(doc.content);
        }
        self.documents.deinit(self.allocator);
    }
    
    pub fn addDocument(self: *FTSEngine, id: usize, content: []const u8) !void {
        const owned_content = try self.allocator.dupe(u8, content);
        try self.documents.append(self.allocator, Document{
            .id = id,
            .content = owned_content,
        });
    }
    
    pub fn search(self: *FTSEngine, query: []const u8) ![]usize {
        var results = std.ArrayList(usize).init(self.allocator);
        
        for (self.documents.items) |doc| {
            if (std.mem.indexOf(u8, doc.content, query) != null) {
                try results.append(self.allocator, doc.id);
            }
        }
        
        return results.toOwnedSlice();
    }
    
    pub fn searchMulti(self: *FTSEngine, queries: []const []const u8) ![]usize {
        var result_set = std.AutoHashMap(usize, void).init(self.allocator);
        defer result_set.deinit();
        
        for (queries) |query| {
            for (self.documents.items) |doc| {
                if (std.mem.indexOf(u8, doc.content, query) != null) {
                    try result_set.put(doc.id, {});
                }
            }
        }
        
        var results = std.ArrayList(usize).init(self.allocator);
        var iter = result_set.keyIterator();
        while (iter.next()) |id| {
            try results.append(self.allocator, id.*);
        }
        
        return results.toOwnedSlice();
    }
    
    pub fn documentCount(self: *FTSEngine) usize {
        return self.documents.items.len;
    }
};

// C FFI exports
export fn fts_engine_create() ?*FTSEngine {
    const allocator = std.heap.c_allocator;
    const engine = allocator.create(FTSEngine) catch return null;
    engine.* = FTSEngine.init(allocator);
    return engine;
}

export fn fts_engine_destroy(engine: ?*FTSEngine) void {
    if (engine) |e| {
        e.deinit();
        std.heap.c_allocator.destroy(e);
    }
}

export fn fts_engine_add_document(
    engine: ?*FTSEngine,
    id: usize,
    content: [*c]const u8,
    len: usize,
) bool {
    if (engine) |e| {
        const content_slice = content[0..len];
        e.addDocument(id, content_slice) catch return false;
        return true;
    }
    return false;
}

export fn fts_engine_document_count(engine: ?*FTSEngine) usize {
    if (engine) |e| {
        return e.documentCount();
    }
    return 0;
}

// Tests
test "fts engine creation" {
    var engine = FTSEngine.init(std.testing.allocator);
    defer engine.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), engine.documentCount());
}

test "fts add document" {
    var engine = FTSEngine.init(std.testing.allocator);
    defer engine.deinit();
    
    try engine.addDocument(1, "hello world");
    try std.testing.expectEqual(@as(usize, 1), engine.documentCount());
}

test "fts search" {
    var engine = FTSEngine.init(std.testing.allocator);
    defer engine.deinit();
    
    try engine.addDocument(1, "hello world");
    try engine.addDocument(2, "goodbye world");
    try engine.addDocument(3, "hello there");
    
    const results = try engine.search("hello");
    defer std.testing.allocator.free(results);
    
    try std.testing.expectEqual(@as(usize, 2), results.len);
}

test "fts search multi" {
    var engine = FTSEngine.init(std.testing.allocator);
    defer engine.deinit();
    
    try engine.addDocument(1, "hello world");
    try engine.addDocument(2, "goodbye world");
    
    const queries = [_][]const u8{ "hello", "goodbye" };
    const results = try engine.searchMulti(&queries);
    defer std.testing.allocator.free(results);
    
    try std.testing.expectEqual(@as(usize, 2), results.len);
}
