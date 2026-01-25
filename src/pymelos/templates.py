"""Templates for workspace initialization."""

PYMELOS_YAML_TEMPLATE = """# pymelos workspace configuration
name: {name}

packages:
  - packages/*
  - app/*

scripts:
{scripts}

command_defaults:
  concurrency: 4
  fail_fast: false
  topological: true

clean:
  patterns:
    - "__pycache__"
    - "*.pyc"
    - ".pytest_cache"
    - ".mypy_cache"
    - ".ruff_cache"
    - "*.egg-info"
    - "dist"
    - "build"
  protected:
    - ".venv"
    - ".git"

bootstrap:
  hooks:
{bootstrap_hooks}

versioning:
  commit_format: conventional
  tag_format: "{{name}}@{{version}}"
  changelog:
    enabled: true
    filename: CHANGELOG.md
"""

PYPROJECT_TOML_TEMPLATE = """[project]
name = "{name}"
version = "0.0.0"
description = "{description}"
requires-python = ">=3.10"
readme = "README.md"

[tool.uv]
workspace = {{ members = ["packages/*", "app/*"] }}

{type_checker_config}

{tools_config}
"""

TEST_SCRIPT_TEMPLATE = """  test:
    description: Run tests
    run: |
      if [ -d tests ] && [ "$(ls -A tests)" ]; then
        pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
      else
        echo "No tests found"
      fi"""

LINT_SCRIPT_TEMPLATE = """  lint:
    run: ruff check .
    description: Run linting

  format:
    run: ruff format .
    description: Format code"""

TYPECHECK_SCRIPT_TEMPLATE = """  typecheck:
    run: {cmd}
    description: Run type checking"""

# Configurations to append to pyproject.toml
TOOL_CONFIGS = {
    "pytest": """[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = ["-ra", "--strict-markers"]
""",
    "ruff": """
[tool.ruff]
line-length = 100
target-version = "py310"
""",
    "ty": """[tool.ty.environment]
python-version = "3.10"
""",
}
