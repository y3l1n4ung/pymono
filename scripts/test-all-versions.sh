#!/usr/bin/env bash
# Test pymelos on all supported Python versions
# Usage: ./scripts/test-all-versions.sh

set -e

VERSIONS=("3.10" "3.11" "3.12" "3.13")
FAILED=()

echo "Testing pymelos on Python versions: ${VERSIONS[*]}"
echo "=============================================="

for version in "${VERSIONS[@]}"; do
    echo ""
    echo "=== Python $version ==="

    # Use isolated venv to avoid conflicts with .venv (VSCode)
    env_name=".venv_py${version//./}"

    UV_PROJECT_ENVIRONMENT="$env_name" uv sync --python "$version" --all-extras --quiet 2>/dev/null || \
    UV_PROJECT_ENVIRONMENT="$env_name" uv sync --python "$version" --all-extras

    # Linting
    echo "  Linting..."
    UV_PROJECT_ENVIRONMENT="$env_name" uv run ruff check src/ tests/
    UV_PROJECT_ENVIRONMENT="$env_name" uv run ruff format --check src/ tests/

    # Type checking
    echo "  Type checking..."
    UV_PROJECT_ENVIRONMENT="$env_name" uv run ty check src/

    # Tests
    echo "  Running tests..."
    if UV_PROJECT_ENVIRONMENT="$env_name" uv run pytest -q; then
        echo "✅ Python $version passed"
    else
        echo "❌ Python $version failed"
        FAILED+=("$version")
    fi
done

echo ""
echo "=============================================="

if [ ${#FAILED[@]} -eq 0 ]; then
    echo "✅ All Python versions passed!"
    exit 0
else
    echo "❌ Failed versions: ${FAILED[*]}"
    exit 1
fi
