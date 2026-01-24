"""Export command implementation."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from pymelos.commands.base import Command, CommandContext
from pymelos.errors import PyMelosError
from pymelos.uv.sync import lock
from pymelos.workspace import Package
from pymelos.workspace.workspace import Workspace


@dataclass
class ExportResult:
    """Result of export command."""

    output_path: Path
    packages_exported: list[str]
    success: bool = True


@dataclass
class ExportOptions:
    """Options for export command."""

    package_name: str
    output: str = "dist"
    clean: bool = True
    include_dev: bool = False


class ExportCommand(Command[ExportResult]):
    """Export a package and its dependencies for deployment."""

    def __init__(self, context: CommandContext, options: ExportOptions) -> None:
        super().__init__(context)
        self.options = options

    def validate(self) -> list[str]:
        """Validate the command."""
        errors = super().validate()
        if self.options.package_name not in self.workspace.packages:
            errors.append(f"Package '{self.options.package_name}' not found in workspace.")
        return errors

    def _get_local_dependencies(self, package: Package, collected: set[str]) -> None:
        """Recursively find all local workspace dependencies."""
        if package.name in collected:
            return

        collected.add(package.name)

        for dep_name in package.workspace_dependencies:
            dep_pkg = self.workspace.get_package(dep_name)
            self._get_local_dependencies(dep_pkg, collected)

    def _create_mini_workspace_config(self, output_path: Path, members: list[str]) -> None:
        """Create a pyproject.toml for the exported mini-workspace."""
        members_list = [f"packages/{name}" for name in members]
        formatted_members = ", ".join(f'"{m}"' for m in members_list)

        # Simple workspace definition compatible with uv
        content = f"""[project]
name = "exported-workspace"
version = "0.1.0"
requires-python = ">=3.10"

[tool.uv]
members = [{formatted_members}]
"""
        (output_path / "pyproject.toml").write_text(content)

    def _copy_package(self, package: Package, dest_root: Path) -> None:
        """Copy package source to destination."""
        # Use package name as folder name in packages/
        dest_dir = dest_root / "packages" / package.name

        # Ignore common artifacts
        ignore = shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".git", ".venv", ".pytest_cache", "dist", "build"
        )

        shutil.copytree(package.path, dest_dir, ignore=ignore)

    async def execute(self) -> ExportResult:
        """Execute the export."""
        errors = self.validate()
        if errors:
            raise PyMelosError("\n".join(errors))

        target_pkg = self.workspace.get_package(self.options.package_name)

        # 1. Identify all needed packages
        needed_packages: set[str] = set()
        self._get_local_dependencies(target_pkg, needed_packages)

        # 2. Prepare output directory
        output_path = Path(self.options.output).resolve()
        if self.options.clean and output_path.exists():
            shutil.rmtree(output_path)

        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "packages").mkdir(exist_ok=True)

        # 3. Copy packages
        exported_list = []
        for pkg_name in needed_packages:
            pkg = self.workspace.get_package(pkg_name)
            self._copy_package(pkg, output_path)
            exported_list.append(pkg_name)

        # 4. Generate workspace config
        self._create_mini_workspace_config(output_path, exported_list)

        # 5. Generate lockfile for the new workspace
        # This ensures the exported folder is immediately usable
        lock(output_path)

        return ExportResult(output_path=output_path, packages_exported=exported_list)


async def export_package(
    workspace: Workspace,
    package_name: str,
    *,
    output: str = "dist",
    clean: bool = True,
) -> ExportResult:
    """Convenience function to export a package."""
    context = CommandContext(workspace=workspace)
    options = ExportOptions(
        package_name=package_name,
        output=output,
        clean=clean,
    )
    cmd = ExportCommand(context, options)
    return await cmd.execute()


async def handle_export_command(
    workspace: Workspace,
    package_name: str,
    *,
    console: Console,  # noqa: ARG001
    error_console: Console,
    output: str = "dist",
    clean: bool = True,
) -> None:
    """Handle the export command."""
    import typer

    try:
        result = await export_package(
            workspace,
            package_name,
            output=output,
            clean=clean,
        )

        console.print(
            f"[green]Successfully exported {len(result.packages_exported)} packages to {result.output_path}[/green]"
        )
        console.print("Exported packages:")
        for pkg in result.packages_exported:
            console.print(f"  - {pkg}")

    except Exception as e:
        error_console.print_exception()
        raise typer.Exit(1) from e
