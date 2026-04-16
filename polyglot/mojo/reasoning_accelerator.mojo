"""Reasoning Accelerator - Mojo 0.26.1"""
from math import sqrt, exp

fn weighted_sum(weights: List[Float32], values: List[Float32]) -> Float32:
    """Compute weighted sum."""
    var result: Float32 = 0.0
    var n = min(len(weights), len(values))
    for i in range(n):
        result += weights[i] * values[i]
    return result

fn softmax(values: List[Float32]) -> List[Float32]:
    """Compute softmax probabilities."""
    var max_val: Float32 = -1e9
    for i in range(len(values)):
        if values[i] > max_val:
            max_val = values[i]
    
    var exp_sum: Float32 = 0.0
    var exps = List[Float32]()
    for i in range(len(values)):
        var e = exp(values[i] - max_val)
        exps.append(e)
        exp_sum += e
    
    var probs = List[Float32]()
    for i in range(len(exps)):
        probs.append(exps[i] / exp_sum)
    
    return probs^

fn main():
    print("Reasoning Accelerator v0.26.1")
