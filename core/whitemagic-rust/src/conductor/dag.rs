//! Dependency graph (DAG) execution

use std::collections::{HashMap, HashSet, VecDeque};

/// DAG node
#[derive(Debug, Clone)]
pub struct DagNode {
    pub id: u32,
    pub dependencies: HashSet<u32>,
    pub dependents: HashSet<u32>,
}

impl DagNode {
    /// Create new node
    pub fn new(id: u32) -> Self {
        Self {
            id,
            dependencies: HashSet::new(),
            dependents: HashSet::new(),
        }
    }
}

/// Dependency graph for orchestration
#[derive(Debug, Default)]
pub struct DependencyGraph {
    nodes: HashMap<u32, DagNode>,
}

impl DependencyGraph {
    /// Create new graph
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
        }
    }

    /// Add node
    pub fn add_node(&mut self, id: u32) {
        self.nodes.entry(id).or_insert_with(|| DagNode::new(id));
    }

    /// Remove node
    pub fn remove_node(&mut self, id: u32) -> bool {
        if let Some(node) = self.nodes.remove(&id) {
            // Remove from dependents' dependencies
            for &dependent in &node.dependents {
                if let Some(dep) = self.nodes.get_mut(&dependent) {
                    dep.dependencies.remove(&id);
                }
            }
            // Remove from dependencies' dependents
            for &dependency in &node.dependencies {
                if let Some(dep) = self.nodes.get_mut(&dependency) {
                    dep.dependents.remove(&id);
                }
            }
            true
        } else {
            false
        }
    }

    /// Add edge (dependency relationship)
    pub fn add_edge(&mut self, from: u32, to: u32) -> Result<(), DagError> {
        // from depends on to

        // Check for cycles
        if self.would_create_cycle(from, to) {
            return Err(DagError::WouldCreateCycle(from, to));
        }

        // Ensure nodes exist
        self.add_node(from);
        self.add_node(to);

        // Add dependency
        if let Some(node) = self.nodes.get_mut(&from) {
            node.dependencies.insert(to);
        }

        // Add dependent
        if let Some(node) = self.nodes.get_mut(&to) {
            node.dependents.insert(from);
        }

        Ok(())
    }

    /// Check if adding edge would create cycle
    fn would_create_cycle(&self, from: u32, to: u32) -> bool {
        // If 'to' can reach 'from', adding edge from->to creates cycle
        self.can_reach(to, from, &mut HashSet::new())
    }

    /// Check if start can reach target
    fn can_reach(&self, start: u32, target: u32, visited: &mut HashSet<u32>) -> bool {
        if start == target {
            return true;
        }

        if !visited.insert(start) {
            return false;
        }

        if let Some(node) = self.nodes.get(&start) {
            // Traverse through dependencies (forward chain) to detect cycles
            for &dependency in &node.dependencies {
                if self.can_reach(dependency, target, visited) {
                    return true;
                }
            }
        }

        false
    }

    /// Get node
    pub fn get_node(&self, id: u32) -> Option<&DagNode> {
        self.nodes.get(&id)
    }

    /// Get all nodes
    pub fn get_nodes(&self) -> Vec<u32> {
        self.nodes.keys().cloned().collect()
    }

    /// Topological sort (Kahn's algorithm)
    pub fn topological_sort(&self) -> Result<Vec<u32>, DagError> {
        let mut in_degree: HashMap<u32, usize> = HashMap::new();
        let mut result = Vec::new();
        let mut queue = VecDeque::new();

        // Calculate in-degrees
        for (&id, node) in &self.nodes {
            let degree = node.dependencies.len();
            in_degree.insert(id, degree);

            if degree == 0 {
                queue.push_back(id);
            }
        }

        while let Some(id) = queue.pop_front() {
            result.push(id);

            if let Some(node) = self.nodes.get(&id) {
                for &dependent in &node.dependents {
                    if let Some(degree) = in_degree.get_mut(&dependent) {
                        *degree -= 1;
                        if *degree == 0 {
                            queue.push_back(dependent);
                        }
                    }
                }
            }
        }

        // Check for cycles
        if result.len() != self.nodes.len() {
            return Err(DagError::CycleDetected);
        }

        Ok(result)
    }

    /// Get execution batches (parallelizable groups)
    pub fn get_execution_batches(&self) -> Vec<Vec<u32>> {
        let mut in_degree: HashMap<u32, usize> = HashMap::new();
        let mut batches = Vec::new();

        // Calculate in-degrees
        for (&id, node) in &self.nodes {
            in_degree.insert(id, node.dependencies.len());
        }

        let mut remaining: HashSet<u32> = self.nodes.keys().cloned().collect();

        while !remaining.is_empty() {
            // Find all nodes with in-degree 0
            let batch: Vec<u32> = remaining
                .iter()
                .filter(|&&id| in_degree.get(&id).copied().unwrap_or(0) == 0)
                .cloned()
                .collect();

            if batch.is_empty() {
                // Cycle detected, break
                break;
            }

            // Remove batch from remaining
            for &id in &batch {
                remaining.remove(&id);
            }

            // Update in-degrees
            for &id in &batch {
                if let Some(node) = self.nodes.get(&id) {
                    for &dependent in &node.dependents {
                        if let Some(degree) = in_degree.get_mut(&dependent) {
                            *degree -= 1;
                        }
                    }
                }
            }

            batches.push(batch);
        }

        batches
    }

    /// Check if graph is valid DAG
    pub fn is_valid(&self) -> bool {
        self.topological_sort().is_ok()
    }

    /// Count nodes
    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }
}

