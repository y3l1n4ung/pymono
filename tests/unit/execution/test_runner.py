"""Test execution runner."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pymelos.execution.runner import run_command, run_in_package
from pymelos.workspace.package import Package


@pytest.mark.asyncio
async def test_run_command_success():
    with patch("asyncio.create_subprocess_shell") as mock_create:
        # Mock process
        process = AsyncMock()
        process.returncode = 0
        process.wait.return_value = None

        # Mock streams
        async def mock_read():
            yield b"line1\n"
            yield b"line2\n"

        process.stdout = AsyncMock()
        process.stdout.readline.side_effect = [b"stdout\n", b""]
        process.stderr = AsyncMock()
        process.stderr.readline.side_effect = [b"stderr\n", b""]

        mock_create.return_value = process

        exit_code, stdout, stderr, duration = await run_command(
            "echo test", cwd=Path("."), timeout=1.0
        )

        assert exit_code == 0
        assert "stdout" in stdout
        assert "stderr" in stderr
        assert duration >= 0


@pytest.mark.asyncio
async def test_run_command_timeout():
    with patch("asyncio.create_subprocess_shell") as mock_create:
        process = AsyncMock()
        # kill is synchronous method
        process.kill = MagicMock()
        # wait is async
        process.wait.return_value = None

        process.stdout = AsyncMock()
        process.stdout.readline.side_effect = [b""]
        process.stderr = AsyncMock()
        process.stderr.readline.side_effect = [b""]

        mock_create.return_value = process

        # Mock wait_for to raise TimeoutError
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            exit_code, stdout, stderr, duration = await run_command(
                "sleep 10", cwd=Path("."), timeout=0.1
            )

            assert exit_code == -1
            assert "timed out" in stderr
            process.kill.assert_called_once()
            process.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_command_callbacks():
    stdout_cb = MagicMock()
    stderr_cb = MagicMock()

    with patch("asyncio.create_subprocess_shell") as mock_create:
        process = AsyncMock()
        process.returncode = 0
        process.stdout = AsyncMock()
        process.stdout.readline.side_effect = [b"out\n", b""]
        process.stderr = AsyncMock()
        process.stderr.readline.side_effect = [b"err\n", b""]
        mock_create.return_value = process

        await run_command("cmd", cwd=Path("."), on_stdout=stdout_cb, on_stderr=stderr_cb)

        stdout_cb.assert_called_with("out")
        stderr_cb.assert_called_with("err")


@pytest.mark.asyncio
async def test_run_in_package():
    pkg = MagicMock(spec=Package)
    pkg.name = "pkg-a"
    pkg.path = Path("/path/to/pkg-a")
    pkg.version = "1.0.0"

    with patch("pymelos.execution.runner.run_command") as mock_run:
        mock_run.return_value = (0, "ok", "", 10)

        result = await run_in_package(pkg, "cmd")

        assert result.success
        assert result.package_name == "pkg-a"

        # Check env injection
        call_kwargs = mock_run.call_args.kwargs
        env = call_kwargs["env"]
        assert env["PYMELOS_PACKAGE_NAME"] == "pkg-a"
        assert str(env["PYMELOS_PACKAGE_PATH"]) == "/path/to/pkg-a"
        assert env["PYMELOS_PACKAGE_VERSION"] == "1.0.0"


@pytest.mark.asyncio
async def test_run_command_error():
    with patch("asyncio.create_subprocess_shell") as mock_create:
        process = AsyncMock()
        process.returncode = 1
        process.stdout.readline.side_effect = [b""]
        process.stderr.readline.side_effect = [b"error\n", b""]
        mock_create.return_value = process

        exit_code, stdout, stderr, duration = await run_command("fail", cwd=Path("."))

        assert exit_code == 1
        assert "error" in stderr


@pytest.mark.asyncio
async def test_run_command_exception():
    with patch("asyncio.create_subprocess_shell", side_effect=ValueError("Boom")):
        exit_code, stdout, stderr, duration = await run_command("fail", cwd=Path("."))

        assert exit_code == -1
        assert "Boom" in stderr
