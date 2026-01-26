"""Tests for CLI application entry point using CliRunner."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from pymelos.cli.app import app

runner = CliRunner()


def test_version_flag():
    with patch("pymelos.__version__", "1.2.3"):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "pymelos 1.2.3" in result.stdout


def test_init_command_invocation():
    with patch("pymelos.cli.commands.init.handle_init") as mock_handle:
        result = runner.invoke(app, ["init", "my-repo"])
        assert result.exit_code == 0
        mock_handle.assert_called_once()


def test_bootstrap_command_invocation():
    with (
        patch("pymelos.cli.app.get_workspace"),
        patch("pymelos.commands.handle_bootstrap", new_callable=AsyncMock) as mock_handle,
    ):
        result = runner.invoke(app, ["bootstrap", "--clean"])
        assert result.exit_code == 0
        mock_handle.assert_called_once()
        assert mock_handle.call_args[1]["clean_first"] is True


def test_add_command_invocation():
    with (
        patch("pymelos.cli.app.get_workspace"),
        patch("pymelos.commands.handle_add_project", new_callable=AsyncMock) as mock_handle,
    ):
        result = runner.invoke(app, ["add", "pkg-a", "--project-type", "app"])
        assert result.exit_code == 0
        mock_handle.assert_called_once()
        assert mock_handle.call_args[1]["project_type"] == "app"


def test_run_command_invocation():
    with (
        patch("pymelos.cli.app.get_workspace") as mock_get_ws,
        patch("pymelos.commands.handle_run_script", new_callable=AsyncMock) as mock_handle,
    ):
        # Mock script config lookup
        mock_ws = MagicMock()
        mock_get_ws.return_value = mock_ws

        result = runner.invoke(app, ["run", "test", "--concurrency", "8"])
        assert result.exit_code == 0
        mock_handle.assert_called_once()
        assert mock_handle.call_args[1]["concurrency"] == 8


def test_exec_command_invocation():
    with (
        patch("pymelos.cli.app.get_workspace"),
        patch("pymelos.commands.handle_exec_command", new_callable=AsyncMock) as mock_handle,
    ):
        result = runner.invoke(app, ["exec", "ls -la", "--scope", "pkg-*"])
        assert result.exit_code == 0
        mock_handle.assert_called_once()
        assert mock_handle.call_args[1]["scope"] == "pkg-*"


def test_list_command_invocation():
    with (
        patch("pymelos.cli.app.get_workspace"),
        patch("pymelos.cli.app.handle_list_command") as mock_handle,
    ):
        result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0
        mock_handle.assert_called_once()
        assert mock_handle.call_args[1]["json_output"] is True


def test_clean_command_invocation():
    with (
        patch("pymelos.cli.app.get_workspace"),
        patch("pymelos.commands.handle_clean_command", new_callable=AsyncMock) as mock_handle,
    ):
        result = runner.invoke(app, ["clean", "--dry-run"])
        assert result.exit_code == 0
        mock_handle.assert_called_once()
        assert mock_handle.call_args[1]["dry_run"] is True


def test_export_command_invocation():
    with (
        patch("pymelos.cli.app.get_workspace"),
        patch(
            "pymelos.commands.export.handle_export_command", new_callable=AsyncMock
        ) as mock_handle,
    ):
        result = runner.invoke(app, ["export", "pkg-a", "--output", "build"])
        assert result.exit_code == 0
        mock_handle.assert_called_once()
        assert mock_handle.call_args[1]["package_name"] == "pkg-a"
        assert mock_handle.call_args[1]["output"] == "build"


def test_run_command_interactive_trigger():
    """Test that run command triggers interactive mode if no script provided."""
    with (
        patch("pymelos.cli.app.get_workspace") as mock_get_ws,
        patch("pymelos.interactive.select_script") as mock_select_script,
        patch("pymelos.interactive.select_execution_options") as mock_select_opts,
        patch("pymelos.commands.handle_run_script", new_callable=AsyncMock) as mock_handle,
    ):
        # Setup workspace with scripts
        mock_ws = MagicMock()
        from pymelos.config.schema import ScriptConfig

        mock_ws.config.scripts = {"test": ScriptConfig(run="pytest")}
        mock_get_ws.return_value = mock_ws

        # Mock selections
        mock_select_script.return_value = "test"
        # Mock scope selection to return "all" so we don't need to select packages
        mock_select_opts.return_value = {"scope": "all"}

        # Run without script arg
        result = runner.invoke(app, ["run"])

        assert result.exit_code == 0, f"Output: {result.stdout}"
        mock_select_script.assert_called_once()
        mock_select_opts.assert_called_once()
        mock_handle.assert_called_once()
        assert mock_handle.call_args[1]["script_name"] == "test"


def test_changed_command_interactive_trigger():
    """Test that changed command triggers interactive mode if no since provided."""
    with (
        patch("pymelos.cli.app.get_workspace") as mock_get_ws,
        patch("pymelos.git.repo.get_recent_refs") as mock_get_refs,
        patch("pymelos.interactive.select_git_reference") as mock_select_ref,
        patch("pymelos.commands.changed.get_changed_packages") as mock_get_packages,
        # Patching select_package_for_review ensures we don't hit IO if review runs
        patch("pymelos.interactive.select_package_for_review") as mock_select_pkg,
        patch("pymelos.cli.app.console"),
    ):
        mock_ws = MagicMock()
        from pathlib import Path

        mock_ws.root = Path("root")
        mock_get_ws.return_value = mock_ws

        # Mock git refs and selection
        mock_get_refs.return_value = [("main", "main")]
        mock_select_ref.return_value = "main"

        # Mock changed packages
        mock_pkg = MagicMock()
        mock_pkg.name = "pkg"
        mock_result = MagicMock()
        mock_result.changed = [mock_pkg]
        mock_get_packages.return_value = mock_result

        # Mock package selection to Exit immediately
        mock_select_pkg.return_value = None

        # Run without args
        result = runner.invoke(app, ["changed"])

        assert result.exit_code == 0, f"Output: {result.stdout}, Exc: {result.exception}"
        mock_select_ref.assert_called_once()
        # Verify review loop started (by checking if package selection was attempted)
        mock_select_pkg.assert_called_once()
