"""
LoCoMo V020 WhiteMagic Self-Test
100 memories, 300 questions to test WM-enabled retrieval
"""

import json
from typing import List, Dict, Any
from datetime import datetime


def generate_v020_self_test() -> Dict[str, Any]:
    """Generate comprehensive V020 test for WhiteMagic self-testing."""
    
    test = {
        "version": "V020-WM",
        "description": "WhiteMagic self-test with 100 memories, 300 questions",
        "generated_at": datetime.now().isoformat(),
        "config": {
            "total_memories": 100,
            "total_questions": 300,
            "semantic_scoring": True,
            "query_type_weights": {
                "single_hop": {"vector": 0.4, "bm25": 0.5, "graph": 0.1},
                "multi_hop": {"vector": 0.3, "bm25": 0.3, "graph": 0.4},
                "temporal": {"vector": 0.6, "bm25": 0.3, "graph": 0.1},
                "open_domain": {"vector": 0.5, "bm25": 0.3, "graph": 0.2},
            }
        },
        "memories": [],
        "questions": []
    }
    
    # Generate 100 memories with rich interconnections
    test["memories"] = _generate_memory_corpus()
    
    # Generate 300 questions across types
    test["questions"] = _generate_question_suite(test["memories"])
    
    return test


def _generate_memory_corpus() -> List[Dict]:
    """Generate 100 memories with interconnected topics."""
    memories = []
    
    # Topic clusters for multi-hop testing
    topics = {
        "mcp_architecture": list(range(0, 15)),
        "memory_systems": list(range(15, 30)),
        "graph_algorithms": list(range(30, 45)),
        "embedding_models": list(range(45, 60)),
        "dream_cycles": list(range(60, 75)),
        "bridge_synthesis": list(range(75, 90)),
        "hybrid_fusion": list(range(90, 100)),
    }
    
    memory_templates = [
        # MCP Architecture (0-14)
        {"id": "wm_mcp_001", "title": "MCP Tool Registration Protocol", "topic": "mcp_architecture", "date": "2026-01-15"},
        {"id": "wm_mcp_002", "title": "Sangha Lock Implementation", "topic": "mcp_architecture", "date": "2026-01-16"},
        {"id": "wm_mcp_003", "title": "28 Gana Tool Mapping", "topic": "mcp_architecture", "date": "2026-01-17"},
        {"id": "wm_mcp_004", "title": "MCP 2.0 Schema Evolution", "topic": "mcp_architecture", "date": "2026-01-18"},
        {"id": "wm_mcp_005", "title": "Tool Handler Dispatcher", "topic": "mcp_architecture", "date": "2026-01-19"},
        {"id": "wm_mcp_006", "title": "Response Streaming Format", "topic": "mcp_architecture", "date": "2026-01-20"},
        {"id": "wm_mcp_007", "title": "Error Code Standardization", "topic": "mcp_architecture", "date": "2026-01-21"},
        {"id": "wm_mcp_008", "title": "Capability Negotiation", "topic": "mcp_architecture", "date": "2026-01-22"},
        {"id": "wm_mcp_009", "title": "Resource URI Patterns", "topic": "mcp_architecture", "date": "2026-01-23"},
        {"id": "wm_mcp_010", "title": "Notification Broadcasting", "topic": "mcp_architecture", "date": "2026-01-24"},
        {"id": "wm_mcp_011", "title": "Progress Reporting", "topic": "mcp_architecture", "date": "2026-01-25"},
        {"id": "wm_mcp_012", "title": "Cancellation Protocol", "topic": "mcp_architecture", "date": "2026-01-26"},
        {"id": "wm_mcp_013", "title": "Root URI Resolution", "topic": "mcp_architecture", "date": "2026-01-27"},
        {"id": "wm_mcp_014", "title": "Tool Result Caching", "topic": "mcp_architecture", "date": "2026-01-28"},
        {"id": "wm_mcp_015", "title": "MCP Server Lifecycle", "topic": "mcp_architecture", "date": "2026-01-29"},
        
        # Memory Systems (15-29)
        {"id": "wm_mem_001", "title": "Holographic Coordinate System", "topic": "memory_systems", "date": "2026-02-01"},
        {"id": "wm_mem_002", "title": "Galactic Distance Metrics", "topic": "memory_systems", "date": "2026-02-02"},
        {"id": "wm_mem_003", "title": "Memory Renaissance Pipeline", "topic": "memory_systems", "date": "2026-02-03"},
        {"id": "wm_mem_004", "title": "Quarantine Galaxy Logic", "topic": "memory_systems", "date": "2026-02-04"},
        {"id": "wm_mem_005", "title": "Cold Archive Structure", "topic": "memory_systems", "date": "2026-02-05"},
        {"id": "wm_mem_006", "title": "Hot Archive Indexing", "topic": "memory_systems", "date": "2026-02-06"},
        {"id": "wm_mem_007", "title": "Association Typing System", "topic": "memory_systems", "date": "2026-02-07"},
        {"id": "wm_mem_008", "title": "Typed Relation Extraction", "topic": "memory_systems", "date": "2026-02-08"},
        {"id": "wm_mem_009", "title": "Memory Deduplication", "topic": "memory_systems", "date": "2026-02-09"},
        {"id": "wm_mem_010", "title": "Content-Hash Indexing", "topic": "memory_systems", "date": "2026-02-10"},
        {"id": "wm_mem_011", "title": "Embedding Quantization", "topic": "memory_systems", "date": "2026-02-11"},
        {"id": "wm_mem_012", "title": "BGE Model Selection", "topic": "memory_systems", "date": "2026-02-12"},
        {"id": "wm_mem_013", "title": "Vector Dimension Reduction", "topic": "memory_systems", "date": "2026-02-13"},
        {"id": "wm_mem_014", "title": "Similarity Threshold Tuning", "topic": "memory_systems", "date": "2026-02-14"},
        {"id": "wm_mem_015", "title": "Memory Importance Scoring", "topic": "memory_systems", "date": "2026-02-15"},
        
        # Graph Algorithms (30-44)
        {"id": "wm_graph_001", "title": "Bridging Centrality Detection", "topic": "graph_algorithms", "date": "2026-02-16"},
        {"id": "wm_graph_002", "title": "Community Detection HDBSCAN", "topic": "graph_algorithms", "date": "2026-02-17"},
        {"id": "wm_graph_003", "title": "Constellation Formation", "topic": "graph_algorithms", "date": "2026-02-18"},
        {"id": "wm_graph_004", "title": "Graph Walk Algorithms", "topic": "graph_algorithms", "date": "2026-02-19"},
        {"id": "wm_graph_005", "title": "Semantic Projection Walk", "topic": "graph_algorithms", "date": "2026-02-20"},
        {"id": "wm_graph_006", "title": "PageRank Scoring", "topic": "graph_algorithms", "date": "2026-02-21"},
        {"id": "wm_graph_007", "title": "HRR Look-ahead", "topic": "graph_algorithms", "date": "2026-02-22"},
        {"id": "wm_graph_008", "title": "Transition Probability Computation", "topic": "graph_algorithms", "date": "2026-02-23"},
        {"id": "wm_graph_009", "title": "Parallel BFS Traversal", "topic": "graph_algorithms", "date": "2026-02-24"},
        {"id": "wm_graph_010", "title": "Association Strength Metrics", "topic": "graph_algorithms", "date": "2026-02-25"},
        {"id": "wm_graph_011", "title": "Graph Persistence Layer", "topic": "graph_algorithms", "date": "2026-02-26"},
        {"id": "wm_graph_012", "title": "NetworkX Integration", "topic": "graph_algorithms", "date": "2026-02-27"},
        {"id": "wm_graph_013", "title": "Graph Visualization Export", "topic": "graph_algorithms", "date": "2026-02-28"},
        {"id": "wm_graph_014", "title": "Causality Enforcement", "topic": "graph_algorithms", "date": "2026-03-01"},
        {"id": "wm_graph_015", "title": "Temporal Edge Ordering", "topic": "graph_algorithms", "date": "2026-03-02"},
        
        # Embedding Models (45-59)
        {"id": "wm_emb_001", "title": "BGE-Small Model Fine-tuning", "topic": "embedding_models", "date": "2026-03-03"},
        {"id": "wm_emb_002", "title": "ONNX Runtime Optimization", "topic": "embedding_models", "date": "2026-03-04"},
        {"id": "wm_emb_003", "title": "Batch Encoding Pipeline", "topic": "embedding_models", "date": "2026-03-05"},
        {"id": "wm_emb_004", "title": "Embedding Cache Strategy", "topic": "embedding_models", "date": "2026-03-06"},
        {"id": "wm_emb_005", "title": "Cosine Similarity SIMD", "topic": "embedding_models", "date": "2026-03-07"},
        {"id": "wm_emb_006", "title": "Top-K Approximate Search", "topic": "embedding_models", "date": "2026-03-08"},
        {"id": "wm_emb_007", "title": "Embedding Normalization", "topic": "embedding_models", "date": "2026-03-09"},
        {"id": "wm_emb_008", "title": "Multi-modal Embeddings", "topic": "embedding_models", "date": "2026-03-10"},
        {"id": "wm_emb_009", "title": "Code Embedding Strategy", "topic": "embedding_models", "date": "2026-03-11"},
        {"id": "wm_emb_010", "title": "Semantic Chunking", "topic": "embedding_models", "date": "2026-03-12"},
        {"id": "wm_emb_011", "title": "Embedding Drift Detection", "topic": "embedding_models", "date": "2026-03-13"},
        {"id": "wm_emb_012", "title": "Model Version Management", "topic": "embedding_models", "date": "2026-03-14"},
        {"id": "wm_emb_013", "title": "Cross-encoder Reranking", "topic": "embedding_models", "date": "2026-03-15"},
        {"id": "wm_emb_014", "title": "LoCoMo Training Data", "topic": "embedding_models", "date": "2026-03-16"},
        {"id": "wm_emb_015", "title": "Learned Reranker", "topic": "embedding_models", "date": "2026-03-17"},
        
        # Dream Cycles (60-74)
        {"id": "wm_dream_001", "title": "Dream Cycle 8 Phases", "topic": "dream_cycles", "date": "2026-03-18"},
        {"id": "wm_dream_002", "title": "Triage Phase Auto-tagging", "topic": "dream_cycles", "date": "2026-03-19"},
        {"id": "wm_dream_003", "title": "Consolidation Pattern Mining", "topic": "dream_cycles", "date": "2026-03-20"},
        {"id": "wm_dream_004", "title": "Serendipity Bridge Discovery", "topic": "dream_cycles", "date": "2026-03-21"},
        {"id": "wm_dream_005", "title": "Governance Echo Detection", "topic": "dream_cycles", "date": "2026-03-22"},
        {"id": "wm_dream_006", "title": "Narrative Compression", "topic": "dream_cycles", "date": "2026-03-23"},
        {"id": "wm_dream_007", "title": "Kaizen Insight Generation", "topic": "dream_cycles", "date": "2026-03-24"},
        {"id": "wm_dream_008", "title": "Oracle Pattern Suggestion", "topic": "dream_cycles", "date": "2026-03-25"},
        {"id": "wm_dream_009", "title": "Decay Sweep Algorithm", "topic": "dream_cycles", "date": "2026-03-26"},
        {"id": "wm_dream_010", "title": "Dream Daemon Scheduling", "topic": "dream_cycles", "date": "2026-03-27"},
        {"id": "wm_dream_011", "title": "Sleep Phase Detection", "topic": "dream_cycles", "date": "2026-03-28"},
        {"id": "wm_dream_012", "title": "Memory Reconsolidation", "topic": "dream_cycles", "date": "2026-03-29"},
        {"id": "wm_dream_013", "title": "REM Insight Burst", "topic": "dream_cycles", "date": "2026-03-30"},
        {"id": "wm_dream_014", "title": "Dream Synthesis Pipeline", "topic": "dream_cycles", "date": "2026-03-31"},
        {"id": "wm_dream_015", "title": "Oneiric Pattern Recognition", "topic": "dream_cycles", "date": "2026-04-01"},
        
        # Bridge Synthesis (75-89)
        {"id": "wm_bridge_001", "title": "Bridge Node Detection", "topic": "bridge_synthesis", "date": "2026-04-02"},
        {"id": "wm_bridge_002", "title": "Bridging Centrality Algorithm", "topic": "bridge_synthesis", "date": "2026-04-03"},
        {"id": "wm_bridge_003", "title": "Community Bridge Mapping", "topic": "bridge_synthesis", "date": "2026-04-04"},
        {"id": "wm_bridge_004", "title": "Hypothesis Generation LLM", "topic": "bridge_synthesis", "date": "2026-04-05"},
        {"id": "wm_bridge_005", "title": "Bridge Insight Persistence", "topic": "bridge_synthesis", "date": "2026-04-06"},
        {"id": "wm_bridge_006", "title": "Cross-Domain Pattern Mining", "topic": "bridge_synthesis", "date": "2026-04-07"},
        {"id": "wm_bridge_007", "title": "Latent Connection Discovery", "topic": "bridge_synthesis", "date": "2026-04-08"},
        {"id": "wm_bridge_008", "title": "Template Hypothesis Fallback", "topic": "bridge_synthesis", "date": "2026-04-09"},
        {"id": "wm_bridge_009", "title": "Bridge Confidence Scoring", "topic": "bridge_synthesis", "date": "2026-04-10"},
        {"id": "wm_bridge_010", "title": "Multi-Community Bridging", "topic": "bridge_synthesis", "date": "2026-04-11"},
        {"id": "wm_bridge_011", "title": "Bridge Node Tagging", "topic": "bridge_synthesis", "date": "2026-04-12"},
        {"id": "wm_bridge_012", "title": "Bridge Insight Retrieval", "topic": "bridge_synthesis", "date": "2026-04-13"},
        {"id": "wm_bridge_013", "title": "Dynamic Bridge Updates", "topic": "bridge_synthesis", "date": "2026-04-14"},
        {"id": "wm_bridge_014", "title": "Bridge Visualization", "topic": "bridge_synthesis", "date": "2026-04-15"},
        {"id": "wm_bridge_015", "title": "Bridge Quality Metrics", "topic": "bridge_synthesis", "date": "2026-04-16"},
        
        # Hybrid Fusion (90-99)
        {"id": "wm_fusion_001", "title": "Reciprocal Rank Fusion", "topic": "hybrid_fusion", "date": "2026-04-17"},
        {"id": "wm_fusion_002", "title": "RRF Weight Adaptation", "topic": "hybrid_fusion", "date": "2026-04-18"},
        {"id": "wm_fusion_003", "title": "BM25 Title Boosting", "topic": "hybrid_fusion", "date": "2026-04-19"},
        {"id": "wm_fusion_004", "title": "Constellation Boost Factor", "topic": "hybrid_fusion", "date": "2026-04-20"},
        {"id": "wm_fusion_005", "title": "Convex Combination Fusion", "topic": "hybrid_fusion", "date": "2026-04-21"},
        {"id": "wm_fusion_006", "title": "Query-Type Weight Selection", "topic": "hybrid_fusion", "date": "2026-04-22"},
        {"id": "wm_fusion_007", "title": "Multi-Channel Retrieval", "topic": "hybrid_fusion", "date": "2026-04-23"},
        {"id": "wm_fusion_008", "title": "Fusion Result Deduplication", "topic": "hybrid_fusion", "date": "2026-04-24"},
        {"id": "wm_fusion_009", "title": "Learned Fusion Weights", "topic": "hybrid_fusion", "date": "2026-04-25"},
        {"id": "wm_fusion_010", "title": "Real-time Fusion Pipeline", "topic": "hybrid_fusion", "date": "2026-04-26"},
    ]
    
    # Add content and associations to each memory
    for i, mem in enumerate(memory_templates):
        mem["content"] = f"Detailed technical documentation for {mem['title']}. This memory contains implementation details, design patterns, and best practices for WhiteMagic {mem['topic'].replace('_', ' ')} systems. Date: {mem['date']}."
        mem["importance"] = round(0.7 + (i % 3) * 0.1, 2)
        mem["associations"] = _generate_associations(i, memory_templates)
        memories.append(mem)
    
    return memories


