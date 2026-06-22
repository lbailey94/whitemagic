import time

import whitemagic_rust as rs

deployer = rs.MassiveDeployer(8) # Max parallel

tasks = [
    rs.CampaignTask(
        "continuous_executor_coverage",
        "generate_tests",
        "whitemagic/autonomous/executor/continuous_executor.py",
        "python",
        "python",
        10, # priority
        8,  # complexity
        "100% coverage target, focusing on lines 172-207, 230-273, 398-511, 620-681"
    )
]

print("Launching Massive Deployer Test Generation Campaign for Continuous Executor...")
start = time.perf_counter()
result = deployer.deploy_campaign("test_generation_executor", tasks, 500)
elapsed = time.perf_counter() - start

print(f"Deployment Complete in {elapsed:.2f}s")
print(f"Tasks Handled: {result.tasks_completed}/{len(tasks)}")
print(f"Clones Engaged: {result.clones_deployed:,}")
