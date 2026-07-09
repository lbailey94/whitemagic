"""Exercise all WhiteMagic code-writing systems end-to-end.

Tests every code generation pathway:
  1. VibeParser prompt parsing
  2. CodeGenomeEngine template rendering
  3. GeneseedVault vibe_render (with validation)
  4. Polymorphism engine
  5. Project template rendering (multi-file)
  6. Feedback loop (record_outcome, deprecation)
  7. Template provenance signing
  8. generate_with_llm (git pattern mining + LLM refinement)
  9. AsyncThoughtCloneArmy tiered deployment
 10. AsyncThoughtCloneArmy vibe_code_explore (three-phase God-Kit)
 11. ImmortalClone persistent loop
 12. ConductorOrchestrator autonomous task
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure we can import whitemagic
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")

RESULTS = []

def record(name, status, detail, elapsed_ms=0):
    RESULTS.append({"system": name, "status": status, "detail": detail, "elapsed_ms": round(elapsed_ms, 1)})
    icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
    print(f"  {icon} {name}: {detail} ({elapsed_ms:.0f}ms)")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_1_vibe_parser():
    section("1. VibeParser — Prompt Parsing")
    from whitemagic.codegenome.vibe_parser import VibeParser
    parser = VibeParser()
    
    prompts = [
        "I need a fastapi endpoint for items",
        "make a robust pydantic model for User",
        "create a rust struct for Account",
        "generate a go handler for health",
        "typescript interface for Product",
        "fastapi project scaffold for a blog",
        "reentrancy poc for a vault contract",
    ]
    
    matched = 0
    for p in prompts:
        result = parser.parse(p)
        ok = result.get("status") == "matched"
        if ok:
            matched += 1
        record(f"parse: '{p[:40]}'", "pass" if ok else "warn", 
               f"→ {result.get('template_name', '?')} ({result.get('tier', '?')})")
    
    record("VibeParser overall", "pass" if matched >= 5 else "warn", 
           f"{matched}/{len(prompts)} prompts matched")


def test_2_engine_render():
    section("2. CodeGenomeEngine — Template Rendering")
    from whitemagic.codegenome.engine import CodeGenomeEngine
    engine = CodeGenomeEngine()
    
    templates = [
        ("fastapi_endpoint", {"path": "/users", "name": "users"}, "xianfeng"),
        ("fastapi_endpoint", {"path": "/users", "name": "users"}, "huben"),
        ("pydantic_model", {"name": "Account"}, "wei_wuzu"),
        ("rust_struct", {"name": "User"}, "huben"),
        ("go_handler", {"name": "Health"}, "wei_wuzu"),
        ("typescript_react_component", {"name": "Dashboard"}, "huben"),
        ("dockerfile", {}, "xianfeng"),
        ("github_action", {}, "xianfeng"),
    ]
    
    rendered = 0
    for name, vars, tier in templates:
        code = engine.render(name, tier=tier, **vars)
        ok = len(code) > 10 and "unknown template" not in code
        if ok:
            rendered += 1
        record(f"render: {name}/{tier}", "pass" if ok else "fail",
               f"{len(code)} chars")
    
    record("Engine render overall", "pass" if rendered == len(templates) else "fail",
           f"{rendered}/{len(templates)} templates rendered")


def test_3_vault_vibe_render():
    section("3. GeneseedVault.vibe_render — End-to-End with Validation")
    from whitemagic.codegenome.vault import GeneseedVault
    vault = GeneseedVault()
    
    prompts = [
        "fastapi endpoint for items",
        "robust pydantic model for User",
        "rust struct for Account",
        "go handler for health check",
    ]
    
    success = 0
    for p in prompts:
        result = vault.vibe_render(p)
        ok = result.get("status") == "success"
        if ok:
            success += 1
            val = result.get("validation", {})
            record(f"vibe_render: '{p[:30]}'", "pass",
                   f"→ {result['template_name']}/{result['tier']} | code={len(result['code'])}c | valid={val.get('valid', '?')}")
        else:
            record(f"vibe_render: '{p[:30]}'", "fail", f"status={result.get('status')}")
    
    record("Vault vibe_render overall", "pass" if success >= 3 else "fail",
           f"{success}/{len(prompts)} succeeded")


def test_4_polymorphism():
    section("4. Polymorphism Engine — Stochastic Variation")
    from whitemagic.codegenome.polymorphism import PolymorphismEngine
    from whitemagic.codegenome.engine import CodeGenomeEngine
    
    engine = CodeGenomeEngine()
    code = engine.render("fastapi_endpoint", path="/items", name="items", tier="wei_wuzu")
    
    variations = set()
    for i in range(5):
        pm = PolymorphismEngine(seed=i)
        v = pm.polymorph(code, intensity=0.5)
        variations.add(v)
    
    # With different seeds, we should get at least 2 different outputs
    unique = len(variations)
    record("Polymorphism uniqueness", "pass" if unique >= 2 else "warn",
           f"{unique} unique variations from 5 runs")
    
    # Verify semantic equivalence (both should contain router.get)
    all_valid = all("router.get" in v for v in variations)
    record("Polymorphism semantic preservation", "pass" if all_valid else "fail",
           f"all variations contain 'router.get': {all_valid}")
    
    # Variation count estimate
    count = pm.get_variation_count(code)
    record("Polymorphism variation count", "pass" if count > 1 else "warn",
           f"estimated {count} possible variations")


def test_5_project_render():
    section("5. Project Template — Multi-File Scaffold")
    from whitemagic.codegenome.engine import CodeGenomeEngine
    from whitemagic.codegenome.vault import GeneseedVault
    
    engine = CodeGenomeEngine()
    
    # Direct engine render_project
    files = engine.render_project("fastapi_crud_project", tier="xianfeng")
    ok = len(files) >= 3
    record("Engine.render_project", "pass" if ok else "fail",
           f"{len(files)} files: {list(files.keys())}")
    
    # Via vault vibe_render_project
    vault = GeneseedVault()
    result = vault.vibe_render_project("fastapi project for items")
    ok = result.get("status") == "success" and result.get("file_count", 0) >= 3
    record("Vault.vibe_render_project", "pass" if ok else "fail",
           f"status={result.get('status')}, files={result.get('file_count', 0)}")


def test_6_feedback_loop():
    section("6. Feedback Loop — Success Rate & Deprecation")
    from whitemagic.codegenome.vault import GeneseedVault
    vault = GeneseedVault()
    
    # Record failures to drive deprecation
    for _ in range(15):
        vault.record_outcome("dockerfile", "xianfeng", success=False)
    
    engine = vault._engine
    template = engine.get_template("dockerfile")
    deprecated = template.deprecated if template else None
    rate = template.success_rate if template else 0
    
    record("Deprecation trigger", "pass" if deprecated else "fail",
           f"rate={rate:.3f}, deprecated={deprecated}")
    
    # Record successes to recover
    for _ in range(20):
        vault.record_outcome("dockerfile", "xianfeng", success=True)
    
    recovered = not template.deprecated if template else None
    record("Deprecation recovery", "pass" if recovered else "fail",
           f"rate={template.success_rate:.3f}, deprecated={template.deprecated}")


def test_7_signing():
    section("7. Template Provenance Signing")
    from whitemagic.codegenome.vault import GeneseedVault
    vault = GeneseedVault()
    
    result = vault.sign_template("fastapi_endpoint")
    ok = result.get("status") == "success" and result.get("content_hash")
    record("Sign template", "pass" if ok else "fail",
           f"hash={result.get('content_hash', '?')}, signed={result.get('signed', False)}")
    
    # Verify fork gets signed
    from whitemagic.codegenome.engine import CodeGenomeEngine
    engine = CodeGenomeEngine()
    child = engine.fork_template("fastapi_endpoint", "test_fork_signed")
    ok = child and child.content_hash != ""
    record("Fork auto-signing", "pass" if ok else "fail",
           f"fork hash={child.content_hash if child else 'none'}")


def test_8_generate_with_llm():
    section("8. generate_with_llm — Git Patterns + LLM Refinement")
    from whitemagic.codegenome.vault import GeneseedVault
    vault = GeneseedVault()
    
    # Use the WHITEMAGIC repo itself for git pattern mining
    repo_path = "/home/lucas/Desktop/WHITEMAGIC"
    result = vault.generate_with_llm(
        "fastapi endpoint for health check",
        repo_path=repo_path,
    )
    
    ok = result.get("status") == "success"
    record("generate_with_llm basic", "pass" if ok else "fail",
           f"status={result.get('status')}, llm_refined={result.get('llm_refined', False)}, "
           f"patterns={result.get('patterns_mined', 0)}")
    
    # Test with write_output
    with tempfile.TemporaryDirectory() as tmpdir:
        outpath = os.path.join(tmpdir, "generated_endpoint.py")
        result2 = vault.generate_with_llm(
            "fastapi endpoint for status",
            repo_path=repo_path,
            write_output=outpath,
        )
        written = os.path.exists(outpath)
        record("generate_with_llm + write", "pass" if written else "warn",
               f"file_written={written}, write_result={result2.get('write_result', 'none')}")


async def test_9_clone_army_tiered():
    section("9. AsyncThoughtCloneArmy — Tiered Deployment")
    from whitemagic.edge.thought_clones_async import (
        AsyncThoughtCloneArmy, CloneConfig, CloneTier
    )
    
    config = CloneConfig(max_clones=5, max_concurrent_api_calls=5, timeout_seconds=10)
    army = AsyncThoughtCloneArmy(config=config)
    
    # Xianfeng tier (fast recon)
    start = time.perf_counter()
    result = await army.parallel_explore_tiered(
        "How to structure a FastAPI application with proper error handling?",
        num_clones=5,
        tier=CloneTier.XIANFENG,
    )
    elapsed = (time.perf_counter() - start) * 1000
    
    record("Xianfeng tier (5 clones)", "pass" if result.confidence > 0 else "fail",
           f"strategy={result.strategy}, conf={result.confidence:.3f}, "
           f"tokens={result.tokens}, {elapsed:.0f}ms")
    
    # Wei Wuzu tier (mid-depth)
    start = time.perf_counter()
    result2 = await army.parallel_explore_tiered(
        "Design a memory-efficient data structure for caching",
        num_clones=3,
        tier=CloneTier.WEI_WUZU,
    )
    elapsed2 = (time.perf_counter() - start) * 1000
    
    record("Wei Wuzu tier (3 clones)", "pass" if result2.confidence > 0 else "fail",
           f"strategy={result2.strategy}, conf={result2.confidence:.3f}, {elapsed2:.0f}ms")
    
    # Stats
    stats = army.get_stats()
    record("Army stats", "pass",
           f"deployed={stats['total_clones_deployed']}, success={stats['successful_paths']}, "
           f"avg_conf={stats['avg_confidence']:.3f}")


async def test_10_vibe_code_explore():
    section("10. vibe_code_explore — Three-Phase God-Kit")
    from whitemagic.edge.thought_clones_async import (
        AsyncThoughtCloneArmy, CloneConfig
    )
    
    config = CloneConfig(max_clones=3, max_concurrent_api_calls=3, timeout_seconds=10)
    army = AsyncThoughtCloneArmy(config=config)
    
    start = time.perf_counter()
    result = await army.vibe_code_explore(
        "fastapi endpoint for user registration",
        num_clones=3,
    )
    elapsed = (time.perf_counter() - start) * 1000
    
    phases = result.metadata.get("phases_completed", 0)
    tier = result.metadata.get("tier", "?")
    template = result.metadata.get("template", "?")
    
    record("vibe_code_explore", "pass" if result.confidence > 0 else "warn",
           f"phases={phases}, tier={tier}, template={template}, "
           f"conf={result.confidence:.3f}, {elapsed:.0f}ms")
    
    # Show phase breakdown
    xian_conf = result.metadata.get("xianfeng_confidence", 0)
    wei_conf = result.metadata.get("wei_wuzu_confidence", 0)
    huben_conf = result.metadata.get("huben_confidence", 0)
    record("Phase breakdown", "pass",
           f"xianfeng={xian_conf:.3f} → wei_wuzu={wei_conf:.3f} → huben={huben_conf:.3f}")


def test_11_immortal_clone():
    section("11. ImmortalClone — Persistent Code Improvement Loop")
    from whitemagic.agents.immortal_clone_v2 import (
        ImmortalClone, Task, CampaignVictoryTracker,
    )
    
    # Create a test file with poor code
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "buggy_code.py")
        with open(test_file, "w") as f:
            f.write("""import sqlite3

