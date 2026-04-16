
with open("tests/unit/autonomous/executor/test_continuous_executor.py") as f:
    content = f.read()

# Make tests handle the rust_daemon mock properly if they mock __init__ or run_continuous
content = content.replace(
    """@pytest.fixture
def executor(mock_config):
    with patch('whitemagic.core.governor.get_governor'):
        # Mock subsystems to prevent actual execution during tests""",
    """@pytest.fixture
def executor(mock_config):
    with patch('whitemagic.core.governor.get_governor'):
        # Mock rust daemon initialization to avoid cross-platform test issues
        with patch('whitemagic.autonomous.executor.continuous_executor.ContinuousExecutor.__init__') as mock_init:
            # We don't actually want to mock __init__ entirely, just handle the daemon
            pass

        # Proper way: patch rs module
        with patch('whitemagic.autonomous.executor.continuous_executor.rs', create=True):
            pass

        # Mock subsystems to prevent actual execution during tests"""
)

# Better mock setup in the fixture
content = content.replace(
    """    with patch('whitemagic.core.governor.get_governor'):
        # Mock rust daemon initialization to avoid cross-platform test issues
        with patch('whitemagic.autonomous.executor.continuous_executor.ContinuousExecutor.__init__') as mock_init:
            # We don't actually want to mock __init__ entirely, just handle the daemon
            pass

        # Proper way: patch rs module
        with patch('whitemagic.autonomous.executor.continuous_executor.rs', create=True):
            pass

        # Mock subsystems to prevent actual execution during tests
        with patch('whitemagic.autonomous.executor.continuous_executor.ResourceLimits') as mock_limits, \\
             patch('whitemagic.autonomous.executor.continuous_executor.ObjectiveGenerator') as mock_generator, \\
             patch('whitemagic.autonomous.executor.continuous_executor.ProgressAssessor') as mock_assessor:

            executor = ContinuousExecutor(mock_config)""",
    """    with patch('whitemagic.core.governor.get_governor'):
        with patch('whitemagic.autonomous.executor.continuous_executor.ResourceLimits') as mock_limits, \\
             patch('whitemagic.autonomous.executor.continuous_executor.ObjectiveGenerator') as mock_generator, \\
             patch('whitemagic.autonomous.executor.continuous_executor.ProgressAssessor') as mock_assessor, \\
             patch('whitemagic.autonomous.executor.continuous_executor.rs', create=True) as mock_rs:

            # Setup rs.ContinuousDaemon() mock
            mock_daemon = MagicMock()
            mock_daemon.is_running.return_value = False
            mock_rs.ContinuousDaemon.return_value = mock_daemon

            executor = ContinuousExecutor(mock_config)"""
)

with open("tests/unit/autonomous/executor/test_continuous_executor.py", "w") as f:
    f.write(content)
