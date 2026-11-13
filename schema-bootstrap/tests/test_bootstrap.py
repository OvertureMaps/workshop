"""End-to-end and unit tests, against a real TIGER/Line extract.

The fixture is 88 Utah places with envelope geometry, carrying its original ISO 19110
feature catalogue. It is chosen because it exercises the three cases that matter: a
declared domain wider than the extract, a value in the data that no authority declares,
and a column whose whole vocabulary is one value only because of how the file was cut.
"""

from __future__ import annotations

import sys
import types
from enum import Enum
from pathlib import Path
from typing import Any

import duckdb
import pytest

from schema_bootstrap import bootstrap, inspect_source
from schema_bootstrap.column import Column
from schema_bootstrap.introspect import srid_from_geometry
from schema_bootstrap.render import enum_class_name, field_name, member_name
from schema_bootstrap.sidecar import SidecarResult

FIXTURE = Path(__file__).parent / "fixtures" / "utah_places.shp"


@pytest.fixture(scope="module")
def inspected() -> tuple[list[Column], SidecarResult]:
    return inspect_source(FIXTURE)


@pytest.fixture(scope="module")
def columns(inspected: tuple[list[Column], SidecarResult]) -> dict[str, Column]:
    return {c.name: c for c in inspected[0]}


def test_sidecar_is_found(inspected: tuple[list[Column], SidecarResult]) -> None:
    sidecar = inspected[1]
    assert sidecar.path is not None
    assert sidecar.path.name.endswith(".ea.iso.xml")


def test_unmatched_metadata_attributes_are_reported(
    inspected: tuple[list[Column], SidecarResult],
) -> None:
    """A described attribute matching no column must not vanish.

    TIGER's own catalogue documents PCINECTA -- a New England indicator -- which this
    shapefile does not carry. Dropping it silently is indistinguishable from the
    metadata never having mentioned it, and that is the failure this reports.
    """
    assert inspected[1].unmatched == ["PCINECTA"]
    assert inspected[1].matched == 16


def test_synthetic_column_is_dropped(columns: dict[str, Column]) -> None:
    assert "OGC_FID" not in columns


def test_geometry_is_typed_and_carries_its_srid(columns: dict[str, Column]) -> None:
    geom = columns["geom"]
    assert geom.is_geometry
    assert geom.py_type == "Geometry"
    assert geom.srid == 4269


def test_sidecar_supplies_descriptions(columns: dict[str, Column]) -> None:
    # Every non-geometry column in TIGER's catalogue is defined.
    undescribed = [c.name for c in columns.values() if not c.is_geometry and not c.description]
    assert undescribed == []
    assert "Federal Information Processing" in (columns["STATEFP"].description or "")


def test_declared_domain_is_wider_than_the_extract(columns: dict[str, Column]) -> None:
    """The point of preferring a sidecar: it knows values this file does not contain."""
    lsad = columns["LSAD"]
    assert lsad.domain is not None
    assert len(lsad.domain) == 14
    assert lsad.observed_values is not None
    assert len(lsad.observed_values) < len(lsad.domain)
    assert lsad.unobserved_values, "a wider domain must report what the extract lacks"
    assert lsad.meanings["25"] == "city (suffix)"


def test_undeclared_value_is_surfaced_not_swallowed(columns: dict[str, Column]) -> None:
    """LSAD 35 is real, in use, and absent from every authority we can consult."""
    assert columns["LSAD"].undeclared_values == ["35"]
    assert "35" not in columns["LSAD"].meanings


def test_single_value_column_is_still_only_a_lower_bound(columns: dict[str, Column]) -> None:
    """STATEFP looks like a one-value enum only because the extract is one state."""
    statefp = columns["STATEFP"]
    assert statefp.observed_values == ["49"]
    # TIGER cites an external register for STATEFP rather than enumerating it, so there
    # is no declared domain -- which is exactly when the emitted warning must appear.
    assert statefp.domain is None


@pytest.mark.parametrize(
    ("type_string", "expected"),
    [
        ("GEOMETRY('EPSG:4269')", 4269),
        ("geometry('epsg:3857')", 3857),
        ('GEOMETRY(\'{"id":{"authority":"EPSG","code":4326}}\')', 4326),
        ("GEOMETRY()", None),
        ("GEOMETRY('NAD83')", None),
    ],
)
def test_srid_recovery(type_string: str, expected: int | None) -> None:
    assert srid_from_geometry(type_string)[0] == expected


def test_srid_failure_is_reported_not_silent() -> None:
    srid, notes = srid_from_geometry("GEOMETRY('NAD83')")
    assert srid is None
    assert notes, "an unrecoverable CRS must leave a note"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("25", "V_25"), ("G4110", "G4110"), ("city and borough", "CITY_AND_BOROUGH"), ("", "UNNAMED")],
)
def test_member_name(value: str, expected: str) -> None:
    assert member_name(value) == expected


def test_enum_class_name() -> None:
    assert enum_class_name("CLASSFP") == "Classfp"
    assert enum_class_name("place_type") == "PlaceType"


