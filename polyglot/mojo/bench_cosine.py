"""Python Cosine Similarity Benchmark - for comparison with Mojo"""
import math
import time

def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    denom = mag_a * mag_b
    return dot / denom if denom > 0 else 0.0

def benchmark():
    dim = 384
    num_vecs = 1000
    
    # Build vectors
    vecs = []
    for i in range(num_vecs):
        v = [((i + j) % 100) / 100.0 for j in range(dim)]
        vecs.append(v)
    
    # Query vector
    q = [(j % 100) / 100.0 for j in range(dim)]
    
    # Benchmark
    start = time.time()
    total_sim = 0.0
    for v in vecs:
        total_sim += cosine_similarity(v, q)
    end = time.time()
    
    ms = (end - start) * 1000
    print("Python Results:")
    print(f"{num_vecs} vectors, {dim} dimensions")
    print(f"Time: {ms:.2f} ms")
    print(f"Throughput: {num_vecs / (ms/1000):.0f} vectors/sec")
    print(f"Average similarity: {total_sim / num_vecs:.6f}")
    print(f"Last similarity: {cosine_similarity(vecs[-1], q):.6f}")

if __name__ == "__main__":
    benchmark()
