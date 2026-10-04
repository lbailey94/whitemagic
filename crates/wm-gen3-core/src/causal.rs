//! Causal Graph Memory, Structural Causal Models (SCM), Pearl's $do(X)$ Interventions,
//! and Counterfactual Reasoning (Level 2: Dynamics & Level 3: Phenotypes).
//!
//! # Epistemic Demarcation & Theoretical Grounding
//!
//! Passive retrieval and statistical correlation constitute Pearl's Layer 1 (Association: $P(Y \mid X)$).
//! Standard language models and vector databases operate purely in Layer 1, suffering from:
//! 1. Confounding bias: Common causes $Z \to X$ and $Z \to Y$ lead to spurious correlations.
//! 2. Superstitious reinforcement: Associating success with irrelevant context features.
//! 3. Inability to answer interventional ("What if we DO X?") and counterfactual ("What if we HAD DONE X?") queries.
//!
//! This module formalizes Pearl's complete 3-layer causal hierarchy for the WhiteMagic cyberbrain:
//! - **Layer 1 (Association / Observation):** $P(Y \mid X)$ — Observational conditional expectations.
//! - **Layer 2 (Intervention / Graph Mutilation):** $P(Y \mid do(X = x))$ — External structural surgery
//!   severing incoming parental edges into $X$, computing back-door and front-door adjusted effects.
//! - **Layer 3 (Counterfactual Reasoning):** $P(Y_{X=x'} \mid X=x, Y=y)$ — Three-phase
//!   Abduction $\to$ Action $\to$ Prediction on structural equations.
//!
//! Cryptographic accountability: Interventions and counterfactual bounds produce Ed25519-signed
//! causal receipts preventing retroactive causal narrative tampering.

#![forbid(unsafe_code)]

use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::fmt;

pub use ed25519_dalek::{Signer, SigningKey, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Errors encountered in causal modeling and graph surgery.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CausalError {
    CyclicGraph(String),
    NodeNotFound(String),
    EdgeNotFound(String, String),
    InvalidIntervention(String),
    BackdoorViolation(String),
    ComputationError(String),
}

impl fmt::Display for CausalError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::CyclicGraph(msg) => write!(f, "Causal DAG cycle detected: {msg}"),
            Self::NodeNotFound(id) => write!(f, "Causal node not found: {id}"),
            Self::EdgeNotFound(src, dst) => write!(f, "Causal edge not found: {src} -> {dst}"),
            Self::InvalidIntervention(msg) => write!(f, "Invalid causal intervention: {msg}"),
            Self::BackdoorViolation(msg) => write!(f, "Back-door criterion violation: {msg}"),
            Self::ComputationError(msg) => write!(f, "Causal computation error: {msg}"),
        }
    }
}

impl std::error::Error for CausalError {}

/// The role/nature of a causal variable in the cyberbrain cognitive topology.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum VariableRole {
    /// Contextual / environmental state (e.g. system load, user intent class).
    Context,
    /// Decision / action candidate (e.g. routing choice, tool call, synthesis tier).
    Treatment,
    /// Unobserved or partially observed confounder affecting both treatment and outcome.
    Confounder,
    /// Intermediate execution mediator (e.g. retrieval shortlist, parse tree).
    Mediator,
    /// Observable outcome / performance metric (e.g. latency, success, verification score).
    Outcome,
    /// Exogenous background noise variable $U_i$.
    Exogenous,
}

/// A node in the Causal DAG representing a random variable.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CausalNode {
    pub id: String,
    pub name: String,
    pub role: VariableRole,
    pub is_exogenous: bool,
    pub description: String,
}

/// A directed causal edge $X \to Y$ representing a structural dependency.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CausalEdge {
    pub from: String,
    pub to: String,
    /// Linear path coefficient or structural coupling strength.
    pub weight: f64,
    /// Qualitative interaction sign: +1 (excitatory/promotive), -1 (inhibitory/suppressive).
    pub sign: i8,
    pub mechanism: String,
}

/// Linear structural equation with additive noise:
/// $X_i := c_0 + \sum_{p \in \text{Pa}(X_i)} w_p \cdot X_p + U_i$
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LinearStructuralEquation {
    pub intercept: f64,
    pub coefficients: BTreeMap<String, f64>,
    /// Base mean of the exogenous error $U_i$.
    pub noise_mean: f64,
    /// Standard deviation of the exogenous error $U_i$.
    pub noise_std: f64,
}

