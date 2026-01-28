"""Interactive terminal UI components."""

from __future__ import annotations

from typing import Any
import sys

try:
    import questionary
    from questionary import Style
    _QUESTIONARY_AVAILABLE = True
except Exception:  # ImportError or any issue importing questionary
    questionary = None  # type: ignore
    Style = object  # type: ignore
    _QUESTIONARY_AVAILABLE = False

from pymelos.workspace.package import Package

def _ensure_questionary_available() -> None:
    """
    Ensure the interactive dependency `questionary` is available; raise a RuntimeError with installation instructions if it is missing.
    
    Raises:
        RuntimeError: If `questionary` is not installed. The error message includes pip install instructions.
    """
    if not _QUESTIONARY_AVAILABLE:
        raise RuntimeError(
            "Interactive UI requires the 'questionary' package. "
            "Install it with: pip install 'pymelos[interactive]' or 'pip install questionary'"
        )

def get_style() -> Style:
    """
    Provide the Style used for interactive prompts.
    
    Returns:
        style (Style): A Style configured with color and attribute mappings for prompt elements
        (`qmark`, `question`, `answer`, `pointer`, `highlighted`, `selected`, `separator`,
        `instruction`).
    """
    _ensure_questionary_available()

    return Style(
        [
            ("qmark", "fg:#673ab7 bold"),  # Purple question mark
            ("question", "bold"),  # Bold question text
            ("answer", "fg:#f44336 bold"),  # Red answer
            ("pointer", "fg:#673ab7 bold"),  # Purple pointer
            ("highlighted", "fg:#673ab7 bold"),  # Purple selected item
            ("selected", "fg:#cc5454"),  # Checkbox selected
            ("separator", "fg:#cc5454"),
            ("instruction", "fg:#888888"),  # Gray instructions
        ]
    )

def _safe_ask(fn, *args, default=None, **kwargs):
    """
    Invoke a questionary prompt function and return a normalized result when the prompt is cancelled, interrupted, or fails.
    
    Parameters:
        fn: The questionary function or prompt object factory to call (for example `questionary.select`, `questionary.checkbox`, or `questionary.prompt`).
        *args: Positional arguments forwarded to `fn`.
        **kwargs: Keyword arguments forwarded to `fn`.
        default: Value to return when the user cancels (KeyboardInterrupt), when prompting fails (e.g., non-tty), or when the prompt returns `None`.
    
    Returns:
        The prompt's result, or `default` if the prompt was cancelled, interrupted, or raised an exception.
    """
    _ensure_questionary_available()

    try:
        prompt_obj = fn(*args, **kwargs)
    except KeyboardInterrupt:
        # User pressed Ctrl-C during prompt creation; treat as cancellation.
        return default
    except Exception:
        # Some questionary functions may raise on non-tty environments; treat as cancellation.
        return default

    # For questionary.select/checkbox/etc, prompt_obj.ask() performs the actual prompt.
    # For questionary.prompt(questions) the function itself performs prompting and returns dict or None.
    try:
        # If the returned object has an ask method, call it.
        if hasattr(prompt_obj, "ask"):
            res = prompt_obj.ask()
        else:
            # questionary.prompt returns the result directly
            res = prompt_obj
    except KeyboardInterrupt:
        return default
    except Exception:
        return default

    # Normalize None => default
    return res if res is not None else default

def select_script(scripts: dict[str, str]) -> str | None:
    """
    Present a selectable list of scripts and return the chosen script name.
    
    Parameters:
        scripts (dict[str, str]): Mapping of script name to description or command.
    
    Returns:
        Selected script name (str) if a choice was made, or None if cancelled.
    """
    if not scripts:
        return None

    choices = [
        questionary.Choice(
            title=f"{name.ljust(15)} {desc}",
            value=name,
        )
        for name, desc in scripts.items()
    ]

    return _safe_ask(
        questionary.select,
        "Which script would you like to run?",
        choices=choices,
        style=get_style(),
        use_indicator=True,
        default=None,
    )

def select_packages(packages: list[Package]) -> list[Package]:
    """Interactively select packages.

    Args:
        packages: List of available packages.

    Returns:
        List of selected packages (empty list if cancelled or none selected).
    """
    if not packages:
        return []

    # Sort packages by name
    sorted_pkgs = sorted(packages, key=lambda p: p.name)

    choices = [
        questionary.Choice(
            title=f"{p.name} ({p.path.name})",
            value=p,
            checked=False,
        )
        for p in sorted_pkgs
    ]

    selected = _safe_ask(
        questionary.checkbox,
        "Select packages:",
        choices=choices,
        validate=lambda _: True,  # Allow empty selection
        style=get_style(),
        instruction="(Space to select, Enter to confirm)",
        default=[],
    )

    return selected or []

def select_git_reference(refs: list[tuple[str, str]]) -> str | None:
    """Interactively select a git reference.

    Args:
        refs: List of (label, value) tuples.

    Returns:
        Selected reference value or None.
    """
    if not refs:
        return None

    choices = [questionary.Choice(title=label, value=val) for label, val in refs]
    choices.append(questionary.Choice(title="Enter manually...", value="manual"))

    selection = _safe_ask(
        questionary.select,
        "Select a base git reference:",
        choices=choices,
        style=get_style(),
        use_indicator=True,
        default=None,
    )

    if selection == "manual":
        return _safe_ask(questionary.text, "Enter git reference:", style=get_style(), default=None)

    return selection

def select_execution_options() -> dict[str, bool | str]:
    """
    Prompt the user to choose the execution scope for running tasks.
    
    Returns:
        dict: Mapping of option names to selected values. Contains the key `"scope"` with value `"all"`, `"changed"`, or `"manual"`. Returns an empty dict if the prompt was cancelled or not available.
    """
    questions = [
        {
            "type": "select",
            "name": "scope",
            "message": "Where should this run?",
            "choices": [
                questionary.Choice("All packages", value="all"),
                questionary.Choice("Changed packages (since main)", value="changed"),
                questionary.Choice("Select manually", value="manual"),
            ],
        },
    ]

    result = _safe_ask(questionary.prompt, questions, style=get_style(), default={})
    return result or {}

def select_package_for_review(packages: list[Any]) -> str | None:
    """Interactively select a changed package to review.

    Args:
        packages: List of ChangedPackage objects (typed as Any to avoid circular import).

    Returns:
        Selected package name or None to exit.
    """
    if not packages:
        return None

    choices = [
        questionary.Choice(
            title=f"{p.name} ({p.files_changed} files)",
            value=p.name,
        )
        for p in packages
    ]
    choices.append(questionary.Choice(title="Exit", value=None))

    return _safe_ask(
        questionary.select,
        "Select a package to review changes:",
        choices=choices,
        style=get_style(),
        use_indicator=True,
        default=None,
    )

def select_file_for_review(files: list[str]) -> str | None:
    """Interactively select a file to view diff.

    Args:
        files: List of file paths.

    Returns:
        Selected file path or None to go back.
    """
    if not files:
        return None

    choices = [questionary.Choice(title=f, value=f) for f in files]
    choices.append(questionary.Choice(title="< Back to packages", value="__BACK__"))

    selection = _safe_ask(
        questionary.select,
        "Select a file to view diff:",
        choices=choices,
        style=get_style(),
        use_indicator=True,
        default="__BACK__",
    )

    return None if selection == "__BACK__" else selection