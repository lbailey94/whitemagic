"""
Example: Using Art of War Strategic Planning

This example demonstrates how to use Sun Tzu's principles
for strategic task assessment before execution.
"""

from whitemagic.strategy import FiveFactorsAssessment
from whitemagic.threading_tiers import get_tier_threads, recommend_tier


def example_terrain_assessment():
    """Example of terrain analysis."""
    print("=== Terrain Analysis Example ===\n")

    # Example 1: Simple bug fix (ACCESSIBLE)
    print("Task: Fix simple bug")
    print("Terrain: ACCESSIBLE - Straightforward execution")
    print("Recommendation: Proceed directly with Tier 1 (16 threads)\n")

    # Example 2: Feature needing research (TEMPORIZING)
    print("Task: Implement complex feature")
    print("Terrain: TEMPORIZING - Need more information")
    print("Recommendation: Gather requirements first, don't code yet\n")

    # Example 3: Database migration (PRECIPITOUS)
    print("Task: Database schema migration")
    print("Terrain: PRECIPITOUS - High risk operation")
    print("Recommendation: Sequential execution, test thoroughly\n")


def example_five_factors():
    """Example of five factors assessment."""
    print("=== Five Factors Assessment ===\n")

    # Good conditions
    factors_good = FiveFactorsAssessment(
        dao_aligned=True,  # ✅ Aligned with values
        heaven_favorable=True,  # ✅ Good timing
        earth_prepared=True,  # ✅ Have resources
        general_ready=True,  # ✅ Clear strategy
        law_followed=True,  # ✅ Following practices
    )

    print(f"All factors favorable: {factors_good.all_favorable}")
    print(f"Score: {factors_good.score:.1f}/1.0")
    print(f"Recommendation: {factors_good.recommendation}\n")

    # Unfavorable conditions
    factors_bad = FiveFactorsAssessment(
        dao_aligned=True,
        heaven_favorable=False,  # ❌ Bad timing
        earth_prepared=False,  # ❌ Lacking resources
        general_ready=True,
        law_followed=True,
    )

    print(f"Some factors unfavorable: {not factors_bad.all_favorable}")
    print(f"Score: {factors_bad.score:.1f}/1.0")
    print(f"Recommendation: {factors_bad.recommendation}\n")


def example_threading_tiers():
    """Example of I Ching-aligned threading."""
    print("=== Threading Tiers (I Ching) ===\n")

    for tier in range(6):
        threads = get_tier_threads(tier)
        desc = {
            0: "8 trigrams (☰☱☲☳☴☵☶☷)",
            1: "2 × 8",
            2: "4 × 8",
            3: "64 hexagrams (SWEET SPOT!)",
            4: "2 × 64",
            5: "Ultimate complexity",
        }[tier]

        print(f"Tier {tier}: {threads} threads - {desc}")

    print("\nAutomatic recommendations:")
    print(
        f"Simple task: Tier {recommend_tier('simple')} ({get_tier_threads(recommend_tier('simple'))} threads)"
    )
    print(
        f"Moderate task: Tier {recommend_tier('moderate')} ({get_tier_threads(recommend_tier('moderate'))} threads)"
    )
    print(
        f"Complex task: Tier {recommend_tier('complex')} ({get_tier_threads(recommend_tier('complex'))} threads)"
    )


def example_complete_workflow():
    """Complete workflow example."""
    print("\n=== Complete Workflow Example ===\n")

    task = "Implement new API endpoint with database changes"

    # Step 1: Terrain analysis
    print(f"Task: {task}\n")
    print("Step 1: Analyze terrain")
    print("  - Has dependencies: database schema")
    print("  - Requires testing: yes")
    print("  - Parallelizable: partially")
    print("  → Terrain: ENTANGLING (resolve dependencies first)\n")

    # Step 2: Five factors
    print("Step 2: Five factors check")
    factors = FiveFactorsAssessment(
        dao_aligned=True,
        heaven_favorable=True,
        earth_prepared=True,
        general_ready=True,
        law_followed=True,
    )
    print(f"  → Score: {factors.score:.1f}, {factors.recommendation}\n")

    # Step 3: Threading tier
    print("Step 3: Select threading tier")
    tier = 3  # Hexagram level for complex task
    threads = get_tier_threads(tier)
    print(f"  → Tier {tier}: {threads} threads (hexagram-level complexity)\n")

    # Step 4: Decision
    print("Step 4: Strategic decision")
    if factors.score >= 0.8:
        print("  ✅ PROCEED")
        print("  ✅ Resolve database dependencies first")
        print("  ✅ Then execute with 64 threads")
        print("  ✅ Test thoroughly before deployment")
    else:
        print("  ⚠️ PREPARE MORE")


if __name__ == "__main__":
    example_terrain_assessment()
    print("\n" + "=" * 50 + "\n")

    example_five_factors()
    print("\n" + "=" * 50 + "\n")

    example_threading_tiers()
    print("\n" + "=" * 50 + "\n")

    example_complete_workflow()

    print("\n" + "=" * 50)
    print("Sun Tzu says: 'Know your enemy and know yourself'")
    print("In AI: Know your task and know your resources!")
    print("=" * 50)
