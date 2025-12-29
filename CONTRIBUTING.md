# Contributing to pymelos

Thank you for your interest in contributing to pymelos! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Git

### Getting Started

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pymelos.git
   cd pymelos
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Install pre-commit hooks:
   ```bash
   uv run pre-commit install
   uv run pre-commit install --hook-type commit-msg
   ```

4. Verify setup:
   ```bash
   uv run pytest
   uv run ruff check .
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/unit/commands/test_list.py

# Run tests matching a pattern
uv run pytest -k "test_list"
```

### Code Quality

```bash
# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Fix lint issues automatically
uv run ruff check . --fix
```

### Pre-commit Hooks

The project uses pre-commit hooks for:
- **Ruff** - Linting and formatting
- **Pytest** - Run tests before commit
- **Commitizen** - Validate commit messages

Hooks run automatically on `git commit`. To run manually:
```bash
uv run pre-commit run --all-files
```

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/). Format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Formatting, no code change
- `refactor` - Code change that neither fixes a bug nor adds a feature
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

### Examples

```
feat(cli): add --json flag to list command
fix(release): handle missing changelog gracefully
docs: update installation instructions
test(bootstrap): add edge case tests
```

## Pull Request Process

1. Create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```

2. Make your changes and commit using conventional commits

3. Ensure all checks pass:
   ```bash
   uv run ruff check .
   uv run pytest
   ```

4. Push and create a PR:
   ```bash
   git push origin feat/my-feature
   ```

5. Fill out the PR template completely

6. Wait for review and address feedback

## Project Structure

```
src/pymelos/
├── cli/          # CLI commands (Typer)
├── commands/     # Command implementations
├── config/       # Configuration loading (Pydantic)
├── execution/    # Parallel execution engine
├── filters/      # Package filtering
├── git/          # Git integration
├── uv/           # UV package manager integration
├── versioning/   # Semantic versioning
└── workspace/    # Workspace discovery
```

## Adding a New Command

1. Create command in `src/pymelos/commands/`
2. Add CLI handler in `src/pymelos/cli/commands/`
3. Register in `src/pymelos/cli/app.py`
4. Add tests in `tests/unit/commands/`
5. Update README if needed

## Questions?

- Open a [Discussion](https://github.com/y3l1n4ung/pymelos/discussions)
- Check existing [Issues](https://github.com/y3l1n4ung/pymelos/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
