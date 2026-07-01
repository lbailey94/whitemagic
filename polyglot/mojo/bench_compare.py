"""Compare Mojo vs Python performance"""
import subprocess
import time
import sys

import logging
logger = logging.getLogger(__name__)

def run_mojo():
    """Run Mojo benchmark and parse output."""
    start = time.time()
    result = subprocess.run(
        ["pixi", "run", "mojo", "run", "bench_cosine.mojo"],
        cwd="/home/user/Desktop/whitemagic/whitemagic-mojo",
        capture_output=True,
        text=True
    )
    end = time.time()
    mojo_time = (end - start) * 1000  # ms
    return mojo_time, result.stdout, result.returncode

def run_python():
    """Run Python benchmark."""
    start = time.time()
    result = subprocess.run(
        [sys.executable, "bench_cosine.py"],
        cwd="/home/user/Desktop/whitemagic/whitemagic-mojo",
        capture_output=True,
        text=True
    )
    end = time.time()
    py_time = (end - start) * 1000
    return py_time, result.stdout, result.returncode

logger.debug("=" * 50)
logger.debug("MOJO vs PYTHON BENCHMARK")
logger.debug("=" * 50)
logger.debug("\n1. Running Mojo...")
mojo_time, mojo_out, mojo_rc = run_mojo()
if mojo_rc == 0:
    logger.debug("   Mojo time: %s ms", mojo_time)
else:
    logger.debug("   Mojo FAILED: %s", mojo_out)

logger.debug("\n2. Running Python...")
py_time, py_out, py_rc = run_python()
if py_rc == 0:
    logger.debug("   Python time: %s ms", py_time)
else:
    logger.debug("   Python FAILED: %s", py_out)

if mojo_rc == 0 and py_rc == 0:
    speedup = py_time / mojo_time
    logger.debug("\n" + "=" * 50)
    logger.debug("RESULTS:")
    logger.debug("  Python:  %s ms", py_time)
    logger.debug("  Mojo:    %s ms", mojo_time)
    logger.debug("  Speedup: %sx", speedup)
    logger.debug("=" * 50)
