"""Bootstrap command implementation."""

from __future__ import annotations

from dataclasses import dataclass

from pymelos.commands.base import Command, CommandContext, pip_install_editable
from pymelos.execution import ExecutionResult
from pymelos.uv import sync
from pymelos.workspace.workspace import Workspace


@dataclass
class BootstrapResult:
    """Result of bootstrap command.

    Attributes:
        success: Whether bootstrap succeeded.
        packages_installed: Number of packages in workspace.
        hook_results: Results of bootstrap hooks.
        uv_output: Output from uv sync.
    """

    success: bool
    packages_installed: int
    hook_results: list[ExecutionResult]
    uv_output: str


@dataclass
class BootstrapOptions:
    """Options for bootstrap command."""

    clean_first: bool = False
    frozen: bool = False
    locked: bool = True
    skip_hooks: bool = False
    editable: bool = True


class BootstrapCommand(Command[BootstrapResult]):
    """Bootstrap the workspace.

    This command:
    1. Runs uv sync to install dependencies
    2. Verifies workspace package linking
    3. Runs bootstrap hooks from configuration
    """

    def __init__(self, context: CommandContext, options: BootstrapOptions | None = None) -> None:
        super().__init__(context)
        self.options = options or BootstrapOptions()

    async def execute(self) -> BootstrapResult:
        """Execute bootstrap."""
        from pymelos.commands.clean import CleanCommand, CleanOptions
        from pymelos.execution import run_in_package

        hook_results: list[ExecutionResult] = []

        # Optionally clean first
        if self.options.clean_first:
            clean_cmd = CleanCommand(self.context, CleanOptions())
            await clean_cmd.execute()

        # Check if lockfile exists - if not, don't use --locked flag
        lockfile = self.workspace.root / "uv.lock"
        use_locked = self.options.locked and lockfile.exists()

        # Run uv sync
        exit_code, stdout, stderr = sync(
            self.workspace.root,
            frozen=self.options.frozen,
            locked=use_locked,
            dev=True,
            all_packages=True,
        )

        # If --locked failed due to outdated lockfile, retry without --locked
        if exit_code != 0 and use_locked and "needs to be updated" in stderr:
            exit_code, stdout, stderr = sync(
                self.workspace.root,
                frozen=self.options.frozen,
                locked=False,
            )

        if exit_code != 0:
            return BootstrapResult(
                success=False,
                packages_installed=0,
                hook_results=[],
                uv_output=stderr or stdout,
            )
        # Install workspace packages (editable)
        if self.options.editable and self.workspace.packages:
            package_paths = [pkg.path for pkg in self.workspace.packages.values()]
            pip_install_editable(package_paths)

        # Run bootstrap hooks
        if not self.options.skip_hooks:
            for hook in self.workspace.config.bootstrap.hooks:
                if hook.run_once:
                    # Run at workspace root
                    from pymelos.execution.runner import run_command

                    _, out, err, _ = await run_command(
                        hook.run,
                        self.workspace.root,
                        env=self.context.env,
                    )
                else:
                    # Run in matching packages
                    packages = self.workspace.filter_packages(scope=hook.scope)
                    for pkg in packages:
                        result = await run_in_package(pkg, hook.run, env=self.context.env)
                        hook_results.append(result)

        return BootstrapResult(
            success=True,
            packages_installed=len(self.workspace.packages),
            hook_results=hook_results,
            uv_output=stdout,
        )


async def bootstrap(
    workspace: Workspace,
    *,
    clean_first: bool = False,
    frozen: bool = False,
    skip_hooks: bool = False,
    verbose: bool = False,
) -> BootstrapResult:
    """Convenience function to bootstrap a workspace.

    Args:
        workspace: Workspace to bootstrap.
        clean_first: Clean before bootstrap.
        frozen: Use frozen dependencies.
        skip_hooks: Skip bootstrap hooks.
        verbose: Show verbose output.

    Returns:
        Bootstrap result.
    """

    context = CommandContext(workspace=workspace, verbose=verbose)
    options = BootstrapOptions(
        clean_first=clean_first,
        frozen=frozen,
        skip_hooks=skip_hooks,
    )
    cmd = BootstrapCommand(context, options)
    return await cmd.execute()
