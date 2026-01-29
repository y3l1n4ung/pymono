"""Tests for config schema module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pymelos.config.schema import (
    BootstrapConfig,
    BootstrapHook,
    ChangelogConfig,
    CleanConfig,
    CommandDefaults,
    CommitFormat,
    PublishConfig,
    PyMelosConfig,
    ScriptConfig,
    VersioningConfig,
)


class TestScriptConfig:
    """Tests for ScriptConfig."""

    def test_minimal_script(self) -> None:
        """Script with just run command."""
        script = ScriptConfig(run="pytest")
        assert script.run == "pytest"
        assert script.description is None
        assert script.env == {}
        assert script.fail_fast is False
        assert script.topological is True

    def test_full_script_config(self) -> None:
        """Script with all options."""
        script = ScriptConfig(
            run="pytest -v",
            description="Run tests",
            env={"CI": "true"},
            scope="core",
            fail_fast=True,
            topological=False,
            pre=["lint"],
            post=["report"],
        )
        assert script.run == "pytest -v"
        assert script.description == "Run tests"
        assert script.env == {"CI": "true"}
        assert script.scope == "core"
        assert script.fail_fast is True
        assert script.topological is False
        assert script.pre == ["lint"]
        assert script.post == ["report"]


class TestBootstrapConfig:
    """Tests for BootstrapConfig."""

    def test_default_bootstrap(self) -> None:
        """Default bootstrap has empty hooks."""
        config = BootstrapConfig()
        assert config.hooks == []

    def test_bootstrap_with_hooks(self) -> None:
        """Bootstrap with hooks."""
        config = BootstrapConfig(
            hooks=[
                BootstrapHook(name="Setup", run="echo setup"),
                BootstrapHook(name="Link", run="npm link", run_once=True),
            ]
        )
        assert len(config.hooks) == 2
        assert config.hooks[0].name == "Setup"
        assert config.hooks[1].run_once is True


class TestCleanConfig:
    """Tests for CleanConfig."""

    def test_default_patterns(self) -> None:
        """Default clean config has common patterns."""
        config = CleanConfig()
        assert "__pycache__" in config.patterns
        assert ".pytest_cache" in config.patterns
        assert "dist" in config.patterns

    def test_default_protected(self) -> None:
        """Default protected patterns."""
        config = CleanConfig()
        assert ".venv" in config.protected
        assert ".git" in config.protected

    def test_custom_patterns(self) -> None:
        """Custom clean patterns override defaults."""
        config = CleanConfig(patterns=["custom/*"])
        assert config.patterns == ["custom/*"]


class TestVersioningConfig:
    """Tests for VersioningConfig."""

    def test_default_versioning(self) -> None:
        """Default versioning configuration."""
        config = VersioningConfig()
        assert config.commit_format == CommitFormat.CONVENTIONAL
        assert "{name}" in config.tag_format
        assert "{version}" in config.tag_format
        assert config.changelog.enabled is True

    def test_custom_tag_format(self) -> None:
        """Custom tag format."""
        config = VersioningConfig(tag_format="v{version}")
        assert config.tag_format == "v{version}"


class TestChangelogConfig:
    """Tests for ChangelogConfig."""

    def test_default_changelog(self) -> None:
        """Default changelog configuration."""
        config = ChangelogConfig()
        assert config.enabled is True
        assert config.filename == "CHANGELOG.md"
        assert len(config.sections) > 0

    def test_default_sections(self) -> None:
        """Default sections include feat and fix."""
        config = ChangelogConfig()
        section_types = [s.type for s in config.sections]
        assert "feat" in section_types
        assert "fix" in section_types


class TestPublishConfig:
    """Tests for PublishConfig."""

    def test_default_registry(self) -> None:
        """Default registry is PyPI."""
        config = PublishConfig()
        assert "pypi.org" in config.registry

    def test_custom_registry(self) -> None:
        """Custom registry URL."""
        config = PublishConfig(registry="https://test.pypi.org/legacy/")
        assert "test.pypi.org" in config.registry


class TestCommandDefaults:
    """Tests for CommandDefaults."""

    def test_default_concurrency(self) -> None:
        """Default concurrency is 4."""
        config = CommandDefaults()
        assert config.concurrency == 4

    def test_concurrency_validation(self) -> None:
        """Concurrency must be between 1 and 32."""
        with pytest.raises(ValidationError):
            CommandDefaults(concurrency=0)
        with pytest.raises(ValidationError):
            CommandDefaults(concurrency=100)

    def test_valid_concurrency_range(self) -> None:
        """Valid concurrency values."""
        config = CommandDefaults(concurrency=8)
        assert config.concurrency == 8


class TestPyMelosConfig:
    """Tests for PymelosConfig."""

    def test_minimal_config(self) -> None:
        """Minimal valid configuration."""
        config = PyMelosConfig(name="test", packages=["packages/*"])
        assert config.name == "test"
        assert config.packages == ["packages/*"]

    def test_packages_required(self) -> None:
        """At least one package pattern is required."""
        with pytest.raises(ValidationError):
            PyMelosConfig(name="test", packages=[])

    def test_name_required(self) -> None:
        """Name is required."""
        with pytest.raises(ValidationError):
            PyMelosConfig(packages=["packages/*"])

    def test_script_normalization_string(self) -> None:
        """String scripts are converted to ScriptConfig."""
        config = PyMelosConfig(
            name="test",
            packages=["packages/*"],
            scripts={"test": "pytest"},
        )
        script = config.get_script("test")
        assert script is not None
        assert script.run == "pytest"

    def test_script_normalization_dict(self) -> None:
        """Dict scripts are converted to ScriptConfig."""
        config = PyMelosConfig(
            name="test",
            packages=["packages/*"],
            scripts={
                "test": {"run": "pytest -v", "fail_fast": True},
            },
        )
        script = config.get_script("test")
        assert script is not None
        assert script.run == "pytest -v"
        assert script.fail_fast is True

    def test_get_script_not_found(self) -> None:
        """get_script returns None for unknown script."""
        config = PyMelosConfig(name="test", packages=["packages/*"])
        assert config.get_script("nonexistent") is None

    def test_script_names(self) -> None:
        """script_names returns all script names."""
        config = PyMelosConfig(
            name="test",
            packages=["packages/*"],
            scripts={
                "test": "pytest",
                "lint": "ruff check",
            },
        )
        assert set(config.script_names) == {"test", "lint"}

    def test_full_config(self) -> None:
        """Full configuration with all options."""
        config = PyMelosConfig(
            name="my-workspace",
            packages=["packages/*", "libs/*"],
            ignore=["*-deprecated"],
            scripts={"test": "pytest"},
            command_defaults=CommandDefaults(concurrency=8),
            clean=CleanConfig(patterns=["*.tmp"]),
            versioning=VersioningConfig(tag_format="v{version}"),
            env={"CI": "true"},
        )
        assert config.name == "my-workspace"
        assert len(config.packages) == 2
        assert config.ignore == ["*-deprecated"]
        assert config.command_defaults.concurrency == 8
        assert config.clean.patterns == ["*.tmp"]
        assert config.versioning.tag_format == "v{version}"
        assert config.env == {"CI": "true"}

    def test_defaults_are_populated(self) -> None:
        """Default values are populated for optional fields."""
        config = PyMelosConfig(name="test", packages=["packages/*"])
        assert config.ignore == []
        assert config.scripts == {}
        assert config.env == {}
        assert config.command_defaults.concurrency == 4
        assert config.clean.patterns is not None
        assert config.versioning.commit_format == CommitFormat.CONVENTIONAL