def _generate_associations(idx: int, all_memories: List[Dict]) -> List[str]:
    """Generate cross-topic associations for multi-hop testing."""
    associations = []
    
    # Connect to next 2 in same topic
    topic_memories = [m for m in all_memories if m["topic"] == all_memories[idx]["topic"]]
    topic_idx = topic_memories.index(all_memories[idx])
    for i in range(1, 3):
        if topic_idx + i < len(topic_memories):
            associations.append(topic_memories[topic_idx + i]["id"])
    
    # Connect to 1-2 in related topics (for multi-hop)
    topic_groups = {
        "mcp_architecture": ["memory_systems", "hybrid_fusion"],
        "memory_systems": ["embedding_models", "graph_algorithms"],
        "graph_algorithms": ["bridge_synthesis", "dream_cycles"],
        "embedding_models": ["memory_systems", "hybrid_fusion"],
        "dream_cycles": ["bridge_synthesis", "graph_algorithms"],
        "bridge_synthesis": ["graph_algorithms", "dream_cycles"],
        "hybrid_fusion": ["memory_systems", "embedding_models"],
    }
    
    current_topic = all_memories[idx]["topic"]
    related_topics = topic_groups.get(current_topic, [])
    
    for related_topic in related_topics[:1]:  # Add 1 cross-topic link
        related_memories = [m for m in all_memories if m["topic"] == related_topic]
        if related_memories:
            # Pick a memory with similar index for consistency
            target_idx = idx % len(related_memories)
            associations.append(related_memories[target_idx]["id"])
    
    return associations


