"""Version command implementation for bumping and tagging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pymelos.commands.base import Command, CommandContext
from pymelos.versioning import (
    BumpType,
    Version,
    determine_bump,
    generate_changelog_entry,
    parse_commit,
    prepend_to_changelog,
    update_all_versions,
)

if TYPE_CHECKING:
    from rich.console import Console

    from pymelos.workspace.workspace import Workspace


@dataclass
class VersionResult:
    """Result of version command."""

    releases: list[dict[str, Any]]
    commit_sha: str | None = None
    success: bool = True
    error: str | None = None


@dataclass
class VersionOptions:
    """Options for version command."""

    scope: str | None = None
    bump: BumpType | None = None
    prerelease: str | None = None
    dry_run: bool = False
    no_git_tag: bool = False
    no_changelog: bool = False
    no_commit: bool = False
    yes: bool = False


class VersionCommand(Command[VersionResult]):
    """Manage package versions, changelogs, and git tags."""

    def __init__(self, context: CommandContext, options: VersionOptions | None = None) -> None:
        super().__init__(context)
        self.options = options or VersionOptions()

    async def execute(self) -> VersionResult:
        from pymelos.filters import filter_by_scope

        pkgs = filter_by_scope(list(self.workspace.packages.values()), self.options.scope)

        planned = []
        for pkg in pkgs:
            from pymelos.git import get_commits, get_latest_package_tag

            last_tag = get_latest_package_tag(self.workspace.root, pkg.name)
            since_ref = last_tag.name if last_tag else None

            commits = get_commits(self.workspace.root, since=since_ref, path=pkg.path)

            if not commits and not self.options.bump:
                continue

            parsed = [p for c in commits if (p := parse_commit(c)) is not None]
            bump = self.options.bump or determine_bump(parsed)

            if bump == BumpType.NONE:
                continue

            old_v = Version.parse(pkg.version)
            new_v = old_v.bump(bump, self.options.prerelease)

            planned.append(
                {
                    "name": pkg.name,
                    "old": str(old_v),
                    "new": str(new_v),
                    "bump": bump.value,
                    "pkg_obj": pkg,
                    "changelog": generate_changelog_entry(str(new_v), parsed, package_name=pkg.name)
                    if parsed
                    else f"## {new_v}\n\n- Manual bump\n",
                }
            )

        if not planned:
            return VersionResult([], success=True)

        if self.options.dry_run:
            return VersionResult(planned, success=True)

        # 1. Apply changes to files
        for item in planned:
            pkg = item["pkg_obj"]
            update_all_versions(pkg.path, pkg.name, item["new"])
            if not self.options.no_changelog:
                prepend_to_changelog(pkg.path / "CHANGELOG.md", item["changelog"])

        # 2. Git operations
        from pymelos.git import create_tag, run_git_command

        sha = None
        if not self.options.no_commit:
            run_git_command(["add", "-A"], cwd=self.workspace.root)

            pkg_summaries = ", ".join(f"{i['name']}@{i['new']}" for i in planned)
            msg = self.workspace.config.versioning.commit_message.format(packages=pkg_summaries)

            run_git_command(["commit", "-m", msg], cwd=self.workspace.root)
            sha = run_git_command(["rev-parse", "HEAD"], cwd=self.workspace.root).stdout.strip()

            # 3. Create tags
            if not self.options.no_git_tag:
                for item in planned:
                    tag = self.workspace.config.versioning.tag_format.format(
                        name=item["name"], version=item["new"]
                    )
                    create_tag(self.workspace.root, tag, message=f"Release {tag}")

        return VersionResult(planned, commit_sha=sha)


async def version(
    workspace: Workspace,
    *,
    scope: str | None = None,
    bump: BumpType | None = None,
    prerelease: str | None = None,
    dry_run: bool = False,
    no_git_tag: bool = False,
    no_changelog: bool = False,
    no_commit: bool = False,
    yes: bool = False,
) -> VersionResult:
    """Convenience function for versioning."""
    context = CommandContext(workspace=workspace, dry_run=dry_run)
    options = VersionOptions(
        scope=scope,
        bump=bump,
        prerelease=prerelease,
        dry_run=dry_run,
        no_git_tag=no_git_tag,
        no_changelog=no_changelog,
        no_commit=no_commit,
        yes=yes,
    )
    cmd = VersionCommand(context, options)
    return await cmd.execute()


async def handle_version_command(
    workspace: Workspace,
    *,
    console: Console,
    error_console: Console,
    scope: str | None = None,
    bump: str | None = None,
    prerelease: str | None = None,
    dry_run: bool = False,
    no_git_tag: bool = False,
    no_changelog: bool = False,
    no_commit: bool = False,
    yes: bool = False,
) -> None:
    """CLI handler for the version command."""
    import typer

    from pymelos.cli.output.table import print_table

    try:
        bump_type = None
        if bump:
            try:
                bump_type = BumpType[bump.upper()]
            except KeyError as e:
                error_console.print(f"[red]Invalid bump type:[/red] {bump}")
                raise typer.Exit(1) from e

        # 1. Generate Plan (Dry Run)
        plan = await version(
            workspace,
            scope=scope,
            bump=bump_type,
            prerelease=prerelease,
            dry_run=True,
            no_git_tag=no_git_tag,
            no_changelog=no_changelog,
            no_commit=no_commit,
        )

        if not plan.releases:
            console.print("[yellow]No packages require versioning.[/yellow]")
            return

        # 2. Display Plan with print_table utility
        print("\nVersioning Plan:")
        print_table(data=plan.releases, columns=["name", "old", "new", "bump"])

        if dry_run:
            console.print("\n[yellow]Dry run mode: No changes will be made.[/yellow]")
            return

        # 3. Confirmation
        if not yes and not typer.confirm("\nProceed with these version changes?", default=False):
            console.print("[yellow]Versioning cancelled.[/yellow]")
            return

        # 4. Actual Execution
        result = await version(
            workspace,
            scope=scope,
            bump=bump_type,
            prerelease=prerelease,
            dry_run=False,
            no_git_tag=no_git_tag,
            no_changelog=no_changelog,
            no_commit=no_commit,
        )

        if result.success:
            console.print(
                f"\n[green]Successfully versioned {len(result.releases)} packages.[/green]"
            )
            if result.commit_sha:
                console.print(f"Commit: [blue]{result.commit_sha[:8]}[/blue]")
        else:
            error_console.print(f"\n[red]Versioning failed:[/red] {result.error}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        error_console.print_exception()
        raise typer.Exit(1) from e
