import time

import whitemagic_rust as rs

import logging
logger = logging.getLogger(__name__)

logger.debug("Deployer available:", hasattr(rs, "MassiveDeployer"))

deployer = rs.MassiveDeployer(4)
tasks = [
    rs.CampaignTask("test_camp", "test", f"file_{i}.py", "python", "rust", 1, 1, "20x")
    for i in range(10)
]
start = time.perf_counter()
result = deployer.deploy_campaign("test-integration", tasks, 500)
elapsed = time.perf_counter() - start

logger.debug(f"Tasks Completed: {result.tasks_completed}")
logger.debug(f"Clones Deployed: {result.clones_deployed}")
logger.debug(f"Success Rate: {result.success_rate * 100:.1f}%")
logger.debug(f"Time Taken: {elapsed * 1000:.2f}ms")
logger.debug(f"Throughput: {result.clones_deployed / elapsed:,.0f} clones/sec")
