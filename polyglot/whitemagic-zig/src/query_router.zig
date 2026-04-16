// Polyglot Query Router - Zig Implementation
// H003: <10μs query routing with zero allocations

const std = @import("std");

/// Search strategy enum
pub const SearchStrategy = enum(u8) {
    lexical_only = 0,
    semantic_only = 1,
    hybrid_balanced = 2,
    hybrid_lexical_heavy = 3,
    hybrid_semantic_heavy = 4,

    pub fn weights(self: SearchStrategy) struct { lexical: f32, semantic: f32 } {
        return switch (self) {
            .lexical_only => .{ .lexical = 1.0, .semantic = 0.0 },
            .semantic_only => .{ .lexical = 0.0, .semantic = 1.0 },
            .hybrid_balanced => .{ .lexical = 0.5, .semantic = 0.5 },
            .hybrid_lexical_heavy => .{ .lexical = 0.7, .semantic = 0.3 },
            .hybrid_semantic_heavy => .{ .lexical = 0.3, .semantic = 0.7 },
        };
    }
};

/// Query execution plan
pub const QueryPlan = struct {
    strategy: SearchStrategy,
    weights: struct { lexical: f32, semantic: f32 },
    use_constellation: bool,
    estimated_cost: u64,
    cache_key: [64]u8, // Pre-computed cache key
};

/// H003: <10μs query routing with zero allocations
pub fn route_query(query: []const u8) QueryPlan {
    // Pattern detection (zero allocations)
    const has_quotes = std.mem.indexOf(u8, query, "\"") != null;
    const has_technical = is_technical(query);
    const length = query.len;
    const has_camelcase = has_camel_case(query);
    const has_code_markers = has_code_pattern(query);

    // Decision tree (compiled to jump table by Zig)
    const strategy = blk: {
        if (has_quotes) {
            // Exact phrase search - lexical only
            break :blk SearchStrategy.lexical_only;
        } else if (has_code_markers or has_camelcase) {
            // Code search - lexical heavy
            break :blk SearchStrategy.hybrid_lexical_heavy;
        } else if (has_technical and length > 50) {
            // Long technical query - semantic heavy
            break :blk SearchStrategy.hybrid_semantic_heavy;
        } else if (length < 10) {
            // Short query - lexical only
            break :blk SearchStrategy.lexical_only;
        } else if (length > 100) {
            // Very long query - semantic only
            break :blk SearchStrategy.semantic_only;
        } else {
            // Default - balanced hybrid
            break :blk SearchStrategy.hybrid_balanced;
        }
    };

    const weights_val = strategy.weights();
    const use_constellation = length > 20 and !has_quotes;
    const estimated_cost = estimate_cost(strategy, length);

    // Pre-compute cache key (zero allocations)
    var cache_key: [64]u8 = undefined;
    compute_cache_key(query, strategy, &cache_key);

    return QueryPlan{
        .strategy = strategy,
        .weights = weights_val,
        .use_constellation = use_constellation,
        .estimated_cost = estimated_cost,
        .cache_key = cache_key,
    };
}

/// Check if query contains technical keywords (compile-time optimized)
fn is_technical(query: []const u8) bool {
    // Compile-time keyword list
    const keywords = [_][]const u8{
        "rust",     "python",   "function", "class",    "memory",
        "cache",    "database", "optimize", "benchmark", "algorithm",
        "struct",   "impl",     "trait",    "async",    "await",
        "vector",   "embedding", "semantic", "lexical",  "search",
        "query",    "index",    "hash",     "tree",     "graph",
        "node",     "edge",     "cluster",  "pattern",  "match",
    };

    // Fast substring search (SIMD-optimized by Zig)
    for (keywords) |kw| {
        if (std.mem.indexOf(u8, query, kw)) |_| return true;
    }
    return false;
}

/// Check for camelCase or PascalCase patterns
fn has_camel_case(query: []const u8) bool {
    var prev_lower = false;
    for (query) |c| {
        if (c >= 'A' and c <= 'Z') {
            if (prev_lower) return true;
        }
        prev_lower = (c >= 'a' and c <= 'z');
    }
    return false;
}

