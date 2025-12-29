"""Tests for exec command."""

from __future__ import annotations

from pathlib import Path

from pymelos.commands.base import CommandContext
from pymelos.commands.exec import ExecCommand, ExecOptions, exec_command
from pymelos.workspace.workspace import Workspace


class TestExecCommand:
    """Tests for ExecCommand."""

    async def test_executes_command_in_packages(self, workspace_dir: Path) -> None:
        """Should execute command in all packages."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo hello")

        assert len(result.results) == 3
        for r in result.results:
            assert r.success
            assert "hello" in r.stdout

    async def test_scope_filter(self, workspace_dir: Path) -> None:
        """Should filter packages by scope."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo test", scope="pkg-a")

        assert len(result.results) == 1
        assert result.results[0].package_name == "pkg-a"

    async def test_ignore_filter(self, workspace_dir: Path) -> None:
        """Should exclude packages matching ignore."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo test", ignore=["pkg-c"])

        names = [r.package_name for r in result.results]
        assert "pkg-c" not in names
        assert len(result.results) == 2

    async def test_returns_empty_for_no_packages(self, workspace_dir: Path) -> None:
        """Should return empty result if no packages match."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo test", scope="nonexistent")

        assert len(result.results) == 0

    async def test_captures_stdout(self, workspace_dir: Path) -> None:
        """Should capture command stdout."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo captured_output")

        assert all("captured_output" in r.stdout for r in result.results)

    async def test_captures_stderr(self, workspace_dir: Path) -> None:
        """Should capture command stderr."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo error >&2")

        assert all("error" in r.stderr for r in result.results)

    async def test_reports_exit_code(self, workspace_dir: Path) -> None:
        """Should report command exit code."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "exit 0")

        assert all(r.exit_code == 0 for r in result.results)

    async def test_fail_fast_stops_on_error(self, workspace_dir: Path) -> None:
        """Should stop on first failure when fail_fast=True."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(
            workspace,
            "exit 1",
            fail_fast=True,
            concurrency=1,  # Ensure sequential to test fail_fast
        )

        # At least one failed, possibly stopped early
        failed = [r for r in result.results if not r.success]
        assert len(failed) >= 1


class TestExecCommandClass:
    """Tests for ExecCommand class directly."""

    def test_get_packages_applies_scope(self, workspace_dir: Path) -> None:
        """Should apply scope filter."""
        workspace = Workspace.discover(workspace_dir)
        context = CommandContext(workspace=workspace)
        options = ExecOptions(command="echo", scope="pkg-a")
        cmd = ExecCommand(context, options)

        packages = cmd.get_packages()
        assert len(packages) == 1
        assert packages[0].name == "pkg-a"

    def test_get_packages_applies_ignore(self, workspace_dir: Path) -> None:
        """Should apply ignore filter."""
        workspace = Workspace.discover(workspace_dir)
        context = CommandContext(workspace=workspace)
        options = ExecOptions(command="echo", ignore=["pkg-c"])
        cmd = ExecCommand(context, options)

        packages = cmd.get_packages()
        names = [p.name for p in packages]
        assert "pkg-c" not in names

    def test_options_defaults(self) -> None:
        """Should have correct default options."""
        options = ExecOptions(command="test")
        assert options.concurrency == 4
        assert options.fail_fast is False
        assert options.topological is False
        assert options.scope is None


class TestExecEdgeCases:
    """Edge case tests for exec command."""

    async def test_command_with_spaces(self, workspace_dir: Path) -> None:
        """Should handle commands with spaces."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo hello world")

        assert all("hello world" in r.stdout for r in result.results)

    async def test_command_with_quotes(self, workspace_dir: Path) -> None:
        """Should handle commands with quoted strings."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, 'echo "quoted string"')

        assert all("quoted string" in r.stdout for r in result.results)

    async def test_command_with_pipe(self, workspace_dir: Path) -> None:
        """Should handle commands with pipes."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo test | cat")

        assert all("test" in r.stdout for r in result.results)

    async def test_nonexistent_command(self, workspace_dir: Path) -> None:
        """Should report failure for nonexistent command."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "nonexistent_cmd_12345")

        assert all(not r.success for r in result.results)

    async def test_empty_workspace(self, temp_dir: Path) -> None:
        """Should return empty result for workspace with no packages."""
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("name: empty\npackages:\n  - packages/*\n")
        (temp_dir / "packages").mkdir()

        workspace = Workspace.discover(temp_dir)
        result = await exec_command(workspace, "echo test")

        assert len(result.results) == 0

    async def test_working_directory(self, workspace_dir: Path) -> None:
        """Should execute command in package directory."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "pwd", scope="pkg-a")

        assert "pkg-a" in result.results[0].stdout

    async def test_concurrent_execution(self, workspace_dir: Path) -> None:
        """Should execute concurrently with multiple packages."""
        workspace = Workspace.discover(workspace_dir)
        result = await exec_command(workspace, "echo test", concurrency=3)

        assert len(result.results) == 3
        assert all(r.success for r in result.results)
