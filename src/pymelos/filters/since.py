"""Git-based package filtering (--since)."""

from __future__ import annotations

from pathlib import Path

from pymelos.workspace.package import Package
from pymelos.workspace.workspace import Workspace


def get_changed_files(
    root: Path,
    since: str,
    *,
    include_untracked: bool = True,
) -> set[Path]:
    """Get files changed since a git reference.

    Args:
        root: Repository root.
        since: Git reference (branch, tag, commit).
        include_untracked: Include untracked files.

    Returns:
        Set of changed file paths (relative to root).
    """
    from pymelos.git import get_changed_files_since

    return get_changed_files_since(root, since, include_untracked=include_untracked)


def get_changed_packages(
    workspace: Workspace,
    since: str,
    *,
    include_dependents: bool = False,
) -> list[Package]:
    """Get packages that have changed since a git reference.

    Args:
        workspace: Workspace instance.
        since: Git reference.
        include_dependents: Also include packages that depend on changed packages.

    Returns:
        List of changed packages.
    """
    changed_files = get_changed_files(workspace.root, since)

    # Map changed files to packages
    changed_packages: list[Package] = []

    for package in workspace.packages.values():
        # Check if any changed file is within this package
        for changed_file in changed_files:
            abs_changed = workspace.root / changed_file
            try:
                abs_changed.relative_to(package.path)
                if package not in changed_packages:
                    changed_packages.append(package)
                break
            except ValueError:
                continue

    if include_dependents:
        affected = workspace.get_affected_packages(changed_packages)
        return affected

    return changed_packages


def filter_by_since(
    packages: list[Package],
    workspace: Workspace,
    since: str | None,
    *,
    include_dependents: bool = False,
) -> list[Package]:
    """Filter packages to only those changed since a git reference.

    Args:
        packages: List of packages to filter.
        workspace: Workspace instance.
        since: Git reference.
        include_dependents: Also include packages that depend on changed packages.

    Returns:
        Filtered list of packages.
    """
    if not since:
        return packages

    changed = get_changed_packages(workspace, since, include_dependents=include_dependents)
    changed_names = {p.name for p in changed}

    return [p for p in packages if p.name in changed_names]
