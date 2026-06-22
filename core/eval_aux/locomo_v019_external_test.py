"""LoCoMo V019 External AI Test - Updated Benchmark
Incorporates: hybrid fusion, quarantine deduplication, learned reranking
"""

LOCOMO_V019_PROMPT = """
# LoCoMo V019 Memory Retrieval Benchmark

You are participating in an external validation of a memory retrieval system. 
Your task is to answer questions based ONLY on the provided memory corpus.

## CRITICAL RULES

1. **NO EXTERNAL KNOWLEDGE**: Do not use your training data. Only use the provided memories.
2. **NO WEB SEARCH**: Do not search the internet or external databases.
3. **NO TOOLS**: Do not use any tools, calculators, or APIs.
4. **ISOLATED ENVIRONMENT**: Pretend you are in a sandbox with only the provided memories.

## QUESTION TYPES

- **single_hop**: Direct lookup (e.g., "What is X's value?")
- **multi_hop**: Connect information across multiple memories
- **temporal**: Time-based queries (dates, sequences, "when")
- **open_domain**: Broad questions requiring synthesis
- **adversarial**: Trick questions with negation or false premises

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
- `answer`: Your concise answer
- `confidence`: 0.0-1.0 score (1.0 = certain, 0.0 = guessing)
- `source_memory_ids`: Array of memory IDs you used (can be empty if unsure)
- `reasoning**: Brief explanation (1-2 sentences)

## PROVIDED MEMORY CORPUS

{memory_corpus}

## QUESTIONS

{questions}

## OUTPUT INSTRUCTIONS

1. Answer ALL questions in the JSON format above
2. Use ONLY the provided memories - no external knowledge
3. If you cannot find the answer, set confidence to 0.0 and answer "NOT_FOUND"
4. Include all relevant source_memory_ids that contributed to your answer
5. Return ONLY the JSON array - no markdown code blocks, no extra text

## SAVE INSTRUCTIONS

After completing the test, save your JSON output to:
**`./eval/external_ai_answers_<TIMESTAMP>.json`**

Filename format: `external_ai_answers_YYYYMMDD_HHMMSS.json`
Example: `external_ai_answers_20260219_173245.json`

Use your current system time when you finish answering all questions.
"""

# Updated test configuration reflecting V019 improvements
V019_TEST_CONFIG = {
    "version": "V019",
    "improvements": [
        "hybrid_fusion_rrf",
        "quarantine_deduplication", 
        "learned_reranking_pipeline",
        "query_intent_classification",
        "confidence_thresholding"
    ],
    "expected_score_bump": "+12% (78.3% → 90%+)",
    "question_distribution": {
        "single_hop": 25,
        "multi_hop": 25,
        "temporal": 25,
        "open_domain": 15,
        "adversarial": 10
    }
}


def generate_external_ai_prompt(questions_file: str, memory_sample_file: str) -> str:
    """Generate the complete prompt for an external AI."""
    import json
    
    with open(questions_file) as f:
        questions_data = json.load(f)
    
    with open(memory_sample_file) as f:
        memories = json.load(f)
    
    # Format questions
    questions_formatted = []
    for q in questions_data.get('questions', []):
        questions_formatted.append(f"""### {q['question_id']} ({q['question_type']})
{q['question']}""")
    
    # Format memories (subset for external AI)
    memory_subset = memories[:100] if len(memories) > 100 else memories
    
    # Use string replacement instead of format to avoid JSON brace conflicts
    prompt = LOCOMO_V019_PROMPT.replace('{memory_corpus}', json.dumps(memory_subset, indent=2))
    prompt = prompt.replace('{questions}', '\n'.join(questions_formatted))
    
    return prompt


if __name__ == "__main__":
    # Generate the prompt
    prompt = generate_external_ai_prompt(
        questions_file='./eval/external_ai_questions.json',
        memory_sample_file='./eval/locomo_memory_sample.json'
    )
    
    # Save to file
    with open('./eval/locomo_v019_external_ai_prompt.txt', 'w') as f:
        f.write(prompt)
    
    print("Generated external AI prompt: eval/locomo_v019_external_ai_prompt.txt")
    print(f"Prompt length: {len(prompt)} characters")
