# version

Manage package versions, changelogs, and git tags.

```bash
pymelos version [OPTIONS]
```

## Options

| Option | Alias | Description |
|---|---|---|
| `--scope` | `-s` | Filter packages to version. |
| `--bump` | `-b` | Force bump type (`major`, `minor`, `patch`). |
| `--prerelease` | | Prerelease tag (e.g., `alpha`, `rc`). |
| `--dry-run` | | Show planned changes without applying them. |
| `--no-git-tag` | | Skip creating git tags. |
| `--no-changelog` | | Skip changelog generation. |
| `--no-commit` | | Skip creating a git commit. |
| `--yes` | `-y` | Skip confirmation prompt. |

## Description

The `version` command analyzes your git history (using Conventional Commits) to determine the next version for your packages. It then:
1.  Updates version strings in `pyproject.toml` and `__init__.py`.
2.  Generates or updates `CHANGELOG.md`.
3.  Creates a git commit with the changes.
4.  Tags the commit with the new versions.

## Examples

```bash
# Auto-determine versions based on commits
pymelos version

# Force a patch bump
pymelos version --bump patch

# Create a prerelease
pymelos version --prerelease beta
```