impl LinearStructuralEquation {
    #[must_use]
    pub fn new(intercept: f64, noise_std: f64) -> Self {
        Self {
            intercept,
            coefficients: BTreeMap::new(),
            noise_mean: 0.0,
            noise_std: noise_std.max(1e-6),
        }
    }

    pub fn with_coefficient(mut self, parent: impl Into<String>, weight: f64) -> Self {
        self.coefficients.insert(parent.into(), weight);
        self
    }

    /// Evaluates the structural equation given parent values and a realized noise value $U_i$.
    #[must_use]
    pub fn evaluate(&self, parent_values: &BTreeMap<String, f64>, noise: f64) -> f64 {
        let effective_noise = if self.noise_std < 1e-6 { 0.0 } else { noise };
        let mut val = self.intercept + effective_noise;
        for (parent, weight) in &self.coefficients {
            if let Some(&p_val) = parent_values.get(parent) {
                val += weight * p_val;
            }
        }
        val
    }

    /// Inverts the equation to deduce the unobserved exogenous noise $U_i$ given realized $X_i$ and parent values:
    /// $U_i = X_i - \left(c_0 + \sum w_p X_p\right)$
    #[must_use]
    pub fn abduct_noise(&self, realized_value: f64, parent_values: &BTreeMap<String, f64>) -> f64 {
        let mut predicted = self.intercept;
        for (parent, weight) in &self.coefficients {
            if let Some(&p_val) = parent_values.get(parent) {
                predicted += weight * p_val;
            }
        }
        realized_value - predicted
    }
}

/// A complete Structural Causal Model (SCM) over a Directed Acyclic Graph (DAG).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructuralCausalModel {
    pub nodes: BTreeMap<String, CausalNode>,
    pub edges: Vec<CausalEdge>,
    pub equations: BTreeMap<String, LinearStructuralEquation>,
}

impl Default for StructuralCausalModel {
    fn default() -> Self {
        Self::new()
    }
}

impl StructuralCausalModel {
    #[must_use]
    pub fn new() -> Self {
        Self {
            nodes: BTreeMap::new(),
            edges: Vec::new(),
            equations: BTreeMap::new(),
        }
    }

    /// Adds a causal node to the model.
    pub fn add_node(&mut self, node: CausalNode) {
        let id = node.id.clone();
        self.nodes.insert(id, node);
    }

    /// Adds a directed causal edge $from \to to$.
    pub fn add_edge(&mut self, edge: CausalEdge) -> Result<(), CausalError> {
        if !self.nodes.contains_key(&edge.from) {
            return Err(CausalError::NodeNotFound(edge.from.clone()));
        }
        if !self.nodes.contains_key(&edge.to) {
            return Err(CausalError::NodeNotFound(edge.to.clone()));
        }

        // Check that adding this edge does not introduce a cycle
        let mut temp_edges = self.edges.clone();
        temp_edges.push(edge.clone());
        Self::check_acyclicity(&self.nodes, &temp_edges)?;

        // Update the structural equation coefficient for the destination node
        let eq = self
            .equations
            .entry(edge.to.clone())
            .or_insert_with(|| LinearStructuralEquation::new(0.0, 1.0));
        eq.coefficients.insert(edge.from.clone(), edge.weight);

        self.edges.push(edge);
        Ok(())
    }

    /// Sets the structural equation for a node.
    pub fn set_equation(&mut self, node_id: impl Into<String>, equation: LinearStructuralEquation) {
        self.equations.insert(node_id.into(), equation);
    }

    /// Returns direct parent nodes of a given node: $\{P \mid P \to node\}$.
    #[must_use]
    pub fn parents(&self, node: &str) -> Vec<String> {
        self.edges
            .iter()
            .filter(|e| e.to == node)
            .map(|e| e.from.clone())
            .collect()
    }

    /// Returns direct children nodes of a given node: $\{C \mid node \to C\}$.
    #[must_use]
    pub fn children(&self, node: &str) -> Vec<String> {
        self.edges
            .iter()
            .filter(|e| e.from == node)
            .map(|e| e.to.clone())
            .collect()
    }

    /// Computes all ancestral nodes of `node` in the DAG.
    #[must_use]
    pub fn ancestors(&self, node: &str) -> BTreeSet<String> {
        let mut ancestors = BTreeSet::new();
        let mut queue = VecDeque::new();
        for p in self.parents(node) {
            queue.push_back(p);
        }
        while let Some(curr) = queue.pop_front() {
            if ancestors.insert(curr.clone()) {
                for p in self.parents(&curr) {
                    queue.push_back(p);
                }
            }
        }
        ancestors
    }

