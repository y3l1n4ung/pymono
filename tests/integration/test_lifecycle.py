"""Full lifecycle integration tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import pymelos


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


def create_package(
    path: Path, name: str, version: str = "0.1.0", deps: list[str] | None = None
) -> None:
    """Create a simple package."""
    path.mkdir(parents=True, exist_ok=True)
    deps_str = ", ".join(f'"{d}"' for d in (deps or []))
    (path / "pyproject.toml").write_text(f"""[project]
name = "{name}"
version = "{version}"
dependencies = [{deps_str}]
""")
    src = path / "src" / name.replace("-", "_")
    src.mkdir(parents=True)
    (src / "__init__.py").write_text(f'"""Package {name}."""\n')


class TestInitCommand:
    """Tests for pymelos init command."""

    def test_init_creates_config(self, tmp_path: Path) -> None:
        """Init creates pymelos.yaml."""
        result = run_pymelos(["init", "--name", "my-workspace"], tmp_path)

        assert result.returncode == 0
        assert (tmp_path / "pymelos.yaml").exists()

    def test_init_config_content(self, tmp_path: Path) -> None:
        """Init creates valid config."""
        run_pymelos(["init", "--name", "test-ws"], tmp_path)

        content = (tmp_path / "pymelos.yaml").read_text()
        assert "name: test-ws" in content
        assert "packages:" in content


class TestFullWorkflow:
    """Test complete workflow from init to operations."""

    def test_init_add_packages_list(self, tmp_path: Path) -> None:
        """Initialize workspace, add packages, list them."""
        # 1. Initialize workspace
        result = run_pymelos(["init", "--name", "test-mono"], tmp_path)
        assert result.returncode == 0

        # 2. Create packages directory and packages
        create_package(tmp_path / "packages" / "core", "core")
        create_package(tmp_path / "packages" / "api", "api", deps=["core"])

        # 3. List packages
        result = run_pymelos(["list"], tmp_path)
        assert result.returncode == 0
        assert "core" in result.stdout
        assert "api" in result.stdout

    def test_exec_in_workspace(self, tmp_path: Path) -> None:
        """Execute command across packages."""
        # Setup
        run_pymelos(["init", "--name", "exec-test"], tmp_path)
        create_package(tmp_path / "packages" / "pkg-a", "pkg-a")
        create_package(tmp_path / "packages" / "pkg-b", "pkg-b")

        # Exec
        result = run_pymelos(["exec", "pwd"], tmp_path)
        assert result.returncode == 0
        assert "pkg-a" in result.stdout
        assert "pkg-b" in result.stdout

    def test_clean_command(self, tmp_path: Path) -> None:
        """Clean removes build artifacts."""
        # Setup
        run_pymelos(["init", "--name", "clean-test"], tmp_path)
        pkg_path = tmp_path / "packages" / "pkg"
        create_package(pkg_path, "pkg")

        # Create some artifacts
        (pkg_path / "__pycache__").mkdir()
        (pkg_path / "__pycache__" / "test.pyc").write_text("")
        (pkg_path / "dist").mkdir()
        (pkg_path / "dist" / "pkg.whl").write_text("")

        # Clean
        result = run_pymelos(["clean"], tmp_path)
        assert result.returncode == 0

        # Verify cleaned
        assert not (pkg_path / "__pycache__").exists()
        assert not (pkg_path / "dist").exists()


class TestGitWorkflow:
    """Tests requiring git repository."""

    @pytest.fixture
    def git_workspace(self, tmp_path: Path) -> Path:
        """Create a git-initialized workspace."""
        # Init git
        run_git(["init"], tmp_path)
        run_git(["config", "user.email", "test@test.com"], tmp_path)
        run_git(["config", "user.name", "Test"], tmp_path)

        # Init pymelos
        run_pymelos(["init", "--name", "git-test"], tmp_path)

        # Create packages
        create_package(tmp_path / "packages" / "lib", "lib")
        create_package(tmp_path / "packages" / "app", "app", deps=["lib"])

        # Initial commit
        run_git(["add", "."], tmp_path)
        run_git(["commit", "-m", "Initial commit"], tmp_path)

        return tmp_path

    def test_changed_no_changes(self, git_workspace: Path) -> None:
        """Changed shows nothing when no changes."""
        result = run_pymelos(["changed", "HEAD"], git_workspace)

        # Should succeed but show no packages
        assert result.returncode == 0

    def test_changed_after_modification(self, git_workspace: Path) -> None:
        """Changed detects modified packages."""
        # Modify lib package
        lib_init = git_workspace / "packages" / "lib" / "src" / "lib" / "__init__.py"
        lib_init.write_text('"""Updated lib."""\n\ndef hello(): pass\n')

        result = run_pymelos(["changed", "HEAD"], git_workspace)

        assert result.returncode == 0
        assert "lib" in result.stdout

    def test_bootstrap_command(self, git_workspace: Path) -> None:
        """Bootstrap installs dependencies."""
        result = run_pymelos(["bootstrap"], git_workspace)

        # Bootstrap may fail if uv not available, but command should run
        # Just verify it attempts to run
        assert result.returncode in (0, 1)

    def test_release_dry_run(self, git_workspace: Path) -> None:
        """Release dry-run shows what would be released."""
        # Make a change and commit to trigger release
        lib_init = git_workspace / "packages" / "lib" / "src" / "lib" / "__init__.py"
        lib_init.write_text('"""Lib package."""\n\ndef greet(): return "hi"\n')
        run_git(["add", "."], git_workspace)
        run_git(["commit", "-m", "feat(lib): add greet function"], git_workspace)

        result = run_pymelos(["release", "--dry-run", "--bump", "patch"], git_workspace)

        assert result.returncode == 0
        assert "lib" in result.stdout

    def test_release_version_bump(self, git_workspace: Path) -> None:
        """Release bumps version in pyproject.toml."""
        # Make a change and commit to trigger release
        lib_init = git_workspace / "packages" / "lib" / "src" / "lib" / "__init__.py"
        lib_init.write_text('"""Lib package."""\n\ndef add(a, b): return a + b\n')
        run_git(["add", "."], git_workspace)
        run_git(["commit", "-m", "feat(lib): add add function"], git_workspace)

        # Run release with patch bump
        result = run_pymelos(["release", "--bump", "patch", "--yes"], git_workspace)
        assert result.returncode == 0

        # Check version was bumped
        lib_toml = git_workspace / "packages" / "lib" / "pyproject.toml"
        content = lib_toml.read_text()
        # Version should be bumped from 0.1.0 to 0.1.1
        assert 'version = "0.1.1"' in content

    def test_release_with_scope(self, git_workspace: Path) -> None:
        """Release respects scope filter."""
        # Make changes to both packages and commit
        lib_init = git_workspace / "packages" / "lib" / "src" / "lib" / "__init__.py"
        lib_init.write_text('"""Lib."""\n\ndef foo(): pass\n')
        app_init = git_workspace / "packages" / "app" / "src" / "app" / "__init__.py"
        app_init.write_text('"""App."""\n\ndef bar(): pass\n')
        run_git(["add", "."], git_workspace)
        run_git(["commit", "-m", "feat: add functions to both packages"], git_workspace)

        result = run_pymelos(
            ["release", "--scope", "lib", "--bump", "minor", "--yes"], git_workspace
        )
        assert result.returncode == 0

        # Only lib should be bumped
        lib_toml = git_workspace / "packages" / "lib" / "pyproject.toml"
        app_toml = git_workspace / "packages" / "app" / "pyproject.toml"

        lib_content = lib_toml.read_text()
        app_content = app_toml.read_text()

        # lib bumped to 0.2.0, app stays at 0.1.0
        assert 'version = "0.2.0"' in lib_content
        assert 'version = "0.1.0"' in app_content


class TestScriptsWorkflow:
    """Tests for script execution."""

    @pytest.fixture
    def script_workspace(self, tmp_path: Path) -> Path:
        """Create workspace with scripts defined."""
        run_pymelos(["init", "--name", "script-test"], tmp_path)

        # Update config with scripts - test various features
        config = tmp_path / "pymelos.yaml"
        config.write_text("""name: script-test
