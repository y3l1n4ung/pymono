"""Parallel command execution with concurrency control."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterator

from pymelos.execution.results import BatchResult, ExecutionResult, ExecutionStatus
from pymelos.execution.runner import run_in_package
from pymelos.workspace.package import Package


class ParallelExecutor:
    """Execute commands across packages with controlled parallelism.

    Supports topological ordering and fail-fast behavior.

    Attributes:
        concurrency: Maximum number of concurrent executions.
        fail_fast: Stop on first failure.
    """

    def __init__(
        self,
        concurrency: int = 4,
        fail_fast: bool = False,
    ) -> None:
        """Initialize executor.

        Args:
            concurrency: Maximum parallel executions.
            fail_fast: Stop on first failure.
        """
        self.concurrency = max(1, concurrency)
        self.fail_fast = fail_fast
        self._cancelled = False

    async def execute(
        self,
        packages: list[Package],
        command: str,
        *,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
        output_handler: Callable[[str, str, bool], None] | None = None,
    ) -> BatchResult:
        """Execute command across packages in parallel.

        Args:
            packages: Packages to run command in.
            command: Shell command to execute.
            env: Environment variables.
            timeout: Per-package timeout in seconds.
            output_handler: Callback (pkg_name, line, is_stderr) for streaming output.

        Returns:
            Batch result with all execution results.
        """
        results: list[ExecutionResult] = []
        self._cancelled = False

        semaphore = asyncio.Semaphore(self.concurrency)

        async def run_one(pkg: Package) -> ExecutionResult:
            if self._cancelled:
                return ExecutionResult(
                    package_name=pkg.name,
                    status=ExecutionStatus.CANCELLED,
                    exit_code=-1,
                )

            async with semaphore:
                if self._cancelled:
                    return ExecutionResult(
                        package_name=pkg.name,
                        status=ExecutionStatus.CANCELLED,
                        exit_code=-1,
                    )

                on_out = None
                on_err = None
                if output_handler:
                    handler = output_handler

                    def _on_out(line: str) -> None:
                        handler(pkg.name, line, False)

                    def _on_err(line: str) -> None:
                        handler(pkg.name, line, True)

                    on_out = _on_out
                    on_err = _on_err

                result = await run_in_package(
                    pkg,
                    command,
                    env=env,
                    timeout=timeout,
                    on_stdout=on_out,
                    on_stderr=on_err,
                )

                if self.fail_fast and result.failed:
                    self._cancelled = True

                return result

        tasks = [asyncio.create_task(run_one(pkg)) for pkg in packages]
        results = await asyncio.gather(*tasks)

        return BatchResult(results=list(results))

    async def execute_batches(
        self,
        batches: Iterator[list[Package]],
        command: str,
        *,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
        output_handler: Callable[[str, str, bool], None] | None = None,
    ) -> BatchResult:
        """Execute command across package batches (topological order).

        Each batch is executed in parallel, but batches are sequential.

        Args:
            batches: Iterator of package batches (from parallel_batches).
            command: Shell command to execute.
            env: Environment variables.
            timeout: Per-package timeout in seconds.
            output_handler: Callback (pkg_name, line, is_stderr) for streaming output.

        Returns:
            Batch result with all execution results.
        """
        all_results: list[ExecutionResult] = []
        self._cancelled = False

        for batch in batches:
            if self._cancelled:
                # Mark remaining as cancelled
                for pkg in batch:
                    all_results.append(
                        ExecutionResult(
                            package_name=pkg.name,
                            status=ExecutionStatus.CANCELLED,
                            exit_code=-1,
                        )
                    )
                continue

            batch_result = await self.execute(
                batch,
                command,
                env=env,
                timeout=timeout,
                output_handler=output_handler,
            )
            all_results.extend(batch_result.results)

            if self.fail_fast and batch_result.any_failure:
                self._cancelled = True

        return BatchResult(results=all_results)

    async def stream(
        self,
        packages: list[Package],
        command: str,
        *,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[ExecutionResult]:
        """Stream execution results as they complete.

        Args:
            packages: Packages to run command in.
            command: Shell command to execute.
            env: Environment variables.
            timeout: Per-package timeout in seconds.

        Yields:
            Execution results as they complete.
        """
        self._cancelled = False
        semaphore = asyncio.Semaphore(self.concurrency)

        async def run_one(pkg: Package) -> ExecutionResult:
            if self._cancelled:
                return ExecutionResult(
                    package_name=pkg.name,
                    status=ExecutionStatus.CANCELLED,
                    exit_code=-1,
                )

            async with semaphore:
                return await run_in_package(pkg, command, env=env, timeout=timeout)

        tasks = {asyncio.create_task(run_one(pkg)): pkg for pkg in packages}
        pending = set(tasks.keys())

        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                result = task.result()
                yield result

                if self.fail_fast and result.failed:
                    self._cancelled = True
                    # Cancel pending tasks
                    for p in pending:
                        p.cancel()

    def cancel(self) -> None:
        """Cancel ongoing executions."""
        self._cancelled = True


async def execute_parallel(
    packages: list[Package],
    command: str,
    *,
    concurrency: int = 4,
    fail_fast: bool = False,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> BatchResult:
    """Convenience function for parallel execution.

    Args:
        packages: Packages to run command in.
        command: Shell command to execute.
        concurrency: Maximum parallel executions.
        fail_fast: Stop on first failure.
        env: Environment variables.
        timeout: Per-package timeout in seconds.

    Returns:
        Batch result with all execution results.
    """
    executor = ParallelExecutor(concurrency=concurrency, fail_fast=fail_fast)
    return await executor.execute(packages, command, env=env, timeout=timeout)


async def execute_topological(
    batches: Iterator[list[Package]],
    command: str,
    *,
    concurrency: int = 4,
    fail_fast: bool = False,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> BatchResult:
    """Execute command in topological order.

    Args:
        batches: Package batches from workspace.parallel_batches().
        command: Shell command to execute.
        concurrency: Maximum parallel executions per batch.
        fail_fast: Stop on first failure.
        env: Environment variables.
        timeout: Per-package timeout in seconds.

    Returns:
        Batch result with all execution results.
    """
    executor = ParallelExecutor(concurrency=concurrency, fail_fast=fail_fast)
    return await executor.execute_batches(batches, command, env=env, timeout=timeout)
