"""Synthesis Engine - Mojo 0.26.1"""

fn linear_blend(a: List[Float32], b: List[Float32], t: Float32) -> List[Float32]:
    """Blend two vectors with factor t."""
    var result = List[Float32]()
    var n = min(len(a), len(b))
    for i in range(n):
        result.append(a[i] * (1.0 - t) + b[i] * t)
    return result^

fn synthesis_score(inputs: List[List[Float32]], weights: List[Float32]) -> List[Float32]:
    """Weighted synthesis of multiple inputs."""
    if len(inputs) == 0:
        return List[Float32]()^
    
    var dim = len(inputs[0])
    var result = List[Float32]()
    for i in range(dim):
        var sum: Float32 = 0.0
        var total_weight: Float32 = 0.0
        for j in range(len(inputs)):
            if i < len(inputs[j]):
                sum += inputs[j][i] * weights[j]
                total_weight += weights[j]
        if total_weight > 0.0:
            result.append(sum / total_weight)
        else:
            result.append(0.0)
    return result^

fn main():
    print("Synthesis Engine v0.26.1")
