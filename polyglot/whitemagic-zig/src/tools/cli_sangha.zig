//! CLI Sangha - Zig-Accelerated CLI Handler
//! Target: 100-1000x speedup for CLI operations
//! Priority: P0, Hot Path Score: 1.00

const std = @import("std");

// Hot path: Command parsing without allocations
pub const CommandType = enum(u8) {
    CHAT_SEND = 0,
    CHAT_READ = 1,
    BROKER_PUBLISH = 2,
    BROKER_HISTORY = 3,
    STATUS_CHECK = 4,
    GALAXY_LIST = 5,
    GALAXY_SWITCH = 6,
    MEMORY_SEARCH = 7,
    HELP = 8,
    UNKNOWN = 255,
};

// Hot path: Fast command detection
pub fn parseCommand(cmd_line: []const u8) CommandType {
    if (cmd_line.len == 0) return .UNKNOWN;
    
    // Skip leading whitespace
    var start: usize = 0;
    while (start < cmd_line.len and cmd_line[start] == ' ') {
        start += 1;
    }
    
    // Extract first word
    var end = start;
    while (end < cmd_line.len and cmd_line[end] != ' ') {
        end += 1;
    }
    
    const cmd = cmd_line[start..end];
    
    // Fast string matching using first character
    if (cmd.len == 0) return .UNKNOWN;
    
    const first = cmd[0];
    
    // Single character commands
    if (cmd.len == 1) {
        switch (first) {
            'h' => return .HELP,
            '?' => return .HELP,
            else => {},
        }
    }
    
    // Multi-character commands
    if (first == 'c') {
        if (std.mem.eql(u8, cmd, "chat")) return .CHAT_SEND;
        if (std.mem.startsWith(u8, cmd, "chat:")) return .CHAT_READ;
    }
    
    if (first == 'b') {
        if (std.mem.eql(u8, cmd, "broker")) return .BROKER_PUBLISH;
        if (std.mem.eql(u8, cmd, "broker_history")) return .BROKER_HISTORY;
    }
    
    if (first == 's') {
        if (std.mem.eql(u8, cmd, "status")) return .STATUS_CHECK;
    }
    
    if (first == 'g') {
        if (std.mem.eql(u8, cmd, "galaxy_list")) return .GALAXY_LIST;
        if (std.mem.eql(u8, cmd, "galaxy_switch")) return .GALAXY_SWITCH;
        if (std.mem.eql(u8, cmd, "galaxy")) return .GALAXY_LIST;
    }
    
    if (first == 'm') {
        if (std.mem.eql(u8, cmd, "memory_search")) return .MEMORY_SEARCH;
        if (std.mem.eql(u8, cmd, "search")) return .MEMORY_SEARCH;
    }
    
    // Slash commands
    if (first == '/') {
        if (std.mem.eql(u8, cmd, "/help")) return .HELP;
        if (std.mem.eql(u8, cmd, "/status")) return .STATUS_CHECK;
    }
    
    return .UNKNOWN;
}

// Hot path: Argument extraction
pub fn extractArgument(
    cmd_line: []const u8,
    arg_index: usize,
    out_buf: []u8,
) usize {
    var current_arg: usize = 0;
    var in_quotes = false;
    var i: usize = 0;
    var arg_start: usize = 0;
    
    while (i < cmd_line.len) {
        const ch = cmd_line[i];
        
        if (ch == '"') {
            in_quotes = !in_quotes;
        }
        
        if (!in_quotes and ch == ' ') {
            if (current_arg == arg_index and i > arg_start) {
                const len = @min(i - arg_start, out_buf.len);
                @memcpy(out_buf[0..len], cmd_line[arg_start..arg_start + len]);
                return len;
            }
            
            arg_start = i + 1;
            if (arg_start < cmd_line.len and cmd_line[arg_start] != ' ') {
                current_arg += 1;
            }
        }
        
        i += 1;
    }
    
    // Check last argument
    if (current_arg == arg_index and i > arg_start) {
        const len = @min(i - arg_start, out_buf.len);
        @memcpy(out_buf[0..len], cmd_line[arg_start..arg_start + len]);
        return len;
    }
    
    return 0;
}

