#!/usr/bin/env bash
# Test pymelos on all supported Python versions
# Usage: ./scripts/test-all-versions.sh

set -e

VERSIONS=("3.10" "3.11" "3.12" "3.13")
FAILED=()

echo "Testing pymelos on Python versions: ${VERSIONS[*]}"
echo "=============================================="

# Phase 1: Setup all envs and run lint/type checks
echo ""
echo "=== Phase 1: Linting & Type Checking ==="
for version in "${VERSIONS[@]}"; do
    env_name=".test_envs/py${version//./}"
    echo ""
    echo "--- Python $version ---"

    UV_PROJECT_ENVIRONMENT="$env_name" uv sync --python "$version" --all-extras --quiet 2>/dev/null || \
    UV_PROJECT_ENVIRONMENT="$env_name" uv sync --python "$version" --all-extras

    UV_PROJECT_ENVIRONMENT="$env_name" uv run ruff check src/ tests/
    UV_PROJECT_ENVIRONMENT="$env_name" uv run ruff format --check src/ tests/
    UV_PROJECT_ENVIRONMENT="$env_name" uv run ty check src/
    echo "✅ Python $version lint passed"
done

# Phase 2: Run tests
echo ""
echo "=== Phase 2: Testing ==="
for version in "${VERSIONS[@]}"; do
    env_name=".test_envs/py${version//./}"
    echo ""
    echo "--- Python $version ---"

    if UV_PROJECT_ENVIRONMENT="$env_name" uv run pytest -q; then
        echo "✅ Python $version tests passed"
    else
        echo "❌ Python $version tests failed"
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
