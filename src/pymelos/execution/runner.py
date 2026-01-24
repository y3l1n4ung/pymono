"""Command execution engine with standard asynchronous capture."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from pymelos.execution.results import ExecutionResult

if TYPE_CHECKING:
    from pymelos.workspace.package import Package


async def _read_stream(
    stream: asyncio.StreamReader,
    callback: Callable[[str], None] | None,
    buffer: list[str],
) -> None:
    """Read from stream line by line."""
    while True:
        line = await stream.readline()
        if not line:
            break
        decoded = line.decode("utf-8", errors="replace")
        buffer.append(decoded)
        if callback:
            # Strip newline for display as print usually adds one
            callback(decoded.rstrip())


async def run_command(
    command: str,
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    on_stdout: Callable[[str], None] | None = None,
    on_stderr: Callable[[str], None] | None = None,
) -> tuple[int, str, str, int]:
    """Run a shell command asynchronously.

    Args:
        command: Shell command to execute.
        cwd: Working directory.
        env: Environment variables (merged with current env).
        timeout: Timeout in seconds.
        on_stdout: Callback for stdout lines.
        on_stderr: Callback for stderr lines.

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

        if process.stdout is None or process.stderr is None:
            raise RuntimeError("Process stdout/stderr is None")

        stdout_buffer: list[str] = []
        stderr_buffer: list[str] = []

        try:
            # Read streams concurrently
            await asyncio.wait_for(
                asyncio.gather(
                    _read_stream(process.stdout, on_stdout, stdout_buffer),
                    _read_stream(process.stderr, on_stderr, stderr_buffer),
                    process.wait(),
                ),
                timeout=timeout,
            )
        except (asyncio.TimeoutError, TimeoutError):
            process.kill()
            await process.wait()
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return -1, "", f"Command timed out after {timeout}s", duration_ms

        duration_ms = int((time.monotonic() - start_time) * 1000)

        stdout = "".join(stdout_buffer)
        stderr = "".join(stderr_buffer)

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
    on_stdout: Callable[[str], None] | None = None,
    on_stderr: Callable[[str], None] | None = None,
) -> ExecutionResult:
    """Run a command in a package directory.

    Args:
        package: Package to run command in.
        command: Shell command to execute.
        env: Additional environment variables.
        timeout: Timeout in seconds.
        on_stdout: Callback for stdout lines.
        on_stderr: Callback for stderr lines.

    Returns:
        Execution result.
    """
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
        on_stdout=on_stdout,
        on_stderr=on_stderr,
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
