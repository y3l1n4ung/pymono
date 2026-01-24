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

The `init` command scaffolds a new Pymelos workspace.

If run without arguments (or if the workspace name is not provided), it launches an **interactive wizard** to guide you through the setup.

### Interactive Wizard Steps

1.  **Workspace Name**: Enter the name of your monorepo.
2.  **Description**: Provide a short description for `pyproject.toml` and `README.md`.
3.  **Type Checker**: Select a type checker (Recommended: `ty`, or `pyright`, `mypy`).
4.  **Tools**: Enable `ruff` (linter/formatter) and `pytest` (testing).

### Generated Files

The command creates:
- `pymelos.yaml`: Workspace configuration with scripts (`test`, `lint`, `typecheck`, `format`) tailored to your choices.
- `pyproject.toml`: Root project configuration with `uv` workspace settings and selected dev dependencies.
- `packages/` & `app/`: Directories to hold your library and application packages.
- `.gitignore`: Standard Python gitignore.
- `README.md`: Project documentation.
- `.git`: Initializes a git repository if one doesn't exist.

## Examples

```bash
# Interactive setup (Recommended)
pymelos init

# Initialize in a specific directory (triggers wizard for options)
pymelos init my-new-workspace

# Initialize with a name (might skip some wizard steps in future versions, currently still asks)
pymelos init . --name "My Awesome Monorepo"
```