class TestRenderedModel:
    @pytest.fixture(scope="class")
    @classmethod
    def source(cls) -> str:
        return bootstrap(FIXTURE, class_name="UtahPlace")

    def test_subclasses_feature_not_overture_generics(self, source: str) -> None:
        """Third-party models subclass Feature; the theme/type generics are Overture's own."""
        assert "from overture.schema.system.feature import Feature" in source
        assert "class UtahPlace(Feature):" in source
        assert "overture.schema.common" not in source

    def test_imports_overture_system_types(self, source: str) -> None:
        assert "from overture.schema.system.geometric import (" in source
        assert "from overture.schema.system.numeric import (" in source
        assert "    int64," in source
        # No locally redeclared shims.
        assert "class Geometry" not in source
        assert "NewType" not in source

    def test_uses_declared_domain_for_enum_members(self, source: str) -> None:
        # 14 declared LSAD values, not the 4 this extract happens to contain.
        assert '"city (suffix)"' in source
        assert '("21", "borough (suffix)")' in source, (
            "a declared-but-unobserved value belongs in the enum"
        )

    def test_long_definitions_are_split_not_truncated(self, source: str) -> None:
        """A sourced definition is the reason to read the file; never shorten it to fit."""
        assert max(len(line) for line in source.splitlines()) <= 100
        assert "treated as independent of any county subdivision" in source

    def test_enums_are_documented_enums(self, source: str) -> None:
        """Meanings belong in the member, where codegen can read them, not in a comment."""
        assert "from overture.schema.system.doc import DocumentedEnum" in source
        assert "(str, DocumentedEnum):" in source
        assert "(str, Enum):" not in source

    def test_undeclared_value_is_marked(self, source: str) -> None:
        assert '"35"' in source
        assert "occur in the data and are NOT declared" in source

    def test_undocumented_member_still_carries_placeholder_documentation(self, source: str) -> None:
        """Every member is the same shape, so filling one in is an edit not a restructure."""
        assert '("35", "TODO:' in source

    def test_unsourced_facts_are_todos(self, source: str) -> None:
        assert "TODO: what is a UtahPlace, and what does one row represent?" in source
        assert "TODO: confirm against the data" in source

    def test_sourced_facts_are_not_todos(self, source: str) -> None:
        assert "TODO: what is STATEFP" not in source
        assert "Current state Federal Information Processing Series (FIPS) code" in source

    def test_is_syntactically_valid_python(self, source: str) -> None:
        compile(source, "<generated>", "exec")

    def test_source_rows_populate_the_model(self, source: str) -> None:
        """The model must read the file it was bootstrapped from.

        Validation passing proves nothing here: every field is optional and Feature ignores
        unknown keys, so a column the model cannot match is dropped without error. Assert
        that each value lands instead.
        """
        module = types.ModuleType("generated_utah_place")
        sys.modules[module.__name__] = module
        try:
            exec(compile(source, "<generated>", "exec"), module.__dict__)
        finally:
            del sys.modules[module.__name__]
        model = module.UtahPlace

        con = duckdb.connect()
        con.execute("LOAD spatial")
        result = con.execute(
            "SELECT * EXCLUDE (OGC_FID, geom), ST_AsText(geom) AS geometry "
            f"FROM ST_Read('{FIXTURE}')"
        )
        names = [d[0] for d in result.description]
        rows = [dict(zip(names, row, strict=True)) for row in result.fetchall()]
        assert rows

        def plain(value: Any) -> Any:
            return value.value if isinstance(value, Enum) else value

        for row in rows:
            instance = model.model_validate(row)
            landed = {
                name: plain(getattr(instance, field_name(name)))
                for name in names
                if name != "geometry"
            }
            assert landed == {name: row[name] for name in landed}

        salt_lake = model.model_validate(rows[0])
        assert salt_lake.name == "Salt Lake City"
        assert salt_lake.lsad.value == "25"


class TestSecondPublisher:
    """USFS Administrative Forests: FGDC CSDGM, not ISO 19110.

    A second publisher is the control on the first. TIGER turned out to be unusually
    well-documented, and it is also the only one of the two that ships ISO 19110 at all --
    `.shp.ea.iso.xml` is a Census convention, while the rest of federal GIS ships FGDC in
    `.shp.xml`. Reading only ISO would have covered one publisher.
    """

    FIXTURE = Path(__file__).parent / "fixtures" / "usfs_forests.shp"

    @pytest.fixture(scope="class")
    @classmethod
    def inspected(cls) -> tuple[list[Column], SidecarResult]:
        return inspect_source(TestSecondPublisher.FIXTURE)

    def test_fgdc_sidecar_is_read(self, inspected: tuple[list[Column], SidecarResult]) -> None:
        assert inspected[1].path is not None
        assert inspected[1].path.name.endswith(".shp.xml")

    def test_fgdc_unmatched_is_reported(
        self, inspected: tuple[list[Column], SidecarResult]
    ) -> None:
        """FID is documented by FGDC and dropped by us as a GDAL synthetic; say so."""
        assert inspected[1].unmatched == ["FID"]

    def test_fgdc_enumerated_domain_is_extracted(
        self, inspected: tuple[list[Column], SidecarResult]
    ) -> None:
        region = {c.name: c for c in inspected[0]}["REGION"]
        assert region.domain is not None
        assert len(region.domain) == 9

    def test_geometry_description_survives_the_name_mismatch(
        self, inspected: tuple[list[Column], SidecarResult]
    ) -> None:
        """FGDC calls it SHAPE; ST_Read calls it geom. Without aliasing this is lost."""
        geom = next(c for c in inspected[0] if c.is_geometry)
        assert geom.description == "Feature geometry."

    def test_undocumented_columns_are_reported_as_such(
        self, inspected: tuple[list[Column], SidecarResult]
    ) -> None:
        """Not every publisher fills the format in. Four of these are genuinely blank."""
        undescribed = {c.name for c in inspected[0] if not c.description}
        assert undescribed == {"ADMINFORES", "FORESTNUMB", "FORESTORGC", "SHAPE_LEN"}
