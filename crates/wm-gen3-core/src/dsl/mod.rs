//! Vectorized Tool DSL — Layer 2 & 3 Symbolic and Binary Tool Compression.
//!
//! Sub-microsecond logoglyph parsing, wire encoding (LWF-v1), and speculative AST validation.

pub mod fast_ast_validator;
pub mod parser;
pub mod skeleton_bridge;
pub mod wire;

pub use fast_ast_validator::{validate_speculative_fast, SourceBufferIndex};
pub use parser::{
    is_chain_op, is_domain_glyph, is_special_key, is_verb_glyph, GlyphInstruction, GlyphParam,
    GlyphParser,
};
pub use skeleton_bridge::{compile_glyph_to_skeleton, compile_skeleton_to_glyph};
pub use wire::{
    LwfInstruction, LwfValue, FLAG_DRY_RUN, FLAG_HIGH_PRIORITY, FLAG_PIPELINED,
    FLAG_SPECULATIVE, LWF_MAGIC, LWF_VERSION,
};
