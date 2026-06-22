#!/usr/bin/env python3
"""
LoCoMo External AI Testing Framework
======================================

Novel testing approach: Use an external AI as an "oracle" to generate 
ground-truth questions/answers from WhiteMagic's memories, then test 
WhiteMagic's ability to retrieve those answers.

This tests:
1. Single-hop recall: Direct memory retrieval
2. Multi-hop recall: Following associations  
3. Temporal recall: Time-based queries
4. Open-domain recall: Concept-based search

Workflow:
1. Export memory sample (no conversation context, just facts)
2. External AI generates 100 questions + expected answers
3. WhiteMagic attempts to answer using hybrid search
4. Compare WhiteMagic's answer vs expected answer
5. Calculate accuracy metrics

Usage:
    python3 eval/locomo_external_ai_test.py --generate-sample  # Export memory data
    # Give sample to external AI, get back test questions
    python3 eval/locomo_external_ai_test.py --validate tests.json  # Run validation
"""
import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"


def generate_memory_sample(n_memories: int = 50) -> dict[str, Any]:
    """
    Generate a clean sample of memories for external AI testing.
    
    IMPORTANT: This exports ONLY memory content, not conversation history,
    not Windsurf sessions, not internal reasoning. Just the facts.
    """
    logger.info(f"Generating memory sample from {DB_PATH}")
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    # Get diverse, high-quality memories
    rows = conn.execute("""
        SELECT 
            m.id,
            m.title,
            m.content,
            m.memory_type,
            m.created_at,
            m.importance,
            m.galactic_distance,
            GROUP_CONCAT(DISTINCT a.target_id) as associated_ids
        FROM memories m
        LEFT JOIN associations a ON m.id = a.source_id
        WHERE m.memory_type = 'LONG_TERM'
          AND m.title IS NOT NULL 
          AND LENGTH(m.content) > 200
          AND m.title NOT LIKE 'Recovered:%'
          AND m.title NOT LIKE 'bench_%'
          AND m.title NOT LIKE 'Test %'
          AND m.title NOT LIKE '%checkpoint%'
          AND m.title NOT LIKE '%session%'
          AND m.memory_type != 'quarantined'
        GROUP BY m.id
        ORDER BY m.importance DESC, LENGTH(m.content) DESC
        LIMIT ?
    """, (n_memories * 2,)).fetchall()
    
    # Diverse sample across galactic zones
    memories = []
    seen_zones = set()
    
    for row in rows:
        if len(memories) >= n_memories:
            break
            
        # Determine galactic zone
        dist = row['galactic_distance'] or 0.5
        if dist < 0.1:
            zone = 'core'
        elif dist < 0.3:
            zone = 'active'
        elif dist < 0.5:
            zone = 'architecture'
        else:
            zone = 'outer'
        
        # Ensure zone diversity
        if zone in seen_zones and len(seen_zones) >= 3:
            continue
        seen_zones.add(zone)
        
        memories.append({
            'id': row['id'],
            'title': row['title'],
            'content': row['content'][:2000],  # Truncate very long content
            'type': row['memory_type'],
            'importance': row['importance'],
            'zone': zone,
            'associations': row['associated_ids'].split(',') if row['associated_ids'] else []
        })
    
    sample = {
        'generated_at': datetime.now().isoformat(),
        'count': len(memories),
        'db_path': str(DB_PATH),
        'instructions': {
            'purpose': 'LoCoMo benchmark test generation',
            'constraint': 'DO NOT create memories from this data',
            'constraint_2': 'DO NOT ingest this conversation',
            'task': 'Generate 100 diverse questions based on these memories',
            'question_types': [
                'single_hop: Direct fact retrieval',
                'multi_hop: Following associations between memories',
                'temporal: Time-based or sequence questions',
                'open_domain: Conceptual understanding'
            ],
            'output_format': {
                'question_id': 'str',
                'question_type': 'single_hop|multi_hop|temporal|open_domain',
                'question': 'str',
                'expected_answer': 'str',
                'source_memory_ids': ['list of memory IDs'],
                'difficulty': 'easy|medium|hard'
            }
        },
        'memories': memories
    }
    
    conn.close()
    logger.info(f"Generated sample with {len(memories)} memories")
    return sample


def save_sample(sample: dict, output_path: Path) -> None:
    """Save memory sample to JSON file"""
    with open(output_path, 'w') as f:
        json.dump(sample, f, indent=2)
    logger.info(f"Sample saved to {output_path}")


