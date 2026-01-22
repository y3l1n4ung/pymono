# exec

Execute an arbitrary command across packages.

```bash
pymelos exec COMMAND [OPTIONS]
```

## Arguments

| Argument | Description |
|---|---|
| `COMMAND` | The shell command to execute. |

## Options

| Option | Alias | Description | Default |
|---|---|---|---|
| `--scope` | `-s` | Filter packages by glob pattern. | |
| `--since` | | Run only on packages changed since git ref. | |
| `--ignore` | `-i` | Patterns to ignore. | |
| `--concurrency` | `-c` | Number of parallel jobs. | `4` |
| `--fail-fast` | | Stop on first failure. | `False` |

## Description

Runs any shell command in the context of each package. Useful for one-off tasks not defined in `pymelos.yaml`.

## Examples

```bash
# Print working directory for each package
pymelos exec pwd

# Install a package directly (though bootstrap is preferred)
pymelos exec "pip install requests" --scope "packages/my-lib"

# Check directory listing
pymelos exec "ls -la"
```