    /// Computes all descendant nodes of `node` in the DAG.
    #[must_use]
    pub fn descendants(&self, node: &str) -> BTreeSet<String> {
        let mut descendants = BTreeSet::new();
        let mut queue = VecDeque::new();
        for c in self.children(node) {
            queue.push_back(c);
        }
        while let Some(curr) = queue.pop_front() {
            if descendants.insert(curr.clone()) {
                for c in self.children(&curr) {
                    queue.push_back(c);
                }
            }
        }
        descendants
    }

    /// Kahn's algorithm for topological sorting of the DAG.
    pub fn topological_sort(&self) -> Result<Vec<String>, CausalError> {
        Self::compute_topological_sort(&self.nodes, &self.edges)
    }

    fn check_acyclicity(
        nodes: &BTreeMap<String, CausalNode>,
        edges: &[CausalEdge],
    ) -> Result<(), CausalError> {
        Self::compute_topological_sort(nodes, edges).map(|_| ())
    }

    fn compute_topological_sort(
        nodes: &BTreeMap<String, CausalNode>,
        edges: &[CausalEdge],
    ) -> Result<Vec<String>, CausalError> {
        let mut in_degree: BTreeMap<String, usize> = nodes.keys().map(|k| (k.clone(), 0)).collect();
        for e in edges {
            if let Some(entry) = in_degree.get_mut(&e.to) {
                *entry += 1;
            }
        }

        let mut queue: VecDeque<String> = in_degree
            .iter()
            .filter(|(_, deg)| **deg == 0)
            .map(|(k, _)| k.clone())
            .collect();

        let mut sorted = Vec::with_capacity(nodes.len());
        while let Some(u) = queue.pop_front() {
            sorted.push(u.clone());
            for e in edges.iter().filter(|e| e.from == u) {
                if let Some(deg) = in_degree.get_mut(&e.to) {
                    *deg -= 1;
                    if *deg == 0 {
                        queue.push_back(e.to.clone());
                    }
                }
            }
        }

        if sorted.len() != nodes.len() {
            return Err(CausalError::CyclicGraph(
                "Cycle detected; graph is not a Directed Acyclic Graph".into(),
            ));
        }

        Ok(sorted)
    }

    /// Evaluates d-separation: determines if variables $X$ and $Y$ are conditionally
    /// independent given conditioning set $Z$: $(X \perp\!\!\!\perp Y \mid Z)_{\mathcal{G}}$.
    #[must_use]
    pub fn is_d_separated(&self, x: &str, y: &str, z_set: &BTreeSet<String>) -> bool {
        // Build undirected moral graph for ancestral subgraph of X, Y, Z
        let mut relevant_nodes = BTreeSet::new();
        relevant_nodes.insert(x.to_string());
        relevant_nodes.insert(y.to_string());
        for z in z_set {
            relevant_nodes.insert(z.clone());
        }

        let mut all_ancestors = BTreeSet::new();
        for node in &relevant_nodes {
            all_ancestors.insert(node.clone());
            for anc in self.ancestors(node) {
                all_ancestors.insert(anc);
            }
        }

        // Connect moral edges: marry parents that share a common child in the ancestral set
        let mut adjacency: BTreeMap<String, BTreeSet<String>> = all_ancestors
            .iter()
            .map(|n| (n.clone(), BTreeSet::new()))
            .collect();

        // Add directed edges as undirected edges in the moral subgraph
        for e in &self.edges {
            if all_ancestors.contains(&e.from) && all_ancestors.contains(&e.to) {
                adjacency
                    .entry(e.from.clone())
                    .or_default()
                    .insert(e.to.clone());
                adjacency
                    .entry(e.to.clone())
                    .or_default()
                    .insert(e.from.clone());
            }
        }

        // Marry parents (add undirected edge between any two parents of a node in all_ancestors)
        for child in &all_ancestors {
            let parents: Vec<String> = self
                .parents(child)
                .into_iter()
                .filter(|p| all_ancestors.contains(p))
                .collect();
            for i in 0..parents.len() {
                for j in (i + 1)..parents.len() {
                    let p1 = &parents[i];
                    let p2 = &parents[j];
                    adjacency.entry(p1.clone()).or_default().insert(p2.clone());
                    adjacency.entry(p2.clone()).or_default().insert(p1.clone());
                }
            }
        }

        // Delete conditioning set Z from the moralized graph
        for z in z_set {
            adjacency.remove(z);
            for neighbors in adjacency.values_mut() {
                neighbors.remove(z);
            }
        }

        // If there is no active path between X and Y, they are d-separated
        if !adjacency.contains_key(x) || !adjacency.contains_key(y) {
            return true;
        }

        let mut visited = BTreeSet::new();
        let mut queue = VecDeque::new();
        queue.push_back(x.to_string());
        visited.insert(x.to_string());

        while let Some(curr) = queue.pop_front() {
            if curr == y {
                return false; // Path exists, not d-separated
            }
            if let Some(neighbors) = adjacency.get(&curr) {
                for nbr in neighbors {
                    if visited.insert(nbr.clone()) {
                        queue.push_back(nbr.clone());
                    }
                }
            }
        }

        true // No path exists: d-separated!
    }

