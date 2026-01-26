"""Integration tests for uv build and publish."""

import shutil
from unittest.mock import MagicMock, patch

import pytest

from pymelos.uv.publish import build, check_publishable, publish


def is_uv_installed() -> bool:
    return shutil.which("uv") is not None


@pytest.mark.skipif(not is_uv_installed(), reason="uv not installed")
def test_uv_build(tmp_path):
    """Test building a package."""
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "test-pkg"
version = "0.1.0"
requires-python = ">=3.10"
""",
        encoding="utf-8",
    )
    (tmp_path / "src" / "test_pkg").mkdir(parents=True)
    (tmp_path / "src" / "test_pkg" / "__init__.py").touch()

    # Run build
    dist_dir = build(tmp_path)

    assert dist_dir.exists()
    assert len(list(dist_dir.glob("*.whl"))) == 1
    assert len(list(dist_dir.glob("*.tar.gz"))) == 1


def test_uv_publish_mocked(tmp_path):
    """Test publishing with mocked uv command."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "pkg-0.1.0.whl").touch()

    with patch("pymelos.uv.publish.run_uv") as mock_run:
        publish(
            tmp_path, repository="https://test.pypi.org/legacy/", token="token", dist_dir=dist_dir
        )

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "publish" in args
        assert "--publish-url" in args
        assert "--token" in args
        assert str(dist_dir / "pkg-0.1.0.whl") in args


def test_check_publishable(tmp_path):
    """Test publishable check."""
    # Invalid
    (tmp_path / "pyproject.toml").write_text("[project]\nname='foo'", encoding="utf-8")
    issues = check_publishable(tmp_path)
    assert any("Missing required field: project.version" in i for i in issues)

    # Valid
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "valid-pkg"
version = "1.0.0"
description = "Desc"
readme = "README.md"
license = "MIT"
""",
        encoding="utf-8",
    )
    issues = check_publishable(tmp_path)
    assert not issues
