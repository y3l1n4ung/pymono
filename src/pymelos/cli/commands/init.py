"""Init command implementation."""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from pymelos import PyMelosError
from pymelos.errors import ConfigurationError

DEFAULT_PYMELOS_YAML = """# pymelos workspace configuration
name: {name}

packages:
  - packages/*

scripts:
  test:
    run: pytest tests/ -v
    description: Run tests

  lint:
    run: ruff check .
    description: Run linting

  format:
    run: ruff format .
    description: Format code

  typecheck:
    run: type check
    description: Run type checking

command_defaults:
  concurrency: 4
  fail_fast: false
  topological: true

clean:
  patterns:
    - "__pycache__"
    - "*.pyc"
    - ".pytest_cache"
    - ".mypy_cache"
    - ".ruff_cache"
    - "*.egg-info"
    - "dist"
    - "build"
  protected:
    - ".venv"
    - ".git"

versioning:
  commit_format: conventional
  tag_format: "{{name}}@{{version}}"
  changelog:
    enabled: true
    filename: CHANGELOG.md
"""

DEFAULT_PYPROJECT_TOML = """[project]
name = "{name}"
version = "0.0.0"
description = "Python monorepo"
requires-python = ">=3.12"

[tool.uv]
workspace = {{ members = ["packages/*"] }}

dev-dependencies = [
    "pytest>=8.0.0",
    "ruff>=0.8.0",
    "mypy>=1.10.0",
]
"""


def init_workspace(path: Path, name: str | None = None) -> None:
    """Initialize a new pymelos workspace.

    Args:
        path: Directory to initialize.
        name: Workspace name (defaults to directory name).

    Raises:
        ConfigurationError: If workspace already exists.
    """
    path = path.resolve()

    if not path.exists():
        path.mkdir(parents=True)

    # Check if already initialized
    if (path / "pymelos.yaml").exists():
        raise ConfigurationError("Workspace already initialized", path=path / "pymelos.yaml")

    # Use directory name as default
    if not name:
        name = path.name

    # Create pymelos.yaml
    pymelos_yaml = path / "pymelos.yaml"
    pymelos_yaml.write_text(DEFAULT_PYMELOS_YAML.format(name=name), encoding="utf-8")

    # Create pyproject.toml if it doesn't exist
    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(DEFAULT_PYPROJECT_TOML.format(name=name), encoding="utf-8")

    # Create packages directory
    packages_dir = path / "packages"
    packages_dir.mkdir(exist_ok=True)

    # Create .gitignore if it doesn't exist
    gitignore = path / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            """# Python
__pycache__/
*.py[cod]
*.so
.venv/
dist/
build/
*.egg-info/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Type checking
.mypy_cache/

# Linting
.ruff_cache/

# IDE
.vscode/
.idea/

# OS
.DS_Store
""",
            encoding="utf-8",
        )

    # Initialize git if not already a repo
    if not (path / ".git").exists():
        with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)


def handle_init(cwd: Path, name: str | None, console: Console, error_console: Console) -> None:
    try:
        init_workspace(cwd, name)
        console.print("[green]Workspace initialized![/green]")
        console.print("Run [bold]pymelos bootstrap[/bold] to install dependencies.")
    except PyMelosError as e:
        error_console.print(f"[red]Error:[/red] {e.message}")
        raise typer.Exit(1) from e
