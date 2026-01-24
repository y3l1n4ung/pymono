"""Init command implementation."""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from pymelos import PyMelosError
from pymelos.errors import ConfigurationError

# Template for pymelos.yaml
PYMELOS_YAML_TEMPLATE = """# pymelos workspace configuration
name: {name}

packages:
  - packages/*
  - app/*

scripts:
{scripts}

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

# Template for pyproject.toml
PYPROJECT_TOML_TEMPLATE = """[project]
name = "{name}"
version = "0.0.0"
description = "{description}"
requires-python = ">=3.10"
readme = "README.md"

[tool.uv]
workspace = {{ members = ["packages/*", "app/*"] }}

{type_checker_config}

{tools_config}
"""


def get_test_script(use_pytest: bool) -> str:
    if not use_pytest:
        return ""

    return """  test:
    description: Run tests
    run: |
      if [ -d tests ] && [ "$(ls -A tests)" ]; then
        pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
      else
        echo "No tests found"
      fi"""


def get_lint_scripts(use_ruff: bool, type_checker: str) -> str:
    scripts = []

    if use_ruff:
        scripts.append("""  lint:
    run: ruff check .
    description: Run linting""")
        scripts.append("""  format:
    run: ruff format .
    description: Format code""")

    if type_checker != "none":
        check_cmd = {
            "ty": "ty check",
            "pyright": "pyright",
            "mypy": "mypy .",
        }.get(type_checker, "echo 'No type checker configured'")

        scripts.append(f"""  typecheck:
    run: {check_cmd}
    description: Run type checking""")

    return "\n\n".join(scripts)


def get_dev_dependencies(use_pytest: bool, use_ruff: bool, type_checker: str) -> list[str]:
    deps = []
    if use_pytest:
        deps.extend(["pytest>=8.0.0", "pytest-cov>=5.0.0"])
    if use_ruff:
        deps.append("ruff>=0.8.0")

    if type_checker == "ty":
        # ty is installed via tool usually, but can be dev dep?
        # Astral's ty might not be on PyPI as 'ty' yet?
        # Assuming it is available or user has it.
        # If unknown, we might skip adding it to deps and assume global install?
        # Let's add it if known. Currently 'ty' on PyPI is NOT Astral's tool.
        # But per instruction "ty ( is from astral.sh)", we support it.
        # We'll skip adding it to dev-dependencies to avoid pulling the wrong package
        # unless user explicitly wants it.
        pass
    elif type_checker == "pyright":
        deps.append("pyright>=1.1.0")
    elif type_checker == "mypy":
        deps.append("mypy>=1.10.0")

    return deps


def init_workspace(
    path: Path,
    name: str | None = None,
    description: str = "Python monorepo",
    type_checker: str = "none",
    use_ruff: bool = True,
    use_pytest: bool = True,
) -> None:
    """Initialize a new pymelos workspace."""
    path = path.resolve()

    if not path.exists():
        path.mkdir(parents=True)

    # Check if already initialized
    if (path / "pymelos.yaml").exists():
        raise ConfigurationError("Workspace already initialized", path=path / "pymelos.yaml")

    # Use directory name as default
    if not name:
        name = path.name

    # Prepare Scripts
    test_script = get_test_script(use_pytest)
    lint_scripts = get_lint_scripts(use_ruff, type_checker)
    all_scripts = "\n\n".join(filter(None, [test_script, lint_scripts]))

    # Create pymelos.yaml
    pymelos_yaml = path / "pymelos.yaml"
    pymelos_yaml.write_text(
        PYMELOS_YAML_TEMPLATE.format(name=name, scripts=all_scripts), encoding="utf-8"
    )

    # Prepare pyproject.toml content
    type_checker_config = ""
    if type_checker == "ty":
        type_checker_config = '[tool.ty.environment]\npython-version = "3.10"'

    tools_config = ""
    if use_pytest:
        tools_config += """[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = ["-ra", "--strict-markers"]
"""
    if use_ruff:
        tools_config += """
[tool.ruff]
line-length = 100
target-version = "py310"
"""

    # Create pyproject.toml
    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        content = PYPROJECT_TOML_TEMPLATE.format(
            name=name,
            description=description,
            type_checker_config=type_checker_config,
            tools_config=tools_config,
        )
        # Add deps manually to avoid complex f-string escaping
        deps = get_dev_dependencies(use_pytest, use_ruff, type_checker)
        if deps:
            dep_str = '",\n    "'.join(deps)
            content += f'\n[dependency-groups]\ndev = [\n    "{dep_str}",\n]\n'

        pyproject.write_text(content, encoding="utf-8")

    # Create directories
    (path / "packages").mkdir(exist_ok=True)
    (path / "app").mkdir(exist_ok=True)  # Create app/ folder as per new default

    # Create README
    readme = path / "README.md"
    if not readme.exists():
        readme.write_text(f"# {name}\n\n{description}\n", encoding="utf-8")

    # Create .gitignore
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
.ruff_cache/
.dmypy.json
dmypy.json

# IDE
.vscode/
.idea/
.DS_Store
""",
            encoding="utf-8",
        )

    # Initialize git
    if not (path / ".git").exists():
        with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)


