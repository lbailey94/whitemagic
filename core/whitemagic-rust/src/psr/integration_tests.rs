#[cfg(test)]
mod integration_tests {
    use super::*;
    
    #[test]
    fn test_search_integration() {
        let search = Search::new("test.db".to_string(), Some(4));
        assert!(search.is_ok());
    }
    
    #[test]
    fn test_graph_walker_integration() {
        let mut walker = GraphWalker::new();
        walker.add_edge(
            "node1".to_string(),
            "node2".to_string(),
            0.8,
            "related".to_string()
        );
        
        let results = walker.walk("node1".to_string(), 3, 0.5);
        assert!(results.is_ok());
    }
    
    #[test]
    fn test_vector_search_integration() {
        let mut vs = VectorSearch::new();
        vs.add_vector("vec1".to_string(), vec![1.0, 2.0, 3.0]);
        
        let results = vs.search(vec![1.0, 2.0, 3.0], 5);
        assert!(results.is_ok());
    }
    
    #[test]
    fn test_reasoning_engine_integration() {
        let engine = ReasoningEngine::new(Some(0.7));
        
        let premises = vec!["A".to_string(), "B".to_string()];
        let rules = vec![
            (vec!["A".to_string(), "B".to_string()], "C".to_string(), 0.9)
        ];
        
        let results = engine.infer(premises, rules);
        assert!(results.is_ok());
    }
    
    #[test]
    fn test_memory_consolidation_integration() {
        let mut consolidation = MemoryConsolidation::new(Some(0.7));
        
        consolidation.add_candidate(
            "mem1".to_string(),
            0.8,
            5,
            24.0
        ).unwrap();
        
        let results = consolidation.consolidate();
        assert!(results.is_ok());
    }
    
    #[test]
    fn test_kaizen_integration() {
        let mut kaizen = Kaizen::new();
        
        let code = "fn test() { }".to_string();
        let suggestions = kaizen.analyze_code("test.rs".to_string(), code);
        
        assert!(suggestions.is_ok());
    }
    
    #[test]
    fn test_phylogenetics_integration() {
        let mut phylo = Phylogenetics::new();
        
        phylo.track_lineage(
            "code1".to_string(),
            None,
            0.8,
            vec!["mutation1".to_string()]
        ).unwrap();
        
        let best = phylo.get_best_lineage();
        assert!(best.is_ok());
    }
}
