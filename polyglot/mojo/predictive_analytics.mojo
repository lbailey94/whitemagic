"""Predictive Analytics - Mojo 0.26.1"""

fn moving_average(values: List[Float32], window: Int) -> List[Float32]:
    """Compute moving average."""
    var result = List[Float32]()
    for i in range(len(values)):
        var sum: Float32 = 0.0
        var count = 0
        for j in range(max(0, i - window + 1), min(len(values), i + 1)):
            sum += values[j]
            count += 1
        if count > 0:
            result.append(sum / Float32(count))
        else:
            result.append(0.0)
    return result^

fn trend_slope(values: List[Float32]) -> Float32:
    """Simple linear trend slope."""
    var n = len(values)
    if n < 2:
        return 0.0
    
    var sum_x: Float32 = 0.0
    var sum_y: Float32 = 0.0
    var sum_xy: Float32 = 0.0
    var sum_xx: Float32 = 0.0
    
    for i in range(n):
        var x = Float32(i)
        var y = values[i]
        sum_x += x
        sum_y += y
        sum_xy += x * y
        sum_xx += x * x
    
    var denom = Float32(n) * sum_xx - sum_x * sum_x
    if denom != 0.0:
        return (Float32(n) * sum_xy - sum_x * sum_y) / denom
    return 0.0

fn main():
    print("Predictive Analytics v0.26.1")
