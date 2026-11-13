# my-schema

A starting point for modelling your own data with Overture's schema framework.
Codespaces installs it for you; edit `src/my_schema/models.py` in the editor and
run the commands below in the terminal.

## Try the example

```console
overture-schema list-types --tag my_schema
overture-schema validate my-schema/examples/good.json
overture-schema validate my-schema/examples/bad.json
overture-codegen generate --format markdown --tag my_schema --output-dir docs/
```

`--tag my_schema` selects your models. The tag comes from the tag provider in
`src/my_schema/tags.py`, which tags every model this package registers.

## Exercise: add a second model

Run these from the repository root. Paths are relative to it.

**1. Write the model.** Append to `my-schema/src/my_schema/models.py`:

```python
class RailCrossingRating(Feature):
    """A safety star rating for a level crossing, where a road meets a railway."""

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(description="Where the road crosses the railway."),
    ]
    stars: StarRating
```

Then re-export it from `my-schema/src/my_schema/__init__.py`:

```python
from my_schema.models import RailCrossingRating, RoadSafetyRating

__all__ = ["RailCrossingRating", "RoadSafetyRating"]
```

**2. Look for it.** The tools can't see it yet:

```console
$ overture-schema list-types --tag my_schema
road_safety_rating  feature  my_schema
```

They find models through entry points, and this one has none.

**3. Register it.** In `my-schema/pyproject.toml`, add a line under the existing one:

```toml
[project.entry-points."overture.models"]
road_safety_rating = "my_schema:RoadSafetyRating"
rail_crossing_rating = "my_schema:RailCrossingRating"
```

Run `list-types` again: still one model. The tools read entry points from what was
*installed*, not from `pyproject.toml`, and that record is written only at install
time. Re-sync:

```console
$ uv sync --all-packages
$ overture-schema list-types --tag my_schema
rail_crossing_rating  feature  my_schema
road_safety_rating    feature  my_schema
```

Edits to a model's code never need this step; only a new entry point does.

**4. Validate against the right model.** With two models, name the one you mean:

```console
$ overture-schema validate --type road_safety_rating my-schema/examples/motorway-without-speed-limit.json
```

This fails on the motorway rule. Leave out `--type` and the validator picks a model
for you. Here it picks `RailCrossingRating` and reports the geometry instead.

**5. Tag by mode, and mark a draft.** Replace `my-schema/src/my_schema/tags.py` with:

```python
"""Tag this package's models so the tools can select them with `--tag my_schema`."""

from collections.abc import Iterable

from pydantic import BaseModel

from overture.schema.system.discovery import ModelKey

# Entry-point name -> mode, and the models still in draft.
MODE = {"road_safety_rating": "road", "rail_crossing_rating": "rail"}
DRAFTS = {"rail_crossing_rating"}


def my_schema_provider(
    types: Iterable[type[BaseModel]], key: ModelKey, tags: set[str]
) -> set[str]:
    """Tag every model from this package `my_schema`, plus its mode and draft status."""
    if key.entry_point.startswith("my_schema:"):
        tags.add("my_schema")
        tags.add(f"my_schema:mode={MODE[key.name]}")
        if key.name in DRAFTS:
            tags.add("my_schema:draft")
    return tags
```

This is ordinary code, so no re-sync:

```console
$ overture-schema list-types --tag my_schema --group-by my_schema:mode
my_schema:mode=rail (1)
→ rail_crossing_rating  feature  my_schema  my_schema:draft  my_schema:mode=rail

my_schema:mode=road (1)
→ road_safety_rating    feature  my_schema  my_schema:mode=road

$ overture-schema list-types --tag my_schema --exclude my_schema:draft
road_safety_rating  feature  my_schema  my_schema:mode=road
```

**6. Publish only what's ready.** `--exclude` works on the docs too:

```console
$ overture-codegen generate --format markdown --tag my_schema --exclude my_schema:draft --output-dir docs/
```

`docs/my_schema/` has a page for `road_safety_rating` and none for the draft.

## Model your data

1. Write a class in `src/my_schema/models.py` that subclasses `Feature`.
2. Re-export it from `src/my_schema/__init__.py`.
3. Register it in `pyproject.toml` under `[project.entry-points."overture.models"]`.
4. Run `uv sync --all-packages`, then `overture-schema list-types --tag my_schema` to
   check it appears. (`--all-packages` keeps the workshop's other packages; a bare
   `uv sync` in this directory removes them.)

Edits to an existing model take effect immediately. Only a new entry point needs
`uv sync --all-packages`, as in the exercise above.
