# CLI Commands

Pymelos provides a suite of commands to manage your workspace.

## Core Commands

- [`init`](init.md): Initialize a new workspace.
- [`bootstrap`](bootstrap.md): Install dependencies and link packages.
- [`add`](add.md): Add a new package to the workspace.
- [`list`](list.md): List packages in the workspace.
- [`clean`](clean.md): Clean build artifacts.
- [`export`](export.md): Export package for deployment.

## Execution Commands

- [`run`](run.md): Run a script defined in `pymelos.yaml`.
- [`exec`](exec.md): Execute an arbitrary command.

## Change Management

- [`changed`](changed.md): List changed packages.
- [`version`](version.md): Manage versions and changelogs.
- [`release`](release.md): Version and publish packages.

## Global Options

These options are available for most commands (where applicable) or as global flags.

- `--verbose`: Enable verbose output.
- `--help`: Show help message.
- `--version`: Show Pymelos version.
