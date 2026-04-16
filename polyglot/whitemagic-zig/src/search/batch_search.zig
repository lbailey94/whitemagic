// Batch Search - Batch Query Processing (PSR-002)
// Target: 100× speedup for batch queries

const std = @import("std");

pub const SearchQuery = struct {
    id: usize,
    text: []const u8,
};

pub const SearchResult = struct {
    query_id: usize,
    doc_id: usize,
    score: f32,
};

pub const BatchSearchEngine = struct {
    allocator: std.mem.Allocator,
    
    pub fn init(allocator: std.mem.Allocator) BatchSearchEngine {
        return BatchSearchEngine{
            .allocator = allocator,
        };
    }
    
    pub fn searchBatch(
        self: *BatchSearchEngine,
        queries: []const SearchQuery,
        docs: []const []const u8,
    ) ![]SearchResult {
        var results = std.ArrayList(SearchResult).init(self.allocator);
        
        for (queries) |query| {
            for (docs, 0..) |doc, doc_id| {
                const score = self.computeScore(query.text, doc);
                if (score > 0.0) {
                    try results.append(SearchResult{
                        .query_id = query.id,
                        .doc_id = doc_id,
                        .score = score,
                    });
                }
            }
        }
        
        return results.toOwnedSlice();
    }
    
    fn computeScore(self: *BatchSearchEngine, query: []const u8, doc: []const u8) f32 {
        _ = self;
        
        // Simple term matching score
        var matches: f32 = 0.0;
        var query_iter = std.mem.tokenizeAny(u8, query, " \t\n");
        
        while (query_iter.next()) |term| {
            if (std.mem.indexOf(u8, doc, term) != null) {
                matches += 1.0;
            }
        }
        
        return matches;
    }
    
    pub fn parallelSearch(
        self: *BatchSearchEngine,
        queries: []const SearchQuery,
        docs: []const []const u8,
    ) ![]SearchResult {
        // For now, sequential - parallel implementation would use threads
        return self.searchBatch(queries, docs);
    }
};

// C FFI exports
export fn batch_search_create() ?*BatchSearchEngine {
    const allocator = std.heap.c_allocator;
    const engine = allocator.create(BatchSearchEngine) catch return null;
    engine.* = BatchSearchEngine.init(allocator);
    return engine;
}

export fn batch_search_destroy(engine: ?*BatchSearchEngine) void {
    if (engine) |e| {
        _ = e;
        std.heap.c_allocator.destroy(engine.?);
    }
}

// Tests
test "batch search creation" {
    const engine = BatchSearchEngine.init(std.testing.allocator);
    _ = engine;
}

test "batch search execution" {
    var engine = BatchSearchEngine.init(std.testing.allocator);
    
    const queries = [_]SearchQuery{
        SearchQuery{ .id = 0, .text = "hello world" },
        SearchQuery{ .id = 1, .text = "test query" },
    };
    
    const docs = [_][]const u8{
        "hello there world",
        "test document",
        "another test",
    };
    
    const results = try engine.searchBatch(&queries, &docs);
    defer std.testing.allocator.free(results);
    
    try std.testing.expect(results.len > 0);
}

test "compute score" {
    var engine = BatchSearchEngine.init(std.testing.allocator);
    
    const score = engine.computeScore("hello world", "hello there world");
    try std.testing.expect(score > 0.0);
}

test "parallel search" {
    var engine = BatchSearchEngine.init(std.testing.allocator);
    
    const queries = [_]SearchQuery{
        SearchQuery{ .id = 0, .text = "test" },
    };
    
    const docs = [_][]const u8{
        "test document",
    };
    
    const results = try engine.parallelSearch(&queries, &docs);
    defer std.testing.allocator.free(results);
    
    try std.testing.expect(results.len > 0);
}
