"""Test git since filtering."""

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

from pymelos.filters.since import filter_by_since, get_changed_packages
from pymelos.workspace.package import Package


def test_get_changed_packages_direct():
    workspace = MagicMock()
    workspace.root = Path("/root")

    pkg_a = MagicMock(spec=Package)
    pkg_a.name = "pkg-a"
    pkg_a.path = Path("/root/packages/pkg-a")

    pkg_b = MagicMock(spec=Package)
    pkg_b.name = "pkg-b"
    pkg_b.path = Path("/root/packages/pkg-b")

    workspace.packages = {"pkg-a": pkg_a, "pkg-b": pkg_b}

    # Mock changed files
    with patch("pymelos.filters.since.get_changed_files") as mock_files:
        mock_files.return_value = {
            Path("packages/pkg-a/src/code.py"),
            Path("packages/pkg-a/pyproject.toml"),
        }

        changed = get_changed_packages(workspace, "main", include_dependents=False)

        assert len(changed) == 1
        assert changed[0].name == "pkg-a"


def test_get_changed_packages_dependents():
    workspace = MagicMock()
    workspace.root = Path("/root")

    pkg_a = MagicMock(spec=Package, name="pkg-a", path=Path("/root/packages/pkg-a"))
    pkg_b = MagicMock(spec=Package, name="pkg-b", path=Path("/root/packages/pkg-b"))

    workspace.packages = {"pkg-a": pkg_a, "pkg-b": pkg_b}

    # Mock changed files affecting pkg-a
    with patch("pymelos.filters.since.get_changed_files") as mock_files:
        mock_files.return_value = {Path("packages/pkg-a/file.py")}

        # Mock dependents logic: pkg-b depends on pkg-a
        workspace.get_affected_packages.return_value = [pkg_a, pkg_b]

        changed = get_changed_packages(workspace, "main", include_dependents=True)

        assert len(changed) == 2
        assert pkg_a in changed
        assert pkg_b in changed
        workspace.get_affected_packages.assert_called_once()


def test_filter_by_since():
    workspace = MagicMock()
    pkg_a = MagicMock(spec=Package)
    pkg_a.name = "pkg-a"
    pkg_b = MagicMock(spec=Package)
    pkg_b.name = "pkg-b"
    packages = cast("list[Package]", [pkg_a, pkg_b])

    with patch("pymelos.filters.since.get_changed_packages") as mock_changed:
        mock_changed.return_value = [pkg_b]

        filtered = filter_by_since(packages, workspace, "main")

        assert len(filtered) == 1
        assert filtered[0].name == "pkg-b"

        # Verify no filtering if since is None
        assert filter_by_since(packages, workspace, None) == packages
