"""Integration tests for uv sync."""

import shutil

import pytest

from pymelos.uv.sync import add_dependency, lock, remove_dependency, sync, sync_async


def is_uv_installed() -> bool:
    """Check if uv is installed."""
    return shutil.which("uv") is not None


@pytest.mark.asyncio
@pytest.mark.skipif(not is_uv_installed(), reason="uv not installed")
async def test_uv_sync_async(tmp_path):
    """Test async sync."""
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "test-async"
version = "0.1.0"
requires-python = ">=3.10"
""",
        encoding="utf-8",
    )

    # Use locked=False because no lockfile exists yet
    code, stdout, stderr = await sync_async(tmp_path, locked=False)
    assert code == 0, f"Async sync failed: {stderr}"
    assert (tmp_path / ".venv").exists()


@pytest.mark.skipif(not is_uv_installed(), reason="uv not installed")
def test_uv_lock_and_sync(tmp_path):
    """Test lock and sync generation."""
    # Setup minimal workspace
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "test-project"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[tool.uv]
workspace = { members = ["packages/*"] }
""",
        encoding="utf-8",
    )
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "pkg-a").mkdir(parents=True)
    (tmp_path / "packages" / "pkg-a" / "pyproject.toml").write_text(
        """[project]
name = "pkg-a"
version = "0.1.0"
requires-python = ">=3.10"
""",
        encoding="utf-8",
    )

    # Test lock
    code, stdout, stderr = lock(tmp_path)
    assert code == 0, f"Lock failed: {stderr}"
    assert (tmp_path / "uv.lock").exists()

    # Test sync
    code, stdout, stderr = sync(tmp_path)
    assert code == 0, f"Sync failed: {stderr}"
    assert (tmp_path / ".venv").exists()


@pytest.mark.skipif(not is_uv_installed(), reason="uv not installed")
def test_uv_add_dependency(tmp_path):
    """Test adding a dependency."""
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "test-project"
version = "0.1.0"
requires-python = ">=3.10"
""",
        encoding="utf-8",
    )

    # Add 'requests' (small package)
    code, stdout, stderr = add_dependency(tmp_path, "requests", dev=True)

    # uv add might fail if network is down, but we want to test the invocation
    # If it fails due to network, code != 0.
    # We should allow failure but check if command was attempted?
    # No, integration test expects success.

    if code != 0 and "Network" in stderr:
        pytest.skip("Network unavailable")

    assert code == 0, f"Add failed: {stderr}"

    content = (tmp_path / "pyproject.toml").read_text()
    # uv might add to [project.optional-dependencies] dev or [dependency-groups] dev
    assert "requests" in content


@pytest.mark.skipif(not is_uv_installed(), reason="uv not installed")
def test_uv_remove_dependency(tmp_path):
    """Test removing a dependency."""
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "test-remove"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["requests>=2.0.0"]
""",
        encoding="utf-8",
    )

    code, stdout, stderr = remove_dependency(tmp_path, "requests")
    assert code == 0, f"Remove failed: {stderr}"

    content = (tmp_path / "pyproject.toml").read_text()
    assert "requests" not in content