    /// Evaluates Pearl's Back-Door Criterion:
    /// A set of variables $Z$ satisfies the back-door criterion relative to an ordered pair
    /// of variables $(X, Y)$ if:
    /// 1. No node in $Z$ is a descendant of $X$.
    /// 2. $Z$ blocks every path between $X$ and $Y$ that contains an arrow into $X$.
    pub fn is_backdoor_admissible(
        &self,
        treatment: &str,
        outcome: &str,
        z_set: &BTreeSet<String>,
    ) -> Result<bool, CausalError> {
        if !self.nodes.contains_key(treatment) {
            return Err(CausalError::NodeNotFound(treatment.to_string()));
        }
        if !self.nodes.contains_key(outcome) {
            return Err(CausalError::NodeNotFound(outcome.to_string()));
        }

        // Condition 1: No node in Z is a descendant of treatment X
        let x_descendants = self.descendants(treatment);
        for z in z_set {
            if x_descendants.contains(z) {
                return Ok(false);
            }
            if z == treatment {
                return Ok(false);
            }
        }

        // Condition 2: In the mutilated graph where edges leaving X are removed (G_{\underline{X}}),
        // X and Y are d-separated given Z.
        let mut g_under_x = self.clone();
        g_under_x.edges.retain(|e| e.from != treatment);

        Ok(g_under_x.is_d_separated(treatment, outcome, z_set))
    }

    /// Executes Pearl's Graph Mutilation for the intervention $do(X = x)$:
    /// - Mutilates the DAG: severs all incoming arrows directed into $X$ ($Pa(X) \leftarrow \emptyset$).
    /// - Freezes $X$ to a deterministic assignment $x$.
    /// - Leaves all other mechanisms $V_j := f_j(Pa(V_j), U_j)$ intact.
    pub fn intervene(&self, treatment: &str, assigned_value: f64) -> Result<Self, CausalError> {
        if !self.nodes.contains_key(treatment) {
            return Err(CausalError::NodeNotFound(treatment.to_string()));
        }

        let mut mutilated = self.clone();

        // 1. Structural surgery: delete all incoming edges into `treatment`
        mutilated.edges.retain(|e| e.to != treatment);

        // 2. Set deterministic assignment equation: X := assigned_value
        let fixed_eq = LinearStructuralEquation {
            intercept: assigned_value,
            coefficients: BTreeMap::new(),
            noise_mean: 0.0,
            noise_std: 1e-9, // deterministic
        };
        mutilated.equations.insert(treatment.to_string(), fixed_eq);

        Ok(mutilated)
    }

    /// Forward ancestral simulation: computes the values of all variables in topological order
    /// given realized exogenous noises.
    pub fn forward_simulate(
        &self,
        exogenous_noises: &BTreeMap<String, f64>,
    ) -> Result<BTreeMap<String, f64>, CausalError> {
        let order = self.topological_sort()?;
        let mut realized = BTreeMap::new();

        for node_id in order {
            let noise = exogenous_noises.get(&node_id).copied().unwrap_or(0.0);
            let eq = self
                .equations
                .get(&node_id)
                .cloned()
                .unwrap_or_else(|| LinearStructuralEquation::new(0.0, 1.0));

            let val = eq.evaluate(&realized, noise);
            realized.insert(node_id, val);
        }

        Ok(realized)
    }

