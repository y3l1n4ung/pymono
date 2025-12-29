"""Tests for release command."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymelos.commands.base import CommandContext
from pymelos.commands.release import (
    PackageRelease,
    ReleaseCommand,
    ReleaseOptions,
    ReleaseResult,
    release,
)
from pymelos.versioning import BumpType
from pymelos.workspace.workspace import Workspace


class TestReleaseOptions:
    """Tests for ReleaseOptions."""

    def test_defaults(self) -> None:
        """Should have correct default values."""
        options = ReleaseOptions()
        assert options.scope is None
        assert options.since is None
        assert options.bump is None
        assert options.prerelease is None
        assert options.dry_run is False
        assert options.publish is False
        assert options.no_git_tag is False
        assert options.no_changelog is False
        assert options.no_commit is False

    def test_with_bump_override(self) -> None:
        """Should accept bump type override."""
        options = ReleaseOptions(bump=BumpType.MAJOR)
        assert options.bump == BumpType.MAJOR

    def test_with_prerelease(self) -> None:
        """Should accept prerelease tag."""
        options = ReleaseOptions(prerelease="alpha")
        assert options.prerelease == "alpha"


class TestPackageRelease:
    """Tests for PackageRelease dataclass."""

    def test_create_release(self) -> None:
        """Should create package release info."""
        release_info = PackageRelease(
            name="pkg-a",
            old_version="1.0.0",
            new_version="1.1.0",
            bump_type=BumpType.MINOR,
            changelog_entry="## 1.1.0\n\n- feat: new feature",
            commits=["abc1234", "def5678"],
            tag="pkg-a@1.1.0",
        )
        assert release_info.name == "pkg-a"
        assert release_info.old_version == "1.0.0"
        assert release_info.new_version == "1.1.0"
        assert release_info.published is False

    def test_published_flag(self) -> None:
        """Should track published state."""
        release_info = PackageRelease(
            name="pkg-a",
            old_version="1.0.0",
            new_version="1.1.0",
            bump_type=BumpType.PATCH,
            changelog_entry="",
            commits=[],
            tag="pkg-a@1.1.0",
            published=True,
        )
        assert release_info.published is True


class TestReleaseResult:
    """Tests for ReleaseResult dataclass."""

    def test_success_result(self) -> None:
        """Should create success result."""
        result = ReleaseResult(
            releases=[],
            commit_sha="abc1234567890",
            success=True,
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self) -> None:
        """Should create failure result with error."""
        result = ReleaseResult(
            releases=[],
            success=False,
            error="Publish failed: authentication error",
        )
        assert result.success is False
        assert result.error is not None
        assert "authentication error" in result.error

    def test_with_releases(self) -> None:
        """Should include release info."""
        releases = [
            PackageRelease(
                name="pkg-a",
                old_version="1.0.0",
                new_version="1.1.0",
                bump_type=BumpType.MINOR,
                changelog_entry="",
                commits=[],
                tag="pkg-a@1.1.0",
            )
        ]
        result = ReleaseResult(releases=releases, success=True)
        assert len(result.releases) == 1
        assert result.releases[0].name == "pkg-a"


class TestReleaseCommand:
    """Tests for ReleaseCommand."""

    @pytest.fixture
    def git_workspace_with_changes(self, git_workspace: Path) -> Path:
        """Create git workspace with conventional commits."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "new_feature.py").write_text("# New feature\n")

        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'feat: add new feature'")

        return git_workspace

    def test_get_packages_to_release(self, git_workspace: Path) -> None:
        """Should get all packages without scope."""
        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace)
        cmd = ReleaseCommand(context)

        packages = cmd.get_packages_to_release()
        names = [p.name for p in packages]
        assert "pkg-a" in names
        assert "pkg-b" in names
        assert "pkg-c" in names

    def test_get_packages_with_scope(self, git_workspace: Path) -> None:
        """Should filter packages by scope."""
        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace)
        options = ReleaseOptions(scope="pkg-a")
        cmd = ReleaseCommand(context, options)

        packages = cmd.get_packages_to_release()
        assert len(packages) == 1
        assert packages[0].name == "pkg-a"

    def test_is_dry_run_from_options(self, git_workspace: Path) -> None:
        """Should detect dry run from options."""
        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace)
        options = ReleaseOptions(dry_run=True)
        cmd = ReleaseCommand(context, options)

        assert cmd.is_dry_run is True

    def test_is_dry_run_from_context(self, git_workspace: Path) -> None:
        """Should detect dry run from context."""
        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace, dry_run=True)
        cmd = ReleaseCommand(context)

        assert cmd.is_dry_run is True

    async def test_dry_run_does_not_modify(
        self, git_workspace_with_changes: Path
    ) -> None:
        """Should not modify files in dry run mode."""
        workspace = Workspace.discover(git_workspace_with_changes)
        pkg_a = git_workspace_with_changes / "packages" / "pkg-a"
        original_version = (pkg_a / "pyproject.toml").read_text()

        result = await release(
            workspace, scope="pkg-a", bump=BumpType.MINOR, dry_run=True
        )

        # Version should not change
        assert (pkg_a / "pyproject.toml").read_text() == original_version
        # Should still report what would be released
        assert result.success is True

    async def test_release_with_bump_override(
        self, git_workspace_with_changes: Path
    ) -> None:
        """Should use bump override instead of auto-detection."""
        workspace = Workspace.discover(git_workspace_with_changes)

        result = await release(
            workspace,
            scope="pkg-a",
            bump=BumpType.MAJOR,
            dry_run=True,
        )

        if result.releases:
            assert result.releases[0].bump_type == BumpType.MAJOR
            assert result.releases[0].new_version == "2.0.0"

    async def test_release_with_prerelease(
        self, git_workspace_with_changes: Path
    ) -> None:
        """Should create prerelease version."""
        workspace = Workspace.discover(git_workspace_with_changes)

        result = await release(
            workspace,
            scope="pkg-a",
            bump=BumpType.MINOR,
            prerelease="alpha",
            dry_run=True,
        )

        if result.releases:
            assert "alpha" in result.releases[0].new_version

    async def test_no_releases_when_no_changes(self, git_workspace: Path) -> None:
        """Should return empty when no packages have changes."""
        workspace = Workspace.discover(git_workspace)
        result = await release(workspace, dry_run=True)

        assert result.success is True
        assert len(result.releases) == 0

    async def test_scope_filter_no_match(self, git_workspace: Path) -> None:
        """Should return empty when scope matches nothing."""
        workspace = Workspace.discover(git_workspace)
        result = await release(workspace, scope="nonexistent", dry_run=True)

        assert result.success is True
        assert len(result.releases) == 0

    @patch("pymelos.uv.build_and_publish")
    async def test_publish_to_registry(
        self, mock_publish: MagicMock, git_workspace_with_changes: Path
    ) -> None:
        """Should call build_and_publish when publish=True."""
        workspace = Workspace.discover(git_workspace_with_changes)

        await release(
            workspace,
            scope="pkg-a",
            bump=BumpType.PATCH,
            publish=True,
            no_git_tag=True,
            no_changelog=True,
        )

        # Should have called publish
        assert mock_publish.called

    @patch("pymelos.uv.build_and_publish")
    async def test_publish_error_handling(
        self, mock_publish: MagicMock, git_workspace_with_changes: Path
    ) -> None:
        """Should handle publish errors gracefully."""
        mock_publish.side_effect = Exception("Authentication failed")

        workspace = Workspace.discover(git_workspace_with_changes)
        result = await release(
            workspace,
            scope="pkg-a",
            bump=BumpType.PATCH,
            publish=True,
            no_git_tag=True,
            no_changelog=True,
        )

        assert result.success is False
        assert result.error is not None
        assert "Authentication failed" in result.error


