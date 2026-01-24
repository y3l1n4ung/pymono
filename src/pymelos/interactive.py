"""Interactive terminal UI components."""

from __future__ import annotations

import questionary

from pymelos.workspace.package import Package


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
            title=f"{name}  {desc}",
            value=name,
        )
        for name, desc in scripts.items()
    ]

    return questionary.select(
        "Which script would you like to run?",
        choices=choices,
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
        validate=lambda x: True,  # Allow empty selection
    ).ask()

    return selected or []


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

    return questionary.prompt(questions)
