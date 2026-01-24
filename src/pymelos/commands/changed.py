"""Changed command implementation."""

from __future__ import annotations

from dataclasses import dataclass

import typer
from rich.console import Console

from pymelos.commands.base import CommandContext, SyncCommand
from pymelos.workspace.workspace import Workspace


@dataclass
class ChangedPackage:
    """Information about a changed package."""

    name: str
    path: str
    files_changed: int
    is_dependent: bool  # True if changed due to dependency


@dataclass
class ChangedResult:
    """Result of changed command."""

    since: str
    changed: list[ChangedPackage]
    total_files_changed: int


@dataclass
class ChangedOptions:
    """Options for changed command."""

    since: str
    include_dependents: bool = True
    scope: str | None = None
    ignore: list[str] | None = None


class ChangedCommand(SyncCommand[ChangedResult]):
    """List packages that have changed since a git reference."""

    def __init__(self, context: CommandContext, options: ChangedOptions) -> None:
        super().__init__(context)
        self.options = options

    def execute(self) -> ChangedResult:
        """Execute the changed command."""
        from pymelos.filters import apply_filters
        from pymelos.git import get_changed_files_since

        # Get all changed files
        changed_files = get_changed_files_since(self.workspace.root, self.options.since)

        # Map files to packages
        directly_changed: dict[str, list[str]] = {}  # package -> files

        for pkg in self.workspace.packages.values():
            pkg_files: list[str] = []
            for file_path in changed_files:
                abs_path = self.workspace.root / file_path
                try:
                    abs_path.relative_to(pkg.path)
                    pkg_files.append(str(file_path))
                except ValueError:
                    continue

            if pkg_files:
                directly_changed[pkg.name] = pkg_files

        # Get dependents if requested
        dependent_packages: set[str] = set()
        if self.options.include_dependents:
            for pkg_name in list(directly_changed.keys()):
                dependents = self.workspace.graph.get_transitive_dependents(pkg_name)
                for dep in dependents:
                    if dep.name not in directly_changed:
                        dependent_packages.add(dep.name)

        # Build result
        changed_pkgs: list[ChangedPackage] = []

        # Add directly changed packages
        for pkg_name, files in directly_changed.items():
            pkg = self.workspace.get_package(pkg_name)
            changed_pkgs.append(
                ChangedPackage(
                    name=pkg_name,
                    path=str(pkg.path.relative_to(self.workspace.root)),
                    files_changed=len(files),
                    is_dependent=False,
                )
            )

        # Add dependent packages
        for pkg_name in dependent_packages:
            pkg = self.workspace.get_package(pkg_name)
            changed_pkgs.append(
                ChangedPackage(
                    name=pkg_name,
                    path=str(pkg.path.relative_to(self.workspace.root)),
                    files_changed=0,
                    is_dependent=True,
                )
            )

        # Apply filters
        if self.options.scope or self.options.ignore:
            pkg_list = [self.workspace.get_package(p.name) for p in changed_pkgs]
            filtered = apply_filters(
                pkg_list,
                scope=self.options.scope,
                ignore=self.options.ignore,
            )
            filtered_names = {p.name for p in filtered}
            changed_pkgs = [p for p in changed_pkgs if p.name in filtered_names]

        # Sort by name
        changed_pkgs.sort(key=lambda p: p.name)

        return ChangedResult(
            since=self.options.since,
            changed=changed_pkgs,
            total_files_changed=len(changed_files),
        )


def get_changed_packages(
    workspace: Workspace,
    since: str,
    *,
    include_dependents: bool = True,
    scope: str | None = None,
    ignore: list[str] | None = None,
) -> ChangedResult:
    """Convenience function to get changed packages.

    Args:
        workspace: Workspace to check.
        since: Git reference.
        include_dependents: Include transitive dependents.
        scope: Package scope filter.
        ignore: Patterns to exclude.

    Returns:
        Changed result.
    """

    context = CommandContext(workspace=workspace)
    options = ChangedOptions(
        since=since,
        include_dependents=include_dependents,
        scope=scope,
        ignore=ignore,
    )
    cmd = ChangedCommand(context, options)
    return cmd.execute()


def handle_changed_command(
    workspace: Workspace,
    *,
    console: Console,
    error_console: Console,
    since: str,
    include_dependents: bool = True,
    scope: str | None = None,
    ignore: list[str] | None = None,
    json_output: bool = False,
) -> None:
    """Handle changed command."""
    try:
        result = get_changed_packages(
            workspace,
            since,
            include_dependents=include_dependents,
            scope=scope,
            ignore=ignore,
        )
        if json_output:
            import json

            data = [
                {
                    "name": p.name,
                    "path": p.path,
                    "files_changed": p.files_changed,
                    "is_dependent": p.is_dependent,
                }
                for p in result.changed
            ]
            console.print(json.dumps(data, indent=2))
        else:
            console.print(f"Packages changed since [bold]{since}[/bold]:")
            for pkg in result.changed:
                suffix = " [dim](dependent)[/dim]" if pkg.is_dependent else ""
                console.print(f"  - {pkg.name} ({pkg.files_changed} files){suffix}")

            if not result.changed:
                console.print("  [dim]No packages changed[/dim]")

    except Exception as e:
        error_console.print_exception()
        raise typer.Exit(1) from e


def review_changes_interactive(
    workspace: Workspace,
    since: str,
    changed_packages: list[ChangedPackage],
    console: Console,
) -> None:
    """Run interactive review of changed packages.

    Args:
        workspace: Workspace instance.
        since: Git reference.
        changed_packages: List of changed packages.
        console: Console for output.
    """
    from rich.syntax import Syntax

    from pymelos.git.diff import get_changed_files_in_package, get_file_diff
    from pymelos.interactive import select_file_for_review, select_package_for_review

    if not changed_packages:
        console.print("[yellow]No packages changed.[/yellow]")
        return

    while True:
        # Level 1: Select Package
        pkg_name = select_package_for_review(changed_packages)
        if not pkg_name:
            break

        # Find the package object
        pkg = next((p for p in changed_packages if p.name == pkg_name), None)
        if not pkg:
            continue

        # Level 2: Get files (fetch once per package)
        files = get_changed_files_in_package(workspace.root, since, workspace.root / pkg.path)

        while True:
            # Level 2: Select File
            selected_file = select_file_for_review(files)

            if not selected_file:
                break

            # Level 3: Show Diff
            diff = get_file_diff(workspace.root, since, selected_file)

            # Use rich pager for nice scrolling
            syntax = Syntax(diff, "diff", theme="monokai", line_numbers=True)
            with console.pager():
                console.print(syntax)
