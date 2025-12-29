"""Tests for clean command."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymelos.commands.base import CommandContext
from pymelos.commands.clean import CleanCommand, CleanOptions, clean
from pymelos.workspace.workspace import Workspace


class TestCleanCommand:
    """Tests for CleanCommand."""

    @pytest.fixture
    def workspace_with_artifacts(self, workspace_dir: Path) -> Path:
        """Create workspace with build artifacts to clean."""
        pkg_a = workspace_dir / "packages" / "pkg-a"

        # Create __pycache__ directories
        pycache = pkg_a / "__pycache__"
        pycache.mkdir()
        (pycache / "module.cpython-312.pyc").write_bytes(b"fake pyc")

        # Create .pytest_cache
        pytest_cache = pkg_a / ".pytest_cache"
        pytest_cache.mkdir()
        (pytest_cache / "README.md").write_text("pytest cache")

        # Create dist directory
        dist = pkg_a / "dist"
        dist.mkdir()
        (dist / "pkg_a-1.0.0.tar.gz").write_bytes(b"fake tarball")

        return workspace_dir

    async def test_removes_pycache(self, workspace_with_artifacts: Path) -> None:
        """Should remove __pycache__ directories."""
        workspace = Workspace.discover(workspace_with_artifacts)
        pkg_a = workspace_with_artifacts / "packages" / "pkg-a"

        assert (pkg_a / "__pycache__").exists()

        result = await clean(workspace)

        assert not (pkg_a / "__pycache__").exists()
        assert result.dirs_removed >= 1

    async def test_removes_pytest_cache(self, workspace_with_artifacts: Path) -> None:
        """Should remove .pytest_cache directories."""
        workspace = Workspace.discover(workspace_with_artifacts)
        pkg_a = workspace_with_artifacts / "packages" / "pkg-a"

        assert (pkg_a / ".pytest_cache").exists()

        await clean(workspace)

        assert not (pkg_a / ".pytest_cache").exists()

    async def test_dry_run_does_not_remove(self, workspace_with_artifacts: Path) -> None:
        """Should not remove files in dry run mode."""
        workspace = Workspace.discover(workspace_with_artifacts)
        pkg_a = workspace_with_artifacts / "packages" / "pkg-a"

        result = await clean(workspace, dry_run=True)

        # Files should still exist
        assert (pkg_a / "__pycache__").exists()
        assert (pkg_a / ".pytest_cache").exists()

        # But result should report what would be removed
        assert result.dirs_removed >= 2

    async def test_respects_protected_patterns(self, workspace_dir: Path) -> None:
        """Should not remove protected directories."""
        pkg_a = workspace_dir / "packages" / "pkg-a"

        # Create .git directory (protected by default)
        git_dir = pkg_a / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("fake git config")

        workspace = Workspace.discover(workspace_dir)
        await clean(workspace, patterns=[".git"])

        # .git should still exist (protected)
        assert git_dir.exists()

    async def test_scope_filter(self, workspace_with_artifacts: Path) -> None:
        """Should only clean packages matching scope."""
        # Add artifacts to pkg-b
        pkg_b = workspace_with_artifacts / "packages" / "pkg-b"
        pycache_b = pkg_b / "__pycache__"
        pycache_b.mkdir()
        (pycache_b / "module.cpython-312.pyc").write_bytes(b"fake")

        workspace = Workspace.discover(workspace_with_artifacts)
        result = await clean(workspace, scope="pkg-a")

        # pkg-a should be cleaned
        pkg_a = workspace_with_artifacts / "packages" / "pkg-a"
        assert not (pkg_a / "__pycache__").exists()

        # pkg-b should NOT be cleaned
        assert pycache_b.exists()

        assert "pkg-a" in result.packages_cleaned
        assert "pkg-b" not in result.packages_cleaned

    async def test_custom_patterns(self, workspace_dir: Path) -> None:
        """Should use custom patterns when provided."""
        pkg_a = workspace_dir / "packages" / "pkg-a"

        # Create custom artifact
        custom = pkg_a / "custom_build"
        custom.mkdir()
        (custom / "output.txt").write_text("build output")

        workspace = Workspace.discover(workspace_dir)
        await clean(workspace, patterns=["custom_build"])

        assert not custom.exists()

    async def test_returns_bytes_freed(self, workspace_with_artifacts: Path) -> None:
        """Should track bytes freed."""
        workspace = Workspace.discover(workspace_with_artifacts)
        result = await clean(workspace)

        assert result.bytes_freed > 0

    async def test_returns_packages_cleaned(self, workspace_with_artifacts: Path) -> None:
        """Should return list of cleaned packages."""
        workspace = Workspace.discover(workspace_with_artifacts)
        result = await clean(workspace)

        assert "pkg-a" in result.packages_cleaned

    async def test_empty_workspace_no_error(self, workspace_dir: Path) -> None:
        """Should handle workspace with no artifacts gracefully."""
        workspace = Workspace.discover(workspace_dir)
        result = await clean(workspace)

        assert result.files_removed == 0
        assert result.dirs_removed == 0


class TestCleanCommandClass:
    """Tests for CleanCommand class directly."""

    def test_get_patterns_from_config(self, workspace_dir: Path) -> None:
        """Should get patterns from workspace config."""
        workspace = Workspace.discover(workspace_dir)
        context = CommandContext(workspace=workspace)
        cmd = CleanCommand(context)

        patterns = cmd.get_patterns()
        assert "__pycache__" in patterns or "**/__pycache__" in patterns

    def test_get_patterns_override(self, workspace_dir: Path) -> None:
        """Should use override patterns when provided."""
        workspace = Workspace.discover(workspace_dir)
        context = CommandContext(workspace=workspace)
        options = CleanOptions(patterns=["custom_pattern"])
        cmd = CleanCommand(context, options)

        patterns = cmd.get_patterns()
        assert patterns == ["custom_pattern"]

    def test_is_protected(self, workspace_dir: Path) -> None:
        """Should correctly identify protected paths."""
        workspace = Workspace.discover(workspace_dir)
        context = CommandContext(workspace=workspace)
        cmd = CleanCommand(context)

        assert cmd.is_protected(Path(".git"), {".git", ".venv"})
        assert cmd.is_protected(Path(".venv"), {".git", ".venv"})
        assert not cmd.is_protected(Path("__pycache__"), {".git", ".venv"})


class TestCleanEdgeCases:
    """Edge case tests for clean command."""

    async def test_empty_workspace(self, temp_dir: Path) -> None:
        """Should handle workspace with no packages."""
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("name: empty\npackages:\n  - packages/*\n")
        (temp_dir / "packages").mkdir()

        workspace = Workspace.discover(temp_dir)
        result = await clean(workspace)

        assert result.files_removed == 0
        assert result.dirs_removed == 0

    async def test_nested_pycache(self, workspace_dir: Path) -> None:
        """Should clean deeply nested __pycache__."""
        pkg_a = workspace_dir / "packages" / "pkg-a"
        nested = pkg_a / "src" / "pkg_a" / "sub" / "__pycache__"
        nested.mkdir(parents=True)
        (nested / "deep.pyc").write_bytes(b"fake")

        workspace = Workspace.discover(workspace_dir)
        await clean(workspace, patterns=["**/__pycache__"])

        assert not nested.exists()

    async def test_multiple_patterns(self, workspace_dir: Path) -> None:
        """Should clean with multiple patterns."""
        pkg_a = workspace_dir / "packages" / "pkg-a"
        (pkg_a / "__pycache__").mkdir()
        (pkg_a / "dist").mkdir()

        workspace = Workspace.discover(workspace_dir)
        await clean(workspace, patterns=["__pycache__", "dist"])

        assert not (pkg_a / "__pycache__").exists()
        assert not (pkg_a / "dist").exists()

    async def test_file_pattern(self, workspace_dir: Path) -> None:
        """Should clean files matching pattern."""
        pkg_a = workspace_dir / "packages" / "pkg-a"
        (pkg_a / "test.pyc").write_bytes(b"fake")

        workspace = Workspace.discover(workspace_dir)
        result = await clean(workspace, patterns=["*.pyc"])

        assert not (pkg_a / "test.pyc").exists()
        assert result.files_removed >= 1

    async def test_empty_pattern_list(self, workspace_dir: Path) -> None:
        """Should handle empty pattern list."""
        workspace = Workspace.discover(workspace_dir)
        result = await clean(workspace, patterns=[])

        assert result.files_removed == 0
        assert result.dirs_removed == 0
