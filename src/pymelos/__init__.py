"""pymelos - Python monorepo manager.

A Melos-like monorepo management tool for Python, providing:
- Workspace discovery and package management
- Parallel command execution with dependency ordering
- Git-based change detection
- Semantic versioning and release management
- VS Code integration
"""

from pymelos.config import PyMelosConfig, load_config
from pymelos.errors import (
    BootstrapError,
    ConfigurationError,
    CyclicDependencyError,
    ExecutionError,
    GitError,
    PackageNotFoundError,
    PublishError,
    PyMelosError,
    ReleaseError,
    ScriptNotFoundError,
    ValidationError,
    WorkspaceNotFoundError,
)
from pymelos.execution import (
    BatchResult,
    ExecutionResult,
    ExecutionStatus,
    ParallelExecutor,
)
from pymelos.workspace import DependencyGraph, Package, Workspace

__version__ = "0.1.2"

__all__ = [
    # Version
    "__version__",
    # Core
    "Workspace",
    "Package",
    "DependencyGraph",
    "PyMelosConfig",
    "load_config",
    # Execution
    "ExecutionResult",
    "ExecutionStatus",
    "BatchResult",
    "ParallelExecutor",
    # Errors
    "PyMelosError",
    "ConfigurationError",
    "WorkspaceNotFoundError",
    "PackageNotFoundError",
    "CyclicDependencyError",
    "ScriptNotFoundError",
    "ExecutionError",
    "BootstrapError",
    "GitError",
    "ReleaseError",
    "PublishError",
    "ValidationError",
]
