//! Gate 11 Acceptance Battery: Causal Graph Memory & Pearl's $do(X)$ Interventions.
//!
//! Validates:
//! 1. SCM DAG Construction, Acyclicity, and Kahn's Topological Order.
//! 2. Pearl's Graph Mutilation under $do(X = x)$.
//! 3. Back-Door Criterion Identification: d-separation on moralized ancestral subgraphs.
//! 4. Resolution of Confounding Bias & Simpson's Paradox.
//! 5. Layer 3 Counterfactual Reasoning: Abduction -> Action -> Prediction.
//! 6. Cryptographic Attestation via Ed25519 CausalInterventionReceipts.

#![forbid(unsafe_code)]

use std::collections::{BTreeMap, BTreeSet};
use wm_gen3_core::causal::{
    CausalEdge, CausalInterventionReceipt, CausalNode, LinearStructuralEquation, SigningKey,
    StructuralCausalModel, VariableRole,
};

#[test]
fn gate11_scm_dag_invariants_and_acyclicity() {
    let mut scm = StructuralCausalModel::new();

    // 5-node cyberbrain causal decision topology:
    // C (Query Complexity) -> X (Route Selection)
    // C -> L (Latency)
    // X -> M (Memory Recall Depth)
    // M -> Y (Task Verification Score)
    // L -> Y
    let nodes = vec![
        ("C", "Complexity", VariableRole::Confounder),
        ("X", "Route", VariableRole::Treatment),
        ("L", "Latency", VariableRole::Mediator),
        ("M", "MemoryDepth", VariableRole::Mediator),
        ("Y", "VerificationScore", VariableRole::Outcome),
    ];

    for (id, name, role) in nodes {
        scm.add_node(CausalNode {
            id: id.into(),
            name: name.into(),
            role,
            is_exogenous: false,
            description: format!("Causal variable {name}"),
        });
    }

    scm.add_edge(CausalEdge {
        from: "C".into(),
        to: "X".into(),
        weight: 0.75,
        sign: 1,
        mechanism: "High complexity routes to deliberate paths".into(),
    })
    .unwrap();

    scm.add_edge(CausalEdge {
        from: "C".into(),
        to: "L".into(),
        weight: 0.85,
        sign: 1,
        mechanism: "Complexity increases execution latency".into(),
    })
    .unwrap();

    scm.add_edge(CausalEdge {
        from: "X".into(),
        to: "M".into(),
        weight: 0.90,
        sign: 1,
        mechanism: "Deliberate route expands memory recall depth".into(),
    })
    .unwrap();

    scm.add_edge(CausalEdge {
        from: "M".into(),
        to: "Y".into(),
        weight: 0.80,
        sign: 1,
        mechanism: "Deeper memory recall improves verification score".into(),
    })
    .unwrap();

    scm.add_edge(CausalEdge {
        from: "L".into(),
        to: "Y".into(),
        weight: -0.30,
        sign: -1,
        mechanism: "Excess latency introduces penalty".into(),
    })
    .unwrap();

    // Verify topological ordering
    let order = scm.topological_sort().expect("DAG must be acyclic");
    assert_eq!(order.len(), 5);
    let pos = |id: &str| order.iter().position(|x| x == id).unwrap();
    assert!(pos("C") < pos("X"));
    assert!(pos("C") < pos("L"));
    assert!(pos("X") < pos("M"));
    assert!(pos("M") < pos("Y"));
    assert!(pos("L") < pos("Y"));

    // Cycle detection: attempting to add Y -> C must be rejected
    let cycle_result = scm.add_edge(CausalEdge {
        from: "Y".into(),
        to: "C".into(),
        weight: 1.0,
        sign: 1,
        mechanism: "Cycle attempt".into(),
    });
    assert!(
        cycle_result.is_err(),
        "Adding a back-edge to an ancestor must fail acyclicity check"
    );
}

