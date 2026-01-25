"""Test interactive review logic."""

from unittest.mock import MagicMock, patch

from pymelos.commands.changed import ChangedPackage, review_changes_interactive


def test_review_changes_interactive_empty():
    workspace = MagicMock()
    console = MagicMock()

    review_changes_interactive(workspace, "main", [], console)

    # Should print message and return
    console.print.assert_called_with("[yellow]No packages changed.[/yellow]")


def test_review_changes_interactive_exit():
    workspace = MagicMock()
    console = MagicMock()

    pkg = ChangedPackage(name="pkg-a", path="packages/pkg-a", files_changed=1, is_dependent=False)

    # Mock select_package returning None immediately (Exit)
    with patch("pymelos.interactive.select_package_for_review") as mock_select:
        mock_select.return_value = None

        review_changes_interactive(workspace, "main", [pkg], console)

        mock_select.assert_called_once()


def test_interactive_review_flow_success():
    """Test standard interactive review flow: Select Package -> Select File -> Back -> Exit."""
    workspace = MagicMock()
    # Mock root as a Path object so / operator works
    from pathlib import Path

    workspace.root = Path("root")

    console = MagicMock()

    pkg = ChangedPackage(name="pkg-a", path="packages/pkg-a", files_changed=1, is_dependent=False)

    with (
        patch("pymelos.interactive.select_package_for_review") as mock_select_pkg,
        patch("pymelos.git.diff.get_changed_files_in_package") as mock_get_files,
        patch("pymelos.interactive.select_file_for_review") as mock_select_file,
        patch("pymelos.git.diff.get_file_diff") as mock_get_diff,
    ):
        # Scenario:
        # 1. Select Package "pkg-a"
        # 2. _review_package_files is called
        #    a. get_files -> ["file.py"] (Called once per package)
        #    b. select_file -> "file.py"
        #    c. get_diff -> "diff content"
        #    d. select_file -> None (Back)
        # 3. Select Package -> None (Exit)

        mock_select_pkg.side_effect = ["pkg-a", None]
        mock_get_files.return_value = ["file.py"]
        mock_select_file.side_effect = ["file.py", None]
        mock_get_diff.return_value = "diff content"

        review_changes_interactive(workspace, "main", [pkg], console)

        # Verifications
        assert mock_select_pkg.call_count == 2

        # get_changed_files should be called once with relative path
        mock_get_files.assert_called_once()
        args = mock_get_files.call_args
        # args[0] are positional args: (root, since, package_path)
        # package_path should be Path("packages/pkg-a")
        assert args[0][2] == Path("packages/pkg-a")

        assert mock_select_file.call_count == 2
        mock_get_diff.assert_called_once()
        console.pager.assert_called_once()
