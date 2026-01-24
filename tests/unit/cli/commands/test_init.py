"""Test init command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from pymelos.cli.commands.init import handle_init, init_workspace


def test_init_workspace_defaults(tmp_path):
    init_workspace(tmp_path, name="test-workspace")

    # Check structure
    assert (tmp_path / "pymelos.yaml").exists()
    assert (tmp_path / "pyproject.toml").exists()
    assert (tmp_path / "packages").exists()
    assert (tmp_path / "app").exists()
    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / ".git").exists()

    # Check content
    config = yaml.safe_load((tmp_path / "pymelos.yaml").read_text())
    assert config["name"] == "test-workspace"
    assert "packages/*" in config["packages"]
    assert "app/*" in config["packages"]
    assert "test" in config["scripts"]
    assert "lint" in config["scripts"]  # Default use_ruff=True


def test_init_workspace_options(tmp_path):
    init_workspace(
        tmp_path,
        name="custom",
        description="Desc",
        type_checker="ty",
        use_ruff=False,
        use_pytest=True,
    )

    config = yaml.safe_load((tmp_path / "pymelos.yaml").read_text())
    assert "lint" not in config["scripts"]
    assert "typecheck" in config["scripts"]
    assert "ty check" in config["scripts"]["typecheck"]["run"]

    pyproject = (tmp_path / "pyproject.toml").read_text()
    assert "[tool.ty.environment]" in pyproject
    assert "ruff" not in pyproject


def test_handle_init_interactive(tmp_path):
    console = MagicMock()
    error_console = MagicMock()

    # Mock interactive wizard
    with patch("pymelos.cli.commands.init.init_interactive") as mock_interactive:
        mock_interactive.return_value = {
            "name": "interactive-ws",
            "description": "Interactive Desc",
            "type_checker": "pyright",
            "use_ruff": True,
            "use_pytest": False,
        }

        # Call handle_init without name to trigger interactive
        handle_init(tmp_path, None, console, error_console)

        mock_interactive.assert_called_once()

        # Verify file creation based on mocked inputs
        assert (tmp_path / "pymelos.yaml").exists()
        config = yaml.safe_load((tmp_path / "pymelos.yaml").read_text())
        assert config["name"] == "interactive-ws"
        assert "pyright" in config["scripts"]["typecheck"]["run"]
        assert "test" not in config["scripts"]  # use_pytest=False
