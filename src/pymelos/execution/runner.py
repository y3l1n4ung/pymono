"""Command execution engine with standard asynchronous capture."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pymelos.execution.results import ExecutionResult

if TYPE_CHECKING:
    from pymelos.workspace.package import Package


async def run_command(
    command: str,
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> tuple[int, str, str, int]:
    """Run a shell command asynchronously.

    Args:
        command: Shell command to execute.
        cwd: Working directory.
        env: Environment variables (merged with current env).
        timeout: Timeout in seconds.

    Returns:
        Tuple of (exit_code, stdout, stderr, duration_ms).
    """
    # Merge environment
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    start_time = time.monotonic()

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=run_env,
        )

        try:
            # Use communicate to wait for the process and capture all output at once
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, TimeoutError):
            process.kill()
            await process.wait()
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return -1, "", f"Command timed out after {timeout}s", duration_ms

        duration_ms = int((time.monotonic() - start_time) * 1000)

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        return process.returncode or 0, stdout, stderr, duration_ms

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return -1, "", str(e), duration_ms


async def run_in_package(
    package: Package,
    command: str,
    *,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> ExecutionResult:
    """Run a command in a package directory.

    Args:
        package: Package to run command in.
        command: Shell command to execute.
        env: Additional environment variables.
        timeout: Timeout in seconds.

    Returns:
        Execution result.
    """
    print(package.name, command)
    # Build environment with package-specific variables
    run_env = env.copy() if env else {}
    run_env["PYMELOS_PACKAGE_NAME"] = package.name
    run_env["PYMELOS_PACKAGE_PATH"] = str(package.path)
    run_env["PYMELOS_PACKAGE_VERSION"] = package.version

    exit_code, stdout, stderr, duration_ms = await run_command(
        command,
        cwd=package.path,
        env=run_env,
        timeout=timeout,
    )

    if exit_code == 0:
        return ExecutionResult.success_result(
            package_name=package.name,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            command=command,
        )
    else:
        return ExecutionResult.failure_result(
            package_name=package.name,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            command=command,
        )


def run_command_sync(
    command: str,
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> tuple[int, str, str, int]:
    """Run a shell command synchronously.

    Args:
        command: Shell command to execute.
        cwd: Working directory.
        env: Environment variables.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (exit_code, stdout, stderr, duration_ms).
    """
    import subprocess

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    start_time = time.monotonic()

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=run_env,
            timeout=timeout,
        )
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return result.returncode, result.stdout, result.stderr, duration_ms

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return -1, "", f"Command timed out after {timeout}s", duration_ms

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        return -1, "", str(e), duration_ms
