# Pymelos

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

## Projects using Pymelos

*   [Flash Framework](https://github.com/y3l1n4ung/flash-framework)
*   *Using Pymelos? [Submit a PR](https://github.com/y3l1n4ung/pymelos/pulls) to add your project here!*

## Next Steps

- [Getting Started](getting-started.md): Install and initialize your first workspace.
- [Configuration](configuration.md): Learn about `pymelos.yaml` options.
- [Commands](commands/README.md): Explore the CLI commands.
