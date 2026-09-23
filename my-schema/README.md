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

## Model your data

1. Write a class in `src/my_schema/models.py` that subclasses `Feature`.
2. Re-export it from `src/my_schema/__init__.py`.
3. Register it in `pyproject.toml` under `[project.entry-points."overture.models"]`.
4. Run `uv sync --all-packages`, then `overture-schema list-types --tag my_schema` to
   check it appears. (`--all-packages` keeps the workshop's other packages; a bare
   `uv sync` in this directory removes them.)

Edits to an existing model take effect immediately; only a new entry point needs `uv sync --all-packages`.
