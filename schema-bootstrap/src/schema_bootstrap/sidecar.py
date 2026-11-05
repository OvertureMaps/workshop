"""Read column meanings from metadata shipped beside the data.

Two encodings are read, because between them they cover most published government GIS:

* **ISO 19110** feature catalogue (`<file>.shp.ea.iso.xml`), the `gfc:` namespace. Carries
  a definition per attribute and, for coded attributes, the declared domain as
  label/definition pairs.
* **FGDC CSDGM** (`<file>.shp.xml`), the older US standard. Its Entity and Attribute
  section carries the same two things under different element names.

A declared domain beats a `DISTINCT` pass: it is versioned with the extract, needs no
network, and is *wider* than the extract, so it does not mistake "absent here" for
"illegal". What no sidecar supplies is why the column exists -- that remains a person's
job, which is the point of the TODOs `render` leaves behind.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from xml.etree import ElementTree

from .column import Column

#: Names a metadata document uses for the geometry attribute. The reader names the
#: column after the file (`geom`, `SHAPE`, `wkb_geometry`, ...), and the two rarely
#: agree -- FGDC calls it SHAPE while DuckDB's ST_Read calls it geom, so the geometry
#: description is otherwise lost to a name mismatch rather than to absence.
GEOMETRY_ALIASES = ("SHAPE", "GEOMETRY", "GEOM", "THE_GEOM", "WKB_GEOMETRY", "SHAPE_")

_ISO_NS = {
    "gfc": "http://www.isotc211.org/2005/gfc",
    "gco": "http://www.isotc211.org/2005/gco",
}


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def candidate_paths(data_path: str | Path) -> list[Path]:
    """Where a sidecar for this data file would live, most specific first."""
    p = Path(data_path)
    return [
        Path(f"{p}.ea.iso.xml"),  # ISO 19110 feature catalogue (TIGER)
        p.with_suffix(".ea.iso.xml"),
        Path(f"{p}.xml"),  # FGDC CSDGM, or ISO alongside
        p.with_suffix(".xml"),
        p.with_suffix(".shp.xml"),
    ]


def _read_iso_19110(root: ElementTree.Element) -> dict[str, tuple[str, dict[str, str]]]:
    out: dict[str, tuple[str, dict[str, str]]] = {}
    for attr in root.iterfind(".//gfc:FC_FeatureAttribute", _ISO_NS):
        name = _clean(attr.findtext("gfc:memberName/gco:LocalName", None, _ISO_NS))
        if not name:
            continue
        definition = _clean(attr.findtext("gfc:definition/gco:CharacterString", None, _ISO_NS))
        domain: dict[str, str] = {}
        for listed in attr.iterfind("gfc:listedValue/gfc:FC_ListedValue", _ISO_NS):
            # gfc 1.1 gives FC_ListedValue both `label` and `code`. TIGER populates only
            # `label`; other producers use `code`. Take whichever is there.
            label = _clean(
                listed.findtext("gfc:label/gco:CharacterString", None, _ISO_NS)
                or listed.findtext("gfc:code/gco:CharacterString", None, _ISO_NS)
            )
            meaning = _clean(listed.findtext("gfc:definition/gco:CharacterString", None, _ISO_NS))
            # A listed value with no label is a prose citation of an external register
            # (TIGER does this for FIPS and GNIS), not an enumerable value.
            if label and meaning:
                domain[label] = meaning
        out[name] = (definition, domain)
    return out


def _read_fgdc(root: ElementTree.Element) -> dict[str, tuple[str, dict[str, str]]]:
    out: dict[str, tuple[str, dict[str, str]]] = {}
    for attr in root.iterfind(".//detailed/attr"):
        name = _clean(attr.findtext("attrlabl"))
        if not name:
            continue
        definition = _clean(attr.findtext("attrdef"))
        domain: dict[str, str] = {}
        for edom in attr.iterfind(".//edom"):
            label = _clean(edom.findtext("edomv"))
            meaning = _clean(edom.findtext("edomvd"))
            if label and meaning:
                domain[label] = meaning
        out[name] = (definition, domain)
    return out


@dataclass
class SidecarResult:
    """What a sidecar supplied, and what it offered that nothing claimed.

    `unmatched` is the load-bearing field. A metadata attribute whose name matches no
    column is dropped, and a dropped attribute is indistinguishable from an absent one
    unless it is reported: the model still generates, still imports, and is merely
    emptier. DBF truncates names to ten characters, publishers rename between metadata
    and data, and the geometry attribute is named differently by almost everyone.
    """

    path: Path | None = None
    matched: int = 0
    unmatched: list[str] = dc_field(default_factory=list)

    def __bool__(self) -> bool:
        return self.path is not None


def apply_sidecar(columns: list[Column], data_path: str | Path) -> SidecarResult:
    """Attach descriptions and declared domains, reporting what could not be matched."""
    for path in candidate_paths(data_path):
        if not path.exists():
            continue
        try:
            root = ElementTree.parse(path).getroot()
        except ElementTree.ParseError:
            continue
        found = _read_iso_19110(root) or _read_fgdc(root)
        if not found:
            continue
        by_name = {c.name: c for c in columns}
        result = SidecarResult(path=path)
        for name, (definition, domain) in found.items():
            column = by_name.get(name) or _geometry_match(name, columns)
            if column is None:
                result.unmatched.append(name)
                continue
            result.matched += 1
            if definition and not column.description:
                column.description = definition
            if domain:
                column.domain = domain
        return result
    return SidecarResult()


def _geometry_match(name: str, columns: list[Column]) -> Column | None:
    """Match a metadata attribute naming the geometry to whatever the reader called it."""
    if name.upper() not in GEOMETRY_ALIASES:
        return None
    geometries = [c for c in columns if c.is_geometry]
    return geometries[0] if len(geometries) == 1 else None


def resolve_meanings(columns: list[Column]) -> None:
    """Fill `meanings` for observed values, preferring the declared domain."""
    for column in columns:
        if not column.observed_values or not column.domain:
            continue
        for value in column.observed_values:
            if value in column.domain:
                column.meanings.setdefault(value, column.domain[value])
