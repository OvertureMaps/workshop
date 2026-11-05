"""Read a data file's shape, using DuckDB as the reader for every format.

Shapefiles go through `ST_Read`, which types the geometry column explicitly. Parquet
goes through the file directly, where a geometry column written as WKB is indistinguishable
from any other blob -- see `GEOMETRY_IN_BLOB_NOTE`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb

from .column import Column

#: GDAL synthesizes this when reading OGR sources; it is not a column in the data.
SYNTHETIC_COLUMNS = frozenset({"OGC_FID"})

#: A column is proposed as an enum when its distinct count is at or under both bounds.
ENUM_MAX_RATIO = 0.1
ENUM_MAX_VALUES = 60

GEOMETRY_IN_BLOB_NOTE = (
    "stored as a blob: if this is WKB, the type alone cannot say so. "
    "Check the file's GeoParquet 'geo' metadata."
)

_SCALARS = {
    "BIGINT": "int64",
    "INTEGER": "int32",
    "SMALLINT": "int16",
    "TINYINT": "int8",
    "UBIGINT": "uint64",
    "UINTEGER": "uint32",
    "USMALLINT": "uint16",
    "UTINYINT": "uint8",
    "DOUBLE": "float64",
    "FLOAT": "float32",
    "REAL": "float32",
    "VARCHAR": "str",
    "BOOLEAN": "bool",
    "DATE": "date",
    "BLOB": "bytes",
}

#: Types that come from `overture.schema.system.numeric` rather than builtins.
NUMERIC_TYPES = frozenset(
    {"int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "float32", "float64"}
)

_GEOMETRY_RE = re.compile(r"^GEOMETRY\s*\(", re.IGNORECASE)
_EPSG_RE = re.compile(r"^epsg\s*:\s*(\d+)$", re.IGNORECASE)


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    return con


def source_expr(path: str | Path) -> str:
    """How DuckDB should address this file."""
    p = str(path)
    return f"ST_Read('{p}')" if p.lower().endswith((".shp", ".geojson", ".gpkg")) else f"'{p}'"


def srid_from_geometry(source_type: str) -> tuple[int | None, list[str]]:
    """Recover an SRID from a `GEOMETRY(...)` type string.

    Two forms occur: `'epsg:4269'`, which DuckDB writes when reading a shapefile, and an
    entire embedded PROJJSON document, which it writes into its own Parquet output. The
    second is why this is a parser rather than a regex over the whole type string.
    """
    if "(" not in source_type:
        return None, []
    arg = source_type[source_type.index("(") + 1 : source_type.rindex(")")].strip().strip("'\"")
    if not arg:
        return None, []
    if m := _EPSG_RE.match(arg):
        return int(m.group(1)), []
    if arg.lstrip().startswith("{"):
        try:
            doc = json.loads(arg)
        except json.JSONDecodeError:
            return None, ["geometry CRS argument looks like JSON but does not parse"]
        code = (doc.get("id") or {}).get("code")
        if isinstance(code, int):
            return code, []
        if isinstance(code, str) and code.isdigit():
            return int(code), []
        return None, ["embedded PROJJSON carries no id.code"]
    if arg.isdigit():
        return int(arg), []
    return None, [f"unrecognized CRS argument {arg[:40]!r}"]


def describe(path: str | Path) -> list[Column]:
    """One `Column` per column in the file, typed but not yet explained."""
    con = _connect()
    rows = con.execute(f"DESCRIBE SELECT * FROM {source_expr(path)}").fetchall()
    columns: list[Column] = []
    for name, source_type, *_ in rows:
        if name in SYNTHETIC_COLUMNS:
            continue
        column = Column(name=name, source_type=source_type)
        if _GEOMETRY_RE.match(source_type):
            column.is_geometry = True
            column.py_type = "Geometry"
            column.srid, column.notes = srid_from_geometry(source_type)
        elif source_type.upper() == "BLOB":
            column.py_type = "bytes"
            column.notes.append(GEOMETRY_IN_BLOB_NOTE)
        else:
            column.py_type = _SCALARS.get(source_type.upper(), "str")
            if source_type.upper() not in _SCALARS:
                column.notes.append(f"unmapped source type {source_type!r}; defaulted to str")
        columns.append(column)
    return columns


def observe_values(path: str | Path, columns: list[Column]) -> None:
    """Fill in `observed_values` for columns whose distinct count reads as a vocabulary.

    This finds the values *present*, which is a lower bound on the values *legal*. A
    declared domain from `sidecar` is the wider and better source where one exists.
    """
    con = _connect()
    src = source_expr(path)
    (nrows,) = con.execute(f"SELECT count(*) FROM {src}").fetchone() or (0,)
    if not nrows:
        return
    ceiling = min(ENUM_MAX_VALUES, max(1, int(nrows * ENUM_MAX_RATIO)))
    for column in columns:
        if column.is_geometry or column.py_type not in ("str", "int32", "int64"):
            continue
        (approx,) = con.execute(
            f'SELECT approx_count_distinct("{column.name}") FROM {src}'
        ).fetchone() or (0,)
        if approx > ceiling:
            continue
        rows = con.execute(
            f'SELECT DISTINCT "{column.name}" FROM {src} '
            f'WHERE "{column.name}" IS NOT NULL ORDER BY 1'
        ).fetchall()
        if len(rows) <= ceiling:
            column.observed_values = [str(r[0]) for r in rows]