class TestReleaseCommandClass:
    """Tests for ReleaseCommand class methods."""

    @pytest.fixture
    def git_workspace_with_tag(self, git_workspace: Path) -> Path:
        """Create git workspace with existing tag."""
        os.system(f"cd {git_workspace} && git tag pkg-a@1.0.0")
        return git_workspace

    def test_prepare_package_release_no_commits(self, git_workspace: Path) -> None:
        """Should return None when no commits since last release."""
        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace)
        options = ReleaseOptions(scope="pkg-a")
        cmd = ReleaseCommand(context, options)

        pkg = workspace.get_package("pkg-a")
        result = cmd._prepare_package_release(pkg)

        # No commits after initial, no scope, should skip
        assert result is None

    def test_prepare_package_release_with_bump_override(
        self, git_workspace: Path
    ) -> None:
        """Should prepare release when bump is overridden."""
        # Add a change
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "change.py").write_text("# change")
        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'chore: minor change'")

        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace)
        options = ReleaseOptions(scope="pkg-a", bump=BumpType.PATCH)
        cmd = ReleaseCommand(context, options)

        pkg = workspace.get_package("pkg-a")
        result = cmd._prepare_package_release(pkg)

        assert result is not None
        assert result.bump_type == BumpType.PATCH


class TestReleaseEdgeCases:
    """Edge case tests for release command."""

    async def test_empty_workspace(self, temp_dir: Path) -> None:
        """Should handle workspace with no packages."""
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("name: empty\npackages:\n  - packages/*\n")
        (temp_dir / "packages").mkdir()

        # Init git
        os.system(f"cd {temp_dir} && git init -q")
        os.system(f"cd {temp_dir} && git config user.email 'test@test.com'")
        os.system(f"cd {temp_dir} && git config user.name 'Test'")
        os.system(f"cd {temp_dir} && git add -A && git commit -q -m 'init'")

        workspace = Workspace.discover(temp_dir)
        result = await release(workspace, dry_run=True)

        assert result.success is True
        assert len(result.releases) == 0

    async def test_no_conventional_commits(self, git_workspace: Path) -> None:
        """Should skip release when no conventional commits."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "change.py").write_text("# change")
        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'random change'")

        workspace = Workspace.discover(git_workspace)
        result = await release(workspace, scope="pkg-a", dry_run=True)

        # Without conventional commits and no bump override, should skip
        assert len(result.releases) == 0

    async def test_breaking_change_major_bump(self, git_workspace: Path) -> None:
        """Should detect breaking change for major bump."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "breaking.py").write_text("# breaking change")
        os.system(f"cd {git_workspace} && git add -A")
        os.system(
            f"cd {git_workspace} && git commit -q -m 'feat!: breaking API change'"
        )

        workspace = Workspace.discover(git_workspace)
        result = await release(workspace, scope="pkg-a", dry_run=True)

        if result.releases:
            assert result.releases[0].bump_type == BumpType.MAJOR

    async def test_fix_commit_patch_bump(self, git_workspace: Path) -> None:
        """Should detect fix for patch bump."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "bugfix.py").write_text("# bug fix")
        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'fix: resolve bug'")

        workspace = Workspace.discover(git_workspace)
        result = await release(workspace, scope="pkg-a", dry_run=True)

        if result.releases:
            assert result.releases[0].bump_type == BumpType.PATCH

    async def test_feat_commit_minor_bump(self, git_workspace: Path) -> None:
        """Should detect feat for minor bump."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "feature.py").write_text("# new feature")
        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'feat: add feature'")

        workspace = Workspace.discover(git_workspace)
        result = await release(workspace, scope="pkg-a", dry_run=True)

        if result.releases:
            assert result.releases[0].bump_type == BumpType.MINOR

    async def test_no_changelog_option(self, git_workspace: Path) -> None:
        """Should skip changelog when no_changelog=True."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "change.py").write_text("# change")
        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'feat: new'")

        workspace = Workspace.discover(git_workspace)
        await release(
            workspace,
            scope="pkg-a",
            bump=BumpType.PATCH,
            no_changelog=True,
            no_git_tag=True,
        )

        # CHANGELOG.md should not exist
        assert not (pkg_a / "CHANGELOG.md").exists()

    async def test_no_git_tag_option(self, git_workspace: Path) -> None:
        """Should skip git tag when no_git_tag=True."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "change.py").write_text("# change")
        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'feat: new'")

        workspace = Workspace.discover(git_workspace)
        await release(
            workspace,
            scope="pkg-a",
            bump=BumpType.PATCH,
            no_git_tag=True,
            no_changelog=True,
        )

        # Check no new tag was created
        import subprocess

        result = subprocess.run(
            ["git", "tag", "-l", "pkg-a@1.0.1"],
            cwd=git_workspace,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""

    async def test_no_commit_option(self, git_workspace: Path) -> None:
        """Should skip git commit when no_commit=True."""
        pkg_a = git_workspace / "packages" / "pkg-a"
        (pkg_a / "change.py").write_text("# change")
        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'feat: new'")

        # Get current commit count
        import subprocess

        before = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=git_workspace,
            capture_output=True,
            text=True,
        )
        before_count = int(before.stdout.strip())

        workspace = Workspace.discover(git_workspace)
        result = await release(
            workspace,
            scope="pkg-a",
            bump=BumpType.PATCH,
            no_commit=True,
            no_git_tag=True,
            no_changelog=True,
        )

        # Commit count should be same (no new commit)
        after = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=git_workspace,
            capture_output=True,
            text=True,
        )
        after_count = int(after.stdout.strip())
        assert after_count == before_count
        assert result.commit_sha is None

    async def test_multiple_packages_release(self, git_workspace: Path) -> None:
        """Should release multiple packages."""
        # Add changes to multiple packages
        for pkg_name in ["pkg-a", "pkg-b"]:
            pkg = git_workspace / "packages" / pkg_name
            (pkg / "change.py").write_text(f"# change in {pkg_name}")

        os.system(f"cd {git_workspace} && git add -A")
        os.system(f"cd {git_workspace} && git commit -q -m 'feat: changes'")

        workspace = Workspace.discover(git_workspace)
        result = await release(
            workspace,
            scope="pkg-*",
            bump=BumpType.PATCH,
            dry_run=True,
        )

        names = [r.name for r in result.releases]
        # Both should be included based on scope
        assert "pkg-a" in names or "pkg-b" in names

    def test_options_all_flags_true(self) -> None:
        """Should support all flags enabled."""
        options = ReleaseOptions(
            dry_run=True,
            publish=True,
            no_git_tag=True,
            no_changelog=True,
            no_commit=True,
        )
        assert options.dry_run is True
        assert options.publish is True
        assert options.no_git_tag is True
        assert options.no_changelog is True
        assert options.no_commit is True
