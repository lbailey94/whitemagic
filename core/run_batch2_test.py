#!/usr/bin/env python3
"""Test runner for Batch 2 - Rust class exports"""

import sys
sys.path.insert(0, '/media/lucas/SD_CARD/WHITEMAGIC/core')

print("="*60)
print("BATCH 2: Testing Rust Class Exports")
print("="*60)

# Test 1: Import Rust module
print("\n1. Testing whitemagic_rust import...")
try:
    import whitemagic_rust as wmrs
    print("   PASS: whitemagic_rust imported successfully")
except ImportError as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

# Test 2: Check classes exist
print("\n2. Checking exported classes...")
classes_to_check = [
    'PyVectorIndex',
    'PyReasoningEngine', 
    'PyEmergenceDetector',
    'PyCommunityDetector',
    'GraphWalker',
    'Fact',
    'Rule'
]

for cls_name in classes_to_check:
    if hasattr(wmrs, cls_name):
        print(f"   PASS: {cls_name} exists")
    else:
        print(f"   FAIL: {cls_name} NOT FOUND")

# Test 3: Test PyVectorIndex
print("\n3. Testing PyVectorIndex...")
try:
    index = wmrs.PyVectorIndex("cosine")
    idx1 = index.add([1.0, 2.0, 3.0])
    idx2 = index.add([1.1, 2.1, 3.1])
    results = index.search([1.0, 2.0, 3.0], 2)
    assert len(results) == 2
    print(f"   PASS: Vector index works (added {idx1}, {idx2}, found {len(results)} results)")
except Exception as e:
    print(f"   FAIL: {e}")

# Test 4: Test PyReasoningEngine
print("\n4. Testing PyReasoningEngine...")
try:
    engine = wmrs.PyReasoningEngine()
    fact = wmrs.Fact("f1", "is", "sky", "blue", 1.0)
    engine.add_fact(fact)
    rule = wmrs.Rule("r1", ["f1"], "conclusion")
    engine.add_rule(rule)
    count = engine.fact_count()
    print(f"   PASS: Reasoning engine works ({count} facts)")
except Exception as e:
    print(f"   FAIL: {e}")

# Test 5: Test PyEmergenceDetector  
print("\n5. Testing PyEmergenceDetector...")
try:
    detector = wmrs.PyEmergenceDetector(0.5, 5)
    for i in range(10):
        obs = {"metric_a": float(i), "metric_b": float(i * 2)}
        detector.add_observation(obs)
    patterns = detector.detect_patterns()
    count = detector.observation_count()
    print(f"   PASS: Emergence detector works ({count} obs, {len(patterns)} patterns)")
except Exception as e:
    print(f"   FAIL: {e}")

# Test 6: Test PyCommunityDetector
print("\n6. Testing PyCommunityDetector...")
try:
    detector = wmrs.PyCommunityDetector()
    detector.add_edge("a", "b")
    detector.add_edge("b", "c")
    communities = detector.detect_communities(1)
    print(f"   PASS: Community detector works ({len(communities)} communities)")
except Exception as e:
    print(f"   FAIL: {e}")

# Test 7: Test GraphWalker
print("\n7. Testing GraphWalker...")
try:
    walker = wmrs.GraphWalker(5)
    edges = [(1, 2, 0.8), (1, 3, 0.9), (2, 4, 0.7)]
    results = walker.traverse_bfs(1, edges)
    print(f"   PASS: Graph walker works ({len(results)} nodes visited)")
except Exception as e:
    print(f"   FAIL: {e}")

print("\n" + "="*60)
print("BATCH 2 TESTS COMPLETE")
print("="*60)
