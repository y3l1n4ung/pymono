# add

Add a new project to the workspace.

```bash
pymelos add NAME [OPTIONS]
```

## Arguments

| Argument | Description |
|---|---|
| `NAME` | Name of the project to add. |

## Options

| Option | Alias | Description | Default |
|---|---|---|---|
| `--project-type` | `-t` | Type of project: `lib` or `app`. | `lib` |
| `--folder` | `-f` | Target folder. | `packages` (lib) or `examples` (app) |
| `--editable` | | Install the project as editable after creation. | `True` |

## Description

Scaffolds a new Python project within your workspace using `uv init`. It also:
- Creates a `tests` directory.
- Configures `pyproject.toml` for the new package.

## Examples

```bash
# Add a library package (in packages/)
pymelos add my-utils

# Add an application (in examples/)
pymelos add my-cli --project-type app

# Add to a custom folder
pymelos add my-service --folder services
```
