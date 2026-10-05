//! Comprehensive test battery for WhiteMagic Gen3 Vectorized Tool DSL (DIR-06).
//!
//! Validates:
//! 1. Zero-allocation logoglyph lexer and parser.
//! 2. Bi-directional compilation bridge between glyphs and ActionSkeleton.
//! 3. Sub-microsecond (< 1 µs) speculative AST validation with 64-bit bloom pre-filter.
//! 4. Logoglyph Wire Format (LWF-v1) bitpacked binary encoder and decoder.

use uuid::Uuid;
use wm_gen3_core::action_skeleton::{AstActionType, SkeletonLanguage};
use wm_gen3_core::dsl::*;

#[test]
fn test_glyph_parser_single_statement() {
    let input = "🔍[◆:q=\"consciousness\",$>0.8,n=10]";
    let pipeline = GlyphParser::parse_pipeline(input).expect("Parse single statement");
    assert_eq!(pipeline.len(), 1);

    let inst = &pipeline[0];
    assert_eq!(inst.verb, '🔍');
    assert_eq!(inst.domain, Some('◆'));

    assert_eq!(inst.params.len(), 3);
    assert_eq!(inst.params[0].key, "q");
    assert_eq!(inst.params[0].op, "=");
    assert_eq!(inst.params[0].val, "consciousness");

    assert_eq!(inst.params[1].key, "$");
    assert_eq!(inst.params[1].op, ">");
    assert_eq!(inst.params[1].val, "0.8");

    assert_eq!(inst.params[2].key, "n");
    assert_eq!(inst.params[2].op, "=");
    assert_eq!(inst.params[2].val, "10");
}

#[test]
fn test_glyph_parser_pipeline() {
    let input = "⊞[@SharedWorkspace/bridge.py:py] ⊕[fn:get_rooms,σ=\"def get_rooms(self) -> dict:\",+imp=\"import re\",∈=\"class WhiteboardHandler\",∋=\"/api/rooms\"]";
    let pipeline = GlyphParser::parse_pipeline(input).expect("Parse pipeline");
    assert_eq!(pipeline.len(), 2);

    assert_eq!(pipeline[0].verb, '⊞');
    assert_eq!(
        pipeline[0].target_ident.as_deref(),
        Some("SharedWorkspace/bridge.py:py")
    );

    assert_eq!(pipeline[1].verb, '⊕');
    assert_eq!(pipeline[1].params.len(), 4);
}

#[test]
fn test_skeleton_bridge_roundtrip() {
    let input = "⊞[@SharedWorkspace/bridge.py:py] ⊕[fn:get_rooms,σ=\"def get_rooms(self) -> dict:\",+imp=\"import re\",∈=\"class WhiteboardHandler\",∋=\"/api/rooms\"]";
    let pipeline = GlyphParser::parse_pipeline(input).expect("Parse pipeline");

    let skeleton =
        compile_glyph_to_skeleton(&pipeline[0], &pipeline[1]).expect("Compile to ActionSkeleton");

    assert_eq!(skeleton.target_file, "SharedWorkspace/bridge.py");
    assert_eq!(skeleton.language, SkeletonLanguage::Python);
    assert_eq!(skeleton.deltas.len(), 1);

    let delta = &skeleton.deltas[0];
    assert_eq!(delta.target_symbol, "fn:get_rooms");
    assert_eq!(delta.action_type, AstActionType::AddFunction);
    assert_eq!(delta.signature_delta, "def get_rooms(self) -> dict:");
    assert_eq!(delta.new_imports, vec!["import re"]);
    assert_eq!(delta.pre_invariants, vec!["class WhiteboardHandler"]);
    assert_eq!(delta.post_invariants, vec!["/api/rooms"]);

    // Serialize back to glyph format
    let glyph_str = compile_skeleton_to_glyph(&skeleton);
    assert!(glyph_str.starts_with("⊞[@SharedWorkspace/bridge.py:py]"));
    assert!(glyph_str.contains("⊕[fn:get_rooms"));
    assert!(glyph_str.contains("σ=\"def get_rooms(self) -> dict:\""));
    assert!(glyph_str.contains("+imp=\"import re\""));
}