/// Check for code patterns (backticks, parentheses, brackets)
fn has_code_pattern(query: []const u8) bool {
    const markers = [_]u8{ '`', '(', ')', '[', ']', '{', '}', ':', ';' };
    var count: usize = 0;
    for (query) |c| {
        for (markers) |m| {
            if (c == m) {
                count += 1;
                if (count >= 2) return true;
            }
        }
    }
    return false;
}

/// Estimate query execution cost
fn estimate_cost(strategy: SearchStrategy, length: usize) u64 {
    const base_cost: u64 = switch (strategy) {
        .lexical_only => 100,
        .semantic_only => 500,
        .hybrid_balanced => 300,
        .hybrid_lexical_heavy => 200,
        .hybrid_semantic_heavy => 400,
    };
    return base_cost + length * 2;
}

/// Compute cache key (FNV-1a hash)
fn compute_cache_key(query: []const u8, strategy: SearchStrategy, out: *[64]u8) void {
    // FNV-1a hash (fast, good distribution)
    const FNV_OFFSET: u64 = 14695981039346656037;
    const FNV_PRIME: u64 = 1099511628211;

    var hash: u64 = FNV_OFFSET;
    
    // Hash query
    for (query) |byte| {
        hash ^= byte;
        hash *%= FNV_PRIME;
    }
    
    // Mix in strategy
    hash ^= @intFromEnum(strategy);
    hash *%= FNV_PRIME;

    // Convert to hex string
    _ = std.fmt.bufPrint(out, "{x:0>16}", .{hash}) catch unreachable;
}

/// Batch route multiple queries (SIMD-friendly)
pub fn route_batch(queries: []const []const u8, plans: []QueryPlan) void {
    std.debug.assert(queries.len == plans.len);
    
    // Zig auto-vectorizes this loop
    for (queries, 0..) |query, i| {
        plans[i] = route_query(query);
    }
}

// ── Tests ────────────────────────────────────────────────────────────

test "route_query basic" {
    const plan = route_query("simple query");
    try std.testing.expect(plan.strategy == .hybrid_balanced);
}

test "route_query quoted" {
    const plan = route_query("\"exact phrase\"");
    try std.testing.expect(plan.strategy == .lexical_only);
}

test "route_query technical" {
    const plan = route_query("rust function implementation with async await patterns");
    try std.testing.expect(plan.strategy == .hybrid_semantic_heavy);
}

test "route_query short" {
    const plan = route_query("test");
    try std.testing.expect(plan.strategy == .lexical_only);
}

test "route_query code" {
    const plan = route_query("fn myFunction() { return true; }");
    try std.testing.expect(plan.strategy == .hybrid_lexical_heavy);
}

test "route_query camelCase" {
    const plan = route_query("findMemoryById");
    try std.testing.expect(plan.strategy == .hybrid_lexical_heavy);
}

test "route_batch" {
    const queries = [_][]const u8{
        "query one",
        "query two",
        "query three",
    };
    var plans: [3]QueryPlan = undefined;
    
    route_batch(&queries, &plans);
    
    try std.testing.expect(plans.len == 3);
    try std.testing.expect(plans[0].strategy == .hybrid_balanced);
}

test "cache_key uniqueness" {
    var key1: [64]u8 = undefined;
    var key2: [64]u8 = undefined;
    
    compute_cache_key("query one", .hybrid_balanced, &key1);
    compute_cache_key("query two", .hybrid_balanced, &key2);
    
    try std.testing.expect(!std.mem.eql(u8, &key1, &key2));
}

test "performance benchmark" {
    const iterations = 100_000;
    const query = "rust memory optimization with caching and parallel search";
    
    const start = std.time.nanoTimestamp();
    
    var i: usize = 0;
    while (i < iterations) : (i += 1) {
        _ = route_query(query);
    }
    
    const end = std.time.nanoTimestamp();
    const elapsed_ns = @as(u64, @intCast(end - start));
    const avg_ns = elapsed_ns / iterations;
    
    // Should be <10μs (10,000ns) per query
    std.debug.print("\nAverage routing time: {}ns\n", .{avg_ns});
    try std.testing.expect(avg_ns < 10_000);
}
