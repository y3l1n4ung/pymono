"""pymelos commands."""

from pymelos.commands.add import (
    AddProjectCommand,
    AddProjectOptions,
    AddProjectResult,
    add_project,
    handle_add_project,
)
from pymelos.commands.base import Command, CommandContext, SyncCommand
from pymelos.commands.bootstrap import (
    BootstrapCommand,
    BootstrapOptions,
    BootstrapResult,
    bootstrap,
    handle_bootstrap,
)
from pymelos.commands.changed import (
    ChangedCommand,
    ChangedOptions,
    ChangedPackage,
    ChangedResult,
    get_changed_packages,
    handle_changed_command,
)
from pymelos.commands.clean import (
    CleanCommand,
    CleanOptions,
    CleanResult,
    clean,
    handle_clean_command,
)
from pymelos.commands.exec import ExecCommand, ExecOptions, exec_command, handle_exec_command
from pymelos.commands.list import (
    ListCommand,
    ListFormat,
    ListOptions,
    ListResult,
    PackageInfo,
    handle_list_command,
    list_packages,
)
from pymelos.commands.release import (
    PackageRelease,
    ReleaseCommand,
    ReleaseOptions,
    ReleaseResult,
    handle_release_command,
    release,
)
from pymelos.commands.run import RunCommand, RunOptions, handle_run_script, run_script
from pymelos.commands.version import (
    Version,
    VersionCommand,
    VersionOptions,
    VersionResult,
    handle_version_command,
    version,
)

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
    "handle_bootstrap",
    # Run
    "RunCommand",
    "RunOptions",
    "run_script",
    "handle_run_script",
    # Exec
    "ExecCommand",
    "ExecOptions",
    "exec_command",
    "handle_exec_command",
    # List
    "ListCommand",
    "ListOptions",
    "ListResult",
    "ListFormat",
    "PackageInfo",
    "list_packages",
    "handle_list_command",
    # Clean
    "CleanCommand",
    "CleanOptions",
    "CleanResult",
    "clean",
    "handle_clean_command",
    # Changed
    "ChangedCommand",
    "ChangedOptions",
    "ChangedResult",
    "ChangedPackage",
    "get_changed_packages",
    "handle_changed_command"
    # Release
    "ReleaseCommand",
    "ReleaseOptions",
    "ReleaseResult",
    "PackageRelease",
    "release",
    "handle_release_command",
    # Version
    "Version",
    "VersionCommand",
    "VersionOptions",
    "VersionResult",
    "handle_version_command"
    "version"
    # Add Project
    "AddProjectCommand",
    "AddProjectOptions",
    "AddProjectResult",
    "add_project",
    "handle_add_project",
]  # type: ignore
