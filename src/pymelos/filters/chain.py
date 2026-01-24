"""Filter chain composition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymelos.filters.ignore import filter_by_ignore
from pymelos.filters.scope import filter_by_scope
from pymelos.workspace.package import Package
from pymelos.workspace.workspace import Workspace


def apply_filters(
    packages: list[Package],
    *,
    scope: str | None = None,
    ignore: list[str] | None = None,
    names: list[str] | None = None,
) -> list[Package]:
    """Apply multiple filters to a package list.

    Filters are applied in order:
    1. Explicit names (if provided, only these packages)
    2. Scope pattern matching
    3. Ignore pattern exclusion

    Args:
        packages: List of packages to filter.
        scope: Comma-separated names or glob patterns.
        ignore: Patterns to exclude.
        names: Explicit list of package names (overrides scope).

    Returns:
        Filtered list of packages.
    """
    result = packages

    # If explicit names provided, filter to just those first
    if names:
        name_set = set(names)
        result = [p for p in result if p.name in name_set]
    else:
        # Apply scope filter
        result = filter_by_scope(result, scope)

    # Apply ignore filter
    result = filter_by_ignore(result, ignore)

    return result


def apply_filters_with_since(
    packages: list[Package],
    workspace: Workspace,
    *,
    scope: str | None = None,
    since: str | None = None,
    ignore: list[str] | None = None,
    include_dependents: bool = False,
) -> list[Package]:
    """Apply filters including git-based since filter.

    Args:
        packages: List of packages to filter.
        workspace: Workspace instance (needed for since filter).
        scope: Comma-separated names or glob patterns.
        since: Git reference for change detection.
        ignore: Patterns to exclude.
        include_dependents: Include packages that depend on changed packages.

    Returns:
        Filtered list of packages.
    """
    from pymelos.filters.since import filter_by_since

    result = packages

    # Apply scope filter first
    result = filter_by_scope(result, scope)

    # Apply since filter (git-based)
    result = filter_by_since(
        result,
        workspace,
        since,
        include_dependents=include_dependents,
    )

    # Apply ignore filter last
    result = filter_by_ignore(result, ignore)

    return result


# Type alias for filter function signature
if TYPE_CHECKING:
    from collections.abc import Callable

    FilterFunc = Callable[[list["Package"]], list["Package"]]
