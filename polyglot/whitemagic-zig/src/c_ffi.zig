// C FFI exports for Rust integration
// Allows Rust to call Zig query router via C ABI

const std = @import("std");
const router = @import("query_router.zig");

// C-compatible strategy enum
pub const CSearchStrategy = enum(c_int) {
    lexical_only = 0,
    semantic_only = 1,
    hybrid_balanced = 2,
    hybrid_lexical_heavy = 3,
    hybrid_semantic_heavy = 4,
};

// C-compatible query plan struct
pub const CQueryPlan = extern struct {
    strategy: c_int,
    lexical_weight: f32,
    semantic_weight: f32,
    use_constellation: bool,
    estimated_cost: u64,
};

/// C FFI: Route a query and return execution plan
/// 
/// # Safety
/// - query_ptr must be valid UTF-8
/// - query_len must be accurate
/// - plan_out must be a valid pointer
export fn zig_route_query(
    query_ptr: [*]const u8,
    query_len: usize,
    plan_out: *CQueryPlan,
) void {
    const query = query_ptr[0..query_len];
    const plan = router.route_query(query);
    
    plan_out.* = CQueryPlan{
        .strategy = @intFromEnum(plan.strategy),
        .lexical_weight = plan.weights.lexical,
        .semantic_weight = plan.weights.semantic,
        .use_constellation = plan.use_constellation,
        .estimated_cost = plan.estimated_cost,
    };
}

/// C FFI: Get strategy weights
export fn zig_get_strategy_weights(
    strategy: c_int,
    lexical_out: *f32,
    semantic_out: *f32,
) void {
    const strat = @as(router.SearchStrategy, @enumFromInt(@as(u8, @intCast(strategy))));
    const weights = strat.weights();
    lexical_out.* = weights.lexical;
    semantic_out.* = weights.semantic;
}

/// C FFI: Batch route queries
/// 
/// # Safety
/// - queries must be an array of valid string pointers
/// - query_lens must match queries length
/// - plans_out must have space for count plans
export fn zig_route_batch(
    queries: [*]const [*]const u8,
    query_lens: [*]const usize,
    count: usize,
    plans_out: [*]CQueryPlan,
) void {
    var i: usize = 0;
    while (i < count) : (i += 1) {
        const query = queries[i][0..query_lens[i]];
        const plan = router.route_query(query);
        
        plans_out[i] = CQueryPlan{
            .strategy = @intFromEnum(plan.strategy),
            .lexical_weight = plan.weights.lexical,
            .semantic_weight = plan.weights.semantic,
            .use_constellation = plan.use_constellation,
            .estimated_cost = plan.estimated_cost,
        };
    }
}

// ── Tests ────────────────────────────────────────────────────────────

test "c_ffi basic routing" {
    const query = "test query";
    var plan: CQueryPlan = undefined;
    
    zig_route_query(query.ptr, query.len, &plan);
    
    try std.testing.expect(plan.strategy >= 0);
    try std.testing.expect(plan.strategy <= 4);
    try std.testing.expect(plan.lexical_weight >= 0.0);
    try std.testing.expect(plan.semantic_weight >= 0.0);
}

test "c_ffi strategy weights" {
    var lexical: f32 = undefined;
    var semantic: f32 = undefined;
    
    zig_get_strategy_weights(2, &lexical, &semantic); // hybrid_balanced
    
    try std.testing.expectEqual(@as(f32, 0.5), lexical);
    try std.testing.expectEqual(@as(f32, 0.5), semantic);
}