    /// Computes the interventional expectation $\mathbb{E}[Y \mid do(X = x)]$
    /// using Monte Carlo sampling over the mutilated structural causal model.
    pub fn interventional_expectation(
        &self,
        outcome: &str,
        treatment: &str,
        assigned_value: f64,
        sample_count: usize,
        seed: u64,
    ) -> Result<f64, CausalError> {
        let mutilated = self.intervene(treatment, assigned_value)?;
        let mut sum_y = 0.0f64;
        let mut rng_state = seed.wrapping_add(104729);

        let nodes_list: Vec<String> = mutilated.nodes.keys().cloned().collect();

        for _ in 0..sample_count {
            let mut noises = BTreeMap::new();
            for node in &nodes_list {
                // Linear congruential pseudorandom normal approximation via Box-Muller
                let u1 = lcg_f64(&mut rng_state).max(1e-12);
                let u2 = lcg_f64(&mut rng_state);
                let z0 = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

                let std = mutilated
                    .equations
                    .get(node)
                    .map(|eq| eq.noise_std)
                    .unwrap_or(1.0);
                noises.insert(node.clone(), z0 * std);
            }

            let state = mutilated.forward_simulate(&noises)?;
            let y_val = state
                .get(outcome)
                .copied()
                .ok_or_else(|| CausalError::NodeNotFound(outcome.to_string()))?;
            sum_y += y_val;
        }

        Ok(sum_y / (sample_count as f64))
    }

    /// Pearl's Layer 3: Counterfactual Inference.
    /// Answers: "Given that we observed $X = x$ and $Y = y$ in the factual world,
    /// what would $Y$ have been had we chosen $do(X = x^*)$?"
    ///
    /// Executes the canonical 3-step abduction-action-prediction protocol:
    /// 1. **Abduction:** Given factual observations $E = e$, compute the unique exogenous noises $U$.
    /// 2. **Action:** Mutilate the SCM by setting $do(X = x^*)$ (severing $Pa(X)$).
    /// 3. **Prediction:** Forward-simulate the mutilated SCM using the abducted background noise $U$.
    pub fn counterfactual_reasoning(
        &self,
        factual_observations: &BTreeMap<String, f64>,
        treatment: &str,
        counterfactual_value: f64,
        target_outcome: &str,
    ) -> Result<CounterfactualResult, CausalError> {
        if !self.nodes.contains_key(treatment) {
            return Err(CausalError::NodeNotFound(treatment.to_string()));
        }
        if !self.nodes.contains_key(target_outcome) {
            return Err(CausalError::NodeNotFound(target_outcome.to_string()));
        }

        // Step 1: Abduction — Invert equations to recover exact background noise U_i for each node
        let mut abducted_noises = BTreeMap::new();
        for (node_id, &realized_val) in factual_observations {
            if let Some(eq) = self.equations.get(node_id) {
                let u_i = eq.abduct_noise(realized_val, factual_observations);
                abducted_noises.insert(node_id.clone(), u_i);
            } else {
                abducted_noises.insert(node_id.clone(), 0.0);
            }
        }

        // Step 2: Action — Mutilate model with do(X = counterfactual_value)
        let mutilated_scm = self.intervene(treatment, counterfactual_value)?;

        // Step 3: Prediction — Forward simulate using the abducted noises
        let counterfactual_world = mutilated_scm.forward_simulate(&abducted_noises)?;

        let factual_outcome = factual_observations
            .get(target_outcome)
            .copied()
            .unwrap_or(0.0);
        let counterfactual_outcome = counterfactual_world
            .get(target_outcome)
            .copied()
            .ok_or_else(|| CausalError::NodeNotFound(target_outcome.to_string()))?;

        let causal_lift = counterfactual_outcome - factual_outcome;

        Ok(CounterfactualResult {
            treatment: treatment.to_string(),
            factual_treatment_value: factual_observations.get(treatment).copied().unwrap_or(0.0),
            counterfactual_treatment_value: counterfactual_value,
            target_outcome: target_outcome.to_string(),
            factual_outcome,
            counterfactual_outcome,
            causal_lift,
            abducted_noises,
        })
    }
}

/// The result of a Layer 3 counterfactual computation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CounterfactualResult {
    pub treatment: String,
    pub factual_treatment_value: f64,
    pub counterfactual_treatment_value: f64,
    pub target_outcome: String,
    pub factual_outcome: f64,
    pub counterfactual_outcome: f64,
    pub causal_lift: f64,
    pub abducted_noises: BTreeMap<String, f64>,
}

