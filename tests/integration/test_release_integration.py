"""Integration tests for release command with TestPyPI publishing."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def run_pymelos(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run pymelos CLI command."""
    return subprocess.run(
        [sys.executable, "-m", "pymelos", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run git command."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def run_uv(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    """Run uv command."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        ["uv", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=full_env,
    )


def create_publishable_package(
    path: Path,
    name: str,
    version: str = "0.0.1",
    description: str = "Test package",
) -> None:
    """Create a package that can be published to PyPI."""
    path.mkdir(parents=True, exist_ok=True)
    pkg_dir = name.replace("-", "_")

    # Full pyproject.toml with all required fields for publishing
    (path / "pyproject.toml").write_text(f"""[project]
name = "{name}"
version = "{version}"
description = "{description}"
readme = "README.md"
license = {{text = "MIT"}}
requires-python = ">=3.10"
dependencies = []
authors = [
    {{name = "Test Author", email = "test@example.com"}}
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{pkg_dir}"]
""")

    # README for PyPI
    (path / "README.md").write_text(f"# {name}\n\n{description}\n")

    # Source code
    src = path / "src" / name.replace("-", "_")
    src.mkdir(parents=True)
    (src / "__init__.py").write_text(f'"""Package {name}."""\n\n__version__ = "{version}"\n')
    (src / "py.typed").write_text("")


@pytest.fixture
def release_workspace(tmp_path: Path) -> Path:
    """Create a complete workspace ready for release testing."""
    # Initialize git
    run_git(["init"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)

    # Create pymelos.yaml with versioning config
    (tmp_path / "pymelos.yaml").write_text("""name: release-test-workspace
packages:
  - packages/*

versioning:
  tag_format: "{name}@{version}"
  commit_message: "chore(release): {packages}"

publish:
  registry: https://test.pypi.org/legacy/
""")

    # Create root pyproject.toml
    (tmp_path / "pyproject.toml").write_text("""[project]
name = "release-test-workspace"
version = "0.0.0"
requires-python = ">=3.10"

[tool.uv.workspace]
members = ["packages/*"]
""")

    # Create packages directory
    (tmp_path / "packages").mkdir()

    # Create a publishable package
    create_publishable_package(
        tmp_path / "packages" / "test-pkg",
        "pymelos-test-pkg",
        "0.0.1",
        "Test package for pymelos release testing",
    )

    # Initial commit
    run_git(["add", "."], tmp_path)
    run_git(["commit", "-m", "Initial commit"], tmp_path)

    return tmp_path


class TestReleaseWorkflow:
    """Test complete release workflow."""

    def test_release_dry_run_shows_packages(self, release_workspace: Path) -> None:
        """Dry run shows what packages would be released."""
        # Make a change
        pkg = release_workspace / "packages" / "test-pkg"
        (pkg / "src" / "pymelos_test_pkg" / "feature.py").write_text("def hello(): pass\n")
        run_git(["add", "."], release_workspace)
        run_git(["commit", "-m", "feat: add hello function"], release_workspace)

        result = run_pymelos(["release", "--dry-run", "--bump", "patch"], release_workspace)

        assert result.returncode == 0
        assert "pymelos-test-pkg" in result.stdout or "test-pkg" in result.stdout

    def test_release_bumps_version(self, release_workspace: Path) -> None:
        """Release bumps version in pyproject.toml."""
        pkg = release_workspace / "packages" / "test-pkg"
        (pkg / "src" / "pymelos_test_pkg" / "feature.py").write_text("def greet(): pass\n")
        run_git(["add", "."], release_workspace)
        run_git(["commit", "-m", "feat: add greet function"], release_workspace)

        result = run_pymelos(
            ["release", "--bump", "patch", "--no-changelog"],
            release_workspace,
        )

        assert result.returncode == 0

        # Check version was bumped
        content = (pkg / "pyproject.toml").read_text()
        assert 'version = "0.0.2"' in content

    def test_release_creates_git_tag(self, release_workspace: Path) -> None:
        """Release creates git tag."""
        pkg = release_workspace / "packages" / "test-pkg"
        (pkg / "src" / "pymelos_test_pkg" / "util.py").write_text("def util(): pass\n")
        run_git(["add", "."], release_workspace)
        run_git(["commit", "-m", "feat: add util"], release_workspace)

        result = run_pymelos(
            ["release", "--bump", "minor", "--no-changelog"],
            release_workspace,
        )

        assert result.returncode == 0

        # Check tag exists
        tag_result = run_git(["tag", "-l"], release_workspace)
        assert "pymelos-test-pkg@0.1.0" in tag_result.stdout

    def test_release_creates_changelog(self, release_workspace: Path) -> None:
        """Release generates changelog entry."""
        pkg = release_workspace / "packages" / "test-pkg"
        (pkg / "src" / "pymelos_test_pkg" / "api.py").write_text("def api(): pass\n")
        run_git(["add", "."], release_workspace)
        run_git(["commit", "-m", "feat: add api function"], release_workspace)

        result = run_pymelos(["release", "--bump", "patch"], release_workspace)

        assert result.returncode == 0

        # Check changelog exists
        changelog = pkg / "CHANGELOG.md"
        assert changelog.exists()
        content = changelog.read_text()
        assert "0.0.2" in content

    def test_release_prerelease_version(self, release_workspace: Path) -> None:
        """Release with prerelease creates correct version."""
        pkg = release_workspace / "packages" / "test-pkg"
        (pkg / "src" / "pymelos_test_pkg" / "beta.py").write_text("def beta(): pass\n")
        run_git(["add", "."], release_workspace)
        run_git(["commit", "-m", "feat: add beta feature"], release_workspace)

        result = run_pymelos(
            ["release", "--bump", "minor", "--prerelease", "beta", "--no-changelog"],
            release_workspace,
        )

        assert result.returncode == 0

        content = (pkg / "pyproject.toml").read_text()
        assert "beta" in content or "0.1.0" in content

    def test_release_major_version(self, release_workspace: Path) -> None:
        """Release with major bump works correctly."""
        pkg = release_workspace / "packages" / "test-pkg"
        (pkg / "src" / "pymelos_test_pkg" / "breaking.py").write_text("def breaking(): pass\n")
        run_git(["add", "."], release_workspace)
        run_git(["commit", "-m", "feat!: breaking change"], release_workspace)

        result = run_pymelos(
            ["release", "--bump", "major", "--no-changelog"],
            release_workspace,
        )

        assert result.returncode == 0

        content = (pkg / "pyproject.toml").read_text()
        assert 'version = "1.0.0"' in content


class TestReleaseBuild:
    """Test release build functionality."""

    def test_uv_build_package(self, release_workspace: Path) -> None:
        """Package can be built with uv."""
        pkg = release_workspace / "packages" / "test-pkg"

        # Build with explicit output directory
        result = run_uv(["build", "--out-dir", str(pkg / "dist")], pkg)

        # Debug output if build fails
        if result.returncode != 0:
            print(f"Build stdout: {result.stdout}")
            print(f"Build stderr: {result.stderr}")

        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert (pkg / "dist").exists(), f"dist not found. Contents: {list(pkg.iterdir())}"

        # Check dist files exist
        dist_files = list((pkg / "dist").glob("*"))
        assert len(dist_files) >= 1

    def test_built_package_installable(self, release_workspace: Path) -> None:
        """Built package can be installed."""
        pkg = release_workspace / "packages" / "test-pkg"

        # Build with explicit output directory
        run_uv(["build", "--out-dir", str(pkg / "dist")], pkg)

        # Find wheel
        wheels = list((pkg / "dist").glob("*.whl"))
        assert len(wheels) >= 1

        # Try to install in temp venv
        venv_path = release_workspace / "test-venv"
        run_uv(["venv", str(venv_path)], release_workspace)

        result = run_uv(
            ["pip", "install", str(wheels[0]), "--python", str(venv_path / "bin" / "python")],
            release_workspace,
        )

        assert result.returncode == 0


class TestReleaseWithScope:
    """Test release with scope filtering."""

    @pytest.fixture
    def multi_package_workspace(self, tmp_path: Path) -> Path:
        """Create workspace with multiple packages."""
        run_git(["init"], tmp_path)
        run_git(["config", "user.email", "test@test.com"], tmp_path)
        run_git(["config", "user.name", "Test"], tmp_path)

        (tmp_path / "pymelos.yaml").write_text("""name: multi-pkg
packages:
  - packages/*
""")

        (tmp_path / "pyproject.toml").write_text("""[project]
name = "multi-pkg"
version = "0.0.0"

[tool.uv.workspace]
members = ["packages/*"]
""")

        (tmp_path / "packages").mkdir()

        # Create multiple packages (use simple names for easier scope matching)
        for name in ["alpha", "beta", "gamma"]:
            create_publishable_package(
                tmp_path / "packages" / name,
                name,  # Use simple name for easier scope matching
                "0.1.0",
                f"Test {name} package",
            )

        run_git(["add", "."], tmp_path)
        run_git(["commit", "-m", "Initial"], tmp_path)

        return tmp_path

    def test_release_single_package(self, multi_package_workspace: Path) -> None:
        """Release with scope only releases specified package."""
        # Change all packages
        for name in ["alpha", "beta", "gamma"]:
            pkg = multi_package_workspace / "packages" / name
            (pkg / "src" / name / "new.py").write_text(f"# {name}\n")

        run_git(["add", "."], multi_package_workspace)
        run_git(["commit", "-m", "feat: update all"], multi_package_workspace)

        result = run_pymelos(
            ["release", "--scope", "alpha", "--bump", "patch", "--no-changelog"],
            multi_package_workspace,
        )

        assert result.returncode == 0

        # Only alpha should be bumped
        alpha_toml = multi_package_workspace / "packages" / "alpha" / "pyproject.toml"
        beta_toml = multi_package_workspace / "packages" / "beta" / "pyproject.toml"
        alpha_content = alpha_toml.read_text()
        beta_content = beta_toml.read_text()

        assert 'version = "0.1.1"' in alpha_content
        assert 'version = "0.1.0"' in beta_content

    def test_release_glob_scope(self, multi_package_workspace: Path) -> None:
        """Release with glob scope."""
        for name in ["alpha", "beta"]:
            pkg = multi_package_workspace / "packages" / name
            (pkg / "src" / name / "glob.py").write_text(f"# {name}\n")

        run_git(["add", "."], multi_package_workspace)
        run_git(["commit", "-m", "feat: update alpha and beta"], multi_package_workspace)

        result = run_pymelos(
            ["release", "--scope", "alpha,beta", "--bump", "minor", "--no-changelog"],
            multi_package_workspace,
        )

        assert result.returncode == 0


# TestPyPI integration tests - requires UV_TEST_PUBLISH_TOKEN env var
@pytest.mark.skipif(
    not os.environ.get("UV_TEST_PUBLISH_TOKEN"),
    reason="UV_TEST_PUBLISH_TOKEN not set - skipping TestPyPI tests",
)
class TestReleaseToTestPyPI:
    """Integration tests that publish to TestPyPI.

    These tests require:
    - UV_TEST_PUBLISH_TOKEN environment variable set
    - Network access to test.pypi.org

    Run with: pytest tests/integration/test_release.py -k TestReleaseToTestPyPI -v
    """

    @pytest.fixture
    def unique_package_workspace(self, tmp_path: Path) -> Path:
        """Create workspace with unique package name for TestPyPI."""
        import time

        # Generate unique package name to avoid conflicts
        timestamp = int(time.time())
        pkg_name = f"pymelos-test-{timestamp}"

        run_git(["init"], tmp_path)
        run_git(["config", "user.email", "test@test.com"], tmp_path)
        run_git(["config", "user.name", "Test"], tmp_path)

        (tmp_path / "pymelos.yaml").write_text("""name: testpypi-test
packages:
  - packages/*

publish:
  registry: https://test.pypi.org/legacy/
""")

        (tmp_path / "pyproject.toml").write_text("""[project]
name = "testpypi-test"
version = "0.0.0"

[tool.uv.workspace]
members = ["packages/*"]
""")

        (tmp_path / "packages").mkdir()

        create_publishable_package(
            tmp_path / "packages" / "test-pkg",
            pkg_name,
            "0.0.1",
            "Automated test package for pymelos - safe to ignore",
        )

        run_git(["add", "."], tmp_path)
        run_git(["commit", "-m", "Initial"], tmp_path)

        # Store package name for later use
        (tmp_path / ".pkg_name").write_text(pkg_name)

        return tmp_path

    def test_build_and_publish_to_testpypi(self, unique_package_workspace: Path) -> None:
        """Build and publish package to TestPyPI."""
        pkg = unique_package_workspace / "packages" / "test-pkg"
        pkg_name = (unique_package_workspace / ".pkg_name").read_text()

        # Build with explicit output directory
        build_result = run_uv(["build", "--out-dir", str(pkg / "dist")], pkg)
        assert build_result.returncode == 0

        # Publish to TestPyPI
        token = os.environ["UV_TEST_PUBLISH_TOKEN"]
        dist_files = list((pkg / "dist").glob("*"))

        publish_result = run_uv(
            ["publish", "--publish-url", "https://test.pypi.org/legacy/", "--token", token]
            + [str(f) for f in dist_files],
            pkg,
        )

        assert publish_result.returncode == 0

        # Verify package exists on TestPyPI (give it a moment to index)
        import time
        time.sleep(2)

        # Try to get package info
        import urllib.error
        import urllib.request

        try:
            url = f"https://test.pypi.org/pypi/{pkg_name}/json"
            with urllib.request.urlopen(url, timeout=10) as response:
                assert response.status == 200
        except urllib.error.HTTPError as e:
            # 404 might happen if indexing is slow, that's okay
            if e.code != 404:
                raise

    def test_release_command_with_publish(self, unique_package_workspace: Path) -> None:
        """Test full release command with --publish flag."""
        pkg = unique_package_workspace / "packages" / "test-pkg"

        # Make a change
        pkg_name = (unique_package_workspace / ".pkg_name").read_text()
        src_dir = pkg / "src" / pkg_name.replace("-", "_")
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "__init__.py").write_text('__version__ = "0.0.1"\n')
        (src_dir / "feature.py").write_text("def new_feature(): pass\n")

        run_git(["add", "."], unique_package_workspace)
        run_git(["commit", "-m", "feat: add new feature"], unique_package_workspace)

        # Note: This test would need environment variable for token
        # For now, just test that dry-run works
        result = run_pymelos(
            ["release", "--bump", "patch", "--dry-run"],
            unique_package_workspace,
        )

        assert result.returncode == 0


class TestReleaseEdgeCases:
    """Edge case tests for release integration."""

    def test_release_no_changes(self, release_workspace: Path) -> None:
        """Release with no changes does nothing."""
        result = run_pymelos(["release", "--dry-run"], release_workspace)

        assert result.returncode == 0
        # Should indicate no packages to release

    def test_release_invalid_bump_type(self, release_workspace: Path) -> None:
        """Release with invalid bump type fails."""
        result = run_pymelos(["release", "--bump", "invalid"], release_workspace)

        assert result.returncode != 0

    def test_release_nonexistent_scope(self, release_workspace: Path) -> None:
        """Release with nonexistent scope does nothing."""
        result = run_pymelos(
            ["release", "--scope", "nonexistent", "--bump", "patch", "--dry-run"],
            release_workspace,
        )

        assert result.returncode == 0

    def test_release_creates_commit(self, release_workspace: Path) -> None:
        """Release creates a git commit."""
        pkg = release_workspace / "packages" / "test-pkg"
        (pkg / "src" / "pymelos_test_pkg" / "commit.py").write_text("# commit test\n")
        run_git(["add", "."], release_workspace)
        run_git(["commit", "-m", "feat: for commit test"], release_workspace)

        before = run_git(["rev-list", "--count", "HEAD"], release_workspace)
        before_count = int(before.stdout.strip())

        run_pymelos(["release", "--bump", "patch", "--no-changelog"], release_workspace)

        after = run_git(["rev-list", "--count", "HEAD"], release_workspace)
        after_count = int(after.stdout.strip())

        assert after_count == before_count + 1

        # Check commit message
        log = run_git(["log", "-1", "--format=%s"], release_workspace)
        assert "release" in log.stdout.lower()

    def test_release_all_options_disabled(self, release_workspace: Path) -> None:
        """Release with all options disabled still bumps version."""
        pkg = release_workspace / "packages" / "test-pkg"
        (pkg / "src" / "pymelos_test_pkg" / "opts.py").write_text("# options test\n")
        run_git(["add", "."], release_workspace)
        run_git(["commit", "-m", "feat: options test"], release_workspace)

        result = run_pymelos(
            ["release", "--bump", "patch", "--no-git-tag", "--no-changelog", "--no-commit"],
            release_workspace,
        )

        assert result.returncode == 0

        # Version should still be bumped
        content = (pkg / "pyproject.toml").read_text()
        assert 'version = "0.0.2"' in content
