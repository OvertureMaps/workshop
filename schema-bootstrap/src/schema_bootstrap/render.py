"""Emit Pydantic source in Overture's own idiom.

Models subclass `overture.schema.system.feature.Feature`, the base for third-party
models. The theme/type generics in `overture.schema.common` are Overture's contract with
its own themes; a model from elsewhere is selected through a tag provider instead.

Imports `Geometry`/`GeometryType`/`GeometryTypeConstraint` from
`overture.schema.system.geometric` and the width-typed numerics from
`overture.schema.system.numeric` rather than redeclaring shims, so the output is a model
someone can extend rather than a lookalike.

Proposes; never decides. Anything the pipeline could not source is a visible TODO.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import textwrap

from .column import Column
from .introspect import NUMERIC_TYPES

_DEFAULT_GEOMETRY_TYPES = ("POLYGON", "MULTI_POLYGON")


def member_name(value: str) -> str:
    """A Python enum member name for an arbitrary code value."""
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_").upper()
    if not cleaned:
        return "UNNAMED"
    return f"V_{cleaned}" if cleaned[0].isdigit() else cleaned


def enum_class_name(column_name: str) -> str:
    parts = [p for p in re.split(r"[^0-9A-Za-z]+", column_name.lower()) if p]
    return "".join(p.capitalize() for p in parts) or "Value"


def _imports(columns: list[Column]) -> list[str]:
    has_geometry = any(c.is_geometry for c in columns)
    numerics = sorted({c.py_type for c in columns if c.py_type in NUMERIC_TYPES})

    out = [
        "import textwrap",
        "from typing import Annotated",
        "",
        "from pydantic import Field",
        "",
        "from overture.schema.system.feature import Feature",
    ]
    if any(c.is_enum for c in columns):
        out.append("from overture.schema.system.doc import DocumentedEnum")
    if has_geometry:
        out += [
            "from overture.schema.system.geometric import (",
            "    Geometry,",
            "    GeometryType,",
            "    GeometryTypeConstraint,",
            ")",
        ]
    if numerics:
        out += ["from overture.schema.system.numeric import ("]
        out += [f"    {n}," for n in numerics]
        out += [")"]
    return out


def _enum_docstring(column: Column) -> list[str]:
    out = ['    """', f"    Values for {column.name}."]
    if column.description:
        out += ["", *(f"    {line}" for line in textwrap.wrap(column.description, 84))]

    if column.domain:
        out += [
            "",
            f"    The data's own metadata declares {len(column.domain)} legal value(s), of",
            f"    which {len(column.unobserved_values)} do not occur in this extract. Members",
            "    below are the declared domain, so this enum is not narrowed to what one file",
            "    happened to contain.",
        ]
    else:
        n = len(column.observed_values or ())
        out += [
            "",
            f"    WARNING: no declared domain was found, so these {n} value(s) are only what is",
            "    PRESENT IN THIS EXTRACT. That is a lower bound on the vocabulary, not the",
            "    vocabulary. Confirm against the authority before treating this as closed.",
        ]

    undeclared = column.undeclared_values
    if undeclared:
        out += [
            "",
            f"    TODO: {len(undeclared)} value(s) occur in the data and are NOT declared:",
            f"    {', '.join(repr(v) for v in undeclared)}. An undeclared code is not an invalid",
            "    one -- check a sibling column before assuming a defect in the data.",
        ]
    if column.authority_url:
        out += ["", f"    Authority: {column.authority_url}"]
    out.append('    """')
    return out


