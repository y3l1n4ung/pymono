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
from pymelos.templates import (
    LINT_SCRIPT_TEMPLATE,
    PYMELOS_YAML_TEMPLATE,
    PYPROJECT_TOML_TEMPLATE,
    TEST_SCRIPT_TEMPLATE,
    TOOL_CONFIGS,
    TYPECHECK_SCRIPT_TEMPLATE,
)


def get_scripts(use_pytest: bool, use_ruff: bool, type_checker: str) -> str:
    scripts = []
    if use_pytest:
        scripts.append(TEST_SCRIPT_TEMPLATE)

    if use_ruff:
        scripts.append(LINT_SCRIPT_TEMPLATE)

    if type_checker != "none":
        check_cmd = {
            "ty": "ty check",
            "pyright": "pyright",
            "mypy": "mypy .",
        }.get(type_checker, "echo 'No type checker configured'")

        scripts.append(TYPECHECK_SCRIPT_TEMPLATE.format(cmd=check_cmd))

    return "\n\n".join(scripts)


def run_uv_add(cwd: Path, packages: list[str], dev: bool = False) -> None:
    """Run uv add command."""
    if not packages:
        return

    cmd = ["uv", "add"]
    if dev:
        cmd.extend(["--group", "dev"])
    cmd.extend(packages)

    # We use check=False to avoid crashing if uv is missing or fails (e.g. network)
    # But ideally we should warn.
    with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


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

    # 1. Create pymelos.yaml
    scripts_content = get_scripts(use_pytest, use_ruff, type_checker)
    # No bootstrap hooks for deps, we put them in pyproject.toml
    pymelos_yaml = path / "pymelos.yaml"
    pymelos_yaml.write_text(
        PYMELOS_YAML_TEMPLATE.format(name=name, scripts=scripts_content, bootstrap_hooks="    []"),
        encoding="utf-8",
    )

    # 2. Create pyproject.toml
    type_checker_config = TOOL_CONFIGS.get(type_checker, "") if type_checker == "ty" else ""

    tools_config = ""
    if use_pytest:
        tools_config += TOOL_CONFIGS["pytest"] + "\n"
    if use_ruff:
        tools_config += TOOL_CONFIGS["ruff"] + "\n"

    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        content = PYPROJECT_TOML_TEMPLATE.format(
            name=name,
            description=description,
            type_checker_config=type_checker_config,
            tools_config=tools_config,
        )
        pyproject.write_text(content, encoding="utf-8")

    # 3. Create directories
    (path / "packages").mkdir(exist_ok=True)
    (path / "app").mkdir(exist_ok=True)

    # 4. Create README & gitignore
    readme = path / "README.md"
    if not readme.exists():
        readme.write_text(f"# {name}\n\n{description}\n", encoding="utf-8")

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

    # 5. Initialize git
    if not (path / ".git").exists():
        with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)

    # 6. Install dependencies via uv add
    dev_deps = []
    if use_pytest:
        dev_deps.extend(["pytest", "pytest-cov"])
    if use_ruff:
        dev_deps.append("ruff")

    if type_checker == "pyright":
        dev_deps.append("pyright")
    elif type_checker == "mypy":
        dev_deps.append("mypy")
    # ty not added to dev-deps automatically

    if dev_deps:
        run_uv_add(path, dev_deps, dev=True)


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
            except Exception as e:
                # Cancelled or error
                raise typer.Exit(1) from e

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
                "\n[blue]Note:[/blue] You selected 'ty'. "
                "Ensure you have it installed (e.g. via 'uv tool install ty')."
            )

    except PyMelosError as e:
        error_console.print(f"[red]Error:[/red] {e.message}")
        raise typer.Exit(1) from e
