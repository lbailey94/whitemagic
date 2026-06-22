
with open("tests/unit/autonomous/executor/test_continuous_executor.py") as f:
    content = f.read()

content = content.replace(
    "async def test_run_continuous_empty_queue(executor):",
    "async def test_run_continuous_empty_queue(executor):\n    executor.limits.get_status.return_value = {}"
)

with open("tests/unit/autonomous/executor/test_continuous_executor.py", "w") as f:
    f.write(content)
