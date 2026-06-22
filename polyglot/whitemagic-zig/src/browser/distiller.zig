//! DOM Distiller - Zig-Accelerated DOM Simplification
//! Target: 100-1000x speedup for DOM tree processing
//! Priority: P0, Hot Path Score: 1.00

const std = @import("std");

// Hot path: Element type classification (no allocations)
pub const ElementType = enum(u8) {
    INTERACTIVE = 0,  // Clickable, typeable
    TEXT = 1,         // Text content
    CONTAINER = 2,    // Structural (div, section)
    FORM = 3,         // Form elements
    NAVIGATION = 4,   // Nav, menu
    MEDIA = 5,        // Images, videos
    IGNORE = 6,       // CSS, SVG, scripts
};

// Hot path: Simplified element structure (stack-friendly)
pub const SimplifiedElement = extern struct {
    tag: [32]u8,
    tag_len: u8,
    element_type: ElementType,
    selector: [256]u8,
    selector_len: u16,
    text: [1024]u8,
    text_len: u16,
    // Attributes stored as key=value pairs, separated by null bytes
    attributes_buf: [2048]u8,
    attributes_len: u16,
    bounds_x: f32,
    bounds_y: f32,
    bounds_w: f32,
    bounds_h: f32,
    has_bounds: bool,
    // Child indices (indices into a flat array)
    child_start: u32,
    child_count: u16,
};

// Hot path: Fast tag classification without string compare
pub fn classifyElementType(tag: []const u8) ElementType {
    // Use first character for fast dispatch
    if (tag.len == 0) return .IGNORE;
    
    const first = tag[0];
    
    // Interactive elements
    if (first == 'a' or first == 'b') {
        if (std.mem.eql(u8, tag, "a")) return .INTERACTIVE;
        if (std.mem.eql(u8, tag, "button")) return .INTERACTIVE;
    }
    
    if (first == 'i') {
        if (std.mem.eql(u8, tag, "input")) return .FORM;
        if (std.mem.eql(u8, tag, "img")) return .MEDIA;
    }
    
    if (first == 's') {
        if (std.mem.eql(u8, tag, "select")) return .FORM;
        if (std.mem.eql(u8, tag, "script")) return .IGNORE;
        if (std.mem.eql(u8, tag, "style")) return .IGNORE;
        if (std.mem.eql(u8, tag, "svg")) return .IGNORE;
    }
    
    if (first == 't') {
        if (std.mem.eql(u8, tag, "textarea")) return .FORM;
        if (std.mem.eql(u8, tag, "text")) return .TEXT;
    }
    
    if (first == 'n') {
        if (std.mem.eql(u8, tag, "nav")) return .NAVIGATION;
    }
    
    // Container elements
    if (first == 'd' and tag.len >= 2 and tag[1] == 'i') {
        if (std.mem.eql(u8, tag, "div")) return .CONTAINER;
    }
    
    if (first == 's' and tag.len >= 2 and tag[1] == 'e') {
        if (std.mem.eql(u8, tag, "section")) return .CONTAINER;
    }
    
    // Video elements
    if (first == 'v') {
        if (std.mem.eql(u8, tag, "video")) return .MEDIA;
    }
    
    return .TEXT; // Default to text
}

// Hot path: Fast selector generation
pub fn generateSelector(
    tag: []const u8,
    id: ?[]const u8,
    class: ?[]const u8,
    out_buf: []u8,
) !usize {
    var stream = std.io.fixedBufferStream(out_buf);
    var writer = stream.writer();
    
    // Tag
    try writer.writeAll(tag);
    
    // ID
    if (id) |id_val| {
        try writer.writeByte('#');
        try writer.writeAll(id_val);
    }
    
    // Class
    if (class) |class_val| {
        try writer.writeByte('.');
        // Replace spaces with dots for multiple classes
        for (class_val) |ch| {
            if (ch == ' ') {
                try writer.writeByte('.');
            } else {
                try writer.writeByte(ch);
            }
        }
    }
    
    return stream.pos;
}

// Hot path: Text truncation without allocation
pub fn truncateText(text: []const u8, max_len: usize, out_buf: []u8) usize {
    const len = @min(text.len, max_len);
    @memcpy(out_buf[0..len], text[0..len]);
    
    if (text.len > max_len and max_len > 3) {
        // Add ellipsis
        @memcpy(out_buf[max_len - 3 .. max_len], "...");
        return max_len;
    }
    
    return len;
}

