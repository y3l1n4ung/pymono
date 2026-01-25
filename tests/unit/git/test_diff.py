"""Test git diff operations."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from pymelos.git.diff import get_changed_files_in_package, get_file_diff


def test_get_changed_files_in_package_all_states():
    root = Path("/root")
    since = "main"
    pkg_path = Path("packages/pkg-a")

    with patch("pymelos.git.diff.run_git_command") as mock_run:
        # Mock responses for the 4 git calls
        # 1. Commits
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="committed.py\n"),
            MagicMock(returncode=0, stdout="staged.py\n"),
            MagicMock(returncode=0, stdout="unstaged.py\n"),
            MagicMock(returncode=0, stdout="untracked.py\n"),
        ]

        files = get_changed_files_in_package(root, since, pkg_path)

        assert len(files) == 4
        assert "committed.py" in files
        assert "staged.py" in files
        assert "unstaged.py" in files
        assert "untracked.py" in files

        assert mock_run.call_count == 4


def test_get_file_diff_committed():
    root = Path("/root")

    with patch("pymelos.git.diff.run_git_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="diff content")

        diff = get_file_diff(root, "main", "file.py")

        assert diff == "diff content"
        # Should call: git diff --color=always main -- file.py
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "main" in args
        assert "--" in args
        assert "file.py" in args


def test_get_file_diff_untracked():
    root = Path("/root")

    with patch("pymelos.git.diff.run_git_command") as mock_run:
        # 1. git diff main -> empty (because untracked)
        # 2. ls-files -> found
        # 3. git diff /dev/null -> content
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout="file.py"),
            MagicMock(returncode=0, stdout="new file content"),
        ]

        diff = get_file_diff(root, "main", "file.py")

        assert diff == "new file content"
        assert mock_run.call_count == 3
        # Check 3rd call is diff /dev/null
        args = mock_run.call_args[0][0]
        assert "/dev/null" in args


def test_get_changed_files_in_package_partial_failure():
    """Test that failed git commands are ignored (graceful degradation)."""
    root = Path("/root")
    since = "main"
    pkg_path = Path("packages/pkg-a")

    with patch("pymelos.git.diff.run_git_command") as mock_run:
        # Mock responses:
        # 1. Commits -> Success
        # 2. Staged -> Fail
        # 3. Unstaged -> Success
        # 4. Untracked -> Fail
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="committed.py\n"),
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=0, stdout="unstaged.py\n"),
            MagicMock(returncode=128, stdout=""),
        ]

        files = get_changed_files_in_package(root, since, pkg_path)

        assert len(files) == 2
        assert "committed.py" in files
        assert "unstaged.py" in files
        assert "staged.py" not in files

        assert mock_run.call_count == 4
