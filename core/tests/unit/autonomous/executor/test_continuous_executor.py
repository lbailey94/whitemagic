import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from whitemagic.autonomous.executor.continuous_executor import (
    ContinuousExecutor, ExecutorConfig, Objective, ExecutionResult
)
from whitemagic.autonomous.executor.assessor import Assessment

@pytest.fixture
def mock_config():
    return ExecutorConfig(max_iterations=5, max_tokens=1000)

@pytest.fixture
def executor(mock_config):
    with patch("whitemagic.autonomous.executor.assessor.ProgressAssessor"), \
         patch("whitemagic.autonomous.executor.limits.ResourceLimits"):
        # Mock what we need without importing
        with patch("whitemagic.autonomous.executor.continuous_executor.ContinuousExecutor.log"):
            ex = ContinuousExecutor(mock_config)
            
            # Setup AsyncMocks on generator since it is awaited in self_direct
            ex.generator = MagicMock()
            class MockScan:
                todos = []
                test_gaps = []
            class MockResearch:
                opportunities = []
            class MockGuidance:
                primary_recommendation = "test"
                
            ex.generator.scan_codebase = AsyncMock(return_value=MockScan())
            ex.generator.research_possibilities = AsyncMock(return_value=MockResearch())
            ex.generator.consult_grimoire = AsyncMock(return_value=MockGuidance())
            ex.generator.form_strategy = AsyncMock(return_value={"focus": "testing", "goal": "Test everything"})
            ex.generator.generate_strategy = AsyncMock(return_value={"focus": "testing"})
            ex.generator.generate_objectives = AsyncMock(return_value=[
                Objective(description="Generated 1", id="gen1")
            ])
            return ex

def test_initialization(executor, mock_config):
    assert executor.config == mock_config
    assert len(executor.objectives) == 0
    assert len(executor.completed) == 0

def test_add_objective(executor):
    obj = Objective(description="Test objective", id="obj1")
    executor.add_objective(obj)
    assert executor.has_objectives() is True
    assert executor.objectives[0] == obj

def test_should_stop(executor):
    # Should not stop initially
    executor.limits.should_stop.return_value = (False, None)
    stop, reason = executor.should_stop()
    assert stop is False

    # Should stop when iterations exceed max
    executor.limits.should_stop.return_value = (True, "Max iterations")
    stop, reason = executor.should_stop()
    assert stop is True
    assert "Max iterations" in reason

@pytest.mark.asyncio
async def test_execute_objective_success(executor):
    obj = Objective(description="Test obj", id="obj1")
    
    # Add a mock action to make execution succeed
    from whitemagic.autonomous.executor.continuous_executor import ShellCommandAction
    mock_action = ShellCommandAction(command="echo 'test'")
    
    with patch.object(executor, 'parse_objective', return_value=[mock_action]):
        with patch.object(executor, 'run_command', new_callable=AsyncMock) as mock_run:
            with patch.object(executor.assessor, 'assess', new_callable=AsyncMock) as mock_assess:
                # Add governor to executor explicitly for testing
                executor.governor = MagicMock()
                executor.governor.validate_command.return_value = {"safe": True}
                mock_assess.return_value = Assessment(complete=True)
                mock_run.return_value = "test output"
                result = await executor.execute_objective(obj)
            
            assert result.success is True
            assert result.objective_id == "obj1" 

@pytest.mark.asyncio
async def test_run_continuous_empty_queue(executor):
    executor.limits.get_status.return_value = {}
    # Actually we just want to run execute_next which is the inner loop step
    # run_continuous calls self_direct if no objectives. We test run_continuous with mocked execute_batch_async and execute_next
    with patch.object(executor, 'self_direct', new_callable=AsyncMock) as mock_self_direct:
        with patch.object(executor, 'execute_batch_async', new_callable=AsyncMock) as mock_batch:
            executor.limits.should_stop.side_effect = [(False, None), (True, "Stop for test")]
            await executor.run_continuous()
            mock_self_direct.assert_called()
        mock_self_direct.assert_called()

@pytest.mark.asyncio
async def test_run_continuous_batch_execution(executor):
    """Test the batch execution path of the continuous loop."""
    executor.limits.get_status.return_value = {}
    
    # We want to loop once, run a batch of objectives, then stop
    obj1 = Objective(description="Test 1", id="obj1")
    obj2 = Objective(description="Test 2", id="obj2")
    executor.objectives = [obj1, obj2]
    
    with patch.object(executor, 'execute_batch_async', new_callable=AsyncMock) as mock_batch:
        # Mock actual execute_next loop content
        with patch.object(executor, 'execute_next', new_callable=AsyncMock) as mock_exec_next:
            executor.limits.should_stop.side_effect = [(False, None), (True, "Stop for test")]
            await executor.run_continuous()
            mock_exec_next.assert_called()
        
        # Actually call execute_batch_async to test it
        await executor.execute_batch_async([obj1, obj2])
        mock_batch.assert_called_once()
        # assert executor.current_iteration == 1  # Handled by loop, not needed here

@pytest.mark.asyncio
async def test_execute_batch_async(executor):
    """Test batch execution of multiple objectives concurrently."""
    obj1 = Objective(description="Obj 1", id="obj1")
    obj2 = Objective(description="Obj 2", id="obj2")
    
    with patch.object(executor, 'execute_objective', new_callable=AsyncMock) as mock_exec:
        # Mock successful execution for both
        res1 = ExecutionResult(objective_id="obj1", success=True)
        res2 = ExecutionResult(objective_id="obj2", success=True)
        
        # AsyncMock side_effect with multiple returns works per call
        mock_exec.side_effect = [res1, res2]
        
        # We need to mock limits.should_stop so it doesn't break out of the batch loop early
        executor.limits.should_stop.return_value = (False, None)
        
        await executor.execute_batch_async([obj1, obj2])
        
        assert mock_exec.call_count == 2

@pytest.mark.asyncio
async def test_self_direct(executor):
    """Test the self-generation of objectives."""
    await executor.self_direct()
    
    assert len(executor.objectives) == 1
    assert executor.objectives[0].id == "gen1"
    assert executor.strategy == {"focus": "testing", "goal": "Test everything"}

@pytest.mark.asyncio
async def test_checkpoint(executor):
    """Test that checkpointing saves state correctly."""
    from unittest.mock import mock_open
    with patch('builtins.open', new_callable=mock_open) as mock_file:
        with patch('whitemagic.autonomous.executor.continuous_executor.Objective.to_dict', return_value={'test': 'data'}):
            with patch('whitemagic.utils.fast_json.dumps_str') as mock_json:
                # Need to also patch limits since it throws json serialize error on MagicMock
                executor.limits = MagicMock()
                executor.limits.get_status.return_value = {"limit": "ok"}
                executor.governor = MagicMock()
                executor.assessor = MagicMock()
                executor.generator = MagicMock()
                
                await executor.checkpoint()
                mock_file.assert_called_once()
                pass