def _generate_question_suite(memories: List[Dict]) -> List[Dict]:
    """Generate 300 questions across all types."""
    questions = []
    
    # 60 single-hop (direct fact lookup)
    questions.extend(_generate_single_hop_questions(memories, 60))
    
    # 75 multi-hop (require graph traversal)
    questions.extend(_generate_multi_hop_questions(memories, 75))
    
    # 60 temporal (date-based)
    questions.extend(_generate_temporal_questions(memories, 60))
    
    # 60 open-domain (synthesis across multiple)
    questions.extend(_generate_open_domain_questions(memories, 60))
    
    # 30 adversarial (false premises)
    questions.extend(_generate_adversarial_questions(memories, 30))
    
    # 15 calibration (uncertainty testing)
    questions.extend(_generate_calibration_questions(memories, 15))
    
    return questions


def _generate_single_hop_questions(memories: List[Dict], count: int) -> List[Dict]:
    """Generate single-hop questions requiring direct lookup."""
    questions = []
    for i in range(count):
        mem = memories[i % len(memories)]
        questions.append({
            "question_id": f"q_sh_{i+1:03d}",
            "question_type": "single_hop",
            "question": f"What is the importance value of memory {mem['id']}?",
            "expected_answers": [str(mem["importance"])],
            "acceptable_keywords": [str(mem["importance"]), "importance"],
            "source_memory_ids": [mem["id"]],
            "difficulty": "easy",
        })
    return questions


