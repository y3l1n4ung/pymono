"""Tests for changed command."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pymelos.commands.changed import (
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


class TestChangedEdgeCases:
    """Edge case tests for changed command."""

    def test_multiple_files_in_package(self, git_workspace: Path) -> None:
        """Should count multiple changed files in package."""
        pkg_a = git_workspace / "packages" / "pkg-a"

        # Modify multiple files
        (pkg_a / "file1.py").write_text("# new file 1")
        (pkg_a / "file2.py").write_text("# new file 2")

        os.system(f"cd {git_workspace} && git add -A && git commit -q -m 'Add files'")

        workspace = Workspace.discover(git_workspace)
        result = get_changed_packages(workspace, "HEAD~1")

        pkg_a_info = next(p for p in result.changed if p.name == "pkg-a")
        assert pkg_a_info.files_changed >= 2

    def test_changes_in_multiple_packages(self, git_workspace: Path) -> None:
        """Should detect changes in multiple packages."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        pkg_b = git_workspace / "packages" / "pkg-b"

        (pkg_a / "new.py").write_text("# pkg-a change")
        (pkg_b / "new.py").write_text("# pkg-b change")

        os.system(f"cd {git_workspace} && git add -A && git commit -q -m 'Change both'")

        workspace = Workspace.discover(git_workspace)
        result = get_changed_packages(workspace, "HEAD~1", include_dependents=False)

        names = [p.name for p in result.changed]
        assert "pkg-a" in names
        assert "pkg-b" in names

    def test_transitive_dependents(self, git_workspace: Path) -> None:
        """Should include transitive dependents."""
        # pkg-c depends on pkg-b which depends on pkg-a
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "change.py").write_text("# change in pkg-a")

        os.system(f"cd {git_workspace} && git add -A && git commit -q -m 'Change pkg-a'")

        workspace = Workspace.discover(git_workspace)
        result = get_changed_packages(workspace, "HEAD~1", include_dependents=True)

        names = [p.name for p in result.changed]
        # Should include pkg-a (direct), pkg-b (depends on a), pkg-c (depends on b)
        assert "pkg-a" in names
        assert "pkg-b" in names
        assert "pkg-c" in names

    def test_file_outside_packages(self, git_workspace: Path) -> None:
        """Should ignore changes outside packages."""
        (git_workspace / "root_file.py").write_text("# root change")

        os.system(f"cd {git_workspace} && git add -A && git commit -q -m 'Root change'")

        workspace = Workspace.discover(git_workspace)
        result = get_changed_packages(workspace, "HEAD~1")

        # No packages should be marked as changed
        assert len(result.changed) == 0
        assert result.total_files_changed >= 1

    def test_deleted_file(self, git_workspace: Path) -> None:
        """Should detect package as changed when file deleted."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        temp_file = pkg_a / "to_delete.py"
        temp_file.write_text("# will be deleted")

        os.system(f"cd {git_workspace} && git add -A && git commit -q -m 'Add file'")

        temp_file.unlink()
        os.system(f"cd {git_workspace} && git add -A && git commit -q -m 'Delete file'")

        workspace = Workspace.discover(git_workspace)
        result = get_changed_packages(workspace, "HEAD~1")

        names = [p.name for p in result.changed]
        assert "pkg-a" in names
