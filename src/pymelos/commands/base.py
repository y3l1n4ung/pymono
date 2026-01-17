"""Base command infrastructure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import run
from typing import Generic, TypeVar

from pymelos.workspace import Workspace

TResult = TypeVar("TResult")


@dataclass
class CommandContext:
    """Context passed to all commands.

    Attributes:
        workspace: The workspace instance.
        dry_run: If True, show what would happen without making changes.
        verbose: If True, show detailed output.
    """

    workspace: Workspace
    dry_run: bool = False
    verbose: bool = False
    env: dict[str, str] = field(default_factory=dict)


class Command(ABC, Generic[TResult]):
    """Base class for all pymelos commands.

    Commands encapsulate the logic for a specific operation.
    They receive a context and return a result.
    """

    def __init__(self, context: CommandContext) -> None:
        """Initialize command.

        Args:
            context: Command context.
        """
        self.context = context
        self.workspace = context.workspace

    @abstractmethod
    async def execute(self) -> TResult:
        """Execute the command.

        Returns:
            Command-specific result.
        """
        ...

    def validate(self) -> list[str]:
        """Validate that the command can be executed.

        Returns:
            List of validation errors (empty if valid).
        """
        return []


class SyncCommand(ABC, Generic[TResult]):
    """Base class for synchronous commands."""

    def __init__(self, context: CommandContext) -> None:
        """Initialize command.

        Args:
            context: Command context.
        """
        self.context = context
        self.workspace = context.workspace

    @abstractmethod
    def execute(self) -> TResult:
        """Execute the command synchronously.

        Returns:
            Command-specific result.
        """
        ...

    def validate(self) -> list[str]:
        """Validate that the command can be executed.

        Returns:
            List of validation errors (empty if valid).
        """
        return []


def pip_install_editable(paths: Path | Sequence[Path | str]) -> None:
    """
    Install one or more workspace packages in editable mode.
    """
    if isinstance(paths, Path | str):
        paths = [paths]  # wrap single path into list

    # Convert all to strings
    paths_str = [str(p) for p in paths]

    # Run uv pip install -e for all packages
    run(["uv", "pip", "install", "-e", *paths_str], check=True)
