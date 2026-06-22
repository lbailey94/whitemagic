"""
LLM Meta-Harness Benchmark Suite
=================================
Comprehensive benchmarking of local LLM capabilities with WhiteMagic enhancements.

Tests:
1. Baseline performance (direct inference)
2. Memory-grounded RAG
3. Chain-of-thought reasoning
4. Self-correction loops
5. Ensemble voting
6. Pattern injection
7. Dharma alignment
8. Full-stack enhancement

Measures:
- Accuracy (vs. ground truth)
- Latency (ms)
- Token efficiency
- Improvement over baseline
- Confidence calibration
"""

import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from whitemagic.inference.llm_meta_harness import (
    get_meta_harness,
    EnhancementMode,
)


class LLMMetaBenchmark:
    """Benchmark suite for LLM meta-harness."""
    
    def __init__(self, model_name: str = "qwen2.5-coder:1.5b"):
        self.model_name = model_name
        self.harness = get_meta_harness(model_name)
        self.results = []
        
    def get_test_cases(self) -> List[Dict[str, Any]]:
        """Get comprehensive test cases across different domains."""
        return [
            # === Code Understanding ===
            {
                "category": "code_understanding",
                "query": "What does the @property decorator do in Python?",
                "ground_truth": "property decorator converts a method into a getter for a read-only attribute",
                "keywords": ["property", "getter", "method", "attribute"],
            },
            {
                "category": "code_understanding",
                "query": "Explain async/await in Python",
                "ground_truth": "async/await enables asynchronous programming with coroutines",
                "keywords": ["async", "await", "coroutine", "asynchronous"],
            },
            
            # === Code Generation ===
            {
                "category": "code_generation",
                "query": "Write a Python function to calculate fibonacci numbers",
                "ground_truth": "def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)",
                "keywords": ["def", "fib", "return", "recursion"],
            },
            {
                "category": "code_generation",
                "query": "Write a function to reverse a string in Python",
                "ground_truth": "def reverse(s): return s[::-1]",
                "keywords": ["def", "reverse", "return", "slice"],
            },
            
            # === Debugging ===
            {
                "category": "debugging",
                "query": "Why does this fail: x = [1,2,3]; print(x[3])",
                "ground_truth": "IndexError because list index out of range, x[3] doesn't exist",
                "keywords": ["IndexError", "out of range", "index", "3"],
            },
            {
                "category": "debugging",
                "query": "What's wrong with: def add(a, b) return a + b",
                "ground_truth": "SyntaxError missing colon after function definition",
                "keywords": ["SyntaxError", "colon", "missing", ":"],
            },
            
            # === Architecture ===
            {
                "category": "architecture",
                "query": "What is the difference between composition and inheritance?",
                "ground_truth": "Composition uses has-a relationships, inheritance uses is-a relationships",
                "keywords": ["composition", "inheritance", "has-a", "is-a"],
            },
            {
                "category": "architecture",
                "query": "Explain the singleton pattern",
                "ground_truth": "Singleton ensures a class has only one instance with global access",
                "keywords": ["singleton", "one instance", "global", "pattern"],
            },
            
            # === WhiteMagic Specific ===
            {
                "category": "whitemagic",
                "query": "What are the 28 Ganas in WhiteMagic?",
                "ground_truth": "28 Ganas are polymorphic tool families aligned with Lunar Mansions",
                "keywords": ["28", "Ganas", "Lunar Mansions", "tools"],
            },
            {
                "category": "whitemagic",
                "query": "What is Dharma in WhiteMagic?",
                "ground_truth": "Dharma is the ethical framework ensuring consent and harmony",
                "keywords": ["Dharma", "ethical", "consent", "harmony"],
            },
            
            # === Reasoning ===
            {
                "category": "reasoning",
                "query": "If all A are B, and all B are C, are all A also C?",
                "ground_truth": "Yes, by transitive property all A are C",
                "keywords": ["yes", "transitive", "logic", "syllogism"],
            },
            {
                "category": "reasoning",
                "query": "What comes next: 2, 4, 8, 16, ?",
                "ground_truth": "32, the pattern is powers of 2",
                "keywords": ["32", "powers", "double", "2"],
            },
            
            # === Factual Knowledge ===
            {
                "category": "factual",
                "query": "What is the capital of France?",
                "ground_truth": "Paris",
                "keywords": ["Paris"],
            },
            {
                "category": "factual",
                "query": "How many days are in a leap year?",
                "ground_truth": "366 days",
                "keywords": ["366"],
            },
            
            # === Creative ===
            {
                "category": "creative",
                "query": "Write a haiku about coding",
                "ground_truth": "Three lines, 5-7-5 syllables about programming",
                "keywords": ["code", "program", "three lines"],
            },
            {
                "category": "creative",
                "query": "Suggest a name for a memory management system",
                "ground_truth": "Creative name related to memory or cognition",
                "keywords": ["memory", "name"],
            },
        ]
    
    def score_answer(self, answer: str, ground_truth: str, keywords: List[str]) -> float:
        """
        Score answer quality (0.0 to 1.0).
        
        Simple heuristic:
        - 0.5 base if answer exists
        - +0.1 for each keyword found (up to 0.5)
        """
        if not answer or len(answer) < 5:
            return 0.0
        
        score = 0.5  # Base score for providing an answer
        
        answer_lower = answer.lower()
        keyword_matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
        keyword_score = min(0.5, keyword_matches * 0.1)
        
        return min(1.0, score + keyword_score)
    
    async def run_single_test(
        self,
        test_case: Dict[str, Any],
        mode: EnhancementMode,
    ) -> Dict[str, Any]:
        """Run a single test case with specified enhancement mode."""
        query = test_case["query"]
        
        start_time = time.time()
        response = await self.harness.enhance(query, mode=mode, max_tokens=256)
        latency_ms = (time.time() - start_time) * 1000
        
        # Score the answer
        accuracy = self.score_answer(
            response.answer,
            test_case["ground_truth"],
            test_case["keywords"],
        )
        
        return {
            "category": test_case["category"],
            "query": query,
            "mode": mode.value,
            "answer": response.answer,
            "accuracy": accuracy,
            "confidence": response.confidence,
            "latency_ms": latency_ms,
            "tokens_used": response.tokens_used,
            "enhancement_details": response.enhancement_details,
        }
    
    async def run_benchmark(self, modes: List[EnhancementMode] = None) -> Dict[str, Any]:
        """
        Run full benchmark across all test cases and modes.
        
        Args:
            modes: List of enhancement modes to test (default: all)
            
        Returns:
            Comprehensive benchmark results
        """
        if modes is None:
            modes = list(EnhancementMode)
        
        test_cases = self.get_test_cases()
        
        print(f"\n{'='*80}")
        print("LLM Meta-Harness Benchmark")
        print(f"Model: {self.model_name}")
        print(f"Test Cases: {len(test_cases)}")
        print(f"Enhancement Modes: {len(modes)}")
        print(f"{'='*80}\n")
        
        all_results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] {test_case['category']}: {test_case['query'][:60]}...")
            
            for mode in modes:
                try:
                    result = await self.run_single_test(test_case, mode)
                    all_results.append(result)
                    
                    print(f"  {mode.value:20s} | Accuracy: {result['accuracy']:.2f} | "
                          f"Latency: {result['latency_ms']:6.1f}ms | "
                          f"Tokens: {result['tokens_used']:3d}")
                    
                except Exception as e:
                    print(f"  {mode.value:20s} | ERROR: {e}")
                    all_results.append({
                        "category": test_case["category"],
                        "query": test_case["query"],
                        "mode": mode.value,
                        "error": str(e),
                        "accuracy": 0.0,
                        "latency_ms": 0.0,
                        "tokens_used": 0,
                    })
            
            print()
        
        # Aggregate results
        aggregated = self._aggregate_results(all_results)
        
        return {
            "model": self.model_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_cases": len(test_cases),
            "modes_tested": [m.value for m in modes],
            "individual_results": all_results,
            "aggregated": aggregated,
        }
    
    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results by mode and category."""
        by_mode = {}
        by_category = {}
        
        for result in results:
            mode = result["mode"]
            category = result["category"]
            
            # By mode
            if mode not in by_mode:
                by_mode[mode] = {
                    "count": 0,
                    "total_accuracy": 0.0,
                    "total_latency_ms": 0.0,
                    "total_tokens": 0,
                }
            
            by_mode[mode]["count"] += 1
            by_mode[mode]["total_accuracy"] += result.get("accuracy", 0.0)
            by_mode[mode]["total_latency_ms"] += result.get("latency_ms", 0.0)
            by_mode[mode]["total_tokens"] += result.get("tokens_used", 0)
            
            # By category
            if category not in by_category:
                by_category[category] = {
                    "count": 0,
                    "total_accuracy": 0.0,
                }
            
            by_category[category]["count"] += 1
            by_category[category]["total_accuracy"] += result.get("accuracy", 0.0)
        
        # Calculate averages
        for mode, stats in by_mode.items():
            count = stats["count"]
            if count > 0:
                stats["avg_accuracy"] = stats["total_accuracy"] / count
                stats["avg_latency_ms"] = stats["total_latency_ms"] / count
                stats["avg_tokens"] = stats["total_tokens"] / count
        
        for category, stats in by_category.items():
            count = stats["count"]
            if count > 0:
                stats["avg_accuracy"] = stats["total_accuracy"] / count
        
        return {
            "by_mode": by_mode,
            "by_category": by_category,
        }
    
    def print_summary(self, results: Dict[str, Any]):
        """Print human-readable summary of results."""
        print(f"\n{'='*80}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*80}\n")
        
        print(f"Model: {results['model']}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Test Cases: {results['test_cases']}")
        print()
        
        # By mode
        print("Results by Enhancement Mode:")
        print(f"{'Mode':<25} {'Accuracy':>10} {'Latency (ms)':>15} {'Tokens':>10}")
        print("-" * 80)
        
        by_mode = results["aggregated"]["by_mode"]
        
        # Sort by accuracy descending
        sorted_modes = sorted(
            by_mode.items(),
            key=lambda x: x[1].get("avg_accuracy", 0.0),
            reverse=True,
        )
        
        for mode, stats in sorted_modes:
            print(f"{mode:<25} "
                  f"{stats.get('avg_accuracy', 0.0):>9.1%} "
                  f"{stats.get('avg_latency_ms', 0.0):>14.1f} "
                  f"{stats.get('avg_tokens', 0):>10.0f}")
        
        print()
        
        # By category
        print("Results by Category:")
        print(f"{'Category':<25} {'Accuracy':>10}")
        print("-" * 40)
        
        by_category = results["aggregated"]["by_category"]
        sorted_categories = sorted(
            by_category.items(),
            key=lambda x: x[1].get("avg_accuracy", 0.0),
            reverse=True,
        )
        
        for category, stats in sorted_categories:
            print(f"{category:<25} {stats.get('avg_accuracy', 0.0):>9.1%}")
        
        print()
        
        # Calculate improvement over baseline
        if "direct" in by_mode and "full_stack" in by_mode:
            baseline_acc = by_mode["direct"].get("avg_accuracy", 0.0)
            fullstack_acc = by_mode["full_stack"].get("avg_accuracy", 0.0)
            improvement = ((fullstack_acc - baseline_acc) / baseline_acc * 100) if baseline_acc > 0 else 0
            
            print("Enhancement Impact:")
            print(f"  Baseline (direct):     {baseline_acc:.1%}")
            print(f"  Full-stack enhanced:   {fullstack_acc:.1%}")
            print(f"  Improvement:           {improvement:+.1f}%")
            print()


async def main():
    """Run benchmark and save results."""
    import sys
    
    model_name = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:1.5b"
    
    benchmark = LLMMetaBenchmark(model_name=model_name)
    
    if not benchmark.harness.is_available:
        print(f"ERROR: Model {model_name} not available")
        print("Make sure Ollama is running: ollama serve")
        print(f"And model is pulled: ollama pull {model_name}")
        return
    
    # Run benchmark
    results = await benchmark.run_benchmark()
    
    # Print summary
    benchmark.print_summary(results)
    
    # Save results
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"llm_meta_benchmark_{timestamp}.json"
    
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {json_path}")
    
    # Generate markdown report
    md_path = output_dir / f"llm_meta_benchmark_{timestamp}.md"
    generate_markdown_report(results, md_path)
    print(f"Markdown report: {md_path}")


def generate_markdown_report(results: Dict[str, Any], output_path: Path):
    """Generate markdown report from results."""
    lines = [
        "# LLM Meta-Harness Benchmark Report",
        "",
        f"**Model**: {results['model']}  ",
        f"**Timestamp**: {results['timestamp']}  ",
        f"**Test Cases**: {results['test_cases']}  ",
        "",
        "---",
        "",
        "## Summary by Enhancement Mode",
        "",
        "| Mode | Accuracy | Latency (ms) | Tokens | Tests |",
        "|------|----------|--------------|--------|-------|",
    ]
    
    by_mode = results["aggregated"]["by_mode"]
    sorted_modes = sorted(
        by_mode.items(),
        key=lambda x: x[1].get("avg_accuracy", 0.0),
        reverse=True,
    )
    
    for mode, stats in sorted_modes:
        lines.append(
            f"| {mode} | "
            f"{stats.get('avg_accuracy', 0.0):.1%} | "
            f"{stats.get('avg_latency_ms', 0.0):.1f} | "
            f"{stats.get('avg_tokens', 0):.0f} | "
            f"{stats.get('count', 0)} |"
        )
    
    lines.extend([
        "",
        "## Summary by Category",
        "",
        "| Category | Accuracy | Tests |",
        "|----------|----------|-------|",
    ])
    
    by_category = results["aggregated"]["by_category"]
    sorted_categories = sorted(
        by_category.items(),
        key=lambda x: x[1].get("avg_accuracy", 0.0),
        reverse=True,
    )
    
    for category, stats in sorted_categories:
        lines.append(
            f"| {category} | "
            f"{stats.get('avg_accuracy', 0.0):.1%} | "
            f"{stats.get('count', 0)} |"
        )
    
    # Enhancement impact
    if "direct" in by_mode and "full_stack" in by_mode:
        baseline_acc = by_mode["direct"].get("avg_accuracy", 0.0)
        fullstack_acc = by_mode["full_stack"].get("avg_accuracy", 0.0)
        improvement = ((fullstack_acc - baseline_acc) / baseline_acc * 100) if baseline_acc > 0 else 0
        
        lines.extend([
            "",
            "## Enhancement Impact",
            "",
            f"- **Baseline (direct)**: {baseline_acc:.1%}",
            f"- **Full-stack enhanced**: {fullstack_acc:.1%}",
            f"- **Improvement**: {improvement:+.1f}%",
            "",
        ])
    
    lines.append("---")
    lines.append("")
    lines.append("*Generated by WhiteMagic LLM Meta-Harness Benchmark Suite*")
    
    output_path.write_text("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
