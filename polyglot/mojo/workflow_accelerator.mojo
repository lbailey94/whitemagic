"""Workflow Accelerator - Mojo 0.26.1"""

fn pipeline_throughput(stage_times: List[Float32]) -> Float32:
    """Compute pipeline throughput (bottleneck)."""
    var max_time: Float32 = 0.0
    for i in range(len(stage_times)):
        if stage_times[i] > max_time:
            max_time = stage_times[i]
    return 1.0 / max_time if max_time > 0.0 else 0.0

fn parallel_speedup(serial_time: Float32, parallel_time: Float32, num_workers: Int) -> Float32:
    """Compute parallel speedup efficiency."""
    if parallel_time <= 0.0:
        return 0.0
    var speedup = serial_time / parallel_time
    return speedup / Float32(num_workers)

fn main():
    print("Workflow Accelerator v0.26.1")
