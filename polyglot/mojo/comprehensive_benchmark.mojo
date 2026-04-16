"""Comprehensive Benchmark Suite - Mojo 0.26.1"""

from math import sqrt, exp, log

fn benchmark_cosine_similarity():
    print("\n--- Cosine Similarity Benchmark ---")
    var dim = 384
    var num_vecs = 1000
    
    var vecs = List[List[Float32]]()
    for i in range(num_vecs):
        var v = List[Float32]()
        for j in range(dim):
            v.append(Float32((i + j) % 100) / 100.0)
        vecs.append(v^.copy())
    
    var q = List[Float32]()
    for j in range(dim):
        q.append(Float32(j % 100) / 100.0)
    
    var total: Float32 = 0.0
    for i in range(num_vecs):
        var dot: Float32 = 0.0
        var mag_a: Float32 = 0.0
        var mag_b: Float32 = 0.0
        for j in range(dim):
            dot += vecs[i][j] * q[j]
            mag_a += vecs[i][j] * vecs[i][j]
            mag_b += q[j] * q[j]
        var denom = sqrt(mag_a * mag_b)
        if denom > 0.0:
            total += dot / denom
    
    print(num_vecs, "cosine similarities computed")
    print("Average:", total / Float32(num_vecs))

fn benchmark_dot_product():
    print("\n--- Dot Product Benchmark ---")
    var dim = 1000
    var iterations = 10000
    
    var a = List[Float32]()
    var b = List[Float32]()
    for i in range(dim):
        a.append(Float32(i) / 1000.0)
        b.append(Float32(dim - i) / 1000.0)
    
    var total: Float32 = 0.0
    for iter in range(iterations):
        var dot: Float32 = 0.0
        for i in range(dim):
            dot += a[i] * b[i]
        total += dot
    
    print(iterations, "dot products of dimension", dim)
    print("Final sum:", total)

fn benchmark_vector_ops():
    print("\n--- Vector Operations Benchmark ---")
    var dim = 384
    var n = 1000
    
    var vectors = List[List[Float32]]()
    for i in range(n):
        var v = List[Float32]()
        for j in range(dim):
            v.append(Float32((i * j) % 100) / 100.0)
        vectors.append(v^.copy())
    
    var sum_sq: Float32 = 0.0
    for i in range(n):
        for j in range(dim):
            sum_sq += vectors[i][j] * vectors[i][j]
    
    print(n, "vectors normalized (magnitude squared:", sum_sq, ")")

fn benchmark_math_functions():
    print("\n--- Math Functions Benchmark ---")
    var n = 100000
    
    var sum_exp: Float32 = 0.0
    var sum_log: Float32 = 0.0
    var sum_sqrt: Float32 = 0.0
    
    for i in range(n):
        var x = Float32(i + 1) / 1000.0
        sum_exp += exp(-x)
        sum_sqrt += sqrt(x)
        if x > 0.0:
            sum_log += log(x)
    
    print(n, "math function calls")
    print("Sum exp(-x):", sum_exp)
    print("Sum sqrt(x):", sum_sqrt)
    print("Sum log(x):", sum_log)

fn main():
    print("========================================")
    print("MOJO 0.26.1 COMPREHENSIVE BENCHMARK")
    print("========================================")
    
    benchmark_cosine_similarity()
    benchmark_dot_product()
    benchmark_vector_ops()
    benchmark_math_functions()
    
    print("\n========================================")
    print("Benchmark complete!")
    print("========================================")
