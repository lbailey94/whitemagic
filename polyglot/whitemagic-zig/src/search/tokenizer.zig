// Tokenizer - Zero-copy Tokenization (PSR-002)
// Target: 100× speedup for text tokenization

const std = @import("std");

/// Token from tokenization
pub const Token = struct {
    text: []const u8,
    start: usize,
    end: usize,
};

/// Zero-copy tokenizer
pub const Tokenizer = struct {
    allocator: std.mem.Allocator,
    
    pub fn init(allocator: std.mem.Allocator) Tokenizer {
        return Tokenizer{ .allocator = allocator };
    }
    
    /// Tokenize text into words (whitespace-separated)
    pub fn tokenize(self: *Tokenizer, text: []const u8) ![]Token {
        var tokens: std.ArrayListUnmanaged(Token) = .{};
        
        var start: usize = 0;
        var in_token = false;
        
        for (text, 0..) |char, i| {
            const is_whitespace = char == ' ' or char == '\t' or char == '\n' or char == '\r';
            
            if (!is_whitespace and !in_token) {
                start = i;
                in_token = true;
            } else if (is_whitespace and in_token) {
                try tokens.append(self.allocator, Token{
                    .text = text[start..i],
                    .start = start,
                    .end = i,
                });
                in_token = false;
            }
        }
        
        // Handle last token
        if (in_token) {
            try tokens.append(self.allocator, Token{
                .text = text[start..],
                .start = start,
                .end = text.len,
            });
        }
        
        return tokens.toOwnedSlice(self.allocator);
    }
    
    /// Tokenize and lowercase
    pub fn tokenizeLower(self: *Tokenizer, text: []const u8) ![][]u8 {
        const tokens = try self.tokenize(text);
        defer self.allocator.free(tokens);
        
        var result: std.ArrayListUnmanaged([]u8) = .{};
        
        for (tokens) |token| {
            var lower = try self.allocator.alloc(u8, token.text.len);
            for (token.text, 0..) |char, i| {
                lower[i] = if (char >= 'A' and char <= 'Z') char + 32 else char;
            }
            try result.append(self.allocator, lower);
        }
        
        return result.toOwnedSlice(self.allocator);
    }
    
    /// Count tokens
    pub fn countTokens(self: *Tokenizer, text: []const u8) !usize {
        const tokens = try self.tokenize(text);
        defer self.allocator.free(tokens);
        return tokens.len;
    }
};

/// C FFI exports
export fn tokenizer_create() ?*Tokenizer {
    const allocator = std.heap.c_allocator;
    const tok = allocator.create(Tokenizer) catch return null;
    tok.* = Tokenizer.init(allocator);
    return tok;
}

export fn tokenizer_destroy(tok: ?*Tokenizer) void {
    if (tok) |t| {
        std.heap.c_allocator.destroy(t);
    }
}

export fn tokenizer_count(tok: ?*Tokenizer, text: [*c]const u8, len: usize) usize {
    if (tok) |t| {
        const text_slice = text[0..len];
        return t.countTokens(text_slice) catch 0;
    }
    return 0;
}

// Tests
test "tokenize simple" {
    var tok = Tokenizer.init(std.testing.allocator);
    const text = "hello world test";
    
    const tokens = try tok.tokenize(text);
    defer std.testing.allocator.free(tokens);
    
    try std.testing.expectEqual(@as(usize, 3), tokens.len);
    try std.testing.expectEqualStrings("hello", tokens[0].text);
    try std.testing.expectEqualStrings("world", tokens[1].text);
    try std.testing.expectEqualStrings("test", tokens[2].text);
}

test "tokenize with multiple spaces" {
    var tok = Tokenizer.init(std.testing.allocator);
    const text = "hello    world";
    
    const tokens = try tok.tokenize(text);
    defer std.testing.allocator.free(tokens);
    
    try std.testing.expectEqual(@as(usize, 2), tokens.len);
}

test "tokenize empty" {
    var tok = Tokenizer.init(std.testing.allocator);
    const text = "";
    
    const tokens = try tok.tokenize(text);
    defer std.testing.allocator.free(tokens);
    
    try std.testing.expectEqual(@as(usize, 0), tokens.len);
}

test "count tokens" {
    var tok = Tokenizer.init(std.testing.allocator);
    const text = "one two three four";
    
    const count = try tok.countTokens(text);
    try std.testing.expectEqual(@as(usize, 4), count);
}