def _enum_members(column: Column) -> list[str]:
    """Members as `DocumentedEnum` pairs, so each value's meaning is data, not a comment.

    A member with no sourced meaning still gets one: the raw value, marked TODO. That is
    placeholder documentation rather than an invented fact -- it says only what the data
    already says -- and it keeps every member the same shape, so filling one in is an edit
    rather than a restructure.
    """
    # Prefer the declared domain; fall back to what was observed.
    values = list(column.domain) if column.domain else list(column.observed_values or ())
    for v in column.observed_values or ():
        if v not in values:
            values.append(v)

    out: list[str] = []
    for value in values:
        meaning = column.meanings.get(value) or (column.domain or {}).get(value)
        doc = meaning if meaning else f"TODO: {value!r} -- meaning not in any source consulted"
        # No trailing comma: ruff's magic-trailing-comma rule would explode every
        # member onto four lines, including the short ones. Emitted as one logical
        # expression, ruff collapses what fits and splits what does not.
        literal = " ".join(_string_literal(doc))
        out.append(f'    {member_name(value)} = ("{_escape(value)}", {literal})')
    return out


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _string_literal(text: str, width: int = 88) -> list[str]:
    """One or more `"..."` literals, implicitly concatenated when the text is long.

    ruff formats code; it does not break string literals, and truncating a sourced
    definition to fit a line would discard the only thing that made it worth reading.
    Splitting across adjacent literals keeps the whole text and lets ruff own the layout.
    """
    escaped = _escape(text)
    if len(escaped) <= width:
        return [f'"{escaped}"']
    pieces = textwrap.wrap(escaped, width, break_long_words=False, break_on_hyphens=False)
    return [f'"{piece} "' for piece in pieces[:-1]] + [f'"{pieces[-1]}"']


def field_name(column_name: str) -> str:
    """The Python attribute name for a column."""
    return column_name.lower()


def _field(column: Column, enum_names: dict[str, str]) -> list[str]:
    """One optional field, aliased to the column whenever the Python name differs.

    Without the alias the model still validates the source -- Feature ignores extra keys
    and every field defaults to None -- so `LSAD` would be dropped and `lsad` left empty
    with no error. The alias is also the name Overture's tools emit: JSON Schema, docs,
    and Spark all use it.
    """
    annotation = enum_names.get(column.name, column.py_type)
    name = field_name(column.name)
    out = [
        f"    {name}: Annotated[",
        f"        {annotation} | None,",
        "        Field(",
    ]
    if name != column.name:
        out.append(f'            alias="{_escape(column.name)}",')
    out.append('            description=textwrap.dedent("""')
    if column.description:
        out += [f"                {line}" for line in textwrap.wrap(column.description, 76)]
    else:
        out.append(f"                TODO: what is {column.name}, and why does it exist?")
    out += [f"                NOTE: {n}" for n in column.notes]
    out += ['            """).strip()', "        ),", "    ] = None"]
    return out


def render(
    columns: list[Column],
    *,
    class_name: str,
    source: str,
) -> str:
    enums = [c for c in columns if c.is_enum]
    enum_names = {c.name: enum_class_name(c.name) for c in enums}
    geometry = next((c for c in columns if c.is_geometry), None)

    out: list[str] = [
        '"""',
        *textwrap.wrap(f"Bootstrapped from {source}.", 94),
        "",
        "NOT FINISHED. Types and value vocabularies were read off the data and its metadata;",
        "meanings were taken from the metadata where it had them. Every TODO below is a",
        "judgment the sources could not make.",
        '"""',
        "",
        *_imports(columns),
        "",
        "",
    ]

    for column in enums:
        out.append(f"class {enum_names[column.name]}(str, DocumentedEnum):")
        out += _enum_docstring(column)
        out.append("")
        out += _enum_members(column)
        out += ["", ""]

    out += [
        f"class {class_name}(Feature):",
        '    """',
        f"    TODO: what is a {class_name}, and what does one row represent?",
        '    """',
        "",
    ]

    if geometry is not None:
        constraint = ", ".join(f"GeometryType.{g}" for g in _DEFAULT_GEOMETRY_TYPES)
        srid = f" Source SRID {geometry.srid}." if geometry.srid else ""
        description = geometry.description or "TODO: describe the geometry."
        out += [
            "    # Overture Feature",
            "",
            "    geometry: Annotated[",
            "        Geometry,",
            f"        GeometryTypeConstraint({constraint}),  # TODO: confirm against the data",
            "        Field(",
            f'            description="""{description}{srid}""",',
            "        ),",
            "    ]",
            "",
        ]

    out += ["    # Optional", ""]
    for column in columns:
        if column.is_geometry:
            continue
        out += _field(column, enum_names)
    return _format("\n".join(out) + "\n")


def _format(source: str) -> str:
    """Hand the generated module to ruff.

    Line length and import order are ruff's job, not something to hand-manage while
    building strings. Degrades to unformatted output when ruff is not on PATH -- the
    module is valid Python either way.
    """
    ruff = shutil.which("ruff")
    if ruff is None:
        return source
    try:
        result = subprocess.run(
            [ruff, "format", "--stdin-filename", "generated.py", "-"],
            input=source,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return source
    return result.stdout
