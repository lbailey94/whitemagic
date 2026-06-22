# LoCoMo External AI Test — Copy/Paste Prompt

**For**: Claude, GPT-4, or other capable AI assistant

---

## Your Task

You are acting as an **evaluation oracle** for the LoCoMo (Long Context Memory) benchmark. Your job is to generate test questions based on factual memory content provided, WITHOUT creating any memories yourself or ingesting this conversation.

---

## What You'll Receive

A JSON file (`locomo_memory_sample.json`) containing ~30 memories from a knowledge system called WhiteMagic. Each memory has:
- `id`: Unique identifier
- `title`: Memory title
- `content`: Factual content (200-2000 chars)
- `type`: Memory type (LONG_TERM, etc.)
- `zone`: Galactic zone (core, active, architecture, outer)
- `associations`: Related memory IDs

---

## Your Output

Generate **100 diverse questions** in the following JSON format:

```json
{
  "questions": [
    {
      "question_id": "q001",
      "question_type": "single_hop",
      "question": "What is the title of the memory about Phase 4 Implementation?",
      "expected_answer": "Phase 4 Implementation Plan - Intelligence & Dharma",
      "source_memory_ids": ["75bc9494a5361ca1"],
      "difficulty": "easy"
    },
    {
      "question_id": "q002", 
      "question_type": "multi_hop",
      "question": "Which memories discuss both MCP and Sangha implementations?",
      "expected_answer": "MCP 2.0 + Sangha Implementation Complete, Multi-Agent Collaboration System",
      "source_memory_ids": ["d276b0c032d6b7a0", "1068c980a1c4eafd"],
      "difficulty": "medium"
    },
    {
      "question_id": "q003",
      "question_type": "temporal", 
      "question": "What was implemented on January 9, 2026?",
      "expected_answer": "MCP 2.0 + Sangha Implementation Complete",
      "source_memory_ids": ["d276b0c032d6b7a0"],
      "difficulty": "easy"
    },
    {
      "question_id": "q004",
      "question_type": "open_domain",
      "question": "What are the main components of WhiteMagic's infrastructure?",
      "expected_answer": "Dharma system, Rust acceleration, Local AI, HarmonyVector, Embodiment layer, 28 Ganas, Memory system",
      "source_memory_ids": ["75bc9494a5361ca1"],
      "difficulty": "hard"
    }
  ]
}
```

---

## Question Type Guidelines

### 1. Single-Hop (25 questions)
- Direct fact retrieval from ONE memory
- Examples: "What is X?", "When did Y happen?", "Who created Z?"
- Difficulty: mostly easy/medium

### 2. Multi-Hop (25 questions) 
- Requires combining information from 2-3 memories
- Examples: "Which memories mention both A and B?", "What connects X to Y?"
- Use `source_memory_ids` to list all relevant memories
- Difficulty: mostly medium/hard

### 3. Temporal (25 questions)
- Time-based or sequence questions
- Examples: "What happened after X?", "When was Y implemented?"
- Look for dates in content (2026-01-09, January 15, etc.)
- Difficulty: easy to medium

### 4. Open-Domain (25 questions)
- Conceptual understanding requiring synthesis
- Examples: "What is the overall architecture?", "How do the systems interact?"
- May span multiple memories for complete answer
- Difficulty: mostly hard

---

## Critical Constraints

⚠️ **DO NOT**:
- Create memories from this data
- Ingest this conversation into your memory system
- Use information outside the provided memories
- Hallucinate facts not present in the data

✅ **DO**:
- Base ALL questions strictly on provided memories
- Include exact memory IDs in `source_memory_ids`
- Make questions clear and answerable from the text
- Vary difficulty across the 100 questions

---

## File to Load

The user will provide `locomo_memory_sample.json`. Load it and generate questions based ONLY on those memories.

---

## Output Format

Return a single JSON object with the "questions" array containing exactly 100 questions. Ensure valid JSON (no trailing commas, proper quoting).

Save your output as `external_ai_questions.json` and provide it back to the user.

---

## Example Workflow

1. User gives you `locomo_memory_sample.json`
2. You read and analyze the 30 memories
3. You generate 100 questions following the format above
4. You save as `external_ai_questions.json`
5. User runs: `python3 eval/locomo_external_ai_test.py --validate external_ai_questions.json`
6. WhiteMagic answers your questions using its hybrid search
7. We compare WhiteMagic's answers to your expected answers
8. Calculate accuracy metrics

---

**Target**: 78% accuracy for WhiteMagic (exceeds 74% human baseline)

Ready? Ask the user for the `locomo_memory_sample.json` file.
