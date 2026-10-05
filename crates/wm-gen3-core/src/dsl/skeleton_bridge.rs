//! Bi-directional compilation bridge between Vectorized Tool DSL and ActionSkeleton.

use super::parser::GlyphInstruction;
use crate::action_skeleton::{ActionSkeleton, AstActionType, AstDelta, SkeletonLanguage};
use uuid::Uuid;

/// Compiles a target instruction (⊞) and delta instruction (⊕/⊗/⊖) into a typed ActionSkeleton.
pub fn compile_glyph_to_skeleton(
    target_spec: &GlyphInstruction,
    delta_spec: &GlyphInstruction,
) -> Result<ActionSkeleton, String> {
    // 1. Resolve Target File and Language from ⊞[@path:lang]
    let path_and_lang = target_spec
        .target_ident
        .as_ref()
        .ok_or("Missing target in ⊞")?;
    let (target_file, lang_str) = match path_and_lang.split_once(':') {
        Some((p, l)) => (p.trim_start_matches('@'), l),
        None => (path_and_lang.trim_start_matches('@'), "py"),
    };

    let language = match lang_str {
        "rs" | "rust" => SkeletonLanguage::Rust,
        "py" | "python" => SkeletonLanguage::Python,
        "ts" | "typescript" => SkeletonLanguage::TypeScript,
        "toml" => SkeletonLanguage::Toml,
        _ => SkeletonLanguage::Markdown,
    };

    // 2. Resolve AST Action Type from Verb
    let action_type = match delta_spec.verb {
        '⊕' => AstActionType::AddFunction,
        '⊗' => AstActionType::ModifySignature,
        '⊖' => AstActionType::ReplaceSymbol,
        _ => AstActionType::AddFunction,
    };

    let target_symbol = delta_spec
        .target_ident
        .as_deref()
        .unwrap_or("anonymous")
        .to_string();

    let mut signature_delta = String::new();
    let mut new_imports = Vec::new();
    let mut pre_invariants = Vec::new();
    let mut post_invariants = Vec::new();

    for p in &delta_spec.params {
        match p.key.as_ref() {
            "σ" | "sig" => signature_delta = p.val.to_string(),
            "+imp" | "imp" | "+" => new_imports.push(p.val.to_string()),
            "∈" | "pre" => pre_invariants.push(p.val.to_string()),
            "∋" | "post" => post_invariants.push(p.val.to_string()),
            _ => {}
        }
    }

    let delta = AstDelta {
        scope_path: format!("scope:{}", target_symbol),
        target_symbol,
        action_type,
        new_imports,
        signature_delta,
        pre_invariants,
        post_invariants,
    };

    Ok(ActionSkeleton::new(
        Uuid::new_v4(),
        target_file,
        language,
        vec![delta],
    ))
}

/// Serializes an ActionSkeleton into its dense Vectorized Tool DSL representation.
pub fn compile_skeleton_to_glyph(skeleton: &ActionSkeleton) -> String {
    let lang_str = match skeleton.language {
        SkeletonLanguage::Rust => "rs",
        SkeletonLanguage::Python => "py",
        SkeletonLanguage::TypeScript => "ts",
        SkeletonLanguage::Toml => "toml",
        SkeletonLanguage::Markdown => "md",
    };

    let mut out = format!("⊞[@{}:{}]", skeleton.target_file, lang_str);

    for delta in &skeleton.deltas {
        let verb = match delta.action_type {
            AstActionType::AddFunction | AstActionType::AddImport => '⊕',
            AstActionType::ModifySignature | AstActionType::WrapBlock => '⊗',
            AstActionType::ReplaceSymbol => '⊖',
        };

        let mut parts = Vec::new();
        parts.push(delta.target_symbol.clone());

        if !delta.signature_delta.is_empty() {
            parts.push(format!("σ=\"{}\"", delta.signature_delta));
        }
        for imp in &delta.new_imports {
            parts.push(format!("+imp=\"{}\"", imp));
        }
        for pre in &delta.pre_invariants {
            parts.push(format!("∈=\"{}\"", pre));
        }
        for post in &delta.post_invariants {
            parts.push(format!("∋=\"{}\"", post));
        }

        out.push_str(&format!(" {}[{}]", verb, parts.join(",")));
    }

    out
}
