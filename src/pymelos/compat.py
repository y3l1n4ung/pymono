"""Compatibility layer for Python version differences."""

from __future__ import annotations

import sys

# tomllib is only available in Python 3.11+
# Use tomli for Python 3.10
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

__all__ = ["tomllib"]
