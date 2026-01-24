"""Scope-based package filtering."""

from __future__ import annotations

import fnmatch

from pymelos.workspace.package import Package


def parse_scope(scope: str) -> list[str]:
    """Parse a scope string into individual patterns.

    Scope can be comma-separated names or glob patterns:
    - "core,api" -> ["core", "api"]
    - "*-lib" -> ["*-lib"]
    - "core,*-lib" -> ["core", "*-lib"]

    Args:
        scope: Comma-separated scope string.

    Returns:
        List of individual patterns.
    """
    if not scope:
        return []

    patterns = [p.strip() for p in scope.split(",")]
    return [p for p in patterns if p]


def match_scope(package: Package, patterns: list[str]) -> bool:
    """Check if a package matches any of the scope patterns.

    Args:
        package: Package to check.
        patterns: List of name or glob patterns.

    Returns:
        True if package matches any pattern.
    """
    if not patterns:
        return True  # No filter means match all

    name = package.name

    for pattern in patterns:
        # Exact match
        if name == pattern:
            return True

        # Case-insensitive exact match
        if name.lower() == pattern.lower():
            return True

        # Glob pattern match
        if fnmatch.fnmatch(name, pattern):
            return True

        # Try with normalized names (replace - with _)
        normalized_name = name.replace("-", "_")
        normalized_pattern = pattern.replace("-", "_")
        if fnmatch.fnmatch(normalized_name, normalized_pattern):
            return True

    return False


def filter_by_scope(
    packages: list[Package],
    scope: str | None,
) -> list[Package]:
    """Filter packages by scope pattern.

    Args:
        packages: List of packages to filter.
        scope: Comma-separated names or glob patterns.

    Returns:
        Filtered list of packages.
    """
    if not scope:
        return packages

    patterns = parse_scope(scope)
    if not patterns:
        return packages

    return [p for p in packages if match_scope(p, patterns)]
