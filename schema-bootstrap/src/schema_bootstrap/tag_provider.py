"""Emit the tag provider that lets Overture's tools select a generated model.

A `Feature` subclass carries no theme or type, so `--theme`/`--type` cannot find it; a
tag provider registered under `overture.tag_providers` tags it instead, and the tools
select it with `--tag <package>`. Shape follows the workshop's my-schema template:
`tags.py` holds the provider, and `pyproject.toml` registers it beside the model.
"""

from __future__ import annotations

import re

# Discovery drops these with a warning unless an Overture package sets them.
_RESERVED_TAGS = frozenset({"feature", "overture"})
_PACKAGE = re.compile(r"[a-z][a-z0-9_]*")


def check_package(package: str) -> str | None:
    """Why `package` cannot be both an import name and a tag, or None if it can."""
    if not _PACKAGE.fullmatch(package):
        return f"{package!r} must be lowercase letters, digits and underscores"
    if package in _RESERVED_TAGS:
        return f"{package!r} is a tag Overture reserves for its own packages"
    return None


def provider_name(package: str) -> str:
    return f"{package}_provider"


def render_tag_provider(package: str) -> str:
    return f'''"""Tag this package's models so the tools can select them with `--tag {package}`."""

from collections.abc import Iterable

from pydantic import BaseModel

from overture.schema.system.discovery import ModelKey


def {provider_name(package)}(
    types: Iterable[type[BaseModel]], key: ModelKey, tags: set[str]
) -> set[str]:
    """Add `{package}` to every model registered from this package."""
    module = key.entry_point.partition(":")[0]
    if module == "{package}" or module.startswith("{package}."):
        tags.add("{package}")
    return tags
'''


def render_entry_points(package: str, module: str, class_name: str) -> str:
    """The `pyproject.toml` tables that register the model and its tag provider."""
    model_key = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    return f"""\
[project.entry-points."overture.models"]
{model_key} = "{package}.{module}:{class_name}"

[project.entry-points."overture.tag_providers"]
{package} = "{package}.tags:{provider_name(package)}"
"""
