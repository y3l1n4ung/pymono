# init

Initialize a new Pymelos workspace.

```bash
pymelos init [PATH] [OPTIONS]
```

## Arguments

| Argument | Description |
|---|---|
| `PATH` | Directory to initialize. Defaults to current directory. |

## Options

| Option | Alias | Description |
|---|---|---|
| `--name` | `-n` | Name of the workspace. Defaults to directory name. |

## Description

The `init` command scaffolds a new Pymelos workspace. It creates:
- `pymelos.yaml` with default configuration.
- `pyproject.toml` with `uv` workspace configuration.
- `packages/` directory.
- `.gitignore`.
- Initializes git repository if needed.

## Examples

```bash
# Initialize in current directory
pymelos init

# Initialize in a new directory named 'my-repo'
pymelos init my-repo

# Initialize with a specific workspace name
pymelos init . --name "My Awesome Monorepo"
```
