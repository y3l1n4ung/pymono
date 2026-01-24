"""Test export command."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymelos.commands.base import CommandContext
from pymelos.commands.export import ExportCommand, ExportOptions
from pymelos.workspace import Package
from pymelos.workspace.workspace import Workspace


@pytest.fixture
def mock_workspace(tmp_path):
    workspace = MagicMock(spec=Workspace)
    workspace.root = tmp_path
    workspace.packages = {}

    def get_package(name):
        return workspace.packages.get(name)

    workspace.get_package.side_effect = get_package
    return workspace


def create_mock_package(name, path, deps=None):
    pkg = MagicMock(spec=Package)
    pkg.name = name
    pkg.path = path
    pkg.workspace_dependencies = deps or set()
    return pkg


@pytest.mark.asyncio
async def test_export_command_structure(mock_workspace, tmp_path):
    # Setup packages: app -> lib -> utils
    pkg_utils = create_mock_package("utils", tmp_path / "packages" / "utils")
    pkg_lib = create_mock_package("lib", tmp_path / "packages" / "lib", {"utils"})
    pkg_app = create_mock_package("app", tmp_path / "packages" / "app", {"lib"})

    mock_workspace.packages = {"app": pkg_app, "lib": pkg_lib, "utils": pkg_utils}

    # Create physical directories
    for pkg in [pkg_app, pkg_lib, pkg_utils]:
        pkg.path.mkdir(parents=True)
        (pkg.path / "pyproject.toml").touch()
        (pkg.path / "src").mkdir()
        (pkg.path / "src" / "code.py").touch()

    output_dir = tmp_path / "dist"

    context = CommandContext(workspace=mock_workspace)
    options = ExportOptions(package_name="app", output=str(output_dir))

    # Mock lock generation to avoid actual uv calls
    with patch("pymelos.commands.export.lock") as mock_lock:
        cmd = ExportCommand(context, options)
        result = await cmd.execute()

        assert result.success
        assert len(result.packages_exported) == 3
        assert set(result.packages_exported) == {"app", "lib", "utils"}

        # Verify structure
        assert (output_dir / "pyproject.toml").exists()
        assert (output_dir / "packages" / "app").exists()
        assert (output_dir / "packages" / "lib").exists()
        assert (output_dir / "packages" / "utils").exists()

        # Verify content copied
        assert (output_dir / "packages" / "app" / "src" / "code.py").exists()

        # Verify pyproject.toml content
        content = (output_dir / "pyproject.toml").read_text()
        assert '"packages/app"' in content
        assert '"packages/lib"' in content
        assert '"packages/utils"' in content

        mock_lock.assert_called_once_with(output_dir)


@pytest.mark.asyncio
async def test_export_validation_error(mock_workspace):
    context = CommandContext(workspace=mock_workspace)
    options = ExportOptions(package_name="non-existent")

    cmd = ExportCommand(context, options)

    with pytest.raises(Exception) as exc:
        await cmd.execute()
    assert "not found" in str(exc.value)
