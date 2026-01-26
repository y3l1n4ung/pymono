"""Integration tests for version command."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from pymelos.commands.version import VersionCommand, VersionOptions
from pymelos.workspace.workspace import Workspace


def run_git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def git_workspace(tmp_path):
    """Setup a workspace with git history."""
    if not shutil.which("git"):
        pytest.skip("git not found")

    # Init git
    run_git(["init"], tmp_path)
    run_git(["config", "user.email", "test@example.com"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)

    # Files
    (tmp_path / "pymelos.yaml").write_text(
        "name: test-ws\npackages: ['packages/*']", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")

    pkg_dir = tmp_path / "packages" / "pkg-a"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "pyproject.toml").write_text(
        '[project]\nname = "pkg-a"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    (pkg_dir / "src").mkdir()
    (pkg_dir / "src" / "code.py").write_text("print('hello')", encoding="utf-8")

    # Initial commit
    run_git(["add", "."], tmp_path)
    run_git(["commit", "-m", "chore: initial commit"], tmp_path)

    return tmp_path


@pytest.mark.asyncio
async def test_version_bump_flow(git_workspace):
    """Test full version bump flow."""
    # Make a feature commit
    pkg_dir = git_workspace / "packages" / "pkg-a"
    (pkg_dir / "src" / "code.py").write_text("print('updated')", encoding="utf-8")

    run_git(["add", "."], git_workspace)
    run_git(["commit", "-m", "feat: add feature"], git_workspace)

    # Load workspace
    workspace = Workspace.discover(git_workspace)

    # Run Version Command
    # We use no_commit=True to avoid complexity of checking head sha in test environment?
    # No, let's test commit too.
    options = VersionOptions(dry_run=False, no_git_tag=False, no_commit=False, no_changelog=False)

    from pymelos.commands.base import CommandContext

    cmd = VersionCommand(CommandContext(workspace), options)
    result = await cmd.execute()

    assert result.success
    assert len(result.releases) == 1
    rel = result.releases[0]
    assert rel["name"] == "pkg-a"
    assert rel["new"] == "0.1.0"  # 0.0.0 + feat -> 0.1.0

    # Verify file update
    content = (pkg_dir / "pyproject.toml").read_text()
    assert 'version = "0.1.0"' in content

    # Verify changelog
    changelog = (pkg_dir / "CHANGELOG.md").read_text()
    # Pymelos uses tag format in changelog header
    assert "pkg-a@0.1.0" in changelog
    assert "add feature" in changelog

    # Verify git tag
    tags = subprocess.run(["git", "tag"], cwd=git_workspace, capture_output=True, text=True).stdout
    assert "pkg-a@0.1.0" in tags