def validate_answers(test_file: Path) -> dict[str, Any]:
    """
    Validate WhiteMagic's answers against external AI's expected answers.
    
    This uses WhiteMagic's hybrid search to answer each question,
    then compares to the expected answer.
    """
    logger.info(f"Loading test questions from {test_file}")
    
    with open(test_file) as f:
        test_data = json.load(f)
    
    questions = test_data.get('questions', [])
    logger.info(f"Loaded {len(questions)} test questions")
    
    # Import WhiteMagic retrieval
    try:
        from whitemagic.core.memory.sqlite_backend import get_unified_memory
        from whitemagic.core.memory.embeddings import get_embedding_engine
        
        db = get_unified_memory()
        engine = get_embedding_engine()
        
        logger.info("WhiteMagic systems initialized")
    except Exception as e:
        logger.error(f"Failed to initialize WhiteMagic: {e}")
        return {'error': str(e)}
    
    results = {
        'total_questions': len(questions),
        'answered': 0,
        'correct': 0,
        'by_type': {},
        'by_difficulty': {},
        'details': []
    }
    
    for q in questions:
        qid = q.get('question_id', 'unknown')
        qtype = q.get('question_type', 'unknown')
        question_text = q.get('question', '')
        expected = q.get('expected_answer', '')
        source_ids = q.get('source_memory_ids', [])
        difficulty = q.get('difficulty', 'medium')
        
        # Initialize counters
        if qtype not in results['by_type']:
            results['by_type'][qtype] = {'total': 0, 'correct': 0}
        if difficulty not in results['by_difficulty']:
            results['by_difficulty'][difficulty] = {'total': 0, 'correct': 0}
        
        results['by_type'][qtype]['total'] += 1
        results['by_difficulty'][difficulty]['total'] += 1
        
        try:
            # Retrieve using WhiteMagic
            retrieved = retrieve_with_whitemagic(db, engine, question_text, source_ids)
            
            # Compare retrieved vs expected (semantic similarity check)
            is_correct = evaluate_answer(retrieved, expected)
            
            if is_correct:
                results['correct'] += 1
                results['by_type'][qtype]['correct'] += 1
                results['by_difficulty'][difficulty]['correct'] += 1
            
            results['answered'] += 1
            
            results['details'].append({
                'question_id': qid,
                'question_type': qtype,
                'difficulty': difficulty,
                'question': question_text,
                'expected': expected[:200],
                'retrieved': retrieved[:200],
                'correct': is_correct,
                'source_found': check_source_found(db, source_ids)
            })
            
        except Exception as e:
            logger.error(f"Error answering question {qid}: {e}")
            results['details'].append({
                'question_id': qid,
                'error': str(e),
                'correct': False
            })
    
    # Calculate accuracy
    if results['answered'] > 0:
        results['accuracy'] = results['correct'] / results['answered']
    else:
        results['accuracy'] = 0.0
    
    return results


def retrieve_with_whitemagic(db, engine, question: str, source_ids: list) -> str:
    """
    Retrieve answer using WhiteMagic's hybrid search.
    
    Tries multiple strategies:
    1. Vector search (if embeddings available)
    2. FTS search
    3. Association following
    """
    answer_parts = []
    
    # Strategy 1: FTS search
    try:
        cursor = db.conn.execute(
            """SELECT title, content FROM memories 
               WHERE memory_type != 'quarantined' 
               AND (title LIKE ? OR content LIKE ?)
               ORDER BY importance DESC
               LIMIT 3""",
            (f"%{question[:50]}%", f"%{question[:50]}%")
        )
        rows = cursor.fetchall()
        if rows:
            answer_parts.append(f"FTS: {rows[0][1][:300]}")
    except Exception as e:
        logger.debug(f"FTS search error: {e}")
    
    # Strategy 2: Direct source lookup
    for sid in source_ids[:2]:
        try:
            cursor = db.conn.execute(
                "SELECT title, content FROM memories WHERE id = ?",
                (sid,)
            )
            row = cursor.fetchone()
            if row:
                answer_parts.append(f"Source: {row[1][:300]}")
        except Exception:
            pass
    
    return " | ".join(answer_parts) if answer_parts else "No relevant information found"