/// A cryptographically signed Causal Intervention & Attribution Receipt.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CausalInterventionReceipt {
    pub receipt_id: String,
    pub timestamp_utc: String,
    pub treatment: String,
    pub intervention_value: f64,
    pub expected_outcome_lift: f64,
    pub backdoor_set: Vec<String>,
    pub model_dag_hash: String,
    pub verifying_key: String,
    pub signature: String,
}

impl CausalInterventionReceipt {
    /// Mints and signs an intervention receipt with an Ed25519 signing key.
    pub fn mint(
        signing_key: &SigningKey,
        treatment: &str,
        intervention_value: f64,
        expected_outcome_lift: f64,
        backdoor_set: &[String],
        scm: &StructuralCausalModel,
    ) -> Self {
        let timestamp_utc = chrono::Utc::now().to_rfc3339();
        let verifying_key = hex_encode(&signing_key.verifying_key().to_bytes());

        // Compute deterministic hash of the causal model DAG structure
        let mut hasher = Sha256::new();
        hasher.update(serde_json::to_vec(&scm.nodes).unwrap_or_default());
        hasher.update(serde_json::to_vec(&scm.edges).unwrap_or_default());
        let model_dag_hash = hex_encode(&hasher.finalize());

        let receipt_id = format!("causal-rcpt-{}", &model_dag_hash[..16]);

        let payload = format!(
            "{}:{}:{:.6}:{:.6}:{:?}:{}",
            receipt_id,
            treatment,
            intervention_value,
            expected_outcome_lift,
            backdoor_set,
            model_dag_hash
        );

        let signature = hex_encode(&signing_key.sign(payload.as_bytes()).to_bytes());

        Self {
            receipt_id,
            timestamp_utc,
            treatment: treatment.to_string(),
            intervention_value,
            expected_outcome_lift,
            backdoor_set: backdoor_set.to_vec(),
            model_dag_hash,
            verifying_key,
            signature,
        }
    }

    /// Verifies the cryptographic signature of the intervention receipt.
    pub fn verify(&self) -> bool {
        let Some(vk_array) = hex_decode_32(&self.verifying_key) else {
            return false;
        };
        let Ok(vk) = VerifyingKey::from_bytes(&vk_array) else {
            return false;
        };

        let Some(sig_array) = hex_decode_64(&self.signature) else {
            return false;
        };
        let signature = ed25519_dalek::Signature::from_bytes(&sig_array);

        let payload = format!(
            "{}:{}:{:.6}:{:.6}:{:?}:{}",
            self.receipt_id,
            self.treatment,
            self.intervention_value,
            self.expected_outcome_lift,
            self.backdoor_set,
            self.model_dag_hash
        );

        vk.verify_strict(payload.as_bytes(), &signature).is_ok()
    }
}

/// Helper: hex encode arbitrary bytes.
fn hex_encode(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        use std::fmt::Write;
        let _ = write!(s, "{:02x}", b);
    }
    s
}

/// Helper: decode 64 hex characters into 32-byte array.
fn hex_decode_32(hex_str: &str) -> Option<[u8; 32]> {
    if hex_str.len() != 64 {
        return None;
    }
    let mut out = [0u8; 32];
    for i in 0..32 {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16).ok()?;
    }
    Some(out)
}

/// Helper: decode 128 hex characters into 64-byte array.
fn hex_decode_64(hex_str: &str) -> Option<[u8; 64]> {
    if hex_str.len() != 128 {
        return None;
    }
    let mut out = [0u8; 64];
    for i in 0..64 {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16).ok()?;
    }
    Some(out)
}

