"""List command implementation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

from pymelos.commands.base import CommandContext, SyncCommand

if TYPE_CHECKING:
    from pymelos.workspace import Package
    from pymelos.workspace.workspace import Workspace


class ListFormat(Enum):
    """Output format for list command."""

    TABLE = "table"
    JSON = "json"
    GRAPH = "graph"
    NAMES = "names"


@dataclass
class PackageInfo:
    """Information about a package for display."""

    name: str
    version: str
    path: str
    description: str | None
    dependencies: list[str]
    dependents: list[str]


@dataclass
class ListResult:
    """Result of list command."""

    packages: list[PackageInfo]


@dataclass
class ListOptions:
    """Options for list command."""

    scope: str | None = None
    since: str | None = None
    ignore: list[str] | None = None
    format: ListFormat = ListFormat.TABLE
    include_dependents: bool = False


class ListCommand(SyncCommand[ListResult]):
    """List packages in the workspace."""

    def __init__(self, context: CommandContext, options: ListOptions | None = None) -> None:
        super().__init__(context)
        self.options = options or ListOptions()

    def get_packages(self) -> list[Package]:
        """Get packages to list."""
        from pymelos.filters import apply_filters_with_since

        packages = list(self.workspace.packages.values())

        return apply_filters_with_since(
            packages,
            self.workspace,
            scope=self.options.scope,
            since=self.options.since,
            ignore=self.options.ignore,
            include_dependents=self.options.include_dependents,
        )

    def execute(self) -> ListResult:
        """Execute the list command."""
        packages = self.get_packages()
        graph = self.workspace.graph

        infos: list[PackageInfo] = []
        for pkg in packages:
            deps = graph.get_dependencies(pkg.name)
            dependents = graph.get_dependents(pkg.name)

            infos.append(
                PackageInfo(
                    name=pkg.name,
                    version=pkg.version,
                    path=str(pkg.path.relative_to(self.workspace.root)),
                    description=pkg.description,
                    dependencies=[d.name for d in deps],
                    dependents=[d.name for d in dependents],
                )
            )

        # Sort by name
        infos.sort(key=lambda p: p.name)

        return ListResult(packages=infos)


def list_packages(
    workspace: Workspace,
    *,
    scope: str | None = None,
    since: str | None = None,
    ignore: list[str] | None = None,
    format: ListFormat = ListFormat.TABLE,
) -> ListResult:
    """Convenience function to list packages.

    Args:
        workspace: Workspace to list.
        scope: Package scope filter.
        since: Git reference.
        ignore: Patterns to exclude.
        format: Output format.

    Returns:
        List result with package info.
    """

    context = CommandContext(workspace=workspace)
    options = ListOptions(scope=scope, since=since, ignore=ignore, format=format)
    cmd = ListCommand(context, options)
    return cmd.execute()


def handle_list_command(
    workspace: Workspace,
    *,
    console: Console,
    error_console: Console,
    scope: str | None = None,
    since: str | None = None,
    json_output: bool = False,
    graph: bool = False,
) -> None:
    try:
        fmt = ListFormat.TABLE
        if json_output:
            fmt = ListFormat.JSON
        elif graph:
            fmt = ListFormat.GRAPH

        result = list_packages(workspace, scope=scope, since=since, format=fmt)

        if json_output:
            import json

            data = [
                {
                    "name": p.name,
                    "version": p.version,
                    "path": p.path,
                    "description": p.description,
                    "dependencies": p.dependencies,
                }
                for p in result.packages
            ]
            console.print(json.dumps(data, indent=2))
        elif graph:
            # Simple tree output
            for pkg in result.packages:
                if not pkg.dependencies:
                    console.print(f"[bold]{pkg.name}[/bold] v{pkg.version}")
                else:
                    deps_str = ", ".join(pkg.dependencies)
                    console.print(f"[bold]{pkg.name}[/bold] v{pkg.version} -> {deps_str}")
        else:
            table = Table(title="Packages")
            table.add_column("Name", style="bold")
            table.add_column("Version")
            table.add_column("Path")
            table.add_column("Dependencies")

            for pkg in result.packages:
                deps = ", ".join(pkg.dependencies) if pkg.dependencies else "-"
                table.add_row(pkg.name, pkg.version, pkg.path, deps)

            console.print(table)
    except Exception as e:
        error_console.print_exception()
        raise typer.Exit(1) from e
