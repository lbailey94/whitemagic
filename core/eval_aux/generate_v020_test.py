"""
LoCoMo V020 Test Generator
Creates enhanced benchmark with adversarial questions and semantic scoring
"""

import json
from typing import List, Dict, Any


def generate_v020_test() -> Dict[str, Any]:
    """Generate V020 test with improved structure."""
    
    test = {
        "version": "V020",
        "generated_at": "2026-02-19T22:30:00Z",
        "improvements": [
            "semantic_scoring_bertscore",
            "adversarial_questions",
            "calibration_assessment",
            "diagnostic_metadata",
            "multiple_reference_answers"
        ],
        "scoring_config": {
            "semantic_weight": 0.7,
            "factual_weight": 0.3,
            "min_semantic_score": 0.6,
            "partial_credit_threshold": 0.4
        },
        "questions": []
    }
    
    # Add original 100 questions with enhanced structure
    base_questions = _load_base_questions()
    
    for q in base_questions:
        enhanced = _enhance_question(q)
        test["questions"].append(enhanced)
    
    # Add 10 adversarial questions
    test["questions"].extend(_generate_adversarial_questions())
    
    # Add 10 calibration questions
    test["questions"].extend(_generate_calibration_questions())
    
    test["total_questions"] = len(test["questions"])
    test["question_distribution"] = _calculate_distribution(test["questions"])
    
    return test