def _generate_multi_hop_questions(memories: List[Dict], count: int) -> List[Dict]:
    """Generate multi-hop questions requiring graph traversal."""
    questions = []
    for i in range(count):
        # Find memories with associations
        source_mem = memories[i % len(memories)]
        if source_mem["associations"]:
            target_id = source_mem["associations"][0]
            target_mem = next((m for m in memories if m["id"] == target_id), None)
            if target_mem:
                questions.append({
                    "question_id": f"q_mh_{i+1:03d}",
                    "question_type": "multi_hop",
                    "question": f"Which two memories discuss {source_mem['topic'].replace('_', ' ')} and are connected via associations?",
                    "expected_answers": [
                        f"{source_mem['title']} and {target_mem['title']}",
                        f"{source_mem['id']} and {target_id}"
                    ],
                    "acceptable_keywords": [source_mem["title"], target_mem["title"], "associated", "connection"],
                    "source_memory_ids": [source_mem["id"], target_id],
                    "difficulty": "medium",
                    "requires_graph_traversal": True,
                })
    return questions


def _generate_temporal_questions(memories: List[Dict], count: int) -> List[Dict]:
    """Generate temporal questions based on dates."""
    questions = []
    for i in range(count):
        mem = memories[i % len(memories)]
        questions.append({
            "question_id": f"q_tp_{i+1:03d}",
            "question_type": "temporal",
            "question": f"What memory was created on {mem['date']}?",
            "expected_answers": [mem["title"], mem["id"]],
            "acceptable_keywords": [mem["date"], mem["title"]],
            "source_memory_ids": [mem["id"]],
            "difficulty": "easy",
        })
    return questions


