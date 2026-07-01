"""Final Benchmark: Compiled Mojo vs Python"""
import subprocess
import time
import sys

import logging
logger = logging.getLogger(__name__)

logger.debug("=" * 60)
logger.debug("COMPILED MOJO vs PYTHON BENCHMARK")
logger.debug("=" * 60)

logger.debug("\n1. Running COMPILED Mojo binary...")
start = time.time()
result = subprocess.run(
    ["./bench_cosine_mojo"],
    cwd="/home/user/Desktop/whitemagic/whitemagic-mojo",
    capture_output=True,
    text=True
)
mojo_time = (time.time() - start) * 1000
logger.debug(f"   Time: {mojo_time:.2f} ms")

logger.debug("\n2. Running Python...")
start = time.time()
result = subprocess.run(
    [sys.executable, "bench_cosine.py"],
    cwd="/home/user/Desktop/whitemagic/whitemagic-mojo",
    capture_output=True,
    text=True
)
py_time = (time.time() - start) * 1000
logger.debug(f"   Time: {py_time:.2f} ms")

# Results
logger.debug("\n" + "=" * 60)
logger.debug("FINAL RESULTS (1000 vectors, 384 dimensions):")
logger.debug(f"  Python:         {py_time:.2f} ms")
logger.debug(f"  Mojo compiled:  {mojo_time:.2f} ms")
logger.debug(f"  Speedup:        {py_time/mojo_time:.2f}x")
logger.debug("=" * 60)

if py_time > mojo_time:
    logger.debug(f"\n✅ Mojo is {py_time/mojo_time:.2f}x faster than Python!")
else:
    logger.debug(f"\n⚠️  Python is {mojo_time/py_time:.2f}x faster than Mojo")
    logger.debug("   (Mojo startup overhead dominates for small workloads)")
