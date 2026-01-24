"""Run command implementation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.markup import escape

from pymelos.commands.base import Command, CommandContext
from pymelos.errors import ScriptNotFoundError
from pymelos.execution import BatchResult, ParallelExecutor

if TYPE_CHECKING:
    from pymelos.workspace import Package
    from pymelos.workspace.workspace import Workspace


@dataclass
class RunOptions:
    """Options for run command."""

    script_name: str
    scope: str | None = None
    since: str | None = None
    ignore: list[str] | None = None
    concurrency: int = 4
    fail_fast: bool = False
    topological: bool = True
    include_dependents: bool = False


class RunCommand(Command[BatchResult]):
    """Run a defined script across packages.

    Scripts are defined in pymelos.yaml and can be filtered
    by scope, git changes, or ignored patterns.
    """

    def __init__(
        self,
        context: CommandContext,
        options: RunOptions,
        output_handler: Callable[[str, str, bool], None] | None = None,
    ) -> None:
        super().__init__(context)
        self.options = options
        self.output_handler = output_handler

    def validate(self) -> list[str]:
        """Validate the command."""
        errors = super().validate()

        script = self.workspace.config.get_script(self.options.script_name)
        if not script:
            errors.append(
                f"Script '{self.options.script_name}' not found. "
                f"Available: {', '.join(self.workspace.config.script_names)}"
            )

        return errors

    def get_packages(self) -> list[Package]:
        """Get packages to run script in."""
        from pymelos.filters import apply_filters_with_since

        packages = list(self.workspace.packages.values())

        # Get script-specific scope if defined
        script = self.workspace.config.get_script(self.options.script_name)
        scope = self.options.scope
        if not scope and script and script.scope:
            scope = script.scope

        return apply_filters_with_since(
            packages,
            self.workspace,
            scope=scope,
            since=self.options.since,
            ignore=self.options.ignore,
            include_dependents=self.options.include_dependents,
        )

    async def execute(self) -> BatchResult:
        """Execute the script."""
        # Validate first
        errors = self.validate()
        if errors:
            raise ScriptNotFoundError(
                self.options.script_name,
                self.workspace.config.script_names,
            )

        script = self.workspace.config.get_script(self.options.script_name)
        assert script is not None  # validate() already checked

        # Get matching packages
        packages = self.get_packages()
        if not packages:
            return BatchResult(results=[])

        # Build environment
        env = dict(self.context.env)
        env.update(self.workspace.config.env)
        env.update(script.env)

        # Get execution settings
        concurrency = self.options.concurrency
        fail_fast = self.options.fail_fast or script.fail_fast
        topological = self.options.topological and script.topological

        executor = ParallelExecutor(
            concurrency=concurrency,
            fail_fast=fail_fast,
        )

        if topological:
            # Execute in dependency order
            batches = self.workspace.parallel_batches(packages)
            return await executor.execute_batches(
                batches, script.run, env=env, output_handler=self.output_handler
            )
        else:
            # Execute all in parallel
            return await executor.execute(
                packages, script.run, env=env, output_handler=self.output_handler
            )


async def run_script(
    workspace: Workspace,
    script_name: str,
    *,
    scope: str | None = None,
    since: str | None = None,
    ignore: list[str] | None = None,
    concurrency: int = 4,
    fail_fast: bool = False,
    topological: bool = True,
    output_handler: Callable[[str, str, bool], None] | None = None,
) -> BatchResult:
    """Convenience function to run a script.

    Args:
        workspace: Workspace to run in.
        script_name: Name of script to run.
        scope: Package scope filter.
        since: Git reference for change detection.
        ignore: Patterns to exclude.
        concurrency: Parallel jobs.
        fail_fast: Stop on first failure.
        topological: Respect dependency order.
        output_handler: Callback for output streaming.

    Returns:
        Batch result with all execution results.
    """

    context = CommandContext(workspace=workspace)
    options = RunOptions(
        script_name=script_name,
        scope=scope,
        since=since,
        ignore=ignore,
        concurrency=concurrency,
        fail_fast=fail_fast,
        topological=topological,
    )
    cmd = RunCommand(context, options, output_handler=output_handler)
    return await cmd.execute()


async def handle_run_script(
    workspace: Workspace,
    script_name: str,
    *,
    console: Console,
    error_console: Console,
    scope: str | None = None,
    since: str | None = None,
    ignore: list[str] | None = None,
    concurrency: int = 4,
    fail_fast: bool = False,
    topological: bool = True,
) -> None:
    def output_handler(pkg_name: str, line: str, is_stderr: bool) -> None:
        prefix = f"[{pkg_name}] "
        style = "red" if is_stderr else "dim"
        # Using print directly might be safer for interleaved output than console.print?
        # But console.print handles styles.
        # Ensure thread safety if needed, though we are in async loop
        if is_stderr:
            error_console.print(f"[{style}]{escape(prefix)}[/{style}]{escape(line)}")
        else:
            console.print(f"[{style}]{escape(prefix)}[/{style}]{escape(line)}")

    try:
        result = await run_script(
            workspace,
            script_name,
            scope=scope,
            since=since,
            ignore=ignore,
            concurrency=concurrency,
            fail_fast=fail_fast,
            topological=topological,
            output_handler=output_handler,
        )
        if result.all_success:
            console.print(f"\n[green]All {len(result)} packages passed[/green]")
        else:
            console.print(
                f"\n[red]{result.failure_count} failed, {result.success_count} passed[/red]"
            )
            raise typer.Exit(1)

    except Exception as err:
        error_console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1) from err
