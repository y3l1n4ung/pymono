#!/bin/bash
set -e

# Bump version script - ensures lint and tests pass before bumping

INCREMENT=${1:-PATCH}

echo "==> Running lint check..."
uv run ruff check .
uv run ruff format --check .

echo "==> Running tests..."
uv run pytest --tb=short -q

echo "==> Bumping version ($INCREMENT)..."
uv run cz bump --increment "$INCREMENT" --yes

echo "==> Done! Version bumped successfully."
git log --oneline -1
git tag -l | tail -1
