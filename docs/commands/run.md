# run

Run a defined script across packages.

```bash
pymelos run SCRIPT [OPTIONS]
```

## Arguments

| Argument | Description |
|---|---|
| `SCRIPT` | Name of the script defined in `pymelos.yaml`. |

## Options

| Option | Alias | Description | Default |
|---|---|---|---|
| `--scope` | `-s` | Filter packages by glob pattern. | |
| `--since` | | Run only on packages changed since git ref. | |
| `--ignore` | `-i` | Patterns to ignore (comma-separated). | |
| `--concurrency` | `-c` | Number of parallel jobs. | `4` |
| `--fail-fast` | | Stop on first failure. | `False` |
| `--no-topological` | | Ignore dependency order (run in parallel). | |

## Description

Executes a script defined in the `scripts` section of `pymelos.yaml`. This is the primary way to run tasks like testing, linting, or building across your monorepo.

Pymelos automatically handles topological sorting, ensuring dependencies are processed before dependents (unless `--no-topological` is used).

## Examples

```bash
# Run 'test' script in all packages
pymelos run test

# Run 'lint' only on changed packages since 'main'
pymelos run lint --since main

# Run 'build' with 8 parallel jobs
pymelos run build -c 8
```
