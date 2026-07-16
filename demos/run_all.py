#!/usr/bin/env python3
"""Run all WhiteMagic demos in sequence.

Each demo is under 60 seconds and shows something cloud AI cannot do.

Usage:
    python demos/run_all.py          # run all demos
    python demos/run_all.py 1        # run demo 1 only
    python demos/run_all.py 2        # run demo 2 only
    python demos/run_all.py 3        # run demo 3 only
"""
import sys


def main():
    demos = {
        1: ("Offline Memory Persistence", "demo1_offline_memory"),
        2: ("Dream Cycle — Memory Consolidation", "demo2_dream_cycle"),
        3: ("Dharma Governance — Ethics as Code", "demo3_governance"),
    }

    to_run = []
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
            if n in demos:
                to_run = [n]
        except ValueError:
            pass
    if not to_run:
        to_run = sorted(demos.keys())

    for n in to_run:
        name, module_name = demos[n]
        print(f"\n{'=' * 60}")
        print(f"  Starting Demo {n}: {name}")
        print(f"{'=' * 60}")

        try:
            mod = __import__(module_name)
            mod.main()
        except Exception as e:
            print(f"  ❌ Demo {n} failed: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"  All demos complete.")
    print(f"  These are things cloud AI literally cannot do.")
    print(f"  Local-first. Private. Governed. Conscious.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
