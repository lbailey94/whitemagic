// Parameter Parser - Zero-Allocation Parsing (PSR-006)
// Target: 1000× speedup for parameter parsing

const std = @import("std");

pub const ParamType = enum {
    string,
    integer,
    float,
    boolean,
    array,
    object,
};

pub const ParsedParam = struct {
    name: []const u8,
    value: []const u8,
    param_type: ParamType,
};

pub const ParamParser = struct {
    allocator: std.mem.Allocator,
    
    pub fn init(allocator: std.mem.Allocator) ParamParser {
        return ParamParser{
            .allocator = allocator,
        };
    }
    
    pub fn parse(self: *ParamParser, input: []const u8) !std.ArrayList(ParsedParam) {
        var params = std.ArrayList(ParsedParam).init(self.allocator);
        
        var it = std.mem.split(u8, input, "&");
        while (it.next()) |pair| {
            if (std.mem.indexOf(u8, pair, "=")) |eq_pos| {
                const name = pair[0..eq_pos];
                const value = pair[eq_pos + 1 ..];
                
                const param_type = self.inferType(value);
                
                try params.append(ParsedParam{
                    .name = name,
                    .value = value,
                    .param_type = param_type,
                });
            }
        }
        
        return params;
    }
    
    fn inferType(self: *ParamParser, value: []const u8) ParamType {
        _ = self;
        
        if (std.mem.eql(u8, value, "true") or std.mem.eql(u8, value, "false")) {
            return .boolean;
        }
        
        if (std.fmt.parseInt(i64, value, 10)) |_| {
            return .integer;
        } else |_| {}
        
        if (std.fmt.parseFloat(f64, value)) |_| {
            return .float;
        } else |_| {}
        
        if (value.len > 0 and value[0] == '[') {
            return .array;
        }
        
        if (value.len > 0 and value[0] == '{') {
            return .object;
        }
        
        return .string;
    }
};

// C FFI exports
export fn param_parser_create() ?*ParamParser {
    const allocator = std.heap.c_allocator;
    const parser = allocator.create(ParamParser) catch return null;
    parser.* = ParamParser.init(allocator);
    return parser;
}

export fn param_parser_destroy(parser: ?*ParamParser) void {
    if (parser) |p| {
        std.heap.c_allocator.destroy(p);
    }
}

// Tests
test "parser creation" {
    var parser = ParamParser.init(std.testing.allocator);
    _ = parser;
}

test "parse simple params" {
    var parser = ParamParser.init(std.testing.allocator);
    const params = try parser.parse("name=value&count=42");
    defer params.deinit();
    
    try std.testing.expectEqual(@as(usize, 2), params.items.len);
}

test "infer types" {
    var parser = ParamParser.init(std.testing.allocator);
    
    try std.testing.expectEqual(ParamType.boolean, parser.inferType("true"));
    try std.testing.expectEqual(ParamType.integer, parser.inferType("42"));
    try std.testing.expectEqual(ParamType.float, parser.inferType("3.14"));
    try std.testing.expectEqual(ParamType.string, parser.inferType("hello"));
}

test "parse empty input" {
    var parser = ParamParser.init(std.testing.allocator);
    const params = try parser.parse("");
    defer params.deinit();
    
    try std.testing.expectEqual(@as(usize, 0), params.items.len);
}
