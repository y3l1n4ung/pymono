# changed

List packages changed since a git reference.

```bash
pymelos changed SINCE [OPTIONS]
```

## Arguments

| Argument | Description |
|---|---|
| `SINCE` | Git reference (branch, tag, commit SHA) to compare against. |

## Options

| Option | Description |
|---|---|
| `--no-dependents` | Exclude dependent packages (only list directly changed). |
| `--json` | Output as JSON. |

## Description

Identifies packages that have been modified since the specified git reference. By default, it also includes packages that depend on the modified packages (transitive dependents), which is crucial for CI/CD to ensure all affected components are tested.

## Examples

```bash
# Show packages changed since 'main'
pymelos changed main

# Show only packages directly modified (ignore dependents)
pymelos changed main --no-dependents

# JSON output for CI scripts
pymelos changed origin/main --json
```
