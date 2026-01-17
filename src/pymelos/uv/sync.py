"""uv sync operations."""

from __future__ import annotations

from pathlib import Path

from pymelos.uv.client import run_uv, run_uv_async


def sync(
    cwd: Path,
    *,
    frozen: bool = False,
    locked: bool = True,
    all_extras: bool = False,
    dev: bool = True,
    all_packages: bool = True,
) -> tuple[int, str, str]:
    """Run uv sync at the specified path.

    Args:
        cwd: Working directory (workspace root).
        frozen: Use frozen dependencies (no updates).
        locked: Require lock file to be up to date.
        all_extras: Install all extras.
        dev: Install dev dependencies.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    args = ["sync"]

    if frozen:
        args.append("--frozen")
    if locked:
        args.append("--locked")
    if all_extras:
        args.append("--all-extras")
    if all_packages:
        args.append("--all-packages")
    if not dev:
        args.append("--no-dev")

    result = run_uv(args, cwd=cwd, check=False)
    return result.returncode, result.stdout, result.stderr


async def sync_async(
    cwd: Path,
    *,
    frozen: bool = False,
    locked: bool = True,
    all_extras: bool = False,
    dev: bool = True,
    all_packages: bool = True,
) -> tuple[int, str, str]:
    """Run uv sync asynchronously.

    Args:
        cwd: Working directory.
        frozen: Use frozen dependencies.
        locked: Require lock file to be up to date.
        all_extras: Install all extras.
        dev: Install dev dependencies.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    args = ["sync"]

    if frozen:
        args.append("--frozen")
    if locked:
        args.append("--locked")
    if all_extras:
        args.append("--all-extras")
    if all_packages:
        args.append("--all-packages")

    if not dev:
        args.append("--no-dev")

    return await run_uv_async(args, cwd=cwd, check=False)


def lock(cwd: Path) -> tuple[int, str, str]:
    """Update the lock file.

    Args:
        cwd: Working directory.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    result = run_uv(["lock"], cwd=cwd, check=False)
    return result.returncode, result.stdout, result.stderr


def add_dependency(
    cwd: Path,
    package: str,
    *,
    dev: bool = False,
    extras: list[str] | None = None,
) -> tuple[int, str, str]:
    """Add a dependency.

    Args:
        cwd: Working directory.
        package: Package to add (e.g., "requests>=2.0").
        dev: Add as dev dependency.
        extras: Extras to include.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    args = ["add", package]

    if dev:
        args.append("--dev")
    if extras:
        for extra in extras:
            args.extend(["--extra", extra])

    result = run_uv(args, cwd=cwd, check=False)
    return result.returncode, result.stdout, result.stderr


def remove_dependency(
    cwd: Path,
    package: str,
    *,
    dev: bool = False,
) -> tuple[int, str, str]:
    """Remove a dependency.

    Args:
        cwd: Working directory.
        package: Package to remove.
        dev: Remove from dev dependencies.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    args = ["remove", package]

    if dev:
        args.append("--dev")

    result = run_uv(args, cwd=cwd, check=False)
    return result.returncode, result.stdout, result.stderr


def pip_list(cwd: Path) -> list[tuple[str, str]]:
    """List installed packages.

    Args:
        cwd: Working directory.

    Returns:
        List of (name, version) tuples.
    """
    result = run_uv(["pip", "list", "--format", "json"], cwd=cwd)

    import json

    packages = json.loads(result.stdout)
    return [(p["name"], p["version"]) for p in packages]
