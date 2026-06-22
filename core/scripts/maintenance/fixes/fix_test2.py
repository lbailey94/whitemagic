
with open("tests/unit/autonomous/executor/test_continuous_executor.py") as f:
    content = f.read()

# Fix batch execution test again
content = content.replace(
    "executor.generator.scan_codebase = AsyncMock(return_value={})",
    ""
)

with open("tests/unit/autonomous/executor/test_continuous_executor.py", "w") as f:
    f.write(content)
