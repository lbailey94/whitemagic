
# Geneseed Auto-Transmuted Mojo Kernel
# Original: Python cosine_similarity
from sys.intrinsics import simd_reduce_add

fn fast_cosine_similarity(vec_a: SIMD[DType.float32, 16], vec_b: SIMD[DType.float32, 16]) -> Float32:
    # Auto-generated SIMD implementation
    return simd_reduce_add(vec_a * vec_b)
