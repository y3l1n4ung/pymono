"""Test interactive mode components."""

from unittest.mock import MagicMock, patch

import pytest

from pymelos.interactive import (
    select_execution_options,
    select_git_reference,
    select_packages,
    select_script,
)
from pymelos.workspace import Package


@pytest.fixture
def mock_packages(tmp_path):
    p1 = MagicMock(spec=Package)
    p1.name = "pkg-a"
    p1.path = tmp_path / "pkg-a"

    p2 = MagicMock(spec=Package)
    p2.name = "pkg-b"
    p2.path = tmp_path / "pkg-b"

    return [p1, p2]


def test_select_script_empty():
    assert select_script({}) is None


def test_select_script_selection():
    scripts = {"test": "Run tests", "lint": "Lint code"}

    # Mock questionary.select().ask()
    with patch("questionary.select") as mock_select:
        mock_ask = mock_select.return_value.ask
        mock_ask.return_value = "test"

        result = select_script(scripts)

        assert result == "test"
        mock_select.assert_called_once()
        # Verify prompt text
        args, _ = mock_select.call_args
        assert args[0] == "Which script would you like to run?"


def test_select_packages_empty():
    assert select_packages([]) == []


def test_select_packages_selection(mock_packages):
    with patch("questionary.checkbox") as mock_checkbox:
        mock_ask = mock_checkbox.return_value.ask
        mock_ask.return_value = [mock_packages[0]]  # Select pkg-a

        result = select_packages(mock_packages)

        assert result == [mock_packages[0]]
        mock_checkbox.assert_called_once()
        # Verify prompt text
        args, _ = mock_checkbox.call_args
        assert args[0] == "Select packages:"


def test_select_execution_options():
    with patch("questionary.prompt") as mock_prompt:
        mock_prompt.return_value = {"scope": "changed"}

        result = select_execution_options()

        assert result == {"scope": "changed"}
        mock_prompt.assert_called_once()


def test_select_git_reference():
    refs = [("main (default)", "main"), ("v1.0 (tag)", "v1.0")]
    with patch("questionary.select") as mock_select:
        mock_ask = mock_select.return_value.ask
        mock_ask.return_value = "main"

        result = select_git_reference(refs)

        assert result == "main"
        mock_select.assert_called_once()
        args, _ = mock_select.call_args
        assert args[0] == "Select a base git reference:"


def test_select_git_reference_manual():
    refs = [("main (default)", "main")]
    with patch("questionary.select") as mock_select, patch("questionary.text") as mock_text:
        # First select "manual"
        mock_select.return_value.ask.return_value = "manual"
        # Then type "feature-branch"
        mock_text.return_value.ask.return_value = "feature-branch"

        result = select_git_reference(refs)

        assert result == "feature-branch"
        mock_select.assert_called_once()
        mock_text.assert_called_once()