// Hot path: Batch element processing
pub export fn distill_elements_batch(
    raw_elements_ptr: [*]const u8,
    raw_elements_len: usize,
    element_count: usize,
    out_elements: [*]SimplifiedElement,
    out_count: *usize,
) void {
    var count: usize = 0;
    var offset: usize = 0;
    
    var i: usize = 0;
    while (i < element_count and offset < raw_elements_len) : (i += 1) {
        // Parse raw element (simplified: tag\0id\0class\0text\0)
        // This is a fast path - assumes well-formed input
        
        var elem: SimplifiedElement = std.mem.zeroes(SimplifiedElement);
        
        // Extract tag (null-terminated)
        var tag_len: usize = 0;
        while (offset + tag_len < raw_elements_len and raw_elements_ptr[offset + tag_len] != 0) {
            tag_len += 1;
        }
        
        if (tag_len > 0 and tag_len <= 32) {
            @memcpy(&elem.tag, raw_elements_ptr[offset..offset + tag_len], tag_len);
            elem.tag_len = @intCast(tag_len);
            elem.element_type = classifyElementType(elem.tag[0..tag_len]);
        }
        
        offset += tag_len + 1; // Skip null terminator
        
        // Skip remaining fields for this hot path (would parse id, class, text)
        // For now, just count elements
        count += 1;
        
        if (count >= 1000) break; // Max 1000 elements per batch
    }
    
    out_count.* = count;
}

// Hot path: Filter elements by type
pub export fn filter_elements_by_type(
    elements_ptr: [*]const SimplifiedElement,
    element_count: usize,
    filter_type: ElementType,
    out_indices: [*]u32,
    out_count: *usize,
) void {
    var count: usize = 0;
    
    var i: usize = 0;
    while (i < element_count) : (i += 1) {
        if (elements_ptr[i].element_type == filter_type) {
            out_indices[count] = @intCast(i);
            count += 1;
            
            if (count >= 1000) break; // Max 1000 matches
        }
    }
    
    out_count.* = count;
}

// Hot path: Find interactive elements (buttons, links, inputs)
pub export fn find_interactive_elements(
    elements_ptr: [*]const SimplifiedElement,
    element_count: usize,
    out_indices: [*]u32,
    out_count: *usize,
) void {
    var count: usize = 0;
    
    var i: usize = 0;
    while (i < element_count) : (i += 1) {
        const elem_type = elements_ptr[i].element_type;
        if (elem_type == .INTERACTIVE or elem_type == .FORM) {
            out_indices[count] = @intCast(i);
            count += 1;
            
            if (count >= 1000) break;
        }
    }
    
    out_count.* = count;
}

// Hot path: Serialize to JSON (minimal allocation)
pub export fn serialize_element_json(
    elem_ptr: *const SimplifiedElement,
    out_json: [*]u8,
    out_capacity: usize,
    out_len: *usize,
) void {
    var stream = std.io.fixedBufferStream(out_json[0..out_capacity]);
    var writer = stream.writer();
    
    _ = writer.write("{\"tag\":\"") catch {};
    _ = writer.write(elem_ptr.tag[0..elem_ptr.tag_len]) catch {};
    _ = writer.write("\",\"type\":\"") catch {};
    
    // Type name
    const type_name = switch (elem_ptr.element_type) {
        .INTERACTIVE => "INTERACTIVE",
        .TEXT => "TEXT",
        .CONTAINER => "CONTAINER",
        .FORM => "FORM",
        .NAVIGATION => "NAVIGATION",
        .MEDIA => "MEDIA",
        .IGNORE => "IGNORE",
    };
    _ = writer.write(type_name) catch {};
    
    _ = writer.write("\",\"selector\":\"") catch {};
    _ = writer.write(elem_ptr.selector[0..elem_ptr.selector_len]) catch {};
    
    _ = writer.write("\",\"text\":\"") catch {};
    _ = writer.write(elem_ptr.text[0..elem_ptr.text_len]) catch {};
    
    if (elem_ptr.has_bounds) {
        _ = writer.print("\",\"bounds\":{{\"x\":{d:.2},\"y\":{d:.2},\"w\":{d:.2},\"h\":{d:.2}}}}", .{
            elem_ptr.bounds_x,
            elem_ptr.bounds_y,
            elem_ptr.bounds_w,
            elem_ptr.bounds_h,
        }) catch {};
    }
    
    _ = writer.write("}") catch {};
    
    out_len.* = stream.pos;
}

// Benchmark entry point
pub export fn benchmark_dom_distill(iterations: u32) u64 {
    var timer = std.time.Timer.start() catch return 0;
    
    var i: u32 = 0;
    while (i < iterations) : (i += 1) {
        // Simulate classifying 100 elements
        var j: u32 = 0;
        while (j < 100) : (j += 1) {
            _ = classifyElementType("div");
            _ = classifyElementType("button");
            _ = classifyElementType("a");
        }
    }
    
    return timer.read();
}
