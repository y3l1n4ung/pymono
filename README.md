# Pymelos

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Pymelos** is a monorepo management tool for Python, inspired by [Melos](https://github.com/invertase/melos).

It is designed to manage multiple Python packages efficiently using modern tooling such as **uv** and **Ruff**, while providing fully automated **semantic release** workflows.

## Key Features

- **Fast Dependency Management**: Built on top of **uv** for lightning-fast dependency resolution and installation.
- **Workspace Management**: Leverages **uv workspaces** to handle local package linking and dependencies automatically.
- **Script Execution**: Run scripts across multiple packages with filtering and parallel execution.
- **Versioning & Publishing**: Automated versioning, changelog generation, and publishing inspired by **semantic-release** and [Conventional Commits](https://www.conventionalcommits.org/).
- **Change Detection**: Smartly detect changed packages and their dependents to optimize CI/CD pipelines.

## Why Pymelos?

1.  **Zero-Config Linking**: Leverages **uv workspaces** for instant, automatic package linking.
2.  **Unified Scripts**: Define tasks once in `pymelos.yaml` and run them everywhere.
3.  **Semantic Releases**: Fully automated version bumping, changelogs, and publishing.

## Documentation

Full documentation is available in the [docs/](docs/) directory.

- [Getting Started](docs/getting-started.md)
- [Configuration](docs/configuration.md)
- [CLI Commands](docs/commands/README.md)

## Installation

```bash
# Using uv (recommended)
uv tool install pymelos

# Using pip
pip install pymelos
```

## Quick Start

```bash
# Initialize a new workspace
pymelos init --name my-workspace

# Install dependencies and link local packages
pymelos bootstrap

# List all packages in the workspace
pymelos list

# Run a script across all packages
pymelos run test

# Run on specific packages
pymelos run test --scope my-package

# Run on changed packages since main
pymelos run test --since main

# Execute any command
pymelos exec "pytest -v"

# Show changed packages
pymelos changed main

# Clean build artifacts
pymelos clean

# Semantic release (dry run)
pymelos release --dry-run
```

## Projects using Pymelos

*   [Flash Framework](https://github.com/y3l1n4ung/flash-framework)
*   *Using Pymelos? [Submit a PR](https://github.com/y3l1n4ung/pymelos/pulls) to add your project here!*

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to Pymelos.

## License

MIT
