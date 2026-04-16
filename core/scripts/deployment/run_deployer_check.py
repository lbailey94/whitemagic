import time

import whitemagic_rust as rs

print("Deployer available:", hasattr(rs, "MassiveDeployer"))

deployer = rs.MassiveDeployer(4)
tasks = [
    rs.CampaignTask("test_camp", "test", f"file_{i}.py", "python", "rust", 1, 1, "20x")
    for i in range(10)
]
start = time.perf_counter()
result = deployer.deploy_campaign("test-integration", tasks, 500)
elapsed = time.perf_counter() - start

print(f"Tasks Completed: {result.tasks_completed}")
print(f"Clones Deployed: {result.clones_deployed}")
print(f"Success Rate: {result.success_rate * 100:.1f}%")
print(f"Time Taken: {elapsed * 1000:.2f}ms")
print(f"Throughput: {result.clones_deployed / elapsed:,.0f} clones/sec")
