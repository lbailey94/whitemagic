#!/usr/bin/env python3
"""Apply fitted temperature_by_options to the Laya checkpoint config.

Base: the shipped config backup (restores noul/score temperatures and the
training block). Override: choice buckets with the fitted values.
"""
import json
import shutil

CONFIG = "/home/lucas/tools/laya/models/laya-base/rl_agent_config.json"
REPORT = "/tmp/opencode/s1_refit_report.json"

report = json.load(open(REPORT))
base = json.load(open(CONFIG + ".shipped.bak"))
fitted = report["fitted"]

before = dict(base.get("temperature_by_options", {}))
after = dict(before)
after.update(fitted)
base["temperature_by_options"] = after

shutil.copy(CONFIG, CONFIG + ".raw.bak")
json.dump(base, open(CONFIG, "w"), indent=2)

print("fitted choice temperatures applied:")
for key in sorted(fitted):
    print(f"  {key:12s} {before.get(key, float('nan')):.4f} -> {fitted[key]:.4f}")
print(f"config: {CONFIG}")
