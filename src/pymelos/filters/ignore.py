"""Ignore-based package filtering."""

from __future__ import annotations

import fnmatch

from pymelos.workspace.package import Package


def should_ignore(package: Package, patterns: list[str]) -> bool:
    """Check if a package matches any ignore pattern.

    Args:
        package: Package to check.
        patterns: List of ignore patterns.

    Returns:
        True if package should be ignored.
    """
    if not patterns:
        return False

    name = package.name
    path_str = str(package.path)

    for pattern in patterns:
        # Match by name
        if fnmatch.fnmatch(name, pattern):
            return True

        # Match by normalized name
        if fnmatch.fnmatch(name.replace("-", "_"), pattern.replace("-", "_")):
            return True

        # Match by path
        if fnmatch.fnmatch(path_str, pattern):
            return True

    return False


def filter_by_ignore(
    packages: list[Package],
    ignore: list[str] | None,
) -> list[Package]:
    """Filter out packages matching ignore patterns.

    Args:
        packages: List of packages to filter.
        ignore: List of ignore patterns.

    Returns:
        Filtered list of packages (not matching any ignore pattern).
    """
    if not ignore:
        return packages

    return [p for p in packages if not should_ignore(p, ignore)]
