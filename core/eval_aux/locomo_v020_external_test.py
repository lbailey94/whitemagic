"""
LoCoMo V020 External AI Test - Enhanced Benchmark
Implements: semantic scoring, adversarial questions, calibration assessment
"""

LOCOMO_V020_PROMPT = """
# LoCoMo V020 Memory Retrieval Benchmark

You are participating in an external validation of a memory retrieval system. 
Your task is to answer questions based ONLY on the provided memory corpus.

## CRITICAL RULES

1. **NO EXTERNAL KNOWLEDGE**: Do not use your training data. Only use the provided memories.
2. **NO WEB SEARCH**: Do not search the internet or external databases.
3. **NO TOOLS**: Do not use any tools, calculators, or APIs.
4. **ISOLATED ENVIRONMENT**: Pretend you are in a sandbox with only the provided memories.

## QUESTION TYPES

- **single_hop**: Direct lookup (e.g., "What is X's value?")
- **multi_hop**: Cross-memory connections requiring synthesis
- **temporal**: Time-based queries (dates, sequences, "when")
- **open_domain**: Broad questions requiring synthesis across multiple memories
- **adversarial**: Questions with false premises - TESTS CRITICAL READING
  - May contain incorrect dates, wrong numbers, fabricated claims
  - Correct response: Flag the error, reject premise, or note discrepancy
- **calibration**: Questions testing appropriate uncertainty
  - Some have no answer in corpus - admit "NOT_FOUND" with low confidence
  - Others have clear answers - answer with high confidence

## ANSWER FORMAT

Respond with a JSON array of answer objects:

```json
[
  {
    "question_id": "q001",
    "answer": "Your answer here",
    "confidence": 0.95,
    "source_memory_ids": ["memory-id-1", "memory-id-2"],
    "reasoning": "Brief explanation of how you found the answer"
  }
]
```

Field descriptions:
- `question_id`: Match the question ID exactly
- `answer`: Your concise answer (can be "NOT_FOUND" if truly unavailable)
- `confidence`: 0.0-1.0 score (1.0 = certain, 0.0 = pure guess)
- `source_memory_ids`: Array of memory IDs you used (empty if guessing)
- `reasoning`: 1-2 sentence explanation

## ADVERSARIAL QUESTION HANDLING

Some questions contain **false premises** (wrong dates, incorrect facts). Examples:
- "What happened on January 12, 2026?" when memory is from January 9
- "Memory X says Y" when it actually says Z

**Correct behavior**: 
- Do NOT hallucinate an answer to fit the false premise
- Do NOT ignore the error and answer as if premise were true
- DO flag the discrepancy: "Memory is dated January 9, not January 12"
- DO reject the premise if clearly wrong

## CALIBRATION GUIDANCE

Your confidence should match your actual certainty:
- 0.9-1.0: Exact fact from memory (title, date, number)
- 0.7-0.9: Strong inference from clear evidence
- 0.4-0.7: Partial information, educated guess
- 0.0-0.3: Information not in corpus, pure speculation

**Good calibration examples**:
- "What is the title of memory X?" → confidence 1.0 (exact match in text)
- "What are all 34 MCP tools?" → confidence 0.3 (tools mentioned but not listed)
- "What is Aria's favorite color?" → confidence 0.0 (not in corpus)

## PROVIDED MEMORY CORPUS

{memory_corpus}

## QUESTIONS

{questions}

## SAVE INSTRUCTIONS

After completing the test, save your JSON output to:
**`./eval/external_ai_answers_<TIMESTAMP>.json`**

Filename format: `external_ai_answers_YYYYMMDD_HHMMSS.json`
Example: `external_ai_answers_20260219_173245.json`

Use your current system time when you finish answering all questions.

## FINAL REMINDER

Return ONLY the JSON array - no markdown code blocks, no extra text.
If you cannot find the answer, set confidence to 0.0 and answer "NOT_FOUND".
Watch for adversarial questions with false premises - flag them appropriately.
"""


V020_TEST_CONFIG = {
    "version": "V020",
    "improvements": [
        "semantic_scoring_bertscore",  # Replaces exact-match
        "adversarial_questions",       # Tests critical reading
        "calibration_assessment",      # Confidence vs accuracy
        "diagnostic_metadata",         # Retrieval depth, reasoning
        "multiple_reference_answers" # Accepts paraphrases
    ],
    "expected_advancements": [
        "More nuanced than binary correct/incorrect",
        "Reveals reasoning failures, not just wrong answers",
        "Tests what AI *shouldn't* retrieve (adversarial)",
        "Measures appropriate uncertainty (calibration)",
        "Better alignment with human judgment"
    ],
    "scoring": {
        "semantic_weight": 0.7,  # BERTScore similarity
        "factual_weight": 0.3,   # Keyword/concept coverage
        "adversarial_bonus": 0.1,  # Extra credit for catching traps
        "calibration_penalty": 0.05  # Penalty for overconfidence
    }
}


def generate_v020_prompt(questions_file: str, memory_sample_file: str) -> str:
    """Generate the complete V020 prompt for an external AI."""
    import json
    
    with open(questions_file) as f:
        questions_data = json.load(f)
    
    with open(memory_sample_file) as f:
        memories = json.load(f)
    
    # Format questions with adversarial warnings
    questions_formatted = []
    for q in questions_data.get('questions', []):
        qtype = q.get('question_type', 'unknown')
        warning = ""
        if qtype == 'adversarial':
            warning = " [ADVERSARIAL - Check for false premise]"
        elif qtype == 'calibration':
            warning = " [CALIBRATION - Assess your uncertainty]"
        
        questions_formatted.append(f"""### {q['question_id']} ({qtype}){warning}
{q['question']}""")
    
    # Format memories (subset for external AI)
    memory_subset = memories[:100] if len(memories) > 100 else memories
    
    # Use string replacement instead of format to avoid JSON brace conflicts
    prompt = LOCOMO_V020_PROMPT.replace('{memory_corpus}', json.dumps(memory_subset, indent=2))
    prompt = prompt.replace('{questions}', '\n'.join(questions_formatted))
    
    return prompt


if __name__ == "__main__":
    # Generate the prompt
    prompt = generate_v020_prompt(
        questions_file='./eval/locomo_v020_test.json',
        memory_sample_file='./eval/locomo_memory_sample.json'
    )
    
    # Save to file
    with open('./eval/locomo_v020_external_ai_prompt.txt', 'w') as f:
        f.write(prompt)
    
    print("Generated V020 external AI prompt")
    print(f"Prompt length: {len(prompt)} characters")
    print("\nKey improvements over V019:")
    for imp in V020_TEST_CONFIG['improvements']:
        print(f"  - {imp}")