def _generate_open_domain_questions(memories: List[Dict], count: int) -> List[Dict]:
    """Generate open-domain questions requiring synthesis."""
    questions = []
    topics = ["mcp_architecture", "memory_systems", "graph_algorithms", "dream_cycles"]
    
    for i in range(count):
        topic = topics[i % len(topics)]
        topic_memories = [m for m in memories if m["topic"] == topic]
        if len(topic_memories) >= 3:
            selected = topic_memories[:3]
            questions.append({
                "question_id": f"q_od_{i+1:03d}",
                "question_type": "open_domain",
                "question": f"What are the key components of WhiteMagic {topic.replace('_', ' ')}?",
                "expected_answers": [
                    "System includes: " + ", ".join([m["title"] for m in selected])
                ],
                "acceptable_keywords": [m["title"] for m in selected] + [topic.replace("_", " ")],
                "source_memory_ids": [m["id"] for m in selected],
                "difficulty": "hard",
                "requires_synthesis": True,
            })
    return questions


def _generate_adversarial_questions(memories: List[Dict], count: int) -> List[Dict]:
    """Generate adversarial questions with false premises."""
    questions = []
    
    adversarial_templates = [
        {
            "question": "What was the MCP implementation date on February 30, 2026?",
            "trap": "February 30 doesn't exist",
            "expected": ["February 30 doesn't exist", "invalid date", "false premise"]
        },
        {
            "question": "Which memory states that WhiteMagic has 500 tools?",
            "trap": "No memory states 500 tools",
            "expected": ["no memory states", "not found", "false premise"]
        },
        {
            "question": "What is the graph algorithm date for January 12, 2026?",
            "trap": "Wrong date format expectation",
            "expected": ["wrong date", "mismatch", "incorrect"]
        },
    ]
    
    for i in range(count):
        template = adversarial_templates[i % len(adversarial_templates)]
        questions.append({
            "question_id": f"q_adv_{i+1:03d}",
            "question_type": "adversarial",
            "question": template["question"],
            "expected_answers": template["expected"],
            "acceptable_keywords": ["false", "premise", "incorrect", "not found", "invalid"],
            "source_memory_ids": [],
            "difficulty": "medium",
            "trap": template["trap"],
        })
    
    return questions