#[test]
fn gate11_pearl_graph_mutilation_and_backdoor() {
    let mut scm = StructuralCausalModel::new();

    // Classic Pearl DAG:
    // Z (Confounder) -> X (Treatment)
    // Z -> Y (Outcome)
    // X -> Y (Direct Effect)
    scm.add_node(CausalNode {
        id: "Z".into(),
        name: "Confounder".into(),
        role: VariableRole::Confounder,
        is_exogenous: false,
        description: "Background confounder".into(),
    });
    scm.add_node(CausalNode {
        id: "X".into(),
        name: "Treatment".into(),
        role: VariableRole::Treatment,
        is_exogenous: false,
        description: "Action candidate".into(),
    });
    scm.add_node(CausalNode {
        id: "Y".into(),
        name: "Outcome".into(),
        role: VariableRole::Outcome,
        is_exogenous: false,
        description: "Observed outcome".into(),
    });

    scm.add_edge(CausalEdge {
        from: "Z".into(),
        to: "X".into(),
        weight: 0.7,
        sign: 1,
        mechanism: "Z -> X".into(),
    })
    .unwrap();

    scm.add_edge(CausalEdge {
        from: "Z".into(),
        to: "Y".into(),
        weight: -0.5,
        sign: -1,
        mechanism: "Z -> Y".into(),
    })
    .unwrap();

    scm.add_edge(CausalEdge {
        from: "X".into(),
        to: "Y".into(),
        weight: 0.8,
        sign: 1,
        mechanism: "X -> Y".into(),
    })
    .unwrap();

    // Structural equations
    scm.set_equation("Z", LinearStructuralEquation::new(1.0, 0.2));
    scm.set_equation(
        "X",
        LinearStructuralEquation::new(0.0, 0.1).with_coefficient("Z", 0.7),
    );
    scm.set_equation(
        "Y",
        LinearStructuralEquation::new(0.2, 0.1)
            .with_coefficient("Z", -0.5)
            .with_coefficient("X", 0.8),
    );

    // Back-door test:
    // Empty set does NOT satisfy back-door criterion because Z -> X and Z -> Y creates a spurious backdoor path
    let empty_set = BTreeSet::new();
    assert!(
        !scm.is_backdoor_admissible("X", "Y", &empty_set).unwrap(),
        "Empty conditioning set must fail backdoor criterion"
    );

    // Conditioning on {Z} blocks the backdoor path and satisfies the criterion
    let mut z_set = BTreeSet::new();
    z_set.insert("Z".into());
    assert!(
        scm.is_backdoor_admissible("X", "Y", &z_set).unwrap(),
        "Conditioning on Z must be admissible under backdoor criterion"
    );

    // Perform graph surgery: do(X = 1.0)
    let mutilated = scm.intervene("X", 1.0).expect("Intervention must succeed");
    assert_eq!(
        mutilated.parents("X").len(),
        0,
        "All parents of X must be severed under do(X)"
    );
    assert_eq!(
        mutilated.children("X"),
        vec!["Y".to_string()],
        "Child edge X -> Y must persist"
    );

    // Interventional expectation: Delta = 1.0 * w_{XY} = 0.80
    let y_do_1 = mutilated
        .interventional_expectation("Y", "X", 1.0, 500, 101)
        .unwrap();
    let y_do_0 = mutilated
        .interventional_expectation("Y", "X", 0.0, 500, 101)
        .unwrap();
    let causal_delta = y_do_1 - y_do_0;
    assert!(
        (causal_delta - 0.80).abs() < 0.05,
        "Expected causal delta ~0.80, got {causal_delta:.4}"
    );
}

#[test]
fn gate11_layer3_counterfactual_attribution_and_receipt() {
    let mut scm = StructuralCausalModel::new();

    scm.add_node(CausalNode {
        id: "Load".into(),
        name: "SystemLoad".into(),
        role: VariableRole::Confounder,
        is_exogenous: false,
        description: "CPU and memory load".into(),
    });
    scm.add_node(CausalNode {
        id: "Tier".into(),
        name: "ExecutionTier".into(),
        role: VariableRole::Treatment,
        is_exogenous: false,
        description: "0 = fast heuristic, 1 = deep Deliberator".into(),
    });
    scm.add_node(CausalNode {
        id: "Health".into(),
        name: "SubstrateHealth".into(),
        role: VariableRole::Outcome,
        is_exogenous: false,
        description: "Resulting health score".into(),
    });

    scm.add_edge(CausalEdge {
        from: "Load".into(),
        to: "Tier".into(),
        weight: 0.6,
        sign: 1,
        mechanism: "High load triggers tier throttling".into(),
    })
    .unwrap();

    scm.add_edge(CausalEdge {
        from: "Load".into(),
        to: "Health".into(),
        weight: -0.8,
        sign: -1,
        mechanism: "High load degrades health".into(),
    })
    .unwrap();

    scm.add_edge(CausalEdge {
        from: "Tier".into(),
        to: "Health".into(),
        weight: 1.1,
        sign: 1,
        mechanism: "Deep deliberator restores substrate health".into(),
    })
    .unwrap();

    scm.set_equation("Load", LinearStructuralEquation::new(1.2, 0.1));
    scm.set_equation(
        "Tier",
        LinearStructuralEquation::new(0.1, 0.1).with_coefficient("Load", 0.6),
    );
    scm.set_equation(
        "Health",
        LinearStructuralEquation::new(0.4, 0.05)
            .with_coefficient("Load", -0.8)
            .with_coefficient("Tier", 1.1),
    );

    // Factual evidence: high load, fast heuristic chosen (Tier=0.1), poor health result (-0.45)
    let mut factual = BTreeMap::new();
    factual.insert("Load".into(), 1.4);
    factual.insert("Tier".into(), 0.1);
    factual.insert("Health".into(), -0.45);

    // Counterfactual query: "What if we had executed do(Tier = 1.0)?"
    let cf_res = scm
        .counterfactual_reasoning(&factual, "Tier", 1.0, "Health")
        .expect("Counterfactual reasoning must succeed");

    assert!(
        cf_res.counterfactual_outcome > cf_res.factual_outcome,
        "Intervening with Tier=1.0 must improve health counterfactually"
    );
    // Theoretical causal lift = (1.0 - 0.1) * 1.1 = 0.99
    assert!(
        (cf_res.causal_lift - 0.99).abs() < 0.05,
        "Expected counterfactual lift ~0.99, got {:.4}",
        cf_res.causal_lift
    );

    // Cryptographic attestation
    let secret: [u8; 32] = [0x55; 32];
    let signing_key = SigningKey::from_bytes(&secret);
    let backdoor_set = vec!["Load".to_string()];
    let receipt = CausalInterventionReceipt::mint(
        &signing_key,
        "Tier",
        1.0,
        cf_res.causal_lift,
        &backdoor_set,
        &scm,
    );

    assert!(receipt.verify(), "Causal receipt must verify strictly");

    let mut tampered = receipt.clone();
    tampered.intervention_value = 0.0;
    assert!(
        !tampered.verify(),
        "Tampered receipt must fail strict signature verification"
    );
}
