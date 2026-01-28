import pytest
from unittest.mock import patch, MagicMock

from pymelos import interactive

def test_select_script_returns_choice():
    scripts = {"build": "Build packages", "test": "Run tests"}
    # Patch the questionary.select callable used in interactive.select_script
    with patch("pymelos.interactive.questionary.select") as mock_select:
        mock_obj = MagicMock()
        mock_obj.ask.return_value = "build"
        mock_select.return_value = mock_obj
        selected = interactive.select_script(scripts)
        assert selected == "build"

def test_select_script_cancelled_returns_none():
    scripts = {"build": "Build packages", "test": "Run tests"}
    with patch("pymelos.interactive.questionary.select") as mock_select:
        mock_obj = MagicMock()
        mock_obj.ask.return_value = None  # Simulate cancellation
        mock_select.return_value = mock_obj
        selected = interactive.select_script(scripts)
        assert selected is None

def test_select_packages_returns_list():
    class DummyPath:
        def __init__(self, name):
            self.name = name

    class DummyPkg:
        def __init__(self, name):
            self.name = name
            self.path = DummyPath(name)

    pkgs = [DummyPkg("a"), DummyPkg("b")]
    with patch("pymelos.interactive.questionary.checkbox") as mock_checkbox:
        mock_obj = MagicMock()
        mock_obj.ask.return_value = [pkgs[0]]
        mock_checkbox.return_value = mock_obj
        selected = interactive.select_packages(pkgs)
        assert isinstance(selected, list)
        assert selected[0].name == "a"

def test_select_file_for_review_back():
    files = ["a.py", "b.py"]
    with patch("pymelos.interactive.questionary.select") as mock_select:
        mock_obj = MagicMock()
        mock_obj.ask.return_value = "__BACK__"
        mock_select.return_value = mock_obj
        assert interactive.select_file_for_review(files) is None

def test_select_execution_options_cancelled_returns_empty_dict():
    with patch("pymelos.interactive.questionary.prompt") as mock_prompt:
        mock_prompt.return_value = None
        result = interactive.select_execution_options()
        assert result == {}
