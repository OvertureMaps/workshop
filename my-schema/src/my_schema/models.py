"""An example model. Copy it, rename it, and make it describe your data."""

from datetime import date
from typing import Annotated, NewType

from pydantic import BaseModel, Field

from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.feature import Feature
from overture.schema.system.geometric import Geometry, GeometryType, GeometryTypeConstraint
from overture.schema.system.model_constraint import FieldEqCondition, no_extra_fields, require_if
from overture.schema.system.numeric import uint8, uint16

# A named type carries its description and constraints everywhere it is used.
StarRating = NewType(
    "StarRating",
    Annotated[uint8, Field(ge=1, le=5, description="Star rating from 1 (least safe) to 5 (safest).")],
)


# A coded column: list every legal value and what it means.
class RoadType(str, DocumentedEnum):
    """Kind of road that was rated."""

    MOTORWAY = ("motorway", "Divided highway with controlled access.")
    ARTERIAL = ("arterial", "Major road connecting districts.")
    LOCAL = ("local", "Street serving the properties along it.")


# A struct: a group of related fields.
@no_extra_fields
class Survey(BaseModel):
    """Who rated the road, and when."""

    assessor: str
    surveyed_on: date | None = None


# A rule across fields, written as data so the docs can state it.
# Avoid @field_validator and @model_validator: they run, but no tool can read them.
@no_extra_fields
@require_if(["speed_limit_kph"], FieldEqCondition("road_type", "motorway"))
class RoadSafetyRating(Feature):
    """A road-safety star rating for a stretch of road."""

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.LINE_STRING),
        Field(description="The rated stretch of road."),
    ]
    stars: StarRating
    road_type: Annotated[RoadType | None, Field(description="Kind of road that was rated.")] = None
    speed_limit_kph: Annotated[
        uint16 | None, Field(description="Posted speed limit, in kilometres per hour.")
    ] = None
    survey: Annotated[
        Survey | None, Field(description="The survey this rating came from.")
    ] = None
