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
    # We need to check:
    # 1. Commits since ref
    # 2. Staged changes
    # 3. Unstaged changes
    # 4. Untracked files

    files = set()
    package_path_str = str(package_path)

    # 1. Commits
    result = run_git_command(
        ["diff", "--name-only", f"{since}...HEAD", "--", package_path_str],
        cwd=root,
        check=False,
    )
    if result.returncode == 0:
        files.update(result.stdout.strip().splitlines())

    # 2. Staged
    result = run_git_command(
        ["diff", "--name-only", "--cached", "--", package_path_str],
        cwd=root,
        check=False,
    )
    if result.returncode == 0:
        files.update(result.stdout.strip().splitlines())

    # 3. Unstaged
    result = run_git_command(
        ["diff", "--name-only", "--", package_path_str],
        cwd=root,
        check=False,
    )
    if result.returncode == 0:
        files.update(result.stdout.strip().splitlines())

    # 4. Untracked
    result = run_git_command(
        ["ls-files", "--others", "--exclude-standard", "--", package_path_str],
        cwd=root,
        check=False,
    )
    if result.returncode == 0:
        files.update(result.stdout.strip().splitlines())

    return sorted([f for f in files if f])


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
    # Use 'since' directly (no ...HEAD) to compare against working directory
    # This captures committed, staged, and unstaged changes.
    result = run_git_command(
        ["diff", "--color=always", since, "--", file_path],
        cwd=root,
        check=False,
    )

    # If untracked, show content as new file?
    # git diff won't show untracked.
    # We can check if file is untracked using ls-files
    if not result.stdout.strip():
        # Check if untracked
        untracked = run_git_command(
            ["ls-files", "--others", "--exclude-standard", "--", file_path],
            cwd=root,
            check=False,
        )
        if untracked.returncode == 0 and untracked.stdout.strip():
            # Show file content as diff (green)
            # Use diff /dev/null file to generate diff
            diff = run_git_command(
                ["diff", "--color=always", "/dev/null", file_path], cwd=root, check=False
            )
            return diff.stdout

    return result.stdout
