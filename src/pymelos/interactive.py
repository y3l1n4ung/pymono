"""Interactive terminal UI components."""

from __future__ import annotations

from typing import Any

import questionary
from questionary import Style

from pymelos.workspace.package import Package


def get_style() -> Style:
    """Get the custom style for interactive prompts."""
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


def select_script(scripts: dict[str, str]) -> str | None:
    """Interactively select a script to run.

    Args:
        scripts: Dictionary of script name -> description/command.

    Returns:
        Selected script name or None if cancelled.
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

    return questionary.select(
        "Which script would you like to run?",
        choices=choices,
        style=get_style(),
        use_indicator=True,
    ).ask()


def select_packages(packages: list[Package]) -> list[Package]:
    """Interactively select packages.

    Args:
        packages: List of available packages.

    Returns:
        List of selected packages.
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

    selected = questionary.checkbox(
        "Select packages:",
        choices=choices,
        validate=lambda _: True,  # Allow empty selection
        style=get_style(),
        instruction="(Space to select, Enter to confirm)",
    ).ask()

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

    selection = questionary.select(
        "Select a base git reference:",
        choices=choices,
        style=get_style(),
        use_indicator=True,
    ).ask()

    if selection == "manual":
        return questionary.text("Enter git reference:", style=get_style()).ask()

    return selection


def select_execution_options() -> dict[str, bool | str]:
    """Select execution options interactively.

    Returns:
        Dictionary of selected options.
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

    return questionary.prompt(questions, style=get_style())


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

    return questionary.select(
        "Select a package to review changes:",
        choices=choices,
        style=get_style(),
        use_indicator=True,
    ).ask()


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

    selection = questionary.select(
        "Select a file to view diff:",
        choices=choices,
        style=get_style(),
        use_indicator=True,
    ).ask()

    return None if selection == "__BACK__" else selection
