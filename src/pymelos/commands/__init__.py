"""pymelos commands."""

from pymelos.commands.add import AddProjectCommand, AddProjectOptions, AddProjectResult, add_project
from pymelos.commands.base import Command, CommandContext, SyncCommand
from pymelos.commands.bootstrap import (
    BootstrapCommand,
    BootstrapOptions,
    BootstrapResult,
    bootstrap,
)
from pymelos.commands.changed import (
    ChangedCommand,
    ChangedOptions,
    ChangedPackage,
    ChangedResult,
    get_changed_packages,
)
from pymelos.commands.clean import CleanCommand, CleanOptions, CleanResult, clean
from pymelos.commands.exec import ExecCommand, ExecOptions, exec_command
from pymelos.commands.list import (
    ListCommand,
    ListFormat,
    ListOptions,
    ListResult,
    PackageInfo,
    list_packages,
)
from pymelos.commands.release import (
    PackageRelease,
    ReleaseCommand,
    ReleaseOptions,
    ReleaseResult,
    release,
)
from pymelos.commands.run import RunCommand, RunOptions, run_script

__all__ = [
    # Base
    "Command",
    "SyncCommand",
    "CommandContext",
    # Bootstrap
    "BootstrapCommand",
    "BootstrapOptions",
    "BootstrapResult",
    "bootstrap",
    # Run
    "RunCommand",
    "RunOptions",
    "run_script",
    # Exec
    "ExecCommand",
    "ExecOptions",
    "exec_command",
    # List
    "ListCommand",
    "ListOptions",
    "ListResult",
    "ListFormat",
    "PackageInfo",
    "list_packages",
    # Clean
    "CleanCommand",
    "CleanOptions",
    "CleanResult",
    "clean",
    # Changed
    "ChangedCommand",
    "ChangedOptions",
    "ChangedResult",
    "ChangedPackage",
    "get_changed_packages",
    # Release
    "ReleaseCommand",
    "ReleaseOptions",
    "ReleaseResult",
    "PackageRelease",
    "release",
    # Add Project
    "AddProjectCommand",
    "AddProjectOptions",
    "AddProjectResult",
    "add_project",
]