def _generate_calibration_questions(memories: List[Dict], count: int) -> List[Dict]:
    """Generate calibration questions testing uncertainty."""
    questions = []
    
    for i in range(count):
        questions.append({
            "question_id": f"q_cal_{i+1:03d}",
            "question_type": "calibration",
            "question": "What is the exact total number of associations in the entire database?",
            "expected_answers": [
                "Cannot determine from provided memories",
                "Information not available",
                "NOT_FOUND"
            ],
            "acceptable_keywords": ["cannot", "not available", "unknown", "not found"],
            "source_memory_ids": [],
            "difficulty": "hard",
            "ideal_confidence": 0.0,
        })
    
    return questions


if __name__ == "__main__":
    test = generate_v020_self_test()
    
    output_path = str(__import__("pathlib").Path(__file__).parent / "locomo_v020_self_test.json")
    with open(output_path, "w") as f:
        json.dump(test, f, indent=2)
    
    print(f"Generated V020 Self-Test: {output_path}")
    print(f"Memories: {len(test['memories'])}")
    print(f"Questions: {len(test['questions'])}")
    
    # Distribution
    by_type = {}
    for q in test["questions"]:
        qtype = q["question_type"]
        by_type[qtype] = by_type.get(qtype, 0) + 1
    
    print("\nQuestion Distribution:")
    for qtype, count in sorted(by_type.items()):
        print(f"  {qtype}: {count}")