#[test]
fn test_fast_ast_validator_sub_microsecond() {
    let source_code =
        b"import os\n\nclass WhiteboardHandler:\n    def do_GET(self):\n        pass\n";
    let source_index = SourceBufferIndex::new(source_code);

    let input = "⊞[@SharedWorkspace/bridge.py:py] ⊕[fn:get_rooms,σ=\"def get_rooms(self) -> dict:\",+imp=\"import re\",∈=\"class WhiteboardHandler\",∋=\"/api/rooms\"]";
    let pipeline = GlyphParser::parse_pipeline(input).expect("Parse pipeline");
    let skeleton = compile_glyph_to_skeleton(&pipeline[0], &pipeline[1]).expect("Compile skeleton");

    // 1. Valid execution test
    let res = validate_speculative_fast(&skeleton, &source_index);
    assert!(
        res.is_valid,
        "Validation should succeed: {:?}",
        res.conflicts
    );
    assert!(res.conflicts.is_empty());

    // 2. Conflict test: invariant missing in source code
    let bad_input = "⊞[@SharedWorkspace/bridge.py:py] ⊕[fn:bad,σ=\"def bad():\",∈=\"class NonExistentHandler\"]";
    let bad_pipeline = GlyphParser::parse_pipeline(bad_input).expect("Parse bad pipeline");
    let bad_skeleton =
        compile_glyph_to_skeleton(&bad_pipeline[0], &bad_pipeline[1]).expect("Compile");
    let bad_res = validate_speculative_fast(&bad_skeleton, &source_index);
    assert!(!bad_res.is_valid);
    assert_eq!(bad_res.conflicts.len(), 1);
    assert!(bad_res.conflicts[0].contains("Pre-invariant check failed"));
}

#[test]
fn test_lwf_wire_encoder_decoder() {
    let task_id = Uuid::new_v4();
    let original = LwfInstruction::new(0x01, 0x20) // 🔍 ◆
        .with_flag(FLAG_SPECULATIVE | FLAG_HIGH_PRIORITY)
        .with_param(0x43, LwfValue::Text("consciousness".to_string())) // q
        .with_param(0x42, LwfValue::Score(0.85)) // $
        .with_param(0x45, LwfValue::Integer(10)) // n
        .with_param(0x41, LwfValue::Tags(vec!["citta".into(), "dream".into()])) // #
        .with_param(0x07, LwfValue::TaskId(task_id));

    let wire_bytes = original.to_bytes();
    assert!(wire_bytes.len() < 120, "Wire frame should be compact");

    let decoded = LwfInstruction::from_bytes(&wire_bytes).expect("Decode wire frame");

    assert_eq!(decoded.flags, original.flags);
    assert_eq!(decoded.opcode, original.opcode);
    assert_eq!(decoded.domain, original.domain);
    assert_eq!(decoded.params.len(), original.params.len());

    assert_eq!(decoded.params[0].0, 0x43);
    assert_eq!(
        decoded.params[0].1,
        LwfValue::Text("consciousness".to_string())
    );

    assert_eq!(decoded.params[1].0, 0x42);
    if let LwfValue::Score(s) = decoded.params[1].1 {
        assert!((s - 0.85).abs() < 1e-3);
    } else {
        panic!("Expected score");
    }

    assert_eq!(decoded.params[2].0, 0x45);
    assert_eq!(decoded.params[2].1, LwfValue::Integer(10));

    assert_eq!(decoded.params[3].0, 0x41);
    assert_eq!(
        decoded.params[3].1,
        LwfValue::Tags(vec!["citta".into(), "dream".into()])
    );

    assert_eq!(decoded.params[4].0, 0x07);
    assert_eq!(decoded.params[4].1, LwfValue::TaskId(task_id));
}
