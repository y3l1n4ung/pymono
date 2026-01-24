"""Clean command implementation."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console

from pymelos.commands.base import Command, CommandContext
from pymelos.workspace import Package
from pymelos.workspace.workspace import Workspace


@dataclass
class CleanResult:
    """Result of clean command."""

    files_removed: int
    dirs_removed: int
    bytes_freed: int
    packages_cleaned: list[str]


@dataclass
class CleanOptions:
    """Options for clean command."""

    scope: str | None = None
    patterns: list[str] | None = None
    protected: list[str] | None = None
    dry_run: bool = False


class CleanCommand(Command[CleanResult]):
    """Clean build artifacts from packages."""

    def __init__(self, context: CommandContext, options: CleanOptions | None = None) -> None:
        super().__init__(context)
        self.options = options or CleanOptions()

    def get_packages(self) -> list[Package]:
        """Get packages to clean."""
        from pymelos.filters import apply_filters

        packages = list(self.workspace.packages.values())
        return apply_filters(packages, scope=self.options.scope)

    def get_patterns(self) -> list[str]:
        """Get patterns to clean."""
        if self.options.patterns:
            return self.options.patterns
        return self.workspace.config.clean.patterns

    def get_protected(self) -> set[str]:
        """Get protected patterns."""
        if self.options.protected:
            return set(self.options.protected)
        return set(self.workspace.config.clean.protected)

    def is_protected(self, path: Path, protected: set[str]) -> bool:
        """Check if a path is protected."""
        import fnmatch

        return any(fnmatch.fnmatch(path.name, pattern) for pattern in protected)

    def _calculate_size(self, path: Path) -> int:
        """Calculate total size of a path (file or directory)."""
        if path.is_file():
            return path.stat().st_size
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

    def _get_paths_to_clean(
        self, packages: list[Package], patterns: list[str], protected: set[str]
    ) -> list[tuple[str, Path]]:
        """Get all paths to clean with their package names."""
        return [
            (pkg.name, path)
            for pkg in packages
            for pattern in patterns
            for path in pkg.path.glob(pattern)
            if not self.is_protected(path, protected)
        ]

    async def execute(self) -> CleanResult:
        """Execute the clean command."""
        paths_to_clean = self._get_paths_to_clean(
            self.get_packages(), self.get_patterns(), self.get_protected()
        )

        files_removed = 0
        dirs_removed = 0
        bytes_freed = 0
        packages_cleaned: set[str] = set()
        is_dry_run = self.options.dry_run or self.context.dry_run

        for pkg_name, path in paths_to_clean:
            bytes_freed += self._calculate_size(path)
            packages_cleaned.add(pkg_name)

            if path.is_file():
                files_removed += 1
                if not is_dry_run:
                    path.unlink()
            elif path.is_dir():
                dirs_removed += 1
                if not is_dry_run:
                    shutil.rmtree(path)

        return CleanResult(
            files_removed=files_removed,
            dirs_removed=dirs_removed,
            bytes_freed=bytes_freed,
            packages_cleaned=list(packages_cleaned),
        )


async def clean(
    workspace: Workspace,
    *,
    scope: str | None = None,
    patterns: list[str] | None = None,
    dry_run: bool = False,
) -> CleanResult:
    """Convenience function to clean packages.

    Args:
        workspace: Workspace to clean.
        scope: Package scope filter.
        patterns: Override clean patterns.
        dry_run: Show what would be cleaned.

    Returns:
        Clean result.
    """

    context = CommandContext(workspace=workspace, dry_run=dry_run)
    options = CleanOptions(scope=scope, patterns=patterns, dry_run=dry_run)
    cmd = CleanCommand(context, options)
    return await cmd.execute()


async def handle_clean_command(
    workspace: Workspace,
    console: Console,
    error_console: Console,
    scope: str | None = None,
    patterns: list[str] | None = None,
    dry_run: bool = False,
) -> None:
    try:
        result = await clean(workspace, scope=scope, patterns=patterns, dry_run=dry_run)

        if dry_run:
            console.print("[yellow]Dry run - no files removed[/yellow]")

        console.print(
            f"{'Would clean' if dry_run else 'Cleaned'} "
            f"{result.files_removed} files, {result.dirs_removed} directories "
            f"({result.bytes_freed / 1024:.1f} KB)"
        )
    except Exception as e:
        error_console.print_exception()
        raise typer.Exit(1) from e
