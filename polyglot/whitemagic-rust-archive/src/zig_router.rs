//! Zig Query Router FFI Bindings
//! 
//! Provides Rust interface to Zig's <10μs query router

use std::ffi::CString;

#[repr(C)]
pub struct CQueryPlan {
    pub strategy: i32,
    pub lexical_weight: f32,
    pub semantic_weight: f32,
    pub use_constellation: bool,
    pub estimated_cost: u64,
}

#[link(name = "whitemagic-zig", kind = "static")]
extern "C" {
    fn zig_route_query(
        query_ptr: *const u8,
        query_len: usize,
        plan_out: *mut CQueryPlan,
    );
    
    fn zig_get_strategy_weights(
        strategy: i32,
        lexical_out: *mut f32,
        semantic_out: *mut f32,
    );
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ZigSearchStrategy {
    LexicalOnly = 0,
    SemanticOnly = 1,
    HybridBalanced = 2,
    HybridLexicalHeavy = 3,
    HybridSemanticHeavy = 4,
}

impl From<i32> for ZigSearchStrategy {
    fn from(value: i32) -> Self {
        match value {
            0 => ZigSearchStrategy::LexicalOnly,
            1 => ZigSearchStrategy::SemanticOnly,
            2 => ZigSearchStrategy::HybridBalanced,
            3 => ZigSearchStrategy::HybridLexicalHeavy,
            4 => ZigSearchStrategy::HybridSemanticHeavy,
            _ => ZigSearchStrategy::HybridBalanced,
        }
    }
}

#[derive(Debug, Clone)]
pub struct QueryPlan {
    pub strategy: ZigSearchStrategy,
    pub lexical_weight: f32,
    pub semantic_weight: f32,
    pub use_constellation: bool,
    pub estimated_cost: u64,
}

/// Route a query using Zig's <10μs router
pub fn route_query(query: &str) -> QueryPlan {
    let mut c_plan = CQueryPlan {
        strategy: 2, // Default to balanced
        lexical_weight: 0.5,
        semantic_weight: 0.5,
        use_constellation: false,
        estimated_cost: 0,
    };
    
    unsafe {
        zig_route_query(
            query.as_ptr(),
            query.len(),
            &mut c_plan,
        );
    }
    
    QueryPlan {
        strategy: ZigSearchStrategy::from(c_plan.strategy),
        lexical_weight: c_plan.lexical_weight,
        semantic_weight: c_plan.semantic_weight,
        use_constellation: c_plan.use_constellation,
        estimated_cost: c_plan.estimated_cost,
    }
}

/// Get weights for a specific strategy
pub fn get_strategy_weights(strategy: ZigSearchStrategy) -> (f32, f32) {
    let mut lexical = 0.0;
    let mut semantic = 0.0;
    
    unsafe {
        zig_get_strategy_weights(
            strategy as i32,
            &mut lexical,
            &mut semantic,
        );
    }
    
    (lexical, semantic)
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_route_query() {
        let plan = route_query("test query");
        assert!(plan.lexical_weight >= 0.0 && plan.lexical_weight <= 1.0);
        assert!(plan.semantic_weight >= 0.0 && plan.semantic_weight <= 1.0);
    }
    
    #[test]
    fn test_strategy_weights() {
        let (lex, sem) = get_strategy_weights(ZigSearchStrategy::HybridBalanced);
        assert_eq!(lex, 0.5);
        assert_eq!(sem, 0.5);
    }
    
    #[test]
    fn test_quoted_query() {
        let plan = route_query("\"exact phrase\"");
        // Should route to lexical only
        assert_eq!(plan.strategy, ZigSearchStrategy::LexicalOnly);
    }
    
    #[test]
    fn test_code_query() {
        let plan = route_query("fn myFunction() { return true; }");
        // Should route to lexical heavy
        assert_eq!(plan.strategy, ZigSearchStrategy::HybridLexicalHeavy);
    }
}