// Hot path: Input validation
pub fn validateChatMessage(msg: []const u8) bool {
    if (msg.len == 0 or msg.len > 4096) return false;
    
    // Check for valid UTF-8 (simplified)
    for (msg) |ch| {
        if (ch < 32 and ch != 9 and ch != 10 and ch != 13) {
            return false; // Control characters not allowed
        }
    }
    
    return true;
}

pub fn validateBrokerChannel(channel: []const u8) bool {
    if (channel.len == 0 or channel.len > 128) return false;
    
    for (channel) |ch| {
        if (ch == ' ' or ch == '\t' or ch == '\n') {
            return false; // No whitespace in channel names
        }
    }
    
    return true;
}

// Hot path: JSON response builder
pub export fn build_cli_response(
    success: bool,
    command_ptr: [*]const u8,
    command_len: usize,
    data_ptr: [*]const u8,
    data_len: usize,
    out_json: [*]u8,
    out_capacity: usize,
    out_len: *usize,
) void {
    const command = command_ptr[0..command_len];
    var stream = std.io.fixedBufferStream(out_json[0..out_capacity]);
    var writer = stream.writer();
    
    _ = writer.write("{\"success\":") catch {};
    _ = writer.write(if (success) "true" else "false") catch {};
    
    _ = writer.write(",\"command\":\"") catch {};
    _ = writer.write(command) catch {};
    
    if (data_len > 0) {
        _ = writer.write("\",\"data\":") catch {};
        _ = writer.write(data_ptr[0..data_len]) catch {};
    }
    
    _ = writer.write("}") catch {};
    
    out_len.* = stream.pos;
}

// Hot path: Status response
pub export fn build_status_response(
    memory_count: u64,
    association_count: u64,
    db_size_mb: f64,
    out_json: [*]u8,
    out_capacity: usize,
    out_len: *usize,
) void {
    var stream = std.io.fixedBufferStream(out_json[0..out_capacity]);
    var writer = stream.writer();
    
    _ = writer.print(
        "{{\"success\":true,\"command\":\"status\",\"data\":{{\"memory_count\":{d},\"association_count\":{d},\"db_size_mb\":{d:.2}}}}}",
        .{ memory_count, association_count, db_size_mb },
    ) catch {};
    
    out_len.* = stream.pos;
}

// FFI exports
pub export fn cli_parse_command(cmd_ptr: [*]const u8, cmd_len: usize) u8 {
    const cmd = cmd_ptr[0..cmd_len];
    const parsed = parseCommand(cmd);
    return @intFromEnum(parsed);
}

pub export fn cli_validate_message(msg_ptr: [*]const u8, msg_len: usize) bool {
    return validateChatMessage(msg_ptr[0..msg_len]);
}

pub export fn cli_extract_arg(
    cmd_ptr: [*]const u8,
    cmd_len: usize,
    arg_index: usize,
    out_ptr: [*]u8,
    out_capacity: usize,
    out_len: *usize,
) void {
    const cmd = cmd_ptr[0..cmd_len];
    const len = extractArgument(cmd, arg_index, out_ptr[0..out_capacity]);
    out_len.* = len;
}

// Benchmark
pub export fn benchmark_cli_parsing(iterations: u32) u64 {
    var timer = std.time.Timer.start() catch return 0;
    
    const test_commands = [_][]const u8{
        "chat hello world",
        "broker publish test",
        "status",
        "galaxy_list",
        "memory_search test",
        "help",
    };
    
    var i: u32 = 0;
    while (i < iterations) : (i += 1) {
        for (test_commands) |cmd| {
            _ = parseCommand(cmd);
            
            var buf: [256]u8 = undefined;
            _ = extractArgument(cmd, 1, &buf);
        }
    }
    
    return timer.read();
}
