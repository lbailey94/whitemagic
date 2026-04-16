"""Final Benchmark: Compiled Mojo vs Python"""
import subprocess
import time
import sys

print("=" * 60)
print("COMPILED MOJO vs PYTHON BENCHMARK")
print("=" * 60)

# Run compiled Mojo binary
print("\n1. Running COMPILED Mojo binary...")
start = time.time()
result = subprocess.run(
    ["./bench_cosine_mojo"],
    cwd="/home/lucas/Desktop/whitemagicdev/whitemagic-mojo",
    capture_output=True,
    text=True
)
mojo_time = (time.time() - start) * 1000
print(f"   Time: {mojo_time:.2f} ms")

# Run Python
print("\n2. Running Python...")
start = time.time()
result = subprocess.run(
    [sys.executable, "bench_cosine.py"],
    cwd="/home/lucas/Desktop/whitemagicdev/whitemagic-mojo",
    capture_output=True,
    text=True
)
py_time = (time.time() - start) * 1000
print(f"   Time: {py_time:.2f} ms")

# Results
print("\n" + "=" * 60)
print("FINAL RESULTS (1000 vectors, 384 dimensions):")
print(f"  Python:         {py_time:.2f} ms")
print(f"  Mojo compiled:  {mojo_time:.2f} ms")
print(f"  Speedup:        {py_time/mojo_time:.2f}x")
print("=" * 60)

if py_time > mojo_time:
    print(f"\n✅ Mojo is {py_time/mojo_time:.2f}x faster than Python!")
else:
    print(f"\n⚠️  Python is {mojo_time/py_time:.2f}x faster than Mojo")
    print("   (Mojo startup overhead dominates for small workloads)")
