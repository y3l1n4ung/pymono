# bootstrap

Install dependencies and link packages.

```bash
pymelos bootstrap [OPTIONS]
```

## Options

| Option | Description |
|---|---|
| `--clean` | Clean the workspace before bootstrapping. |
| `--frozen` | Sync with frozen dependencies (respect `uv.lock`). |
| `--skip-hooks` | Skip running bootstrap hooks defined in `pymelos.yaml`. |

## Description

The `bootstrap` command ensures your workspace is ready for development. It performs the following steps:

1.  **Dependency Installation**: Runs `uv sync` to install dependencies for all packages.
2.  **Package Linking**: Ensures local packages are linked correctly (handled by `uv` workspaces).
3.  **Hooks**: Executes any post-bootstrap hooks defined in `pymelos.yaml`.

## Examples

```bash
# Standard bootstrap
pymelos bootstrap

# Clean artifacts before bootstrapping
pymelos bootstrap --clean

# CI mode (frozen lockfile)
pymelos bootstrap --frozen
```
