"""pymelos CLI application."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

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
    from pymelos.cli.commands.init import init_workspace

    try:
        init_workspace(path or Path.cwd(), name)
        console.print("[green]Workspace initialized![/green]")
        console.print("Run [bold]pymelos bootstrap[/bold] to install dependencies.")
    except PyMelosError as e:
        error_console.print(f"[red]Error:[/red] {e.message}")
        raise typer.Exit(1) from e


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
    from pymelos.commands import bootstrap as do_bootstrap

    workspace = get_workspace()

    async def run() -> None:
        result = await do_bootstrap(
            workspace,
            clean_first=clean,
            frozen=frozen,
            skip_hooks=skip_hooks,
        )
        if result.success:
            console.print(f"[green]Bootstrapped {result.packages_installed} packages[/green]")
        else:
            error_console.print(f"[red]Bootstrap failed:[/red] {result.uv_output}")
            raise typer.Exit(1)

    asyncio.run(run())


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
    from pymelos.commands import add_project

    workspace = get_workspace()

    async def run() -> None:
        result = await add_project(workspace, name, project_type, folder, editable)
        if result.success:
            console.print(f"[green]Added project {name}[/green]")
        else:
            error_console.print(f"[red]Failed to add project {name}:[/red] {result.message}")
            raise typer.Exit(1)

    asyncio.run(run())


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
    from pymelos.commands import run_script

    workspace = get_workspace()
    ignore_list = parse_comma_list(ignore)

    async def run() -> None:
        result = await run_script(
            workspace,
            script,
            scope=scope,
            since=since,
            ignore=ignore_list,
            concurrency=concurrency,
            fail_fast=fail_fast,
            topological=not no_topological,
        )

        for r in result:
            package_name = escape(f"[{r.package_name}]")
            if r.success:
                console.print(f"[green]✓[/green] {package_name} ({r.duration_ms}ms)")
                if r.stdout:
                    console.print(r.stdout)
            else:
                console.print(f"[red]✗[/red] {package_name} (exit {r.exit_code})")
                if r.stderr:
                    console.print(r.stderr)

        if result.all_success:
            console.print(f"\n[green]All {len(result)} packages passed[/green]")
        else:
            console.print(
                f"\n[red]{result.failure_count} failed, {result.success_count} passed[/red]"
            )
            raise typer.Exit(1)

    asyncio.run(run())


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
    from pymelos.commands import exec_command

    workspace = get_workspace()
    ignore_list = parse_comma_list(ignore)

    async def run() -> None:
        result = await exec_command(
            workspace,
            command,
            scope=scope,
            since=since,
            ignore=ignore_list,
            concurrency=concurrency,
            fail_fast=fail_fast,
        )

        for r in result:
            console.print(f"\n[bold][{r.package_name}][/bold]")
            if r.stdout:
                console.print(r.stdout)
            if r.stderr:
                error_console.print(r.stderr)

        if not result.all_success:
            raise typer.Exit(1)

    asyncio.run(run())


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
    from pymelos.commands import ListFormat, list_packages

    workspace = get_workspace()

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
    from pymelos.commands import clean as do_clean

    workspace = get_workspace()

    async def run() -> None:
        result = await do_clean(workspace, scope=scope, dry_run=dry_run)

        if dry_run:
            console.print("[yellow]Dry run - no files removed[/yellow]")

        console.print(
            f"{'Would clean' if dry_run else 'Cleaned'} "
            f"{result.files_removed} files, {result.dirs_removed} directories "
            f"({result.bytes_freed / 1024:.1f} KB)"
        )

    asyncio.run(run())


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
    from pymelos.commands import get_changed_packages

    workspace = get_workspace()
    result = get_changed_packages(
        workspace,
        since,
        include_dependents=not no_dependents,
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
) -> None:
    """Version and publish packages."""
    from pymelos.commands import release as do_release
    from pymelos.versioning import BumpType

    workspace = get_workspace()

    bump_type = None
    if bump:
        try:
            bump_type = BumpType[bump.upper()]
        except KeyError:
            error_console.print(f"[red]Invalid bump type:[/red] {bump}")
            raise typer.Exit(1) from None

    async def run() -> None:
        result = await do_release(
            workspace,
            scope=scope,
            bump=bump_type,
            prerelease=prerelease,
            dry_run=dry_run,
            publish=publish,
            no_git_tag=no_git_tag,
            no_changelog=no_changelog,
            no_commit=no_commit,
        )

        if not result.releases:
            console.print("[yellow]No packages to release[/yellow]")
            return

        if dry_run:
            console.print("[yellow]Dry run - no changes made[/yellow]\n")
            console.print("Pending releases:")

        table = Table()
        table.add_column("Package")
        table.add_column("Current")
        table.add_column("Next")
        table.add_column("Bump")

        for r in result.releases:
            table.add_row(
                r.name,
                r.old_version,
                r.new_version,
                r.bump_type.name.lower(),
            )

        console.print(table)

        if not dry_run:
            if result.success:
                console.print(f"\n[green]Released {len(result.releases)} packages[/green]")
                if result.commit_sha:
                    console.print(f"Commit: {result.commit_sha[:8]}")
            else:
                error_console.print(f"\n[red]Release failed:[/red] {result.error}")
                raise typer.Exit(1)

    asyncio.run(run())


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
