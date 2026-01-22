# clean

Clean build artifacts.

```bash
pymelos clean [OPTIONS]
```

## Options

| Option | Alias | Description |
|---|---|---|
| `--scope` | `-s` | Filter packages to clean. |
| `--dry-run` | | Show what would be cleaned without deleting files. |

## Description

Removes temporary files and directories based on patterns defined in `pymelos.yaml` (under `clean`). Default patterns include `__pycache__`, `dist`, `build`, etc.

## Examples

```bash
# Clean workspace
pymelos clean

# See what would be deleted
pymelos clean --dry-run

# Clean only specific packages
pymelos clean --scope "packages/core*"
```
