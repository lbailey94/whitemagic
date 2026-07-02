// trn_gate.zig — Zig thalamic reticular nucleus hard gate
//
// Sub-millisecond hard gate for galaxy access filtering.
// Three-level gating cascade: TRN → Cortex → PFC
//
// The TRN gate is a compile-time-generated lookup table that provides
// O(1) gate evaluation. It acts as a hard filter before the Python
// soft gating (galaxy_gating.py) — memories that fail the TRN gate
// are never even considered for spreading activation.
//
// Based on PLOS Comp Bio 2016: "The Emotional Gatekeeper: A Computational
// Model of Attentional Selection" — amygdala→TRN pathway.

const std = @import("std");

const Galaxy = enum {
    universal,
    codex,
    sessions,
    citta,
    dreams,
    research,
    aria,
    journals,
    substrate,
    tutorial,
};

const Context = enum {
    default,
    coding,
    research,
    introspection,
    creative,
    session,
};

// Hard gate thresholds: galaxies below threshold are blocked
// These are compile-time constants for sub-ms evaluation
const TRN_THRESHOLDS = [_]f64{ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
const CORTEX_THRESHOLDS = [_]f64{ 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1 };
const PFC_THRESHOLDS = [_]f64{ 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2 };

// Context-dependent hard gate masks (0=blocked, 1=allowed)
const CONTEXT_MASKS = [_][10]u8{
    [_]u8{ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 }, // default: all allowed
    [_]u8{ 1, 1, 1, 0, 0, 1, 0, 0, 1, 1 }, // coding: block citta, dreams, aria, journals
    [_]u8{ 1, 1, 0, 0, 0, 1, 1, 1, 1, 1 }, // research: block sessions, citta, dreams
    [_]u8{ 1, 0, 1, 1, 1, 0, 1, 1, 1, 1 }, // introspection: block codex, research
    [_]u8{ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 }, // creative: all allowed
    [_]u8{ 1, 1, 1, 0, 0, 0, 0, 0, 1, 1 }, // session: block citta, dreams, research, aria, journals
};

fn contextFromString(s: []const u8) Context {
    if (std.mem.eql(u8, s, "coding")) return .coding;
    if (std.mem.eql(u8, s, "research")) return .research;
    if (std.mem.eql(u8, s, "introspection")) return .introspection;
    if (std.mem.eql(u8, s, "creative")) return .creative;
    if (std.mem.eql(u8, s, "session")) return .session;
    return .default;
}

fn galaxyFromString(s: []const u8) ?Galaxy {
    if (std.mem.eql(u8, s, "universal")) return .universal;
    if (std.mem.eql(u8, s, "codex")) return .codex;
    if (std.mem.eql(u8, s, "sessions")) return .sessions;
    if (std.mem.eql(u8, s, "citta")) return .citta;
    if (std.mem.eql(u8, s, "dreams")) return .dreams;
    if (std.mem.eql(u8, s, "research")) return .research;
    if (std.mem.eql(u8, s, "aria")) return .aria;
    if (std.mem.eql(u8, s, "journals")) return .journals;
    if (std.mem.eql(u8, s, "substrate")) return .substrate;
    if (std.mem.eql(u8, s, "tutorial")) return .tutorial;
    return null;
}

fn galaxyIndex(g: Galaxy) usize {
    return @intFromEnum(g);
}

fn contextIndex(c: Context) usize {
    return @intFromEnum(c);
}

// Three-level gate check: TRN → Cortex → PFC
fn checkGate(galaxy: Galaxy, context: Context, activation: f64) bool {
    const gi = galaxyIndex(galaxy);
    const ci = contextIndex(context);

    // TRN: context mask (hard block)
    if (CONTEXT_MASKS[ci][gi] == 0) return false;

    // Cortex: minimum activation threshold
    if (activation < CORTEX_THRESHOLDS[gi]) return false;

    // PFC: higher threshold for executive control
    if (activation < PFC_THRESHOLDS[gi]) return false;

    return true;
}

pub fn main() !void {
    const stdin = std.io.getStdIn().reader();
    const stdout = std.io.getStdOut().writer();

    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    // Signal startup
    try stdout.printAll("{\"status\": \"started\", \"backend\": \"zig-trn-gate\"}\n");

    var line_buf: [4096]u8 = undefined;
    while (true) {
        const line = stdin.readUntilDelimiterOrEof(&line_buf, '\n') catch break;
        if (line == null) break;

        // Parse JSON manually (simple substring search for fields)
        const input = line.?;

        if (std.mem.indexOf(u8, input, "\"method\": \"ping\"") != null) {
            try stdout.printAll("{\"status\": \"ok\", \"backend\": \"zig-trn-gate\"}\n");
            continue;
        }

        if (std.mem.indexOf(u8, input, "\"method\": \"check\"") != null) {
            // Extract galaxy, context, activation from JSON
            var galaxy_name: []const u8 = "universal";
            var context_name: []const u8 = "default";
            var activation: f64 = 1.0;

            // Simple JSON field extraction
            if (std.mem.indexOf(u8, input, "\"galaxy\": \"")) |pos| {
                const start = pos + 11;
                if (std.mem.indexOfScalarPos(u8, input, start, '"')) |end| {
                    galaxy_name = input[start..end];
                }
            }
            if (std.mem.indexOf(u8, input, "\"context\": \"")) |pos| {
                const start = pos + 12;
                if (std.mem.indexOfScalarPos(u8, input, start, '"')) |end| {
                    context_name = input[start..end];
                }
            }
            if (std.mem.indexOf(u8, input, "\"activation\": ")) |pos| {
                const start = pos + 14;
                if (std.mem.indexOfAnyPos(u8, input, start, ",}")) |end| {
                    activation = std.fmt.parseFloat(f64, input[start..end]) catch 1.0;
                }
            }

            const galaxy = galaxyFromString(galaxy_name) orelse {
                try stdout.printAll("{\"status\": \"error\", \"error\": \"unknown galaxy\"}\n");
                continue;
            };
            const context = contextFromString(context_name);
            const allowed = checkGate(galaxy, context, activation);

            try stdout.print("{{\"status\": \"ok\", \"allowed\": {}, \"galaxy\": \"{s}\", \"context\": \"{s}\"}}\n", .{
                if (allowed) "true" else "false",
                galaxy_name,
                context_name,
            });
            continue;
        }

        if (std.mem.indexOf(u8, input, "\"method\": \"batch_check\"") != null) {
            // For batch check, just return all allowed (simplified)
            try stdout.printAll("{\"status\": \"ok\", \"results\": []}\n");
            continue;
        }

        try stdout.printAll("{\"status\": \"error\", \"error\": \"unknown method\"}\n");
    }
}
