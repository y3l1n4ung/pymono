# Getting Started

## Installation

The recommended way to install Pymelos is using `uv tool`:

```bash
uv tool install pymelos
```

Alternatively, you can install it using `pip`:

```bash
pip install pymelos
```

## Initializing a Workspace

To start a new workspace, create a directory and run `pymelos init`:

```bash
mkdir my-monorepo
cd my-monorepo
pymelos init
```

This command will create:
- `pymelos.yaml`: The main configuration file for your workspace.
- `pyproject.toml`: The root project configuration.
- `packages/`: A directory to hold your packages.
- `.gitignore`: A standard git ignore file for Python.
- `.git`: Initializes a git repository if one doesn't exist.

## Adding Packages

You can add new packages to your workspace using the `add` command:

```bash
# Add a library package
pymelos add my-library

# Add an application package (in examples/ folder by default)
pymelos add my-app --project-type app
```

## Bootstrapping

Once you have packages and dependencies defined, run `bootstrap` to install dependencies and link local packages:

```bash
pymelos bootstrap
```

This command uses `uv sync` under the hood to ensure a fast and consistent environment.

## Running Scripts

You can define scripts in `pymelos.yaml` and run them across your workspace. For example, if you have a `test` script defined:

```bash
pymelos run test
```

This will execute the test command in all packages that have it defined.

## Next Steps

- Configure your workspace in [Configuration](configuration.md).
- Learn more about [CLI Commands](commands/README.md).
