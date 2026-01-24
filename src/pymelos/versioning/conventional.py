"""Conventional commit parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pymelos.git.commits import Commit
from pymelos.versioning.semver import BumpType

# Conventional commit regex
# Matches: type(scope)!: description
# Examples:
#   feat: add new feature
#   fix(core): fix bug
#   feat!: breaking change
#   refactor(api)!: breaking refactor
CONVENTIONAL_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r": (?P<description>.+)$",
    re.IGNORECASE,
)

# Mapping from commit type to bump type
TYPE_TO_BUMP: dict[str, BumpType] = {
    "feat": BumpType.MINOR,
    "fix": BumpType.PATCH,
    "perf": BumpType.PATCH,
    "refactor": BumpType.NONE,
    "docs": BumpType.NONE,
    "style": BumpType.NONE,
    "test": BumpType.NONE,
    "chore": BumpType.NONE,
    "ci": BumpType.NONE,
    "build": BumpType.NONE,
    "revert": BumpType.PATCH,
}


@dataclass(frozen=True, slots=True)
class ParsedCommit:
    """A parsed conventional commit.

    Attributes:
        sha: Commit SHA.
        type: Commit type (feat, fix, etc.).
        scope: Optional scope.
        description: Commit description.
        body: Commit body.
        breaking: Whether this is a breaking change.
        raw_message: Original commit message.
    """

    sha: str
    type: str
    scope: str | None
    description: str
    body: str | None
    breaking: bool
    raw_message: str

    @property
    def bump_type(self) -> BumpType:
        """Get the version bump type for this commit."""
        if self.breaking:
            return BumpType.MAJOR
        return TYPE_TO_BUMP.get(self.type.lower(), BumpType.NONE)

    @property
    def formatted_scope(self) -> str:
        """Get scope formatted for display."""
        if self.scope:
            return f"({self.scope})"
        return ""

    @property
    def formatted_type(self) -> str:
        """Get type formatted for changelog."""
        type_labels = {
            "feat": "Features",
            "fix": "Bug Fixes",
            "perf": "Performance",
            "refactor": "Refactoring",
            "docs": "Documentation",
            "style": "Style",
            "test": "Tests",
            "chore": "Chores",
            "ci": "CI",
            "build": "Build",
            "revert": "Reverts",
        }
        return type_labels.get(self.type.lower(), self.type.capitalize())


def parse_commit_message(message: str, sha: str = "") -> ParsedCommit | None:
    """Parse a commit message in conventional commit format.

    Args:
        message: Commit message to parse.
        sha: Commit SHA.

    Returns:
        ParsedCommit if the message follows conventional commit format, None otherwise.
    """
    lines = message.strip().split("\n")
    first_line = lines[0]

    match = CONVENTIONAL_PATTERN.match(first_line)
    if not match:
        return None

    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else None

    # Check for breaking change in body
    breaking = bool(match.group("breaking"))
    if body and ("BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body):
        breaking = True

    return ParsedCommit(
        sha=sha,
        type=match.group("type").lower(),
        scope=match.group("scope"),
        description=match.group("description"),
        body=body,
        breaking=breaking,
        raw_message=message,
    )


def parse_commit(commit: Commit) -> ParsedCommit | None:
    """Parse a Commit object into a ParsedCommit.

    Args:
        commit: Git commit object.

    Returns:
        ParsedCommit if valid, None otherwise.
    """
    return parse_commit_message(commit.message, commit.sha)


def determine_bump(commits: list[ParsedCommit]) -> BumpType:
    """Determine the highest bump type from a list of commits.

    Args:
        commits: List of parsed commits.

    Returns:
        The highest bump type needed.
    """
    if not commits:
        return BumpType.NONE

    bump = BumpType.NONE
    for commit in commits:
        if commit.bump_type > bump:
            bump = commit.bump_type
        if bump == BumpType.MAJOR:
            # Can't go higher
            break

    return bump


def filter_commits_by_type(
    commits: list[ParsedCommit],
    types: list[str],
) -> list[ParsedCommit]:
    """Filter commits by type.

    Args:
        commits: List of commits.
        types: Types to include (e.g., ["feat", "fix"]).

    Returns:
        Filtered commits.
    """
    type_set = {t.lower() for t in types}
    return [c for c in commits if c.type.lower() in type_set]


def group_commits_by_type(
    commits: list[ParsedCommit],
) -> dict[str, list[ParsedCommit]]:
    """Group commits by their type.

    Args:
        commits: List of commits.

    Returns:
        Dictionary mapping type to commits.
    """
    groups: dict[str, list[ParsedCommit]] = {}
    for commit in commits:
        commit_type = commit.type.lower()
        if commit_type not in groups:
            groups[commit_type] = []
        groups[commit_type].append(commit)
    return groups


def is_conventional_commit(message: str) -> bool:
    """Check if a message follows conventional commit format.

    Args:
        message: Commit message to check.

    Returns:
        True if it's a valid conventional commit.
    """
    return parse_commit_message(message) is not None
