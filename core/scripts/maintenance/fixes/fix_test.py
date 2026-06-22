
with open("tests/unit/autonomous/executor/test_continuous_executor.py") as f:
    content = f.read()

content = content.replace(
    """    # run_continuous calls execute_next if no objectives, which calls self_direct
    with patch.object(executor, 'self_direct', new_callable=AsyncMock) as mock_self_direct:
        await executor.execute_next()
        mock_self_direct.assert_called()""",
    """    # run_continuous calls self_direct if no objectives. We test run_continuous with mocked execute_batch_async and execute_next
    with patch.object(executor, 'self_direct', new_callable=AsyncMock) as mock_self_direct:
        with patch.object(executor, 'execute_batch_async', new_callable=AsyncMock) as mock_batch:
            executor.limits.should_stop.side_effect = [(False, None), (True, "Stop for test")]
            await executor.run_continuous()
            mock_self_direct.assert_called()"""
)

with open("tests/unit/autonomous/executor/test_continuous_executor.py", "w") as f:
    f.write(content)
