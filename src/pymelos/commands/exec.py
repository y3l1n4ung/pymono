"""Exec command implementation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.markup import escape

from pymelos.commands.base import Command, CommandContext
from pymelos.execution import BatchResult, ParallelExecutor

if TYPE_CHECKING:
    from pymelos.workspace import Package
    from pymelos.workspace.workspace import Workspace


@dataclass
class ExecOptions:
    """Options for exec command."""

    command: str
    scope: str | None = None
    since: str | None = None
    ignore: list[str] | None = None
    concurrency: int = 4
    fail_fast: bool = False
    topological: bool = False  # exec doesn't default to topological
    include_dependents: bool = False


class ExecCommand(Command[BatchResult]):
    """Execute an arbitrary command across packages.

    Unlike 'run', exec takes a direct command string rather
    than a script name from configuration.
    """

    def __init__(
        self,
        context: CommandContext,
        options: ExecOptions,
        output_handler: Callable[[str, str, bool], None] | None = None,
    ) -> None:
        super().__init__(context)
        self.options = options
        self.output_handler = output_handler

    def get_packages(self) -> list[Package]:
        """Get packages to execute command in."""
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

    async def execute(self) -> BatchResult:
        """Execute the command."""
        packages = self.get_packages()
        if not packages:
            return BatchResult(results=[])

        # Build environment
        env = dict(self.context.env)
        env.update(self.workspace.config.env)

        executor = ParallelExecutor(
            concurrency=self.options.concurrency,
            fail_fast=self.options.fail_fast,
        )

        if self.options.topological:
            batches = self.workspace.parallel_batches(packages)
            return await executor.execute_batches(
                batches, self.options.command, env=env, output_handler=self.output_handler
            )
        else:
            return await executor.execute(
                packages, self.options.command, env=env, output_handler=self.output_handler
            )


async def exec_command(
    workspace: Workspace,
    command: str,
    *,
    scope: str | None = None,
    since: str | None = None,
    ignore: list[str] | None = None,
    concurrency: int = 4,
    fail_fast: bool = False,
    topological: bool = False,
    output_handler: Callable[[str, str, bool], None] | None = None,
) -> BatchResult:
    """Convenience function to execute a command.

    Args:
        workspace: Workspace to run in.
        command: Command to execute.
        scope: Package scope filter.
        since: Git reference.
        ignore: Patterns to exclude.
        concurrency: Parallel jobs.
        fail_fast: Stop on first failure.
        topological: Respect dependency order.
        output_handler: Callback for output streaming.

    Returns:
        Batch result.
    """

    context = CommandContext(workspace=workspace)
    options = ExecOptions(
        command=command,
        scope=scope,
        since=since,
        ignore=ignore,
        concurrency=concurrency,
        fail_fast=fail_fast,
        topological=topological,
    )
    cmd = ExecCommand(context, options, output_handler=output_handler)
    return await cmd.execute()


async def handle_exec_command(
    workspace: Workspace,
    command: str,
    *,
    console: Console,
    error_console: Console,
    scope: str | None = None,
    since: str | None = None,
    ignore: list[str] | None = None,
    concurrency: int = 4,
    fail_fast: bool = False,
    topological: bool = False,
) -> None:
    def output_handler(pkg_name: str, line: str, is_stderr: bool) -> None:
        prefix = f"[{pkg_name}] "
        style = "red" if is_stderr else "dim"
        if is_stderr:
            error_console.print(f"[{style}]{escape(prefix)}[/{style}]{escape(line)}")
        else:
            console.print(f"[{style}]{escape(prefix)}[/{style}]{escape(line)}")

    try:
        result = await exec_command(
            workspace,
            command,
            scope=scope,
            since=since,
            ignore=ignore,
            concurrency=concurrency,
            fail_fast=fail_fast,
            topological=topological,
            output_handler=output_handler,
        )
        for r in result:
            package_name = escape(f"[{r.package_name}]")
            if r.success:
                # Output already streamed
                pass
            else:
                error_console.print(f"[red]✗[/red] {package_name} ({r.duration_ms}ms)")
                # Output already streamed
    except Exception as e:
        error_console.print(e)
        raise typer.Exit(1) from e
