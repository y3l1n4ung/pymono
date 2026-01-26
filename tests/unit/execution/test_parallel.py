"""Test parallel execution."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pymelos.execution.parallel import ParallelExecutor
from pymelos.execution.results import ExecutionResult, ExecutionStatus
from pymelos.workspace.package import Package


@pytest.fixture
def mock_packages():
    pkg1 = MagicMock(spec=Package)
    pkg1.name = "pkg1"
    pkg2 = MagicMock(spec=Package)
    pkg2.name = "pkg2"
    pkg3 = MagicMock(spec=Package)
    pkg3.name = "pkg3"
    return [pkg1, pkg2, pkg3]


@pytest.mark.asyncio
async def test_execute_success(mock_packages):
    executor = ParallelExecutor(concurrency=2)

    with patch("pymelos.execution.parallel.run_in_package") as mock_run:
        mock_run.side_effect = [
            ExecutionResult("pkg1", ExecutionStatus.SUCCESS, 0),
            ExecutionResult("pkg2", ExecutionStatus.SUCCESS, 0),
            ExecutionResult("pkg3", ExecutionStatus.SUCCESS, 0),
        ]

        result = await executor.execute(mock_packages, "echo hello")

        assert result.all_success
        assert len(result.results) == 3
        assert mock_run.call_count == 3


@pytest.mark.asyncio
async def test_execute_fail_fast(mock_packages):
    executor = ParallelExecutor(concurrency=1, fail_fast=True)

    # pkg1 fails, pkg2 should be cancelled/skipped
    with patch("pymelos.execution.parallel.run_in_package") as mock_run:
        mock_run.side_effect = [
            ExecutionResult("pkg1", ExecutionStatus.FAILURE, 1),
            # pkg2 might be called if concurrency > 1, but here = 1.
            # Next call should be skipped or cancelled logic triggered
        ]

        result = await executor.execute(mock_packages, "echo hello")

        assert not result.all_success
        # pkg1 failed. pkg2, pkg3 should be cancelled or not run.
        # Since we run tasks immediately, they might be "CANCELLED" in result.

        pkg1_res = next(r for r in result.results if r.package_name == "pkg1")
        assert pkg1_res.failed

        other_res = [r for r in result.results if r.package_name != "pkg1"]
        for r in other_res:
            assert r.status == ExecutionStatus.CANCELLED


@pytest.mark.asyncio
async def test_execute_batches(mock_packages):
    executor = ParallelExecutor()
    batches = [
        [mock_packages[0]],  # Batch 1: pkg1
        [mock_packages[1], mock_packages[2]],  # Batch 2: pkg2, pkg3
    ]

    with patch("pymelos.execution.parallel.run_in_package") as mock_run:
        mock_run.return_value = ExecutionResult("pkg", ExecutionStatus.SUCCESS, 0)

        result = await executor.execute_batches(iter(batches), "echo hello")

        assert result.all_success
        assert len(result.results) == 3
        assert mock_run.call_count == 3


@pytest.mark.asyncio
async def test_execute_output_handler(mock_packages):
    executor = ParallelExecutor()
    handler = MagicMock()

    with patch("pymelos.execution.parallel.run_in_package") as mock_run:
        # Mock run_in_package calling callbacks
        async def side_effect(pkg, cmd, on_stdout, on_stderr, **kwargs):
            if on_stdout:
                on_stdout("stdout line")
            if on_stderr:
                on_stderr("stderr line")
            return ExecutionResult(pkg.name, ExecutionStatus.SUCCESS, 0)

        mock_run.side_effect = side_effect

        await executor.execute([mock_packages[0]], "echo hello", output_handler=handler)

        assert handler.call_count == 2
        # Check calls: (pkg_name, line, is_stderr)
        assert handler.call_args_list[0][0] == ("pkg1", "stdout line", False)
        assert handler.call_args_list[1][0] == ("pkg1", "stderr line", True)


@pytest.mark.asyncio
async def test_stream_execution(mock_packages):
    executor = ParallelExecutor()

    with patch("pymelos.execution.parallel.run_in_package") as mock_run:
        mock_run.return_value = ExecutionResult("pkg", ExecutionStatus.SUCCESS, 0)

        results = []
        async for res in executor.stream(mock_packages, "echo hello"):
            results.append(res)

        assert len(results) == 3
