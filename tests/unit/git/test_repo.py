"""Test git repo utilities."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymelos.git.repo import (
    get_current_branch,
    get_current_commit,
    get_default_branch,
    get_recent_refs,
    get_repo_root,
    is_clean,
    is_git_repo,
    run_git_command,
)


def test_run_git_command_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        result = run_git_command(["status"], cwd=Path("."))

        assert result.returncode == 0
        assert result.stdout == "output"
        mock_run.assert_called_once()
        assert mock_run.call_args[1]["check"] is False


def test_is_git_repo():
    with patch("pymelos.git.repo.run_git_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert is_git_repo(Path(".")) is True

        mock_run.return_value = MagicMock(returncode=128)
        assert is_git_repo(Path(".")) is False


def test_get_repo_root():
    with patch("pymelos.git.repo.run_git_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="/path/to/repo\n")

        root = get_repo_root(Path("."))
        assert root == Path("/path/to/repo")


def test_get_recent_refs():
    with patch("pymelos.git.repo.run_git_command") as mock_run:
        # Mock 3 calls: branch, tag, log
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\nfeature\n"),  # branches
            MagicMock(returncode=0, stdout="v1.0\n"),  # tags
            MagicMock(returncode=0, stdout="abc|abc (HEAD) msg (1h)\n"),  # log
        ]

        refs = get_recent_refs(Path("."))

        assert len(refs) == 4  # main, feature, v1.0, commit
        assert refs[0] == ("[branch] main", "main")
        assert refs[2] == ("[tag] v1.0", "v1.0")
        assert refs[3] == ("abc (HEAD) msg (1h)", "abc")


def test_get_current_branch():
    with patch("pymelos.git.repo.run_git_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
        assert get_current_branch() == "main"


def test_get_current_commit():
    with patch("pymelos.git.repo.run_git_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n")
        assert get_current_commit() == "abc1234"


def test_is_clean():
    with patch("pymelos.git.repo.run_git_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert is_clean() is True

        mock_run.return_value = MagicMock(returncode=0, stdout="M file.py")
        assert is_clean() is False


def test_get_default_branch():
    with patch("pymelos.git.repo.run_git_command") as mock_run:
        # Case 1: remote
        mock_run.return_value = MagicMock(returncode=0, stdout="refs/remotes/origin/main")
        assert get_default_branch() == "main"

        # Case 2: local main
        mock_run.side_effect = [
            MagicMock(returncode=1),  # remote fail
            MagicMock(returncode=0, stdout="* main"),  # local main exists
        ]
        assert get_default_branch() == "main"

        # Case 3: fallback master
        mock_run.side_effect = [
            MagicMock(returncode=1),  # remote fail
            MagicMock(returncode=0, stdout=""),  # local main missing
        ]
        assert get_default_branch() == "master"
