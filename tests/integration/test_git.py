"""Integration tests for git modules.

Tests the git operations with a real git repository to verify
each feature works as expected.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a git repository with some commits."""
    # Initialize repo
    run_git(["init"], tmp_path)
    run_git(["config", "user.email", "test@example.com"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)

    # Create initial commit
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repo")
    run_git(["add", "README.md"], tmp_path)
    run_git(["commit", "-m", "feat: initial commit"], tmp_path)

    return tmp_path


class TestGitRepo:
    """Tests for git/repo.py functions."""

    def test_is_git_repo_true(self, git_repo: Path) -> None:
        """is_git_repo returns True for git repository."""
        from pymelos.git.repo import is_git_repo

        assert is_git_repo(git_repo) is True

    def test_is_git_repo_false(self, tmp_path: Path) -> None:
        """is_git_repo returns False for non-git directory."""
        from pymelos.git.repo import is_git_repo

        assert is_git_repo(tmp_path) is False

    def test_get_repo_root(self, git_repo: Path) -> None:
        """get_repo_root returns repository root."""
        from pymelos.git.repo import get_repo_root

        # Create a subdirectory
        subdir = git_repo / "src" / "module"
        subdir.mkdir(parents=True)

        # get_repo_root should return the root from subdir
        root = get_repo_root(subdir)
        assert root == git_repo

    def test_get_repo_root_not_git_repo(self, tmp_path: Path) -> None:
        """get_repo_root raises GitError for non-git directory."""
        from pymelos.errors import GitError
        from pymelos.git.repo import get_repo_root

        with pytest.raises(GitError, match="Not inside a git repository"):
            get_repo_root(tmp_path)

    def test_get_current_branch(self, git_repo: Path) -> None:
        """get_current_branch returns branch name."""
        from pymelos.git.repo import get_current_branch

        # Default branch after init
        branch = get_current_branch(git_repo)
        assert branch in ("main", "master")

    def test_get_current_commit(self, git_repo: Path) -> None:
        """get_current_commit returns commit SHA."""
        from pymelos.git.repo import get_current_commit

        sha = get_current_commit(git_repo)
        assert len(sha) == 40  # Full SHA
        assert all(c in "0123456789abcdef" for c in sha)

    def test_is_clean_true(self, git_repo: Path) -> None:
        """is_clean returns True for clean repo."""
        from pymelos.git.repo import is_clean

        assert is_clean(git_repo) is True

    def test_is_clean_false_modified(self, git_repo: Path) -> None:
        """is_clean returns False for modified files."""
        from pymelos.git.repo import is_clean

        # Modify a file
        readme = git_repo / "README.md"
        readme.write_text("# Modified")

        assert is_clean(git_repo) is False

    def test_is_clean_false_untracked(self, git_repo: Path) -> None:
        """is_clean returns False for untracked files."""
        from pymelos.git.repo import is_clean

        # Create untracked file
        (git_repo / "new_file.txt").write_text("new")

        assert is_clean(git_repo) is False

    def test_run_git_command(self, git_repo: Path) -> None:
        """run_git_command executes git commands."""
        from pymelos.git.repo import run_git_command

        result = run_git_command(["status", "--porcelain"], cwd=git_repo)
        assert result.returncode == 0
        assert result.stdout == ""  # Clean repo

    def test_run_git_command_failure(self, git_repo: Path) -> None:
        """run_git_command raises GitError on failure."""
        from pymelos.errors import GitError
        from pymelos.git.repo import run_git_command

        with pytest.raises(GitError):
            run_git_command(["checkout", "nonexistent-branch"], cwd=git_repo)


class TestGitCommits:
    """Tests for git/commits.py functions."""

    def test_get_commits(self, git_repo: Path) -> None:
        """get_commits returns list of commits."""
        from pymelos.git.commits import get_commits

        commits = get_commits(git_repo)
        assert len(commits) == 1
        assert commits[0].subject == "feat: initial commit"
        assert commits[0].author_name  # Just check it's not empty
        assert commits[0].author_email  # Just check it's not empty

    def test_get_commits_multiple(self, git_repo: Path) -> None:
        """get_commits returns multiple commits."""
        from pymelos.git.commits import get_commits

        # Add more commits
        (git_repo / "file1.txt").write_text("content1")
        run_git(["add", "file1.txt"], git_repo)
        run_git(["commit", "-m", "feat: add file1"], git_repo)

        (git_repo / "file2.txt").write_text("content2")
        run_git(["add", "file2.txt"], git_repo)
        run_git(["commit", "-m", "fix: add file2"], git_repo)

        commits = get_commits(git_repo)
        assert len(commits) == 3
        # Newest first
        assert commits[0].subject == "fix: add file2"
        assert commits[1].subject == "feat: add file1"
        assert commits[2].subject == "feat: initial commit"

    def test_get_commits_with_limit(self, git_repo: Path) -> None:
        """get_commits respects limit parameter."""
        from pymelos.git.commits import get_commits

        # Add more commits
        (git_repo / "file1.txt").write_text("content1")
        run_git(["add", "file1.txt"], git_repo)
        run_git(["commit", "-m", "feat: add file1"], git_repo)

        (git_repo / "file2.txt").write_text("content2")
        run_git(["add", "file2.txt"], git_repo)
        run_git(["commit", "-m", "fix: add file2"], git_repo)

        commits = get_commits(git_repo, limit=2)
        assert len(commits) == 2

    def test_get_commits_since(self, git_repo: Path) -> None:
        """get_commits with since parameter."""
        from pymelos.git.commits import get_commits
        from pymelos.git.repo import get_current_commit

        # Get initial commit
        initial_sha = get_current_commit(git_repo)

        # Add more commits
        (git_repo / "file1.txt").write_text("content1")
        run_git(["add", "file1.txt"], git_repo)
        run_git(["commit", "-m", "feat: add file1"], git_repo)

        # Get commits since initial
        commits = get_commits(git_repo, since=initial_sha)
        assert len(commits) == 1
        assert commits[0].subject == "feat: add file1"

    def test_get_commits_with_path(self, git_repo: Path) -> None:
        """get_commits filters by path."""
        from pymelos.git.commits import get_commits

        # Create package structure
        pkg = git_repo / "packages" / "foo"
        pkg.mkdir(parents=True)
        (pkg / "file.txt").write_text("content")
        run_git(["add", "."], git_repo)
        run_git(["commit", "-m", "feat: add foo package"], git_repo)

        # Another package
        pkg2 = git_repo / "packages" / "bar"
        pkg2.mkdir(parents=True)
        (pkg2 / "file.txt").write_text("content")
        run_git(["add", "."], git_repo)
        run_git(["commit", "-m", "feat: add bar package"], git_repo)

        # Get commits for foo package only
        commits = get_commits(git_repo, path=pkg)
        assert len(commits) == 1
        assert commits[0].subject == "feat: add foo package"

    def test_get_commit(self, git_repo: Path) -> None:
        """get_commit returns single commit."""
        from pymelos.git.commits import get_commit
        from pymelos.git.repo import get_current_commit

        sha = get_current_commit(git_repo)
        commit = get_commit(git_repo, sha)

        assert commit is not None
        assert commit.sha == sha
        assert commit.subject == "feat: initial commit"

    def test_get_commit_not_found(self, git_repo: Path) -> None:
        """get_commit returns None for invalid ref."""
        from pymelos.git.commits import get_commit

        commit = get_commit(git_repo, "nonexistent")
        assert commit is None

    def test_get_commits_affecting_path(self, git_repo: Path) -> None:
        """get_commits_affecting_path filters by path."""
        from pymelos.git.commits import get_commits_affecting_path

        # Create file
        (git_repo / "src").mkdir()
        (git_repo / "src" / "module.py").write_text("code")
        run_git(["add", "."], git_repo)
        run_git(["commit", "-m", "feat: add module"], git_repo)

        commits = get_commits_affecting_path(git_repo, git_repo / "src")
        assert len(commits) == 1
        assert commits[0].subject == "feat: add module"

    def test_commit_subject_and_body(self, git_repo: Path) -> None:
        """Commit subject and body properties work correctly."""
        from pymelos.git.commits import get_commits

        # Create commit with body (single line body to avoid parsing issues)
        (git_repo / "file.txt").write_text("content")
        run_git(["add", "file.txt"], git_repo)

        # Use -m twice for subject and body
        run_git(["commit", "-m", "feat: add feature", "-m", "This is the body."], git_repo)

        commits = get_commits(git_repo, limit=1)
        assert len(commits) == 1
        assert commits[0].subject == "feat: add feature"
        assert commits[0].body is not None
        assert "This is the body" in commits[0].body


class TestGitTags:
    """Tests for git/tags.py functions."""

    def test_list_tags_empty(self, git_repo: Path) -> None:
        """list_tags returns empty list when no tags."""
        from pymelos.git.tags import list_tags

        tags = list_tags(git_repo)
        assert tags == []

    def test_list_tags(self, git_repo: Path) -> None:
        """list_tags returns all tags."""
        from pymelos.git.tags import list_tags

        # Create tags
        run_git(["tag", "v1.0.0"], git_repo)
        run_git(["tag", "v1.1.0"], git_repo)

        tags = list_tags(git_repo)
        assert len(tags) == 2
        tag_names = [t.name for t in tags]
        assert "v1.0.0" in tag_names
        assert "v1.1.0" in tag_names

    def test_list_tags_with_pattern(self, git_repo: Path) -> None:
        """list_tags filters by pattern."""
        from pymelos.git.tags import list_tags

        # Create tags with different prefixes
        run_git(["tag", "v1.0.0"], git_repo)
        run_git(["tag", "pkg@1.0.0"], git_repo)

        tags = list_tags(git_repo, pattern="v*")
        assert len(tags) == 1
        assert tags[0].name == "v1.0.0"

    def test_create_tag(self, git_repo: Path) -> None:
        """create_tag creates a new tag."""
        from pymelos.git.tags import create_tag, list_tags

        tag = create_tag(git_repo, "v1.0.0")
        assert tag.name == "v1.0.0"
        assert len(tag.sha) > 0

        # Verify tag exists
        tags = list_tags(git_repo)
        assert len(tags) == 1
        assert tags[0].name == "v1.0.0"

    def test_create_annotated_tag(self, git_repo: Path) -> None:
        """create_tag with message creates annotated tag."""
        from pymelos.git.tags import create_tag

        tag = create_tag(git_repo, "v1.0.0", message="Release v1.0.0")
        assert tag.name == "v1.0.0"
        assert tag.is_annotated is True

    def test_delete_tag(self, git_repo: Path) -> None:
        """delete_tag removes a tag."""
        from pymelos.git.tags import create_tag, delete_tag, list_tags

        create_tag(git_repo, "v1.0.0")
        assert len(list_tags(git_repo)) == 1

        delete_tag(git_repo, "v1.0.0")
        assert len(list_tags(git_repo)) == 0

    def test_get_latest_tag(self, git_repo: Path) -> None:
        """get_latest_tag returns most recent tag."""
        from pymelos.git.tags import create_tag, get_latest_tag

        create_tag(git_repo, "v1.0.0")

        # Add another commit and tag
        (git_repo / "file.txt").write_text("content")
        run_git(["add", "file.txt"], git_repo)
        run_git(["commit", "-m", "feat: add file"], git_repo)
        create_tag(git_repo, "v1.1.0")

        latest = get_latest_tag(git_repo)
        assert latest is not None
        assert latest.name == "v1.1.0"

    def test_get_latest_tag_with_pattern(self, git_repo: Path) -> None:
        """get_latest_tag filters by pattern."""
        from pymelos.git.tags import create_tag, get_latest_tag

        create_tag(git_repo, "v1.0.0")
        create_tag(git_repo, "pkg@1.0.0")

        latest = get_latest_tag(git_repo, pattern="v*")
        assert latest is not None
        assert latest.name == "v1.0.0"

    def test_get_latest_tag_none(self, git_repo: Path) -> None:
        """get_latest_tag returns None when no tags."""
        from pymelos.git.tags import get_latest_tag

        latest = get_latest_tag(git_repo)
        assert latest is None

    def test_get_tags_for_commit(self, git_repo: Path) -> None:
        """get_tags_for_commit returns tags pointing to commit."""
        from pymelos.git.repo import get_current_commit
        from pymelos.git.tags import create_tag, get_tags_for_commit

        sha = get_current_commit(git_repo)
        create_tag(git_repo, "v1.0.0")
        create_tag(git_repo, "release-1.0")

        tags = get_tags_for_commit(git_repo, sha)
        assert len(tags) == 2
        tag_names = [t.name for t in tags]
        assert "v1.0.0" in tag_names
        assert "release-1.0" in tag_names

    def test_parse_version_from_tag(self) -> None:
        """parse_version_from_tag extracts version."""
        from pymelos.git.tags import parse_version_from_tag

        # Standard v prefix
        assert parse_version_from_tag("v1.2.3") == "1.2.3"
        assert parse_version_from_tag("1.2.3") == "1.2.3"

        # Package prefix
        assert parse_version_from_tag("pkg@1.2.3") == "1.2.3"
        assert parse_version_from_tag("my-package@1.2.3") == "1.2.3"

        # With prerelease
        assert parse_version_from_tag("v1.2.3-beta.1") == "1.2.3-beta.1"

        # Custom prefix
        assert parse_version_from_tag("pkg@1.2.3", prefix="pkg@") == "1.2.3"

        # Non-version tag
        assert parse_version_from_tag("release-candidate") is None

    def test_get_package_tags(self, git_repo: Path) -> None:
        """get_package_tags returns tags for package."""
        from pymelos.git.tags import create_tag, get_package_tags

        # Create tags for different packages
        create_tag(git_repo, "core@1.0.0")
        create_tag(git_repo, "core@1.1.0")
        create_tag(git_repo, "api@1.0.0")

        core_tags = get_package_tags(git_repo, "core")
        assert len(core_tags) == 2
        tag_names = [t.name for t in core_tags]
        assert "core@1.0.0" in tag_names
        assert "core@1.1.0" in tag_names

    def test_get_latest_package_tag(self, git_repo: Path) -> None:
        """get_latest_package_tag returns latest version."""
        from pymelos.git.tags import create_tag, get_latest_package_tag

        create_tag(git_repo, "core@1.0.0")
        create_tag(git_repo, "core@1.1.0")
        create_tag(git_repo, "core@1.0.5")

        latest = get_latest_package_tag(git_repo, "core")
        assert latest is not None
        assert latest.name == "core@1.1.0"

    def test_get_latest_package_tag_none(self, git_repo: Path) -> None:
        """get_latest_package_tag returns None when no tags."""
        from pymelos.git.tags import get_latest_package_tag

        latest = get_latest_package_tag(git_repo, "nonexistent")
        assert latest is None


class TestGitChanges:
    """Tests for git/changes.py functions."""

    def test_get_changed_files_since(self, git_repo: Path) -> None:
        """get_changed_files_since returns changed files."""
        from pymelos.git.changes import get_changed_files_since
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Add new file
        (git_repo / "new_file.txt").write_text("content")
        run_git(["add", "new_file.txt"], git_repo)
        run_git(["commit", "-m", "feat: add new file"], git_repo)

        changed = get_changed_files_since(git_repo, initial_sha)
        assert Path("new_file.txt") in changed

    def test_get_changed_files_since_includes_staged(self, git_repo: Path) -> None:
        """get_changed_files_since includes staged changes."""
        from pymelos.git.changes import get_changed_files_since
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Stage a file
        (git_repo / "staged.txt").write_text("content")
        run_git(["add", "staged.txt"], git_repo)

        changed = get_changed_files_since(git_repo, initial_sha)
        assert Path("staged.txt") in changed

    def test_get_changed_files_since_includes_unstaged(self, git_repo: Path) -> None:
        """get_changed_files_since includes unstaged changes."""
        from pymelos.git.changes import get_changed_files_since
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Modify existing file
        (git_repo / "README.md").write_text("modified")

        changed = get_changed_files_since(git_repo, initial_sha)
        assert Path("README.md") in changed

    def test_get_changed_files_since_includes_untracked(self, git_repo: Path) -> None:
        """get_changed_files_since includes untracked files."""
        from pymelos.git.changes import get_changed_files_since
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Create untracked file
        (git_repo / "untracked.txt").write_text("content")

        changed = get_changed_files_since(git_repo, initial_sha)
        assert Path("untracked.txt") in changed

    def test_get_changed_files_since_excludes_untracked(self, git_repo: Path) -> None:
        """get_changed_files_since can exclude untracked files."""
        from pymelos.git.changes import get_changed_files_since
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Create untracked file
        (git_repo / "untracked.txt").write_text("content")

        changed = get_changed_files_since(git_repo, initial_sha, include_untracked=False)
        assert Path("untracked.txt") not in changed

    def test_get_files_in_commit(self, git_repo: Path) -> None:
        """get_files_in_commit returns files changed in commit."""
        from pymelos.git.changes import get_files_in_commit
        from pymelos.git.repo import get_current_commit

        # Add multiple files
        (git_repo / "file1.txt").write_text("content1")
        (git_repo / "file2.txt").write_text("content2")
        run_git(["add", "."], git_repo)
        run_git(["commit", "-m", "feat: add files"], git_repo)

        sha = get_current_commit(git_repo)
        files = get_files_in_commit(git_repo, sha)

        assert Path("file1.txt") in files
        assert Path("file2.txt") in files

    def test_get_commits_since(self, git_repo: Path) -> None:
        """get_commits_since returns commit SHAs."""
        from pymelos.git.changes import get_commits_since
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Add commits
        (git_repo / "file1.txt").write_text("content1")
        run_git(["add", "file1.txt"], git_repo)
        run_git(["commit", "-m", "feat: commit 1"], git_repo)

        (git_repo / "file2.txt").write_text("content2")
        run_git(["add", "file2.txt"], git_repo)
        run_git(["commit", "-m", "feat: commit 2"], git_repo)

        commits = get_commits_since(git_repo, initial_sha)
        assert len(commits) == 2

    def test_get_commits_since_with_path(self, git_repo: Path) -> None:
        """get_commits_since filters by path."""
        from pymelos.git.changes import get_commits_since
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Create packages
        pkg1 = git_repo / "packages" / "pkg1"
        pkg1.mkdir(parents=True)
        (pkg1 / "file.txt").write_text("content")
        run_git(["add", "."], git_repo)
        run_git(["commit", "-m", "feat: pkg1 change"], git_repo)

        pkg2 = git_repo / "packages" / "pkg2"
        pkg2.mkdir(parents=True)
        (pkg2 / "file.txt").write_text("content")
        run_git(["add", "."], git_repo)
        run_git(["commit", "-m", "feat: pkg2 change"], git_repo)

        # Get commits only for pkg1
        commits = get_commits_since(git_repo, initial_sha, path=pkg1)
        assert len(commits) == 1

    def test_is_ancestor(self, git_repo: Path) -> None:
        """is_ancestor checks ancestor relationship."""
        from pymelos.git.changes import is_ancestor
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Add commit
        (git_repo / "file.txt").write_text("content")
        run_git(["add", "file.txt"], git_repo)
        run_git(["commit", "-m", "feat: add file"], git_repo)

        current_sha = get_current_commit(git_repo)

        # Initial is ancestor of current
        assert is_ancestor(git_repo, current_sha, initial_sha) is True

        # Current is not ancestor of initial
        assert is_ancestor(git_repo, initial_sha, current_sha) is False

    def test_get_merge_base(self, git_repo: Path) -> None:
        """get_merge_base returns common ancestor."""
        from pymelos.git.changes import get_merge_base
        from pymelos.git.repo import get_current_commit

        initial_sha = get_current_commit(git_repo)

        # Add commit
        (git_repo / "file.txt").write_text("content")
        run_git(["add", "file.txt"], git_repo)
        run_git(["commit", "-m", "feat: add file"], git_repo)

        current_sha = get_current_commit(git_repo)

        # Merge base of initial and current is initial
        merge_base = get_merge_base(git_repo, initial_sha, current_sha)
        assert merge_base == initial_sha
