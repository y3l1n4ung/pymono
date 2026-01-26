"""Test add command."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pymelos.commands.add import AddProjectCommand, AddProjectOptions


@pytest.fixture
def mock_context(tmp_path):
    workspace = MagicMock()
    workspace.root = tmp_path

    context = MagicMock()
    context.env = {}
    context.workspace = workspace
    return context


@pytest.mark.asyncio
async def test_add_project_defaults(mock_context, tmp_path):
    options = AddProjectOptions(name="my-lib")

    target_path = tmp_path / "packages" / "my-lib"

    with patch("pymelos.commands.add.run_command", new_callable=AsyncMock) as mock_run:

        async def create_files(*_args, **_kwargs):
            target_path.mkdir(parents=True, exist_ok=True)
            (target_path / "pyproject.toml").write_text("")
            return (0, "output", "", 100)

        mock_run.side_effect = create_files

        # Pre-create parent folder packages/
        (tmp_path / "packages").mkdir()

        cmd = AddProjectCommand(mock_context, options)
        result = await cmd.execute()

        assert result.success
        assert result.path == target_path

        # Verify uv init call
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert "uv init my-lib --lib" in args[0][0]
        assert args[1]["cwd"] == tmp_path / "packages"

        # Verify pytest config injection
        content = (target_path / "pyproject.toml").read_text()
        assert "[tool.pytest.ini_options]" in content
        assert 'addopts = "--cov=my-lib"' in content

        # Verify tests folder
        assert (target_path / "tests").exists()


@pytest.mark.asyncio
async def test_add_project_app_custom_folder(mock_context, tmp_path):
    options = AddProjectOptions(name="my-app", project_type="app", folder="apps")
    target_path = tmp_path / "apps" / "my-app"

    with patch("pymelos.commands.add.run_command", new_callable=AsyncMock) as mock_run:

        async def create_files(*_args, **_kwargs):
            target_path.mkdir(parents=True, exist_ok=True)
            (target_path / "pyproject.toml").write_text("")
            return (0, "output", "", 100)

        mock_run.side_effect = create_files
        (tmp_path / "apps").mkdir()

        cmd = AddProjectCommand(mock_context, options)
        result = await cmd.execute()

        assert result.success
        assert result.path == target_path

        mock_run.assert_called_once()
        assert "uv init my-app --app" in mock_run.call_args[0][0]
        assert mock_run.call_args[1]["cwd"] == tmp_path / "apps"


@pytest.mark.asyncio
async def test_add_project_exists(mock_context, tmp_path):
    options = AddProjectOptions(name="existing-lib")
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "existing-lib").mkdir()

    cmd = AddProjectCommand(mock_context, options)

    with pytest.raises(RuntimeError) as exc:
        await cmd.execute()
    assert "already exists" in str(exc.value)


@pytest.mark.asyncio
async def test_add_project_failure(mock_context, tmp_path):
    options = AddProjectOptions(name="fail-lib")
    (tmp_path / "packages").mkdir()

    with patch("pymelos.commands.add.run_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (1, "", "uv error", 100)

        cmd = AddProjectCommand(mock_context, options)
        result = await cmd.execute()

        assert not result.success
        assert "uv error" in result.message
