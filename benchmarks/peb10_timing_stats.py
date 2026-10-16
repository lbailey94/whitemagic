import statistics
import re

FLOOR = 1.4
SAMPLE = re.compile(
    r"^PEB10_TIMING_SAMPLE pulse_us=([0-9.]+) "
    r"dag_emulated_us=([0-9.]+) speedup=([0-9.]+)$",
    re.M,
)


def parse_sample(output):
    match = SAMPLE.search(output)
    if not match:
        return None
    pulse, dag, speedup = map(float, match.groups())
    if pulse <= 0 or dag <= 0 or abs(dag / pulse - speedup) > 1e-8:
        return None
    return {"pulse_avg_us": pulse, "dag_emulated_avg_us": dag, "speedup_x": speedup}


def summarize(samples):
    values = [sample["speedup_x"] for sample in samples]
    return statistics.median(values) if values else None
