"""Tag this package's models so the tools can select them with `--tag my_schema`."""

from collections.abc import Iterable

from pydantic import BaseModel

from overture.schema.system.discovery import ModelKey


def my_schema_provider(
    types: Iterable[type[BaseModel]], key: ModelKey, tags: set[str]
) -> set[str]:
    """Add `my_schema` to every model registered from this package."""
    if key.entry_point.startswith("my_schema:"):
        tags.add("my_schema")
    return tags
