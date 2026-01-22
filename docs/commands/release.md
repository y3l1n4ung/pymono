# release

Version and publish packages.

```bash
pymelos release [OPTIONS]
```

## Options

| Option | Alias | Description |
|---|---|---|
| `--publish` | | Publish to PyPI (or configured registry). |
| *All options from `version` command are also supported.* |

## Description

The `release` command combines the `version` command with publishing capabilities. It performs the versioning steps (update files, changelog, commit, tag) and then optionally publishes the packages to a package registry (like PyPI).

## Workflow

1.  **Analyze**: Determine new versions from commits.
2.  **Plan**: Show a summary of changes (versions, changelogs).
3.  **Apply**: Update files and generate changelogs.
4.  **Commit & Tag**: Create git commit and tags.
5.  **Publish** (if `--publish`): Build and upload to registry.

## Examples

```bash
# Dry run to see what would happen
pymelos release --dry-run

# Version and publish
pymelos release --publish

# Publish a prerelease
pymelos release --publish --prerelease rc
```
