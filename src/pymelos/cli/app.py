"""pymelos CLI application."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console

from pymelos.commands.list import handle_list_command
from pymelos.errors import PyMelosError
from pymelos.workspace import Workspace


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from pymelos import __version__

        print(f"pymelos {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="pymelos",
    help="Python monorepo manager powered",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _app_callback(
    version: Annotated[  # noqa: ARG001
        bool,
        typer.Option("--version", "-V", help="Show version and exit", callback=version_callback),
    ] = False,
) -> None:
    """Python monorepo manager ."""
    pass


console = Console()
error_console = Console(stderr=True)


def parse_comma_list(value: str | None) -> list[str] | None:
    """Parse comma-separated string into list."""
    return value.split(",") if value else None


def get_workspace(path: Path | None = None) -> Workspace:
    """Load workspace from current directory or specified path."""
    try:
        return Workspace.discover(path)
    except PyMelosError as e:
        error_console.print(f"[red]Error:[/red] {e.message}")
        raise typer.Exit(1) from e


@app.command()
def init(
    path: Annotated[
        Path | None,
        typer.Argument(help="Directory to initialize"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Workspace name"),
    ] = None,
) -> None:
    """Initialize a new pymelos workspace."""
    from pymelos.cli.commands.init import handle_init

    handle_init(path or Path.cwd(), name, console, error_console)


@app.command()
def bootstrap(
    clean: Annotated[
        bool,
        typer.Option("--clean", help="Clean before bootstrap"),
    ] = False,
    frozen: Annotated[
        bool,
        typer.Option("--frozen", help="Use frozen dependencies"),
    ] = False,
    skip_hooks: Annotated[
        bool,
        typer.Option("--skip-hooks", help="Skip bootstrap hooks"),
    ] = False,
) -> None:
    """Install dependencies and link packages."""
    from pymelos.commands import handle_bootstrap

    workspace = get_workspace()

    asyncio.run(
        handle_bootstrap(
            workspace=workspace,
            clean_first=clean,
            frozen=frozen,
            skip_hooks=skip_hooks,
            console=console,
            error_console=error_console,
        )
    )


@app.command(name="add")
def run_add_project(
    name: Annotated[
        str,
        typer.Argument(help="Project name"),
    ],
    project_type: Annotated[
        Literal["lib", "app"],
        typer.Option("--project-type", "-t", help="Project type"),
    ] = "lib",
    folder: Annotated[
        str | None,
        typer.Option("--folder", "-f", help="Target folder"),
    ] = None,
    editable: Annotated[
        bool,
        typer.Option("--editable", help="Install project as editable"),
    ] = True,
) -> None:
    """
    Add a new project to the workspace.
    """
    from pymelos.commands import handle_add_project

    workspace = get_workspace()
    asyncio.run(
        handle_add_project(
            workspace=workspace,
            name=name,
            console=console,
            error_console=error_console,
            project_type=project_type,
            folder=folder,
            editable=editable,
        )
    )


@app.command("run")
def run_cmd(
    script: Annotated[str, typer.Argument(help="Script name to run")],
    scope: Annotated[
        str | None,
        typer.Option("--scope", "-s", help="Package scope filter"),
    ] = None,
    since: Annotated[
        str | None,
        typer.Option("--since", help="Only packages changed since git ref"),
    ] = None,
    ignore: Annotated[
        str | None,
        typer.Option("--ignore", "-i", help="Patterns to ignore (comma-separated)"),
    ] = None,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", "-c", help="Parallel jobs"),
    ] = 4,
    fail_fast: Annotated[
        bool,
        typer.Option("--fail-fast", help="Stop on first failure"),
    ] = False,
    no_topological: Annotated[
        bool,
        typer.Option("--no-topological", help="Ignore dependency order"),
    ] = False,
) -> None:
    """Run a defined script across packages."""
    from pymelos.commands import handle_run_script

    workspace = get_workspace()
    ignore_list = parse_comma_list(ignore)

    asyncio.run(
        handle_run_script(
            workspace=workspace,
            script_name=script,
            console=console,
            error_console=error_console,
            scope=scope,
            since=since,
            ignore=ignore_list,
            concurrency=concurrency,
            fail_fast=fail_fast,
            topological=not no_topological,
        )
    )


@app.command("exec")
def exec_cmd(
    command: Annotated[str, typer.Argument(help="Command to execute")],
    scope: Annotated[
        str | None,
        typer.Option("--scope", "-s", help="Package scope filter"),
    ] = None,
    since: Annotated[
        str | None,
        typer.Option("--since", help="Only packages changed since git ref"),
    ] = None,
    ignore: Annotated[
        str | None,
        typer.Option("--ignore", "-i", help="Patterns to ignore"),
    ] = None,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", "-c", help="Parallel jobs"),
    ] = 4,
    fail_fast: Annotated[
        bool,
        typer.Option("--fail-fast", help="Stop on first failure"),
    ] = False,
) -> None:
    """Execute an arbitrary command across packages."""
    from pymelos.commands import handle_exec_command

    workspace = get_workspace()
    ignore_list = parse_comma_list(ignore)

    asyncio.run(
        handle_exec_command(
            workspace=workspace,
            command=command,
            console=console,
            error_console=error_console,
            scope=scope,
            since=since,
            ignore=ignore_list,
            concurrency=concurrency,
            fail_fast=fail_fast,
        )
    )


@app.command("list")
def list_cmd(
    scope: Annotated[
        str | None,
        typer.Option("--scope", "-s", help="Package scope filter"),
    ] = None,
    since: Annotated[
        str | None,
        typer.Option("--since", help="Only packages changed since git ref"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    graph: Annotated[
        bool,
        typer.Option("--graph", help="Show dependency graph"),
    ] = False,
) -> None:
    """List workspace packages."""

    workspace = get_workspace()

    handle_list_command(
        workspace=workspace,
        console=console,
        error_console=error_console,
        scope=scope,
        since=since,
        json_output=json_output,
        graph=graph,
    )


@app.command()
def clean(
    scope: Annotated[
        str | None,
        typer.Option("--scope", "-s", help="Package scope filter"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be cleaned"),
    ] = False,
) -> None:
    """Clean build artifacts."""
    from pymelos.commands import handle_clean_command

    workspace = get_workspace()

    asyncio.run(
        handle_clean_command(
            workspace=workspace,
            console=console,
            error_console=error_console,
            scope=scope,
            dry_run=dry_run,
        )
    )


@app.command()
def changed(
    since: Annotated[str, typer.Argument(help="Git reference (branch, tag, commit)")],
    no_dependents: Annotated[
        bool,
        typer.Option("--no-dependents", help="Exclude dependent packages"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List packages changed since a git reference."""
    from pymelos.commands import handle_changed_command

    workspace = get_workspace()
    handle_changed_command(
        workspace=workspace,
        console=console,
        error_console=error_console,
        since=since,
        include_dependents=not no_dependents,
        json_output=json_output,
    )