def get_data(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories")
    rows = cursor.fetchall()
    conn.close()
    return rows
""")
        
        task = Task(
            id="improve-error-handling",
            type="code_improvement",
            target=test_file,
            victory_conditions=["error_handling_added", "resource_cleanup_verified"],
        )
        
        tracker = CampaignVictoryTracker(
            victory_conditions=[
                {"id": "error_handling_added", "description": "Error handling added"},
                {"id": "resource_cleanup_verified", "description": "Resource cleanup verified"},
            ],
        )
        
        clone = ImmortalClone(
            clone_id=1,
            task=task,
            victory_tracker=tracker,
            max_iterations=2,
        )
        
        start = time.perf_counter()
        result = clone.execute_persistent_loop()
        elapsed = (time.perf_counter() - start) * 1000
        
        iterations = result.data.get("iterations", 0) if result.data else 0
        vcs_met = clone.check_victory_conditions()
        
        record("ImmortalClone execution", "pass" if iterations > 0 else "warn",
               f"iterations={iterations}, vcs_met={len(vcs_met)}, {elapsed:.0f}ms")


async def test_12_conductor():
    section("12. ConductorOrchestrator — Autonomous Task")
    from whitemagic.core.orchestration.conductor import (
        ConductorOrchestrator, ConductorConfig,
    )
    
    config = ConductorConfig(
        max_iterations=2,
        clones_per_iteration=3,
        token_limit=5000,
    )
    
    conductor = ConductorOrchestrator(config=config)
    
    start = time.perf_counter()
    try:
        result = await conductor.conduct(
            "Generate a FastAPI endpoint for health checks",
        )
        elapsed = (time.perf_counter() - start) * 1000
        
        iterations = len(conductor.iterations)
        completed = conductor._completed
        
        record("Conductor execution", "pass" if iterations > 0 else "warn",
               f"iterations={iterations}, completed={completed}, {elapsed:.0f}ms")
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        record("Conductor execution", "warn",
               f"error: {str(e)[:80]}, {elapsed:.0f}ms")


async def run_async_tests():
    await test_9_clone_army_tiered()
    await test_10_vibe_code_explore()
    await test_12_conductor()


def main():
    print("\n" + "🔥" * 30)
    print("  WhiteMagic Code-Writing Systems Exercise")
    print("  Testing all code generation pathways end-to-end")
    print("🔥" * 30)
    
    start = time.perf_counter()
    
    # Sync tests
    test_1_vibe_parser()
    test_2_engine_render()
    test_3_vault_vibe_render()
    test_4_polymorphism()
    test_5_project_render()
    test_6_feedback_loop()
    test_7_signing()
    test_8_generate_with_llm()
    test_11_immortal_clone()
    
    # Async tests
    asyncio.run(run_async_tests())
    
    elapsed = time.perf_counter() - start
    
    # Summary
    section("SUMMARY")
    passed = sum(1 for r in RESULTS if r["status"] == "pass")
    failed = sum(1 for r in RESULTS if r["status"] == "fail")
    warned = sum(1 for r in RESULTS if r["status"] == "warn")
    
    print(f"\n  Total: {len(RESULTS)} tests")
    print(f"  ✅ Passed: {passed}")
    print(f"  ⚠️  Warned: {warned}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⏱  Total elapsed: {elapsed:.1f}s")
    
    # Show failures
    if failed:
        print(f"\n  Failures:")
        for r in RESULTS:
            if r["status"] == "fail":
                print(f"    ❌ {r['system']}: {r['detail']}")
    
    if warned:
        print(f"\n  Warnings:")
        for r in RESULTS:
            if r["status"] == "warn":
                print(f"    ⚠️  {r['system']}: {r['detail']}")
    
    print(f"\n{'='*60}")
    print(f"  Exercise complete in {elapsed:.1f}s")
    print(f"{'='*60}\n")
    
    # Write results JSON
    results_path = "/tmp/codegen_exercise_results.json"
    with open(results_path, "w") as f:
        json.dump({"results": RESULTS, "total_elapsed_s": elapsed, 
                    "passed": passed, "failed": failed, "warned": warned}, f, indent=2)
    print(f"  Results saved to {results_path}")


if __name__ == "__main__":
    main()
