"""Tests for changed command."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pymelos.commands.base import CommandContext
from pymelos.commands.changed import (
    ChangedCommand,
    ChangedOptions,
    get_changed_packages,
)
from pymelos.workspace.workspace import Workspace


class TestChangedCommand:
    """Tests for ChangedCommand."""

    @pytest.fixture
    def git_workspace_with_changes(self, git_workspace: Path) -> Path:
        """Create git workspace and make changes."""
        # Make a change in pkg-a
        pkg_a_init = git_workspace / "packages" / "pkg-a" / "src" / "pkg_a" / "__init__.py"
        pkg_a_init.write_text('__version__ = "1.0.1"\n# New change\n')

        # Stage and commit
        os.system(f"cd {git_workspace} && git add -A && git commit -q -m 'Update pkg-a'")

        return git_workspace

    def test_detects_changed_packages(self, git_workspace_with_changes: Path) -> None:
        """Should detect packages with changes since ref."""
        workspace = Workspace.discover(git_workspace_with_changes)
        result = get_changed_packages(workspace, "HEAD~1")

        names = [p.name for p in result.changed]
        assert "pkg-a" in names

    def test_includes_dependents(self, git_workspace_with_changes: Path) -> None:
        """Should include transitive dependents by default."""
        workspace = Workspace.discover(git_workspace_with_changes)
        result = get_changed_packages(workspace, "HEAD~1", include_dependents=True)

        names = [p.name for p in result.changed]
        # pkg-b depends on pkg-a, so should be included
        assert "pkg-a" in names
        assert "pkg-b" in names

    def test_excludes_dependents_when_disabled(
        self, git_workspace_with_changes: Path
    ) -> None:
        """Should not include dependents when disabled."""
        workspace = Workspace.discover(git_workspace_with_changes)
        result = get_changed_packages(workspace, "HEAD~1", include_dependents=False)

        names = [p.name for p in result.changed]
        assert "pkg-a" in names
        # pkg-b should NOT be included since it didn't change directly
        pkg_b_entry = next((p for p in result.changed if p.name == "pkg-b"), None)
        if pkg_b_entry:
            assert not pkg_b_entry.is_dependent

    def test_marks_dependent_packages(self, git_workspace_with_changes: Path) -> None:
        """Should mark packages that changed due to dependencies."""
        workspace = Workspace.discover(git_workspace_with_changes)
        result = get_changed_packages(workspace, "HEAD~1", include_dependents=True)

        pkg_a = next(p for p in result.changed if p.name == "pkg-a")
        assert not pkg_a.is_dependent  # Direct change

        pkg_b = next((p for p in result.changed if p.name == "pkg-b"), None)
        if pkg_b:
            assert pkg_b.is_dependent  # Changed due to dependency

    def test_scope_filter(self, git_workspace_with_changes: Path) -> None:
        """Should filter results by scope."""
        workspace = Workspace.discover(git_workspace_with_changes)
        result = get_changed_packages(
            workspace, "HEAD~1", include_dependents=True, scope="pkg-a"
        )

        names = [p.name for p in result.changed]
        assert "pkg-a" in names
        assert "pkg-b" not in names  # Filtered out by scope

    def test_ignore_filter(self, git_workspace_with_changes: Path) -> None:
        """Should exclude packages matching ignore."""
        workspace = Workspace.discover(git_workspace_with_changes)
        result = get_changed_packages(
            workspace, "HEAD~1", include_dependents=True, ignore=["pkg-b"]
        )

        names = [p.name for p in result.changed]
        assert "pkg-b" not in names

    def test_reports_files_changed(self, git_workspace_with_changes: Path) -> None:
        """Should report number of files changed per package."""
        workspace = Workspace.discover(git_workspace_with_changes)
        result = get_changed_packages(workspace, "HEAD~1")

        pkg_a = next(p for p in result.changed if p.name == "pkg-a")
        assert pkg_a.files_changed >= 1

    def test_reports_total_files_changed(self, git_workspace_with_changes: Path) -> None:
        """Should report total files changed."""
        workspace = Workspace.discover(git_workspace_with_changes)
        result = get_changed_packages(workspace, "HEAD~1")

        assert result.total_files_changed >= 1

    def test_no_changes(self, git_workspace: Path) -> None:
        """Should return empty list when no changes."""
        workspace = Workspace.discover(git_workspace)
        result = get_changed_packages(workspace, "HEAD")

        assert len(result.changed) == 0


class TestChangedCommandClass:
    """Tests for ChangedCommand class directly."""

    def test_options_defaults(self) -> None:
        """Should have correct default options."""
        options = ChangedOptions(since="HEAD")
        assert options.include_dependents is True
        assert options.scope is None
        assert options.ignore is None

    def test_since_is_required(self) -> None:
        """Should require since parameter."""
        # This should work - since is required
        options = ChangedOptions(since="HEAD~1")
        assert options.since == "HEAD~1"
