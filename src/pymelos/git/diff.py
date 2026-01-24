"""Git diff operations."""

from __future__ import annotations

from pathlib import Path

from pymelos.git.repo import run_git_command


def get_changed_files_in_package(
    root: Path,
    since: str,
    package_path: Path,
) -> list[str]:
    """Get list of changed files within a package.

    Args:
        root: Repository root.
        since: Git reference.
        package_path: Absolute path to package.

    Returns:
        List of relative file paths within the package.
    """
    # Get all changed files relative to root
    result = run_git_command(
        ["diff", "--name-only", f"{since}...HEAD", "--", str(package_path)],
        cwd=root,
    )

    files = result.stdout.strip().splitlines()
    return [f for f in files if f]


def get_file_diff(
    root: Path,
    since: str,
    file_path: str,
) -> str:
    """Get colorized diff for a specific file.

    Args:
        root: Repository root.
        since: Git reference.
        file_path: Path to file (relative to root).

    Returns:
        Diff output.
    """
    result = run_git_command(
        ["diff", "--color=always", f"{since}...HEAD", "--", file_path],
        cwd=root,
    )
    return result.stdout
