"""Tests for run command."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymelos.commands.base import CommandContext
from pymelos.commands.run import RunCommand, RunOptions, run_script
from pymelos.errors import ScriptNotFoundError
from pymelos.workspace.workspace import Workspace


class TestRunCommand:
    """Tests for RunCommand."""

    @pytest.fixture
    def workspace_with_scripts(self, temp_dir: Path) -> Path:
        """Create workspace with scripts defined."""
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("""
name: test-workspace
packages:
  - packages/*

scripts:
  test:
    run: echo "running tests"
    description: Run tests
  lint:
    run: echo "linting"
    scope: "pkg-*"
  build:
    run: echo "building"
    topological: true
    fail_fast: true
""")

        # Create pyproject.toml
        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-workspace"
version = "0.0.0"

[tool.uv.workspace]
members = ["packages/*"]
""")

        # Create packages
        packages_dir = temp_dir / "packages"
        packages_dir.mkdir()

        for name in ["pkg-a", "pkg-b"]:
            pkg_dir = packages_dir / name
            pkg_dir.mkdir()
            (pkg_dir / "pyproject.toml").write_text(f"""
[project]
name = "{name}"
version = "1.0.0"
""")
            src_dir = pkg_dir / "src" / name.replace("-", "_")
            src_dir.mkdir(parents=True)
            (src_dir / "__init__.py").write_text('__version__ = "1.0.0"\n')

        return temp_dir

    async def test_runs_script_in_packages(self, workspace_with_scripts: Path) -> None:
        """Should run script in all packages."""
        workspace = Workspace.discover(workspace_with_scripts)
        result = await run_script(workspace, "test")

        assert len(result.results) == 2

    async def test_script_not_found_error(self, workspace_with_scripts: Path) -> None:
        """Should raise error for unknown script."""
        workspace = Workspace.discover(workspace_with_scripts)

        with pytest.raises(ScriptNotFoundError):
            await run_script(workspace, "nonexistent")

    async def test_respects_script_scope(self, workspace_with_scripts: Path) -> None:
        """Should use script's scope if defined."""
        workspace = Workspace.discover(workspace_with_scripts)
        result = await run_script(workspace, "lint")

        # lint has scope "pkg-*" which matches both packages
        assert len(result.results) == 2

    async def test_command_scope_overrides_script(self, workspace_with_scripts: Path) -> None:
        """Command scope should override script scope."""
        workspace = Workspace.discover(workspace_with_scripts)
        result = await run_script(workspace, "test", scope="pkg-a")

        assert len(result.results) == 1
        assert result.results[0].package_name == "pkg-a"

    async def test_returns_empty_for_no_packages(self, workspace_with_scripts: Path) -> None:
        """Should return empty result if no packages match."""
        workspace = Workspace.discover(workspace_with_scripts)
        result = await run_script(workspace, "test", scope="nonexistent")

        assert len(result.results) == 0


class TestRunCommandClass:
    """Tests for RunCommand class directly."""

    @pytest.fixture
    def workspace_with_scripts(self, temp_dir: Path) -> Workspace:
        """Create workspace with scripts defined."""
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("""
name: test-workspace
packages:
  - packages/*

scripts:
  test:
    run: echo "test"
  custom:
    run: echo "custom"
    scope: "pkg-a"
""")

        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-workspace"
version = "0.0.0"

[tool.uv.workspace]
members = ["packages/*"]
""")

        packages_dir = temp_dir / "packages"
        packages_dir.mkdir()

        for name in ["pkg-a", "pkg-b"]:
            pkg_dir = packages_dir / name
            pkg_dir.mkdir()
            (pkg_dir / "pyproject.toml").write_text(f"""
[project]
name = "{name}"
version = "1.0.0"
""")
            src_dir = pkg_dir / "src" / name.replace("-", "_")
            src_dir.mkdir(parents=True)
            (src_dir / "__init__.py").write_text('__version__ = "1.0.0"\n')

        return Workspace.discover(temp_dir)

    def test_validate_returns_errors_for_missing_script(
        self, workspace_with_scripts: Workspace
    ) -> None:
        """Should return validation errors for missing script."""
        context = CommandContext(workspace=workspace_with_scripts)
        options = RunOptions(script_name="nonexistent")
        cmd = RunCommand(context, options)

        errors = cmd.validate()
        assert len(errors) > 0
        assert "nonexistent" in errors[0]

    def test_validate_returns_empty_for_valid_script(
        self, workspace_with_scripts: Workspace
    ) -> None:
        """Should return no errors for valid script."""
        context = CommandContext(workspace=workspace_with_scripts)
        options = RunOptions(script_name="test")
        cmd = RunCommand(context, options)

        errors = cmd.validate()
        assert len(errors) == 0

    def test_get_packages_uses_script_scope(
        self, workspace_with_scripts: Workspace
    ) -> None:
        """Should use script's scope when getting packages."""
        context = CommandContext(workspace=workspace_with_scripts)
        options = RunOptions(script_name="custom")  # has scope "pkg-a"
        cmd = RunCommand(context, options)

        packages = cmd.get_packages()
        assert len(packages) == 1
        assert packages[0].name == "pkg-a"


class TestRunEdgeCases:
    """Edge case tests for run command."""

    @pytest.fixture
    def workspace_with_scripts(self, temp_dir: Path) -> Path:
        """Create workspace with various scripts."""
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("""
name: test-workspace
packages:
  - packages/*

scripts:
  passing:
    run: "true"
  failing:
    run: "false"
  with_env:
    run: echo $MY_VAR
    env:
      MY_VAR: "test_value"
""")

        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\nversion = "0.0.0"\n')

        pkg = temp_dir / "packages" / "pkg-a"
        pkg.mkdir(parents=True)
        (pkg / "pyproject.toml").write_text('[project]\nname = "pkg-a"\nversion = "1.0.0"\n')

        return temp_dir

    async def test_script_with_failing_command(self, workspace_with_scripts: Path) -> None:
        """Should report failure for failing script."""
        workspace = Workspace.discover(workspace_with_scripts)
        result = await run_script(workspace, "failing")

        assert any(not r.success for r in result.results)

    async def test_script_with_env_vars(self, workspace_with_scripts: Path) -> None:
        """Should pass environment variables to script."""
        workspace = Workspace.discover(workspace_with_scripts)
        result = await run_script(workspace, "with_env")

        assert any("test_value" in r.stdout for r in result.results)

    async def test_empty_workspace_with_script(self, temp_dir: Path) -> None:
        """Should return empty result for workspace with no packages."""
        pymelos_yaml = temp_dir / "pymelos.yaml"
        config = "name: empty\npackages:\n  - packages/*\nscripts:\n  test:\n    run: echo hi\n"
        pymelos_yaml.write_text(config)
        (temp_dir / "packages").mkdir()

        workspace = Workspace.discover(temp_dir)
        result = await run_script(workspace, "test")

        assert len(result.results) == 0

    def test_run_options_defaults(self) -> None:
        """Should have correct default options."""
        options = RunOptions(script_name="test")
        assert options.concurrency == 4
        assert options.fail_fast is False
        assert options.topological is True
