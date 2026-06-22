// Rule Engine - Fast Rule Evaluation (PSR-004)
// Target: 1000× speedup for rule evaluation

const std = @import("std");

pub const Rule = struct {
    id: []const u8,
    conditions: std.ArrayList([]const u8),
    action: []const u8,
    
    pub fn init(allocator: std.mem.Allocator, id: []const u8, action: []const u8) Rule {
        return Rule{
            .id = id,
            .conditions = std.ArrayList([]const u8).init(allocator),
            .action = action,
        };
    }
    
    pub fn deinit(self: *Rule) void {
        self.conditions.deinit();
    }
    
    pub fn addCondition(self: *Rule, condition: []const u8) !void {
        try self.conditions.append(condition);
    }
};

pub const RuleEngine = struct {
    allocator: std.mem.Allocator,
    rules: std.ArrayList(Rule),
    facts: std.StringHashMap(bool),
    
    pub fn init(allocator: std.mem.Allocator) RuleEngine {
        return RuleEngine{
            .allocator = allocator,
            .rules = std.ArrayList(Rule).init(allocator),
            .facts = std.StringHashMap(bool).init(allocator),
        };
    }
    
    pub fn deinit(self: *RuleEngine) void {
        for (self.rules.items) |*rule| {
            rule.deinit();
        }
        self.rules.deinit();
        self.facts.deinit();
    }
    
    pub fn addRule(self: *RuleEngine, rule: Rule) !void {
        try self.rules.append(rule);
    }
    
    pub fn setFact(self: *RuleEngine, fact: []const u8, value: bool) !void {
        try self.facts.put(fact, value);
    }
    
    pub fn evaluate(self: *RuleEngine) !std.ArrayList([]const u8) {
        var triggered = std.ArrayList([]const u8).init(self.allocator);
        
        for (self.rules.items) |rule| {
            var all_true = true;
            
            for (rule.conditions.items) |condition| {
                if (self.facts.get(condition)) |value| {
                    if (!value) {
                        all_true = false;
                        break;
                    }
                } else {
                    all_true = false;
                    break;
                }
            }
            
            if (all_true) {
                try triggered.append(rule.action);
            }
        }
        
        return triggered;
    }
    
    pub fn ruleCount(self: *const RuleEngine) usize {
        return self.rules.items.len;
    }
};

// C FFI exports
export fn rule_engine_create() ?*RuleEngine {
    const allocator = std.heap.c_allocator;
    const engine = allocator.create(RuleEngine) catch return null;
    engine.* = RuleEngine.init(allocator);
    return engine;
}

export fn rule_engine_destroy(engine: ?*RuleEngine) void {
    if (engine) |eng| {
        eng.deinit();
        std.heap.c_allocator.destroy(eng);
    }
}

export fn rule_engine_rule_count(engine: ?*const RuleEngine) usize {
    if (engine) |eng| {
        return eng.ruleCount();
    }
    return 0;
}

// Tests
test "engine creation" {
    var engine = RuleEngine.init(std.testing.allocator);
    defer engine.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), engine.ruleCount());
}

test "add rule" {
    var engine = RuleEngine.init(std.testing.allocator);
    defer engine.deinit();
    
    var rule = Rule.init(std.testing.allocator, "r1", "action");
    try engine.addRule(rule);
    
    try std.testing.expectEqual(@as(usize, 1), engine.ruleCount());
}

test "evaluate rules" {
    var engine = RuleEngine.init(std.testing.allocator);
    defer engine.deinit();
    
    var rule = Rule.init(std.testing.allocator, "r1", "fire");
    try rule.addCondition("condition1");
    try engine.addRule(rule);
    
    try engine.setFact("condition1", true);
    
    const triggered = try engine.evaluate();
    defer triggered.deinit();
    
    try std.testing.expectEqual(@as(usize, 1), triggered.items.len);
}
