from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console

from pymelos import Workspace
from pymelos.commands.base import Command, CommandContext
from pymelos.execution import run_command


@dataclass
class AddProjectOptions:
    name: str
    project_type: Literal["lib", "app"] = "lib"
    folder: str | None = None  # default to workspace default folder
    bare: bool = False
    editable: bool = True  # whether to pip install -e after creation


class AddProjectResult:
    """Result of AddProjectCommand."""

    def __init__(self, success: bool, path: Path, message: str):
        self.success = success
        self.path = path
        self.message = message


class AddProjectCommand(Command[AddProjectResult]):
    """Add a new library or app to the workspace."""

    DEFAULT_FOLDERS = {
        "lib": "packages",
        "app": "examples",
    }

    def __init__(self, context: CommandContext, options: AddProjectOptions) -> None:
        super().__init__(context)
        self.options = options

    async def execute(self) -> AddProjectResult:
        name = self.options.name
        project_type = self.options.project_type

        # determine target folder
        folder = self.options.folder or self.DEFAULT_FOLDERS[project_type]
        target_dir = self.workspace.root / folder
        project_path = target_dir / name

        if project_path.exists():
            raise RuntimeError(f"Project {name} already exists at {project_path}")

        # run command
        exit_code, stdout, stderr, _ = await run_command(
            f"uv init {name} --{project_type} {'--bare' if self.options.bare else ''}",
            cwd=target_dir,
            env=self.context.env,
        )

        if exit_code != 0:
            return AddProjectResult(False, project_path, stderr)

        ensure_pytest_config(project_path / "pyproject.toml", name)

        create_tests_folder(project_path, name)

        # if project_type == "lib" and self.options.editable:
        #     pip_install_editable(project_path)
        # return result
        return AddProjectResult(True, project_path, f"Created project {name} at {project_path}")


async def add_project(
    workspace: Workspace,
    name: str,
    project_type: Literal["lib", "app"] = "lib",
    folder: str | None = None,
    editable: bool = True,
) -> AddProjectResult:
    context = CommandContext(workspace=workspace)
    return await AddProjectCommand(
        context, AddProjectOptions(name, project_type, folder, editable=editable)
    ).execute()


async def handle_add_project(
    workspace: Workspace,
    name: str,
    console: Console,
    error_console: Console,
    project_type: Literal["lib", "app"] = "lib",
    folder: str | None = None,
    editable: bool = True,
) -> None:
    try:
        result = await add_project(workspace, name, project_type, folder, editable)
        if result.success:
            console.print(f"[green]Added project {name}[/green]")
        else:
            error_console.print(f"[red]Failed to add project {name}:[/red] {result.message}")
            raise typer.Exit(1)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


def ensure_pytest_config(pyproject_path: Path, package_name: str) -> None:
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")

    content = pyproject_path.read_text(encoding="utf-8")

    marker = "[tool.pytest.ini_options]"
    if marker in content:
        return  # already configured

    pytest_block = f"""
{marker}
pythonpath = ["src"]
addopts = "--cov={package_name}"
"""

    pyproject_path.write_text(content.rstrip() + "\n" + pytest_block, encoding="utf-8")


def create_tests_folder(project_path: Path, name: str) -> None:
    tests_root = project_path / "tests"
    package_tests = tests_root / f"tests_{name}"

    tests_root.mkdir(exist_ok=True)
    package_tests.mkdir(exist_ok=True)
