"""Compare Mojo vs Python performance"""
import subprocess
import time
import sys

def run_mojo():
    """Run Mojo benchmark and parse output."""
    start = time.time()
    result = subprocess.run(
        ["pixi", "run", "mojo", "run", "bench_cosine.mojo"],
        cwd="/home/lucas/Desktop/whitemagicdev/whitemagic-mojo",
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
        cwd="/home/lucas/Desktop/whitemagicdev/whitemagic-mojo",
        capture_output=True,
        text=True
    )
    end = time.time()
    py_time = (end - start) * 1000
    return py_time, result.stdout, result.returncode

print("=" * 50)
print("MOJO vs PYTHON BENCHMARK")
print("=" * 50)
print("\n1. Running Mojo...")
mojo_time, mojo_out, mojo_rc = run_mojo()
if mojo_rc == 0:
    print(f"   Mojo time: {mojo_time:.2f} ms")
else:
    print(f"   Mojo FAILED: {mojo_out}")

print("\n2. Running Python...")
py_time, py_out, py_rc = run_python()
if py_rc == 0:
    print(f"   Python time: {py_time:.2f} ms")
else:
    print(f"   Python FAILED: {py_out}")

if mojo_rc == 0 and py_rc == 0:
    speedup = py_time / mojo_time
    print("\n" + "=" * 50)
    print("RESULTS:")
    print(f"  Python:  {py_time:.2f} ms")
    print(f"  Mojo:    {mojo_time:.2f} ms")
    print(f"  Speedup: {speedup:.2f}x")
    print("=" * 50)