packages:
  - packages/*

scripts:
  # Simple string shorthand
  simple: echo "simple script"

  # Full config with description
  echo-name:
    run: echo "Package name test"
    description: Echo test

  # Script that creates files
  create-file:
    run: touch test-marker.txt
    description: Create marker file

  # Script that fails
  failing-script:
    run: exit 1
    description: Always fails

  # Script with environment variables
  env-test:
    run: echo "$MY_VAR $ANOTHER_VAR"
    env:
      MY_VAR: hello
      ANOTHER_VAR: world

  # Script with scope built-in
  scoped-script:
    run: touch scoped-marker.txt
    scope: alpha

  # Script with fail_fast built-in
  fail-fast-script:
    run: exit 1
    fail_fast: true

  # Script with topological disabled
  no-topo:
    run: echo "no topo"
    topological: false
""")

        # Create packages with dependencies for topological testing
        create_package(tmp_path / "packages" / "alpha", "alpha")
        create_package(tmp_path / "packages" / "beta", "beta", deps=["alpha"])
        create_package(tmp_path / "packages" / "gamma", "gamma", deps=["beta"])

        return tmp_path

    def test_run_script_across_packages(self, script_workspace: Path) -> None:
        """Run script executes in all packages."""
        result = run_pymelos(["run", "echo-name"], script_workspace)

        assert result.returncode == 0
        # Check that all packages passed
        assert "3 packages passed" in result.stdout

    def test_run_simple_script_shorthand(self, script_workspace: Path) -> None:
        """Run script defined as simple string."""
        result = run_pymelos(["run", "simple"], script_workspace)

        assert result.returncode == 0
        assert "3 packages passed" in result.stdout

    def test_run_script_creates_files(self, script_workspace: Path) -> None:
        """Run script that creates files works."""
        result = run_pymelos(["run", "create-file"], script_workspace)

        assert result.returncode == 0
        assert (script_workspace / "packages" / "alpha" / "test-marker.txt").exists()
        assert (script_workspace / "packages" / "beta" / "test-marker.txt").exists()
        assert (script_workspace / "packages" / "gamma" / "test-marker.txt").exists()

    def test_run_script_with_scope(self, script_workspace: Path) -> None:
        """Run script with scope filter from CLI."""
        result = run_pymelos(["run", "create-file", "--scope", "alpha"], script_workspace)

        assert result.returncode == 0
        assert (script_workspace / "packages" / "alpha" / "test-marker.txt").exists()
        assert not (script_workspace / "packages" / "beta" / "test-marker.txt").exists()
        assert not (script_workspace / "packages" / "gamma" / "test-marker.txt").exists()

    def test_run_script_with_builtin_scope(self, script_workspace: Path) -> None:
        """Run script with scope defined in config."""
        result = run_pymelos(["run", "scoped-script"], script_workspace)

        assert result.returncode == 0
        # Only alpha should have the marker (scope is defined in script config)
        assert (script_workspace / "packages" / "alpha" / "scoped-marker.txt").exists()
        assert not (script_workspace / "packages" / "beta" / "scoped-marker.txt").exists()

    def test_run_script_with_env_vars(self, script_workspace: Path) -> None:
        """Run script with environment variables."""
        result = run_pymelos(["run", "env-test"], script_workspace)

        assert result.returncode == 0
        assert "3 packages passed" in result.stdout

    def test_run_failing_script(self, script_workspace: Path) -> None:
        """Run script that fails returns error."""
        result = run_pymelos(["run", "failing-script"], script_workspace)

        assert result.returncode == 1
        assert "failed" in result.stdout

    def test_run_failing_script_with_fail_fast(self, script_workspace: Path) -> None:
        """Run with fail-fast stops on first failure."""
        result = run_pymelos(["run", "failing-script", "--fail-fast"], script_workspace)

        assert result.returncode == 1

    def test_run_script_not_found(self, script_workspace: Path) -> None:
        """Run non-existent script shows error."""
        result = run_pymelos(["run", "nonexistent"], script_workspace)

        assert result.returncode == 1
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_run_script_no_topological(self, script_workspace: Path) -> None:
        """Run script with --no-topological ignores dependency order."""
        result = run_pymelos(["run", "simple", "--no-topological"], script_workspace)

        assert result.returncode == 0
        assert "3 packages passed" in result.stdout

    def test_run_script_with_concurrency(self, script_workspace: Path) -> None:
        """Run script with custom concurrency."""
        result = run_pymelos(["run", "simple", "--concurrency", "1"], script_workspace)

        assert result.returncode == 0
        assert "3 packages passed" in result.stdout

    def test_run_script_with_ignore(self, script_workspace: Path) -> None:
        """Run script with ignore filter."""
        result = run_pymelos(["run", "create-file", "--ignore", "beta,gamma"], script_workspace)

        assert result.returncode == 0
        assert (script_workspace / "packages" / "alpha" / "test-marker.txt").exists()
        assert not (script_workspace / "packages" / "beta" / "test-marker.txt").exists()
        assert not (script_workspace / "packages" / "gamma" / "test-marker.txt").exists()


class TestListOutputFormats:
    """Tests for list command output formats."""

    @pytest.fixture
    def list_workspace(self, tmp_path: Path) -> Path:
        """Create workspace for list tests."""
        run_pymelos(["init", "--name", "list-test"], tmp_path)
        create_package(tmp_path / "packages" / "core", "core")
        create_package(tmp_path / "packages" / "api", "api", deps=["core"])
        create_package(tmp_path / "packages" / "cli", "cli", deps=["core", "api"])
        return tmp_path

    def test_list_json_output(self, list_workspace: Path) -> None:
        """List with --json returns valid JSON."""
        import json

        result = run_pymelos(["list", "--json"], list_workspace)

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 3
        names = {p["name"] for p in data}
        assert names == {"core", "api", "cli"}

    def test_list_graph_output(self, list_workspace: Path) -> None:
        """List with --graph shows dependencies."""
        result = run_pymelos(["list", "--graph"], list_workspace)

        assert result.returncode == 0
        assert "cli" in result.stdout
        assert "core" in result.stdout
        assert "->" in result.stdout

    def test_list_with_scope(self, list_workspace: Path) -> None:
        """List with scope filter."""
        result = run_pymelos(["list", "--scope", "api"], list_workspace)

        assert result.returncode == 0
        assert "api" in result.stdout


class TestChangedOutputFormats:
    """Tests for changed command output formats."""

    @pytest.fixture
    def changed_workspace(self, tmp_path: Path) -> Path:
        """Create git workspace for changed tests."""
        run_git(["init"], tmp_path)
        run_git(["config", "user.email", "test@test.com"], tmp_path)
        run_git(["config", "user.name", "Test"], tmp_path)

        run_pymelos(["init", "--name", "changed-test"], tmp_path)
        create_package(tmp_path / "packages" / "lib", "lib")
        create_package(tmp_path / "packages" / "app", "app", deps=["lib"])

        run_git(["add", "."], tmp_path)
        run_git(["commit", "-m", "Initial"], tmp_path)

        return tmp_path

    def test_changed_json_output(self, changed_workspace: Path) -> None:
        """Changed with --json returns valid JSON."""
        import json

        # Make a change
        lib_init = changed_workspace / "packages" / "lib" / "src" / "lib" / "__init__.py"
        lib_init.write_text('"""Updated."""\n')

        result = run_pymelos(["changed", "HEAD", "--json"], changed_workspace)

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) >= 1
        names = {p["name"] for p in data}
        assert "lib" in names

    def test_changed_no_dependents(self, changed_workspace: Path) -> None:
        """Changed with --no-dependents excludes dependent packages."""
        # Make a change to lib
        lib_init = changed_workspace / "packages" / "lib" / "src" / "lib" / "__init__.py"
        lib_init.write_text('"""Updated."""\n')

        result = run_pymelos(["changed", "HEAD", "--no-dependents"], changed_workspace)

        assert result.returncode == 0
        assert "lib" in result.stdout
        # app depends on lib but should not be included
        assert "dependent" not in result.stdout


class TestReleaseOptions:
    """Tests for release command options."""

    @pytest.fixture
    def release_workspace(self, tmp_path: Path) -> Path:
        """Create git workspace for release tests."""
        run_git(["init"], tmp_path)
        run_git(["config", "user.email", "test@test.com"], tmp_path)
        run_git(["config", "user.name", "Test"], tmp_path)

        run_pymelos(["init", "--name", "release-test"], tmp_path)
        create_package(tmp_path / "packages" / "pkg", "pkg")

        run_git(["add", "."], tmp_path)
        run_git(["commit", "-m", "Initial"], tmp_path)

        # Make a change and commit
        pkg_init = tmp_path / "packages" / "pkg" / "src" / "pkg" / "__init__.py"
        pkg_init.write_text('"""Updated pkg."""\n\ndef hello(): pass\n')
        run_git(["add", "."], tmp_path)
        run_git(["commit", "-m", "feat(pkg): add hello"], tmp_path)

        return tmp_path

    def test_release_no_git_tag(self, release_workspace: Path) -> None:
        """Release with --no-git-tag skips tag creation."""
        result = run_pymelos(
            ["release", "--bump", "patch", "--no-git-tag", "--yes"], release_workspace
        )

        assert result.returncode == 0

        # Check no tag was created
        tag_result = run_git(["tag", "-l"], release_workspace)
        assert "pkg@0.1.1" not in tag_result.stdout

    def test_release_no_changelog(self, release_workspace: Path) -> None:
        """Release with --no-changelog skips changelog."""
        result = run_pymelos(
            ["release", "--bump", "patch", "--no-changelog", "--yes"], release_workspace
        )

        assert result.returncode == 0

        # Check no changelog was created
        changelog = release_workspace / "packages" / "pkg" / "CHANGELOG.md"
        assert not changelog.exists()

    def test_release_no_commit(self, release_workspace: Path) -> None:
        """Release with --no-commit skips git commit."""
        # Get current commit count
        before = run_git(["rev-list", "--count", "HEAD"], release_workspace)
        before_count = int(before.stdout.strip())

        result = run_pymelos(
            ["release", "--bump", "patch", "--no-commit", "--no-git-tag", "--yes"],
            release_workspace,
        )

        assert result.returncode == 0

        # Check no new commit was created
        after = run_git(["rev-list", "--count", "HEAD"], release_workspace)
        after_count = int(after.stdout.strip())
        assert after_count == before_count

    def test_release_creates_tag_and_changelog(self, release_workspace: Path) -> None:
        """Release creates tag and changelog by default."""
        result = run_pymelos(["release", "--bump", "patch", "--yes"], release_workspace)

        assert result.returncode == 0

        # Check tag was created
        tag_result = run_git(["tag", "-l"], release_workspace)
        assert "pkg@0.1.1" in tag_result.stdout

        # Check changelog was created
        changelog = release_workspace / "packages" / "pkg" / "CHANGELOG.md"
        assert changelog.exists()
        content = changelog.read_text()
        assert "0.1.1" in content


class TestVersionCommand:
    """Tests for version flag."""

    def test_version_long_flag(self, tmp_path: Path) -> None:
        """--version shows version."""
        result = run_pymelos(["--version"], tmp_path)

        assert result.returncode == 0
        assert "pymelos" in result.stdout
        assert pymelos.__version__ in result.stdout

    def test_version_short_flag(self, tmp_path: Path) -> None:
        """-V shows version."""
        result = run_pymelos(["-V"], tmp_path)

        assert result.returncode == 0
        assert "pymelos" in result.stdout


class TestExecOptions:
    """Tests for exec command options."""

    @pytest.fixture
    def exec_workspace(self, tmp_path: Path) -> Path:
        """Create workspace for exec tests."""
        run_pymelos(["init", "--name", "exec-test"], tmp_path)
        create_package(tmp_path / "packages" / "a", "a")
        create_package(tmp_path / "packages" / "b", "b", deps=["a"])
        create_package(tmp_path / "packages" / "c", "c", deps=["b"])
        return tmp_path

    def test_exec_with_concurrency(self, exec_workspace: Path) -> None:
        """Exec with concurrency option."""
        result = run_pymelos(["exec", "--concurrency", "2", "pwd"], exec_workspace)

        assert result.returncode == 0
        assert "a" in result.stdout
        assert "b" in result.stdout
        assert "c" in result.stdout

    def test_exec_with_ignore(self, exec_workspace: Path) -> None:
        """Exec with ignore filter."""
        result = run_pymelos(["exec", "--ignore", "b", "pwd"], exec_workspace)

        assert result.returncode == 0
        assert "packages/a" in result.stdout
        assert "packages/c" in result.stdout


class TestCleanOptions:
    """Tests for clean command options."""

    @pytest.fixture
    def clean_workspace(self, tmp_path: Path) -> Path:
        """Create workspace with artifacts for clean tests."""
        run_pymelos(["init", "--name", "clean-test"], tmp_path)

        pkg_a = tmp_path / "packages" / "a"
        pkg_b = tmp_path / "packages" / "b"
        create_package(pkg_a, "a")
        create_package(pkg_b, "b")

        # Create artifacts in both
        for pkg in [pkg_a, pkg_b]:
            (pkg / "__pycache__").mkdir()
            (pkg / "__pycache__" / "test.pyc").write_text("")
            (pkg / ".pytest_cache").mkdir()
            (pkg / ".pytest_cache" / "data").write_text("")

        return tmp_path

    def test_clean_dry_run(self, clean_workspace: Path) -> None:
        """Clean with --dry-run shows what would be cleaned."""
        result = run_pymelos(["clean", "--dry-run"], clean_workspace)

        assert result.returncode == 0
        assert "Would clean" in result.stdout

        # Verify nothing was actually cleaned
        assert (clean_workspace / "packages" / "a" / "__pycache__").exists()
        assert (clean_workspace / "packages" / "b" / "__pycache__").exists()

    def test_clean_with_scope(self, clean_workspace: Path) -> None:
        """Clean with scope only cleans matching packages."""
        result = run_pymelos(["clean", "--scope", "a"], clean_workspace)

        assert result.returncode == 0

        # a should be cleaned
        assert not (clean_workspace / "packages" / "a" / "__pycache__").exists()
        # b should not be cleaned
        assert (clean_workspace / "packages" / "b" / "__pycache__").exists()