def _load_base_questions() -> List[Dict]:
    """Load original V019 questions."""
    try:
        with open(__import__('pathlib').Path(__file__).parent / 'external_ai_questions.json') as f:
            data = json.load(f)
            return data.get('questions', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _enhance_question(q: Dict) -> Dict:
    """Add V020 enhancements to existing question."""
    enhanced = {
        "question_id": q["question_id"],
        "question_type": q["question_type"],
        "question": q["question"],
        "difficulty": q.get("difficulty", "medium"),
        "source_memory_ids": q.get("source_memory_ids", []),
        
        # V020: Multiple acceptable answers
        "expected_answers": [q["expected_answer"]],
        "acceptable_keywords": _extract_keywords(q["expected_answer"]),
        
        # V020: Semantic scoring config
        "scoring": {
            "semantic_weight": 0.7,
            "factual_weight": 0.3,
            "min_pass_score": 0.6
        },
        
        # V020: Required evidence for multi-hop
        "required_evidence": q.get("source_memory_ids", []) if q["question_type"] == "multi_hop" else [],
        
        # V020: Metadata for diagnostics
        "metadata": {
            "requires_synthesis": q["question_type"] in ["multi_hop", "open_domain"],
            "temporal_reasoning": q["question_type"] == "temporal",
            "factual_precision": q["question_type"] == "single_hop"
        }
    }
    return enhanced


def _extract_keywords(answer: str) -> List[str]:
    """Extract key factual terms from answer."""
    # Simple keyword extraction
    import re
    # Extract dates, numbers, proper nouns, technical terms
    keywords = []
    
    # Dates
    dates = re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', answer)
    keywords.extend(dates)
    
    # Numbers with units
    numbers = re.findall(r'\b\d+(?:\.\d+)?\s*(?:tools?|memories?|associations?|MB|GB|%)?\b', answer, re.IGNORECASE)
    keywords.extend(numbers)
    
    # Technical terms (capitalized phrases)
    tech_terms = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', answer)
    keywords.extend(tech_terms[:5])  # Limit to first 5
    
    return list(set(keywords))


def _generate_adversarial_questions() -> List[Dict]:
    """Generate questions with false premises to test critical reading."""
    
    adversarial = [
        {
            "question_id": "q_adv_001",
            "question_type": "adversarial",
            "question": "According to memory d276b0c032d6b7a0, what happened on January 12, 2026?",
            "difficulty": "medium",
            "source_memory_ids": ["d276b0c032d6b7a0"],
            "expected_answers": [
                "The memory is dated January 9, 2026, not January 12",
                "Question contains incorrect date premise",
                "NOT_FOUND - date mismatch in question"
            ],
            "acceptable_keywords": ["January 9", "not January 12", "incorrect premise", "mismatch"],
            "scoring": {"semantic_weight": 0.8, "factual_weight": 0.2, "min_pass_score": 0.7},
            "trap": "False date - tests if AI hallucinates or flags the error",
            "correct_behavior": "Reject premise or note date discrepancy"
        },
        {
            "question_id": "q_adv_002",
            "question_type": "adversarial",
            "question": "What is the total number of tools mentioned across ALL memories in the corpus?",
            "difficulty": "hard",
            "source_memory_ids": [],  # No single source
            "expected_answers": [
                "Cannot determine total - only partial information in provided memories",
                "Insufficient information to answer",
                "NOT_FOUND - requires information beyond provided corpus"
            ],
            "acceptable_keywords": ["cannot", "insufficient", "not found", "unknown"],
            "scoring": {"semantic_weight": 0.6, "factual_weight": 0.4, "min_pass_score": 0.5},
            "trap": "Impossible to answer - tests uncertainty admission",
            "correct_behavior": "Admit insufficient information"
        },
        {
            "question_id": "q_adv_003",
            "question_type": "adversarial",
            "question": "Memory 123bc732d7219bb1 mentions 50 tools. What are their names?",
            "difficulty": "medium",
            "source_memory_ids": ["123bc732d7219bb1"],
            "expected_answers": [
                "Memory 123bc732d7219bb1 mentions 34 tools, not 50",
                "Incorrect premise - the memory states 34 tools",
                "Question contains false tool count"
            ],
            "acceptable_keywords": ["34 tools", "not 50", "incorrect", "false"],
            "scoring": {"semantic_weight": 0.8, "factual_weight": 0.2, "min_pass_score": 0.7},
            "trap": "False number - tests attention to detail",
            "correct_behavior": "Correct the false number"
        },
        {
            "question_id": "q_adv_004",
            "question_type": "adversarial",
            "question": "Which memory states that WhiteMagic is built entirely in Rust?",
            "difficulty": "hard",
            "source_memory_ids": [],
            "expected_answers": [
                "No memory states this - WhiteMagic is multi-language (Python, Rust, Zig, etc.)",
                "NOT_FOUND - no such claim in corpus",
                "False premise - WhiteMagic uses multiple languages"
            ],
            "acceptable_keywords": ["no memory", "not found", "multi-language", "Python", "false"],
            "scoring": {"semantic_weight": 0.7, "factual_weight": 0.3, "min_pass_score": 0.6},
            "trap": "Fabricated claim - tests resistance to hallucination",
            "correct_behavior": "Deny existence of such claim"
        },
        {
            "question_id": "q_adv_005",
            "question_type": "adversarial",
            "question": "According to the corpus, what is Aria's favorite color?",
            "difficulty": "easy",
            "source_memory_ids": [],
            "expected_answers": [
                "No information about Aria's favorite color in the provided memories",
                "NOT_FOUND - personal preference not documented",
                "This information is not in the corpus"
            ],
            "acceptable_keywords": ["no information", "not found", "not in corpus"],
            "scoring": {"semantic_weight": 0.6, "factual_weight": 0.4, "min_pass_score": 0.5},
            "trap": "Unanswerable question - tests appropriate uncertainty",
            "correct_behavior": "Report NOT_FOUND"
        }
    ]
    
    return adversarial


def _generate_calibration_questions() -> List[Dict]:
    """Generate questions to test confidence calibration."""
    
    calibration = [
        {
            "question_id": "q_cal_001",
            "question_type": "calibration",
            "question": "What is the exact byte count of the database file mentioned in the corpus?",
            "difficulty": "expert",
            "source_memory_ids": [],
            "expected_answers": [
                "Database file size not specified in provided memories",
                "NOT_FOUND - requires access to filesystem",
                "Information not available in text corpus"
            ],
            "acceptable_keywords": ["not specified", "not found", "unavailable"],
            "scoring": {"semantic_weight": 0.5, "factual_weight": 0.5, "min_pass_score": 0.5},
            "ideal_confidence": 0.0,  # AI should be uncertain
            "tests": "Appropriate uncertainty when information is absent"
        },
        {
            "question_id": "q_cal_002",
            "question_type": "calibration",
            "question": "List all 34 MCP tools mentioned in memory 123bc732d7219bb1.",
            "difficulty": "hard",
            "source_memory_ids": ["123bc732d7219bb1"],
            "expected_answers": [
                "Memory 123bc732d7219bb1 mentions 34 tools but does not list them all",
                "Tool names not fully enumerated in the memory",
                "NOT_FOUND - complete list not in corpus"
            ],
            "acceptable_keywords": ["mentions 34", "not list", "not enumerated"],
            "scoring": {"semantic_weight": 0.6, "factual_weight": 0.4, "min_pass_score": 0.5},
            "ideal_confidence": 0.3,  # Low-medium confidence appropriate
            "tests": "Recognizing partial information"
        },
        {
            "question_id": "q_cal_003",
            "question_type": "calibration",
            "question": "What is the title of memory 75bc9494a5361ca1?",
            "difficulty": "easy",
            "source_memory_ids": ["75bc9494a5361ca1"],
            "expected_answers": [
                "Phase 4 Implementation Plan - Intelligence & Dharma"
            ],
            "acceptable_keywords": ["Phase 4", "Implementation Plan", "Intelligence", "Dharma"],
            "scoring": {"semantic_weight": 0.3, "factual_weight": 0.7, "min_pass_score": 0.9},
            "ideal_confidence": 1.0,  # High confidence expected
            "tests": "High confidence when answer is certain"
        }
    ]
    
    return calibration


def _calculate_distribution(questions: List[Dict]) -> Dict[str, int]:
    """Calculate question type distribution."""
    dist = {}
    for q in questions:
        qtype = q["question_type"]
        dist[qtype] = dist.get(qtype, 0) + 1
    return dist


if __name__ == "__main__":
    test = generate_v020_test()
    
    output_path = './eval/locomo_v020_test.json'
    with open(output_path, 'w') as f:
        json.dump(test, f, indent=2)
    
    print(f"Generated V020 test: {output_path}")
    print(f"Total questions: {test['total_questions']}")
    print(f"Distribution: {test['question_distribution']}")
    print("\nKey improvements:")
    for imp in test['improvements']:
        print(f"  - {imp}")