def init_interactive(cwd: Path, default_name: str | None) -> dict[str, Any]:
    """Run interactive initialization wizard."""
    import questionary
    from pymelos.interactive import get_style

    style = get_style()

    # 1. Name
    name = questionary.text(
        "Workspace name:",
        default=default_name or cwd.name,
        style=style,
    ).ask()

    if not name:
        raise typer.Exit()

    # 2. Description
    description = questionary.text(
        "Description:",
        default="Python monorepo workspace",
        style=style,
    ).ask()

    # 3. Type Checker
    type_checker = questionary.select(
        "Choose type checker:",
        choices=[
            questionary.Choice("ty (Recommended)", value="ty"),
            questionary.Choice("pyright", value="pyright"),
            questionary.Choice("mypy", value="mypy"),
            questionary.Choice("None", value="none"),
        ],
        style=style,
        use_indicator=True,
    ).ask()

    # 4. Tools
    use_ruff = questionary.confirm(
        "Enable Ruff (linter/formatter)?",
        default=True,
        style=style,
    ).ask()

    use_pytest = questionary.confirm(
        "Enable Pytest?",
        default=True,
        style=style,
    ).ask()

    return {
        "name": name,
        "description": description,
        "type_checker": type_checker,
        "use_ruff": use_ruff,
        "use_pytest": use_pytest,
    }


def handle_init(cwd: Path, name: str | None, console: Console, error_console: Console) -> None:
    """Handle init command."""
    # Check if already initialized first to fail fast
    if (cwd / "pymelos.yaml").exists():
        error_console.print(
            f"[red]Error:[/red] Workspace already initialized at {cwd / 'pymelos.yaml'}"
        )
        raise typer.Exit(1)

    try:
        # Check if running interactively (implied if name not provided, or forced?)
        # For init, we usually want interactive unless flags provided?
        # But to keep backward compat, if name IS provided, maybe skip?
        # The user wants "interactive plan for init".
        # Let's assume interactive is default if TTY attached and no name?
        # Or always run interactive if no args?

        # We'll use interactive if no name is provided OR explicit flag (not implemented yet).
        # Since 'name' is optional in CLI, if it's missing, let's go interactive.

        options = {
            "name": name,
            "description": "Python monorepo",
            "type_checker": "none",
            "use_ruff": True,
            "use_pytest": True,
        }

        # If name is NOT provided, Trigger Interactive Mode
        if not name:
            try:
                user_options = init_interactive(cwd, name)
                options.update(user_options)
            except (ImportError, ModuleNotFoundError):
                # Fallback if interactive libs missing (unlikely given deps)
                pass
            except Exception:
                # Cancelled or error
                raise typer.Exit(1)

        init_workspace(
            cwd,
            name=options["name"],
            description=options["description"],
            type_checker=options["type_checker"],
            use_ruff=options["use_ruff"],
            use_pytest=options["use_pytest"],
        )

        console.print(f"[green]Workspace '{options['name']}' initialized![/green]")
        console.print("Created:")
        console.print("  - pymelos.yaml")
        console.print("  - pyproject.toml")
        console.print("  - packages/")
        console.print("  - app/")

        if options["type_checker"] == "ty":
            console.print(
                "\n[blue]Note:[/blue] You selected 'ty'. Ensure you have it installed (e.g. via 'uv tool install ty')."
            )

    except PyMelosError as e:
        error_console.print(f"[red]Error:[/red] {e.message}")
        raise typer.Exit(1) from e
