# schema-bootstrap

Bootstrap an Overture-convention Pydantic model from a data file.

Writing a model for someone else's data from scratch is slow. schema-bootstrap writes the first
draft: fields, types, geometry, descriptions and enum domains, each taken from the data or the
metadata shipped with it. **Anything it cannot find a source for is left as a TODO** — a column
with no description, a code with no documented meaning — for you to fill in.

```console
$ schema-bootstrap places.shp --class-name UtahPlace -o model.py
```

## Where each part of the model comes from

| Source | Gives |
|---|---|
| The data, read with DuckDB (`ST_Read` for Shapefile, GeoPackage and GeoJSON; directly for Parquet) | column names, types, geometry type and SRID |
| A `DISTINCT` pass over each column | the values present, for columns with few enough to be a vocabulary |
| Metadata shipped beside the data: ISO 19110 (`.shp.ea.iso.xml`) or FGDC CSDGM (`.shp.xml`) | a description per column, and the **declared domain** (the legal values) of coded columns |

`OGC_FID`, which GDAL adds on read, is left out.

## Declared and observed values

`DISTINCT` reports the values present in one file, which can be fewer than the values the column
allows. The metadata's declared domain lists the values it allows. `--report` shows both:

```console
$ schema-bootstrap tests/fixtures/utah_places.shp --report
...
  STATEFP      str observed=1
...
  LSAD         str domain=14 observed=4 UNDECLARED=35
...
```

The generated model handles the three cases differently:

- **`LSAD` has a declared domain.** Its enum lists all 14 declared values, not only the 4 in this
  file.
- **`STATEFP` has none.** Its enum holds the one value observed (the file covers one state), and
  its docstring warns that the list is a lower bound to check against the authority.
- **`LSAD` 35 is in the data but not in the declared domain.** It becomes an enum member whose
  meaning is a TODO. 35 is *metro township*, a Utah municipal form created in 2015. Neither the
  shipped metadata nor the Census Bureau's published code list includes it; only the sibling
  column `NAMELSAD` ("Copperton metro township") gives the meaning.

## Registering the model with Overture's tools

The model subclasses `overture.schema.system.feature.Feature`. Overture's `theme`/`type`
generics are for Overture's own themes; a model from another package is found through a tag
provider instead. `--tag-provider` writes one (`tags.py`) beside the model and prints the
`pyproject.toml` entry points that register both:

```console
$ schema-bootstrap places.shp --class-name UtahPlace -o src/utah_schema/utah_places.py \
    --tag-provider utah_schema
[project.entry-points."overture.models"]
utah_place = "utah_schema.utah_places:UtahPlace"

[project.entry-points."overture.tag_providers"]
utah_schema = "utah_schema.tags:utah_schema_provider"
```

Add those to the package's `pyproject.toml` and run `uv sync --all-packages` from the repository
root; `--tag utah_schema` then selects the model. An existing `tags.py` is never overwritten.

## Modules

| Module | Role |
|---|---|
| `column.py` | `Column`, the record every stage reads and fills in |
| `introspect.py` | reads the data: types, geometry, distinct values |
| `sidecar.py` | reads the metadata: descriptions, declared domains |
| `render.py` | writes the Pydantic source in Overture's idiom |
| `tag_provider.py` | writes the tag provider and its entry points |
| `bootstrap.py` | runs the stages in order |

## Development

```console
uv run pytest && uv run mypy .
```

The fixture is 88 Utah places from U.S. Census Bureau TIGER/Line 2023
([`tl_2023_49_place.zip`](https://www2.census.gov/geo/tiger/TIGER2023/PLACE/tl_2023_49_place.zip)).
The rows still cover every coded value in the full file, and geometry is reduced to bounding boxes
to keep it small. `utah_places.shp.ea.iso.xml` is the archive's `tl_2023_49_place.shp.ea.iso.xml`,
unmodified. [docs/tiger-vocabulary.md](docs/tiger-vocabulary.md) documents what those coded columns
mean and where each meaning came from.
