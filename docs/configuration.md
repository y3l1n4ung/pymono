# Configuration

The `pymelos.yaml` file is the heart of your Pymelos workspace. It defines the workspace structure, scripts, and behavior for various commands.

## Root Options

| Option | Type | Description |
|Paths|---|---|
| `name` | `string` | **Required**. The name of the workspace. |
| `packages` | `list[string]` | **Required**. Glob patterns to locate packages (e.g., `["packages/*"]`). |
| `ignore` | `list[string]` | Patterns to exclude from package discovery. |
| `env` | `dict[str, str]` | Environment variables to set for all commands. |

## Scripts (`scripts`)

Define scripts that can be run via `pymelos run <name>`.

```yaml
scripts:
  test:
    run: pytest
    description: Run unit tests
    fail_fast: true
  lint:
    run: ruff check .
```

| Option | Type | Description |
|---|---|---|
| `run` | `string` | **Required**. The command to execute. |
| `description` | `string` | Human-readable description. |
| `env` | `dict[str, str]` | Script-specific environment variables. |
| `scope` | `string` | Package scope filter for this script. |
| `fail_fast` | `bool` | Stop execution on the first failure (default: `false`). |
| `topological` | `bool` | Respect dependency order (default: `true`). |
| `pre` | `list[string]` | Commands to run before the main script. |
| `post` | `list[string]` | Commands to run after the main script. |

## Command Defaults (`command_defaults`)

Set default behavior for commands.

| Option | Type | Default | Description |
|---|---|---|---|
| `concurrency` | `int` | `4` | Default number of parallel jobs. |
| `fail_fast` | `bool` | `false` | Stop on first failure. |
| `topological` | `bool` | `true` | Respect dependency order. |

## Bootstrap Configuration (`bootstrap`)

Configuration for the `pymelos bootstrap` command.

### Hooks

You can define hooks to run after bootstrapping.

```yaml
bootstrap:
  hooks:
    - name: "Install pre-commit"
      run: pre-commit install
      run_once: true
```

| Option | Type | Description |
|---|---|---|
| `hooks` | `list[Hook]` | List of hooks to run. |

**Hook Options:**

| Option | Type | Description |
|---|---|---|
| `name` | `string` | **Required**. Hook name. |
| `run` | `string` | **Required**. Command to execute. |
| `scope` | `string` | Package scope filter. |
| `run_once` | `bool` | If `true`, runs only at workspace root. Default `false`. |

## Clean Configuration (`clean`)

Configuration for the `pymelos clean` command.

| Option | Type | Default | Description |
|---|---|---|---|
| `patterns` | `list[string]` | *See below* | Glob patterns to clean. |
| `protected` | `list[string]` | `.venv`, `.git`, ... | Patterns to never clean. |

**Default Clean Patterns:**
`__pycache__`, `*.pyc`, `*.pyo`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `*.egg-info`, `dist`, `build`, `.coverage`, `htmlcov`.

## Versioning Configuration (`versioning`)

Configuration for `pymelos version` and `pymelos release`.

| Option | Type | Default | Description |
|---|---|---|---|
| `commit_format` | `string` | `conventional` | Commit message format (`conventional` or `angular`). |
| `tag_format` | `string` | `{name}@{version}` | Git tag format. |
| `commit_message` | `string` | `chore(release): {packages}` | Release commit message. |
| `changelog` | `ChangelogConfig` | *Enabled* | Changelog generation settings. |

### Changelog Configuration

```yaml
versioning:
  changelog:
    enabled: true
    filename: CHANGELOG.md
    sections:
      - type: feat
        title: Features
```

## Publish Configuration (`publish`)

Configuration for `pymelos release --publish`.

| Option | Type | Default | Description |
|---|---|---|---|
| `registry` | `string` | PyPI | Repository URL to publish to. |
| `private` | `list[string]` | `[]` | Package patterns to never publish. |