@app.command()
def release(
    scope: Annotated[
        str | None,
        typer.Option("--scope", "-s", help="Package scope filter"),
    ] = None,
    bump: Annotated[
        str | None,
        typer.Option("--bump", "-b", help="Force bump type (major, minor, patch)"),
    ] = None,
    prerelease: Annotated[
        str | None,
        typer.Option("--prerelease", help="Prerelease tag (alpha, beta, rc)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be released"),
    ] = False,
    publish: Annotated[
        bool,
        typer.Option("--publish", help="Publish to PyPI"),
    ] = False,
    no_git_tag: Annotated[
        bool,
        typer.Option("--no-git-tag", help="Skip creating git tags"),
    ] = False,
    no_changelog: Annotated[
        bool,
        typer.Option("--no-changelog", help="Skip changelog generation"),
    ] = False,
    no_commit: Annotated[
        bool,
        typer.Option("--no-commit", help="Skip git commit"),
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Version and publish packages."""
    from pymelos.commands import handle_release_command

    workspace = get_workspace()

    asyncio.run(
        handle_release_command(
            workspace=workspace,
            console=console,
            error_console=error_console,
            scope=scope,
            bump=bump,
            prerelease=prerelease,
            dry_run=dry_run,
            publish=publish,
            no_git_tag=no_git_tag,
            no_changelog=no_changelog,
            no_commit=no_commit,
            yes=yes,
        )
    )


@app.command()
def version(
    scope: Annotated[
        str | None,
        typer.Option("--scope", "-s", help="Package scope filter"),
    ] = None,
    bump: Annotated[
        str | None,
        typer.Option("--bump", "-b", help="Force bump type (major, minor, patch)"),
    ] = None,
    prerelease: Annotated[
        str | None,
        typer.Option("--prerelease", help="Prerelease tag (alpha, beta, rc)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be versioned"),
    ] = False,
    no_git_tag: Annotated[
        bool,
        typer.Option("--no-git-tag", help="Skip creating git tags"),
    ] = False,
    no_changelog: Annotated[
        bool,
        typer.Option("--no-changelog", help="Skip changelog generation"),
    ] = False,
    no_commit: Annotated[
        bool,
        typer.Option("--no-commit", help="Skip git commit"),
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Manage package versions, changelogs, and git tags."""
    from pymelos.commands.version import handle_version_command

    workspace = get_workspace()
    asyncio.run(
        handle_version_command(
            workspace=workspace,
            console=console,
            error_console=error_console,
            scope=scope,
            bump=bump,
            prerelease=prerelease,
            dry_run=dry_run,
            no_git_tag=no_git_tag,
            no_changelog=no_changelog,
            no_commit=no_commit,
            yes=yes,
        )
    )


@app.command()
def export(
    package: Annotated[str, typer.Argument(help="Package to export")],
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output directory"),
    ] = "dist",
    clean: Annotated[
        bool,
        typer.Option("--clean", help="Clean output directory before export"),
    ] = True,
) -> None:
    """Export a package and its dependencies for deployment."""
    from pymelos.commands.export import handle_export_command

    workspace = get_workspace()
    asyncio.run(
        handle_export_command(
            workspace=workspace,
            package_name=package,
            console=console,
            error_console=error_console,
            output=output,
            clean=clean,
        )
    )


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