/// DAG errors
#[derive(Debug, Clone, PartialEq)]
pub enum DagError {
    WouldCreateCycle(u32, u32),
    CycleDetected,
    NodeNotFound(u32),
}

impl std::fmt::Display for DagError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::WouldCreateCycle(from, to) => {
                write!(f, "Adding edge {} -> {} would create cycle", from, to)
            }
            Self::CycleDetected => write!(f, "Cycle detected in graph"),
            Self::NodeNotFound(id) => write!(f, "Node {} not found", id),
        }
    }
}

impl std::error::Error for DagError {}

/// DAG executor
pub struct DagExecutor<'a> {
    graph: &'a DependencyGraph,
}

impl<'a> DagExecutor<'a> {
    /// Create new executor
    pub fn new(graph: &'a DependencyGraph) -> Self {
        Self { graph }
    }

    /// Get topological sort
    pub fn topological_sort(&self) -> Result<Vec<u32>, DagError> {
        self.graph.topological_sort()
    }

    /// Get execution batches for parallel execution
    pub fn get_execution_batches(&self) -> Vec<Vec<u32>> {
        self.graph.get_execution_batches()
    }

    /// Execute with dependency resolution
    pub fn execute<F>(&self, mut executor: F) -> Result<(), DagError>
    where
        F: FnMut(u32) -> Result<(), String>,
    {
        let sequence = self.topological_sort()?;

        for id in sequence {
            executor(id).map_err(|_| DagError::NodeNotFound(id))?;
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_graph_creation() {
        let graph = DependencyGraph::new();
        assert!(graph.is_empty());
        assert!(graph.is_valid());
    }

    #[test]
    fn test_add_nodes() {
        let mut graph = DependencyGraph::new();
        graph.add_node(1);
        graph.add_node(2);

        assert_eq!(graph.len(), 2);
        assert!(graph.get_node(1).is_some());
        assert!(graph.get_node(2).is_some());
    }

    #[test]
    fn test_add_edge() {
        let mut graph = DependencyGraph::new();
        graph.add_node(1);
        graph.add_node(2);

        assert!(graph.add_edge(1, 2).is_ok());

        let node1 = graph.get_node(1).unwrap();
        assert!(node1.dependencies.contains(&2));

        let node2 = graph.get_node(2).unwrap();
        assert!(node2.dependents.contains(&1));
    }

    #[test]
    fn test_cycle_detection() {
        let mut graph = DependencyGraph::new();
        graph.add_node(1);
        graph.add_node(2);
        graph.add_node(3);

        // 1 -> 2 -> 3
        graph.add_edge(1, 2).unwrap();
        graph.add_edge(2, 3).unwrap();

        // Adding 3 -> 1 would create cycle
        assert_eq!(graph.add_edge(3, 1), Err(DagError::WouldCreateCycle(3, 1)));
    }

    #[test]
    fn test_topological_sort() {
        let mut graph = DependencyGraph::new();
        graph.add_node(1);
        graph.add_node(2);
        graph.add_node(3);

        // 1 depends on 2, 2 depends on 3
        graph.add_edge(1, 2).unwrap();
        graph.add_edge(2, 3).unwrap();

        let sorted = graph.topological_sort().unwrap();
        assert_eq!(sorted, vec![3, 2, 1]);
    }

    #[test]
    fn test_execution_batches() {
        let mut graph = DependencyGraph::new();

        // A -> B -> D
        // A -> C -> D
        graph.add_edge(2, 1).unwrap(); // B depends on A
        graph.add_edge(3, 1).unwrap(); // C depends on A
        graph.add_edge(4, 2).unwrap(); // D depends on B
        graph.add_edge(4, 3).unwrap(); // D depends on C

        let batches = graph.get_execution_batches();

        // Batch 1: A
        // Batch 2: B, C
        // Batch 3: D
        assert_eq!(batches.len(), 3);
        assert_eq!(batches[0], vec![1]);
        assert!(batches[1].contains(&2));
        assert!(batches[1].contains(&3));
        assert_eq!(batches[2], vec![4]);
    }

    #[test]
    fn test_remove_node() {
        let mut graph = DependencyGraph::new();
        graph.add_node(1);
        graph.add_node(2);
        graph.add_edge(1, 2).unwrap();

        assert!(graph.remove_node(2));

        let node1 = graph.get_node(1).unwrap();
        assert!(!node1.dependencies.contains(&2));
    }
}
