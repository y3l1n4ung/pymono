# list

List packages in the workspace.

```bash
pymelos list [OPTIONS]
```

## Options

| Option | Alias | Description |
|---|---|---|
| `--scope` | `-s` | Filter packages by glob pattern. |
| `--since` | | List only packages changed since a git reference. |
| `--json` | | Output as JSON. |
| `--graph` | | Show dependency graph (simple tree). |

## Description

Displays information about packages in the workspace, including version, path, and dependencies.

## Examples

```bash
# List all packages
pymelos list

# List packages in 'packages/*'
pymelos list --scope "packages/*"

# List as JSON
pymelos list --json

# Show dependency graph
pymelos list --graph
```