/// Minimal linear congruential generator for deterministic sampling without external RNG state.
fn lcg_f64(state: &mut u64) -> f64 {
    *state = state
        .wrapping_mul(6364136223846793005)
        .wrapping_add(1442695040888963407);
    ((*state >> 11) as f64) / ((1u64 << 53) as f64)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Constructs the classic Confounding / Simpson's Paradox DAG:
    /// Confounder Z (Task Complexity: 0=easy, 1=hard)
    /// Treatment X (Route Choice: 0=fast/shallow, 1=deep deliberator)
    /// Mediator M (Context Enrichment Quality)
    /// Outcome Y (Success Rate: higher is better)
    ///
    /// Graph structure:
    /// Z -> X (Complex tasks trigger deeper routes more frequently)
    /// Z -> Y (Complex tasks have higher baseline failure rates)
    /// X -> M (Deep route improves context enrichment)
    /// M -> Y (Better context directly improves success)
    fn build_confounded_test_scm() -> StructuralCausalModel {
        let mut scm = StructuralCausalModel::new();

        scm.add_node(CausalNode {
            id: "Z".into(),
            name: "TaskComplexity".into(),
            role: VariableRole::Confounder,
            is_exogenous: false,
            description: "Task difficulty and background ambiguity".into(),
        });
        scm.add_node(CausalNode {
            id: "X".into(),
            name: "RouteChoice".into(),
            role: VariableRole::Treatment,
            is_exogenous: false,
            description: "0 = fast shallow, 1 = deep deliberator".into(),
        });
        scm.add_node(CausalNode {
            id: "M".into(),
            name: "ContextQuality".into(),
            role: VariableRole::Mediator,
            is_exogenous: false,
            description: "Context enrichment score".into(),
        });
        scm.add_node(CausalNode {
            id: "Y".into(),
            name: "SuccessScore".into(),
            role: VariableRole::Outcome,
            is_exogenous: false,
            description: "Final task execution score".into(),
        });

        // Add edges:
        // Z -> X (weight = 0.8)
        scm.add_edge(CausalEdge {
            from: "Z".into(),
            to: "X".into(),
            weight: 0.8,
            sign: 1,
            mechanism: "Difficulty induces deliberation".into(),
        })
        .unwrap();

        // Z -> Y (weight = -0.7: harder tasks lower score)
        scm.add_edge(CausalEdge {
            from: "Z".into(),
            to: "Y".into(),
            weight: -0.7,
            sign: -1,
            mechanism: "Inherent task difficulty degrades score".into(),
        })
        .unwrap();

        // X -> M (weight = 0.6)
        scm.add_edge(CausalEdge {
            from: "X".into(),
            to: "M".into(),
            weight: 0.6,
            sign: 1,
            mechanism: "Deliberation enhances context".into(),
        })
        .unwrap();

        // M -> Y (weight = 0.9: enrichment boosts score)
        scm.add_edge(CausalEdge {
            from: "M".into(),
            to: "Y".into(),
            weight: 0.9,
            sign: 1,
            mechanism: "Context quality drives task success".into(),
        })
        .unwrap();

        // Structural equations
        scm.set_equation("Z", LinearStructuralEquation::new(1.0, 0.2));
        scm.set_equation(
            "X",
            LinearStructuralEquation::new(0.1, 0.1).with_coefficient("Z", 0.8),
        );
        scm.set_equation(
            "M",
            LinearStructuralEquation::new(0.2, 0.1).with_coefficient("X", 0.6),
        );
        scm.set_equation(
            "Y",
            LinearStructuralEquation::new(0.5, 0.1)
                .with_coefficient("Z", -0.7)
                .with_coefficient("M", 0.9),
        );

        scm
    }

    #[test]
    fn test_topological_sort_and_acyclicity() {
        let scm = build_confounded_test_scm();
        let order = scm.topological_sort().expect("Must be a valid DAG");

        let z_idx = order.iter().position(|r| r == "Z").unwrap();
        let x_idx = order.iter().position(|r| r == "X").unwrap();
        let m_idx = order.iter().position(|r| r == "M").unwrap();
        let y_idx = order.iter().position(|r| r == "Y").unwrap();

        assert!(z_idx < x_idx, "Z must precede X");
        assert!(x_idx < m_idx, "X must precede M");
        assert!(m_idx < y_idx, "M must precede Y");
        assert!(z_idx < y_idx, "Z must precede Y");
    }

    #[test]
    fn test_backdoor_criterion_identification() {
        let scm = build_confounded_test_scm();

        // Z is the true confounder: conditioning on Z blocks the backdoor path X <- Z -> Y
        let mut z_set = BTreeSet::new();
        z_set.insert("Z".into());
        assert!(
            scm.is_backdoor_admissible("X", "Y", &z_set).unwrap(),
            "Conditioning on confounder Z MUST satisfy backdoor criterion"
        );

        // Empty set fails backdoor criterion because X <- Z -> Y is open
        let empty_set = BTreeSet::new();
        assert!(
            !scm.is_backdoor_admissible("X", "Y", &empty_set).unwrap(),
            "Empty conditioning set must FAIL backdoor criterion due to confounder Z"
        );

        // Mediator M is a descendant of X; conditioning on M violates condition 1 of backdoor criterion!
        let mut m_set = BTreeSet::new();
        m_set.insert("M".into());
        assert!(
            !scm.is_backdoor_admissible("X", "Y", &m_set).unwrap(),
            "Conditioning on mediator M must FAIL backdoor criterion"
        );
    }

    #[test]
    fn test_graph_mutilation_pearl_do_calculus() {
        let scm = build_confounded_test_scm();

        // Intervene: do(X = 1.0)
        let mutilated = scm.intervene("X", 1.0).expect("Mutilation must succeed");

        // In the mutilated graph, X has ZERO parents: edge Z -> X is severed!
        assert_eq!(
            mutilated.parents("X").len(),
            0,
            "Incoming parents to X must be severed under do(X)"
        );

        // But downstream edges X -> M and M -> Y must remain intact!
        assert_eq!(mutilated.children("X"), vec!["M".to_string()]);
        assert_eq!(mutilated.children("M"), vec!["Y".to_string()]);

        // Non-intervened relations (Z -> Y) must also remain intact!
        assert!(mutilated.parents("Y").contains(&"Z".to_string()));
        assert!(mutilated.parents("Y").contains(&"M".to_string()));
    }

    #[test]
    fn test_interventional_expectation_vs_observational_bias() {
        let scm = build_confounded_test_scm();

        // Compute interventional effect of do(X = 1.0) vs do(X = 0.0)
        let y_do_1 = scm
            .interventional_expectation("Y", "X", 1.0, 500, 42)
            .unwrap();
        let y_do_0 = scm
            .interventional_expectation("Y", "X", 0.0, 500, 42)
            .unwrap();

        // Structural effect: Delta = (1.0 - 0.0) * w_{XM} * w_{MY} = 1.0 * 0.6 * 0.9 = 0.54
        let causal_effect = y_do_1 - y_do_0;
        assert!(
            (causal_effect - 0.54).abs() < 0.05,
            "True interventional causal effect should be ~0.54, got {causal_effect:.4}"
        );
    }

    #[test]
    fn test_pearl_layer3_counterfactual_reasoning() {
        let scm = build_confounded_test_scm();

        // Factual world observation:
        // We had a hard task (Z = 1.5).
        // The shallow route was used (X = 0.2).
        // Context quality was mediocre (M = 0.32).
        // The final score was low (Y = -0.26).
        let mut factual = BTreeMap::new();
        factual.insert("Z".into(), 1.5);
        factual.insert("X".into(), 0.2);
        factual.insert("M".into(), 0.32);
        factual.insert("Y".into(), -0.26);

        // Counterfactual query: "What would the score Y have been had we taken do(X = 1.0)?"
        let cf_result = scm
            .counterfactual_reasoning(&factual, "X", 1.0, "Y")
            .expect("Counterfactual reasoning must succeed");

        assert_eq!(cf_result.factual_outcome, -0.26);
        assert!(
            cf_result.counterfactual_outcome > cf_result.factual_outcome,
            "Intervening with deep deliberator (X=1.0) must improve counterfactual outcome"
        );
        assert!(
            (cf_result.causal_lift - 0.432).abs() < 0.05,
            "Causal lift should be ~0.432 (0.8 * 0.6 * 0.9), got {:.4}",
            cf_result.causal_lift
        );
    }

    #[test]
    fn test_causal_receipt_cryptographic_verification() {
        let scm = build_confounded_test_scm();
        let secret_bytes: [u8; 32] = [
            0x9d, 0x61, 0xb1, 0x9d, 0xef, 0xfd, 0x5a, 0x60, 0xba, 0x84, 0x4a, 0xf4, 0x92, 0xec,
            0x2c, 0xc4, 0x44, 0x49, 0xc5, 0x69, 0x7b, 0x32, 0x69, 0x19, 0x70, 0x3b, 0xac, 0x03,
            0x1c, 0xae, 0x7f, 0x60,
        ];
        let signing_key = SigningKey::from_bytes(&secret_bytes);

        let backdoor = vec!["Z".to_string()];
        let receipt =
            CausalInterventionReceipt::mint(&signing_key, "X", 1.0, 0.54, &backdoor, &scm);

        assert!(
            receipt.verify(),
            "Valid causal receipt must verify strictly"
        );

        // Tamper test: alter the expected outcome lift
        let mut tampered = receipt.clone();
        tampered.expected_outcome_lift = 0.9999;
        assert!(
            !tampered.verify(),
            "Tampered causal receipt must be rejected immediately"
        );
    }
}
