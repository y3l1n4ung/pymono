"""Shared test fixtures for pymelos tests."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env from project root (doesn't override existing env vars)
load_dotenv(Path(__file__).parent.parent / ".env")


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_pyproject() -> str:
    """Sample pyproject.toml content."""
    return """\
[project]
name = "sample-pkg"
version = "1.0.0"
description = "A sample package"
dependencies = ["requests>=2.0.0"]

[project.optional-dependencies]
dev = ["pytest>=7.0.0"]
"""


@pytest.fixture
def sample_pymelos_yaml() -> str:
    """Sample pymelos.yaml content."""
    return """\
name: test-workspace
packages:
  - packages/*

scripts:
  test: pytest tests/ -v
  lint: ruff check .
  format: ruff format .

command_defaults:
  concurrency: 4
  fail_fast: false

clean:
  patterns:
    - "**/__pycache__"
    - "**/*.pyc"
    - ".pytest_cache"
    - "dist"
    - "*.egg-info"
  protected:
    - ".git"
    - ".venv"

versioning:
  tag_format: "{name}@{version}"
  commit_message: "chore(release): {packages}"

publish:
  registry: https://upload.pypi.org/legacy/
"""


@pytest.fixture
def workspace_dir(temp_dir: Path, sample_pymelos_yaml: str) -> Path:
    """Create a sample workspace directory structure."""
    # Create pymelos.yaml
    (temp_dir / "pymelos.yaml").write_text(sample_pymelos_yaml)

    # Create root pyproject.toml (workspace)
    (temp_dir / "pyproject.toml").write_text("""\
[project]
name = "test-workspace"
version = "0.0.0"

[tool.uv.workspace]
members = ["packages/*"]
""")

    # Create packages directory
    packages_dir = temp_dir / "packages"
    packages_dir.mkdir()

    # Create pkg-a
    pkg_a = packages_dir / "pkg-a"
    pkg_a.mkdir()
    (pkg_a / "pyproject.toml").write_text("""\
[project]
name = "pkg-a"
version = "1.0.0"
description = "Package A"
dependencies = []
""")
    (pkg_a / "src").mkdir()
    (pkg_a / "src" / "pkg_a").mkdir(parents=True)
    (pkg_a / "src" / "pkg_a" / "__init__.py").write_text('__version__ = "1.0.0"\n')

    # Create pkg-b (depends on pkg-a)
    pkg_b = packages_dir / "pkg-b"
    pkg_b.mkdir()
    (pkg_b / "pyproject.toml").write_text("""\
[project]
name = "pkg-b"
version = "2.0.0"
description = "Package B"
dependencies = ["pkg-a"]

[tool.uv.sources]
pkg-a = { workspace = true }
""")
    (pkg_b / "src").mkdir()
    (pkg_b / "src" / "pkg_b").mkdir(parents=True)
    (pkg_b / "src" / "pkg_b" / "__init__.py").write_text('__version__ = "2.0.0"\n')

    # Create pkg-c (depends on pkg-b)
    pkg_c = packages_dir / "pkg-c"
    pkg_c.mkdir()
    (pkg_c / "pyproject.toml").write_text("""\
[project]
name = "pkg-c"
version = "0.1.0"
description = "Package C"
dependencies = ["pkg-b"]

[tool.uv.sources]
pkg-b = { workspace = true }
""")
    (pkg_c / "src").mkdir()
    (pkg_c / "src" / "pkg_c").mkdir(parents=True)
    (pkg_c / "src" / "pkg_c" / "__init__.py").write_text('__version__ = "0.1.0"\n')

    return temp_dir


@pytest.fixture
def git_workspace(workspace_dir: Path) -> Path:
    """Create a workspace with git initialized."""
    os.system(f"cd {workspace_dir} && git init -q")
    os.system(f"cd {workspace_dir} && git config user.email 'test@test.com'")
    os.system(f"cd {workspace_dir} && git config user.name 'Test'")
    os.system(f"cd {workspace_dir} && git add -A")
    os.system(f"cd {workspace_dir} && git commit -q -m 'Initial commit'")
    return workspace_dir