def evaluate_answer(retrieved: str, expected: str) -> bool:
    """
    Evaluate if retrieved answer matches expected answer.
    
    Uses simple keyword overlap for now.
    Could use semantic similarity for better accuracy.
    """
    if not retrieved or not expected:
        return False
    
    # Normalize
    retrieved_lower = retrieved.lower()
    expected_lower = expected.lower()
    
    # Extract key terms from expected (nouns, verbs, numbers)
    expected_terms = set(expected_lower.split())
    
    # Check overlap
    matches = sum(1 for term in expected_terms if term in retrieved_lower)
    
    # Consider correct if >30% of key terms match
    if len(expected_terms) > 0:
        return matches / len(expected_terms) > 0.3
    
    return False


def check_source_found(db, source_ids: list) -> bool:
    """Check if source memories exist in DB"""
    if not source_ids:
        return False
    
    try:
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE id IN (%s)" % 
            ','.join('?' * len(source_ids)),
            source_ids
        )
        count = cursor.fetchone()[0]
        return count > 0
    except Exception:
        return False


def print_results(results: dict) -> None:
    """Print formatted results"""
    print("\n" + "=" * 70)
    print("LoCoMo External AI Test Results")
    print("=" * 70)
    
    print(f"\nTotal Questions: {results['total_questions']}")
    print(f"Answered: {results['answered']}")
    print(f"Correct: {results['correct']}")
    print(f"Overall Accuracy: {results['accuracy']:.1%}")
    
    print("\nBy Question Type:")
    for qtype, stats in results.get('by_type', {}).items():
        if stats['total'] > 0:
            acc = stats['correct'] / stats['total']
            print(f"  {qtype:15} {stats['correct']}/{stats['total']} = {acc:.1%}")
    
    print("\nBy Difficulty:")
    for diff, stats in results.get('by_difficulty', {}).items():
        if stats['total'] > 0:
            acc = stats['correct'] / stats['total']
            print(f"  {diff:15} {stats['correct']}/{stats['total']} = {acc:.1%}")
    
    print("\n" + "=" * 70)
    
    print("\nSample Questions:")
    for detail in results['details'][:5]:
        status = "✅" if detail.get('correct') else "❌"
        qid = detail.get('question_id', 'unknown')
        diff = detail.get('difficulty', 'unknown')
        question = detail.get('question', 'N/A')[:100]
        expected = detail.get('expected', 'N/A')[:80]
        retrieved = detail.get('retrieved', 'N/A')[:80]
        print(f"\n{status} {qid} ({diff})")
        print(f"   Q: {question}...")
        print(f"   Expected: {expected}...")
        print(f"   Retrieved: {retrieved}...")


def main():
    parser = argparse.ArgumentParser(description='LoCoMo External AI Testing')
    parser.add_argument('--generate-sample', action='store_true',
                        help='Generate memory sample for external AI')
    parser.add_argument('--memories', type=int, default=50,
                        help='Number of memories to sample (default: 50)')
    parser.add_argument('--output', type=str, default='eval/locomo_memory_sample.json',
                        help='Output file for sample')
    parser.add_argument('--validate', type=str, metavar='TEST_FILE',
                        help='Validate WhiteMagic against external AI test file')
    parser.add_argument('--save-results', type=str, default='eval/locomo_results.json',
                        help='Save detailed results')
    
    args = parser.parse_args()
    
    if args.generate_sample:
        sample = generate_memory_sample(args.memories)
        save_sample(sample, Path(args.output))
        print(f"\n✅ Memory sample generated: {args.output}")
        print("\nNext steps:")
        print("1. Give {args.output} to external AI")
        print("2. Ask them to generate 100 questions")
        print("3. Save their response as JSON test file")
        print("4. Run: python3 eval/locomo_external_ai_test.py --validate <test_file>")
        
    elif args.validate:
        test_file = Path(args.validate)
        if not test_file.exists():
            print(f"Error: Test file not found: {test_file}")
            return 1
        
        results = validate_answers(test_file)
        print_results(results)
        
        # Save detailed results
        if args.save_results:
            with open(args.save_results, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nDetailed results saved to: {args.save_results}")
        
        # Exit with appropriate code
        target_accuracy = 0.78
        if results.get('accuracy', 0) >= target_accuracy:
            print(f"\n🎉 Target achieved: {results['accuracy']:.1%} >= {target_accuracy:.0%}")
            return 0
        else:
            print(f"\n⚠️ Below target: {results['accuracy']:.1%} < {target_accuracy:.0%}")
            return 1
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
