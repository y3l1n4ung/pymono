# export

Export a package and its dependencies for deployment.

```bash
pymelos export PACKAGE [OPTIONS]
```

## Arguments

| Argument | Description |
|---|---|
| `PACKAGE` | Name of the package to export. |

## Options

| Option | Alias | Description | Default |
|---|---|---|---|
| `--output` | `-o` | Output directory. | `dist` |
| `--clean` | | Clean output directory before export. | `True` |

## Description

The `export` command creates a standalone, deployable bundle of a package and all its local workspace dependencies. This is particularly useful for building Docker images or deploying applications that depend on local library packages.

It creates a "mini-workspace" in the output directory containing:
1.  A new `pyproject.toml` workspace configuration.
2.  Copies of the target package and all its transitive local dependencies.
3.  A generated `uv.lock` for the exported workspace.

This ensures that you can simply copy the output directory (e.g., into a Docker container) and run `uv sync` or `pip install .` without worrying about missing relative path dependencies.

## Examples

```bash
# Export 'my-app' to 'dist' folder
pymelos export my-app

# Export to a specific directory
pymelos export my-app --output ./deploy/build

# Export without cleaning the directory first
pymelos export my-app --no-clean
```

## Docker Usage Example

After exporting:

```dockerfile
FROM python:3.10-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy the exported workspace
COPY dist/ .

# Install dependencies
RUN uv sync --frozen

# Run the app
CMD ["uv", "run", "python", "-m", "my_app"]
```
