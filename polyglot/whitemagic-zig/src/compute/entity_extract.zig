const std = @import("std");

/// SIMD-accelerated entity extraction for fast disambiguation.
/// Identifies candidate entities from query text using heuristic patterns.

/// Common stopwords to filter out
const STOPWORDS = [_][]const u8{
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall",
    "can", "need", "dare", "ought", "used", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into",
    "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "and", "but", "if",
    "or", "because", "until", "while", "what", "which", "who",
    "whom", "this", "that", "these", "those", "am", "it",
};

/// Check if word is a stopword
fn isStopword(word: []const u8) bool {
    const lower = std.ascii.lowerString(&[_]u8{0} ** 64, word);
    for (STOPWORDS) |stop| {
        if (std.mem.eql(u8, lower[0..word.len], stop)) return true;
    }
    return false;
}

/// Extract capitalized phrases as entity candidates
export fn wm_extract_entities_capitalized(
    text_ptr: [*]const u8,
    text_len: usize,
    entities_out: [*][*]u8,
    entity_lens_out: [*]usize,
    max_entities: usize,
) usize {
    if (text_len == 0) return 0;
    
    var count: usize = 0;
    var i: usize = 0;
    
    while (i < text_len and count < max_entities) {
        // Skip non-uppercase
        while (i < text_len and !std.ascii.isUpper(text_ptr[i])) {
            i += 1;
        }
        
        if (i >= text_len) break;
        
        // Found start of potential entity
        const start = i;
        
        // Consume entity: Capitalized word(s)
        while (i < text_len) {
            if (text_ptr[i] == ' ' or text_ptr[i] == '-') {
                // Check if next word is also capitalized
                if (i + 1 < text_len and std.ascii.isUpper(text_ptr[i + 1])) {
                    i += 1; // Include space and continue
                } else {
                    break;
                }
            } else if (std.ascii.isAlphanumeric(text_ptr[i]) or text_ptr[i] == '_') {
                i += 1;
            } else {
                break;
            }
        }
        
        const entity_len = i - start;
        if (entity_len > 2) { // Filter short tokens
            entities_out[count] = @constCast(text_ptr + start);
            entity_lens_out[count] = entity_len;
            count += 1;
        }
        
        // Skip to next word
        while (i < text_len and !std.ascii.isAlphanumeric(text_ptr[i])) {
            i += 1;
        }
    }
    
    return count;
}

/// Extract quoted phrases as entity candidates
export fn wm_extract_entities_quoted(
    text_ptr: [*]const u8,
    text_len: usize,
    entities_out: [*][*]u8,
    entity_lens_out: [*]usize,
    max_entities: usize,
) usize {
    if (text_len == 0) return 0;
    
    var count: usize = 0;
    var i: usize = 0;
    
    while (i < text_len and count < max_entities) {
        // Find opening quote
        while (i < text_len and text_ptr[i] != '"' and text_ptr[i] != '\'' and text_ptr[i] != '`') {
            i += 1;
        }
        
        if (i >= text_len) break;
        
        const quote_char = text_ptr[i];
        i += 1; // Skip opening quote
        const start = i;
        
        // Find closing quote
        while (i < text_len and text_ptr[i] != quote_char) {
            i += 1;
        }
        
        const entity_len = i - start;
        if (entity_len > 2) {
            entities_out[count] = @constCast(text_ptr + start);
            entity_lens_out[count] = entity_len;
            count += 1;
        }
        
        if (i < text_len) i += 1; // Skip closing quote
    }
    
    return count;
}

/// Compute entity-text match score using token overlap
export fn wm_entity_match_score(
    entity_ptr: [*]const u8,
    entity_len: usize,
    text_ptr: [*]const u8,
    text_len: usize,
) f32 {
    if (entity_len == 0 or text_len == 0) return 0.0;
    
    // Simple substring search
    var matches: usize = 0;
    var i: usize = 0;
    
    while (i <= text_len - entity_len) : (i += 1) {
        var match = true;
        for (0..entity_len) |j| {
            if (std.ascii.toLower(text_ptr[i + j]) != std.ascii.toLower(entity_ptr[j])) {
                match = false;
                break;
            }
        }
        if (match) {
            matches += 1;
            i += entity_len; // Skip past this match
        }
    }
    
    // Score based on match frequency and entity length
    const base_score = @as(f32, @floatFromInt(matches)) * @as(f32, @floatFromInt(entity_len));
    return @min(base_score / 100.0, 1.0);
}

/// Batch score multiple memories against extracted entities
export fn wm_batch_entity_score(
    entity_ptrs: [*][*]const u8,
    entity_lens: [*]const usize,
    num_entities: usize,
    memory_text_ptr: [*]const u8,
    memory_text_len: usize,
    scores_out: [*]f32,
) void {
    for (0..num_entities) |i| {
        scores_out[i] = wm_entity_match_score(
            entity_ptrs[i],
            entity_lens[i],
            memory_text_ptr,
            memory_text_len,
        );
    }
}
