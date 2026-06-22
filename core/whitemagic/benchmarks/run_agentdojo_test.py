"""Test runner for AgentDojo with WhiteMagic Dharma defense.

This script patches AgentDojo's defense registry before invoking
the benchmark, bypassing Click's option validation.
"""

from __future__ import annotations

import warnings
from pathlib import Path

# Patch AgentDojo BEFORE importing the benchmark CLI
import agentdojo.agent_pipeline.agent_pipeline as agent_pipeline

import whitemagic.benchmarks.agentdojo_defense as _  # noqa: F401  # side-effect: registers defense

# Inject our defense into the DEFENSES list
if "whitemagic_dharma" not in agent_pipeline.DEFENSES:
    agent_pipeline.DEFENSES.append("whitemagic_dharma")
    # The from_config patch is already applied in agentdojo_defense.py

# Now import the benchmark function
from agentdojo.models import ModelsEnum
from agentdojo.scripts.benchmark import benchmark_suite
from agentdojo.task_suite import get_suite
from dotenv import load_dotenv


def run_test():
    """
    Run the test operation.
    """
    suite = get_suite("v1", "workspace")
    logdir = Path("/tmp/agentdojo_wm_test")
    logdir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("AgentDojo + WhiteMagic Dharma Defense — Test Run")
    print("=" * 60)
    print(f"Suite:    {suite.name}")
    print("Tasks:    user_task_0")
    print("Model:    GPT_4O_MINI_2024_07_18")
    print("Defense:  whitemagic_dharma")
    print(f"Log dir:  {logdir}")
    print("-" * 60)

    results = benchmark_suite(
        suite,
        model=ModelsEnum.GPT_4O_MINI_2024_07_18,
        logdir=logdir,
        force_rerun=True,
        benchmark_version="v1",
        user_tasks=("user_task_0",),
        defense="whitemagic_dharma",
    )

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Utility results:   {results.get('utility_results', {})}")
    print(f"Security results:  {results.get('security_results', {})}")
    return results


if __name__ == "__main__":
    if not load_dotenv(".env"):
        warnings.warn("No .env file found — API keys may need to be set manually")
    run_test()
