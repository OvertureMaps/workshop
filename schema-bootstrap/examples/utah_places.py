"""
Bootstrapped from utah_places.shp (+ utah_places.shp.ea.iso.xml); 1 metadata attribute(s)
matched no column and were NOT applied: PCINECTA.

NOT FINISHED. Types and value vocabularies were read off the data and its metadata;
meanings were taken from the metadata where it had them. Every TODO below is a
judgment the sources could not make.
"""

import textwrap
from typing import Annotated

from pydantic import Field

from overture.schema.system.feature import Feature
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.geometric import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.numeric import (
    int64,
)


class Statefp(str, DocumentedEnum):
    """
    Values for STATEFP.

    Current state Federal Information Processing Series (FIPS) code

    WARNING: no declared domain was found, so these 1 value(s) are only what is
    PRESENT IN THIS EXTRACT. That is a lower bound on the vocabulary, not the
    vocabulary. Confirm against the authority before treating this as closed.
    """

    V_49 = ("49", "TODO: '49' -- meaning not in any source consulted")


class Lsad(str, DocumentedEnum):
    """
    Values for LSAD.

    Current legal/statistical area description code for place

    The data's own metadata declares 14 legal value(s), of
    which 11 do not occur in this extract. Members
    below are the declared domain, so this enum is not narrowed to what one file
    happened to contain.

    TODO: 1 value(s) occur in the data and are NOT declared:
    '35'. An undeclared code is not an invalid
    one -- check a sibling column before assuming a defect in the data.
    """

    V_00 = ("00", "Blank")
    V_21 = ("21", "borough (suffix)")
    V_25 = ("25", "city (suffix)")
    V_37 = ("37", "municipality (suffix)")
    V_43 = ("43", "town (suffix)")
    V_47 = ("47", "village (suffix)")
    V_53 = ("53", "city and borough (suffix)")
    V_55 = ("55", "comunidad (suffix)")
    V_57 = ("57", "census designated place (CDP) (suffix)")
    V_62 = ("62", "zona urbana (suffix)")
    CN = ("CN", "corporation (suffix)")
    MG = ("MG", "metropolitan government (suffix)")
    UC = ("UC", "urban county (suffix)")
    UG = ("UG", "unified government (suffix)")
    V_35 = ("35", "TODO: '35' -- meaning not in any source consulted")


class Classfp(str, DocumentedEnum):
    """
    Values for CLASSFP.

    Current Federal Information Processing Series (FIPS) class code

    The data's own metadata declares 10 legal value(s), of
    which 6 do not occur in this extract. Members
    below are the declared domain, so this enum is not narrowed to what one file
    happened to contain.
    """

    C1 = ("C1", "An active incorporated place that does not serve as a county subdivision")
    C2 = (
        "C2",
        "An active incorporated place that is legally coextensive with a county subdivision but "
        "treated as independent of any county subdivision",
    )
    C5 = (
        "C5",
        "An active incorporated place that is independent of any county subdivision and serves as "
        "a county subdivision equivalent",
    )
    C6 = (
        "C6",
        "An active incorporated place that is coextensive with or approximates an Alaska Native "
        "village statistical area",
    )
    C7 = ("C7", "An incorporated place that is independent of any county")
    C8 = (
        "C8",
        "The balance of a consolidated city excluding the separately incorporated place(s) within "
        "that consolidated government",
    )
    C9 = ("C9", "An inactive or nonfunctioning incorporated place")
    M2 = ("M2", "A military or other defense installation entirely within a place")
    U1 = ("U1", "A census designated place with an official federally recognized name")
    U2 = ("U2", "A census designated place without an official federally recognized name")


class Pcicbsa(str, DocumentedEnum):
    """
    Values for PCICBSA.

    Current metropolitan or micropolitan statistical area principal city indicator

    The data's own metadata declares 2 legal value(s), of
    which 0 do not occur in this extract. Members
    below are the declared domain, so this enum is not narrowed to what one file
    happened to contain.
    """

    N = ("N", "Geographic entity is not a principal city of a CBSA")
    Y = ("Y", "Geographic entity is a principal city of a CBSA")


class Mtfcc(str, DocumentedEnum):
    """
    Values for MTFCC.

    MAF/TIGER feature class code

    The data's own metadata declares 2 legal value(s), of
    which 0 do not occur in this extract. Members
    below are the declared domain, so this enum is not narrowed to what one file
    happened to contain.
    """

    G4110 = ("G4110", "Incorporated place")
    G4210 = ("G4210", "Census designated place")


class Funcstat(str, DocumentedEnum):
    """
    Values for FUNCSTAT.

    Current functional status

    The data's own metadata declares 6 legal value(s), of
    which 4 do not occur in this extract. Members
    below are the declared domain, so this enum is not narrowed to what one file
    happened to contain.
    """

    A = ("A", "Active government providing primary general-purpose functions")
    B = (
        "B",
        "Active government that is partially consolidated with another government but with "
        "separate officials providing primary general-purpose functions",
    )
    F = ("F", "Fictitious entity created to fill the Census Bureau geographic hierachy")
    I = (
        "I",
        "Inactive governemental unit that has the power to provide primary special-purpose "
        "functions",
    )
    N = ("N", "Nonfunctioning legal entity")
    S = ("S", "Statistical entity")


class UtahPlace(Feature):
    """
    TODO: what is a UtahPlace, and what does one row represent?
    """

    # Overture Feature

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(
            GeometryType.POLYGON, GeometryType.MULTI_POLYGON
        ),  # TODO: confirm against the data
        Field(
            description="""TODO: describe the geometry. Source SRID 4269.""",
        ),
    ]

    # Optional

    statefp: Annotated[
        Statefp | None,
        Field(
            alias="STATEFP",
            description=textwrap.dedent("""
                Current state Federal Information Processing Series (FIPS) code
            """).strip(),
        ),
    ] = None
    placefp: Annotated[
        str | None,
        Field(
            alias="PLACEFP",
            description=textwrap.dedent("""
                Current place Federal Information Processing Series (FIPS) code
            """).strip(),
        ),
    ] = None
    placens: Annotated[
        str | None,
        Field(
            alias="PLACENS",
            description=textwrap.dedent("""
                Current place GNIS code
            """).strip(),
        ),
    ] = None
    geoid: Annotated[
        str | None,
        Field(
            alias="GEOID",
            description=textwrap.dedent("""
                Place identifier; a concatenation of Current state FIPS code and place FIPS
                code
            """).strip(),
        ),
    ] = None
    geoidfq: Annotated[
        str | None,
        Field(
            alias="GEOIDFQ",
            description=textwrap.dedent("""
                Fully qualified place identifier; a concatenation of census survey summary
                level information with the place identifier. The GEOIDFQ attribute is
                calculated to facilitate joining census spatial data to census survey
                summary files.
            """).strip(),
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(
            alias="NAME",
            description=textwrap.dedent("""
                Current place name
            """).strip(),
        ),
    ] = None
    namelsad: Annotated[
        str | None,
        Field(
            alias="NAMELSAD",
            description=textwrap.dedent("""
                Current name and the translated legal/statistical area description for place
            """).strip(),
        ),
    ] = None
    lsad: Annotated[
        Lsad | None,
        Field(
            alias="LSAD",
            description=textwrap.dedent("""
                Current legal/statistical area description code for place
            """).strip(),
        ),
    ] = None
    classfp: Annotated[
        Classfp | None,
        Field(
            alias="CLASSFP",
            description=textwrap.dedent("""
                Current Federal Information Processing Series (FIPS) class code
            """).strip(),
        ),
    ] = None
    pcicbsa: Annotated[
        Pcicbsa | None,
        Field(
            alias="PCICBSA",
            description=textwrap.dedent("""
                Current metropolitan or micropolitan statistical area principal city
                indicator
            """).strip(),
        ),
    ] = None
    mtfcc: Annotated[
        Mtfcc | None,
        Field(
            alias="MTFCC",
            description=textwrap.dedent("""
                MAF/TIGER feature class code
            """).strip(),
        ),
    ] = None
    funcstat: Annotated[
        Funcstat | None,
        Field(
            alias="FUNCSTAT",
            description=textwrap.dedent("""
                Current functional status
            """).strip(),
        ),
    ] = None
    aland: Annotated[
        int64 | None,
        Field(
            alias="ALAND",
            description=textwrap.dedent("""
                Current land area (square meters)
            """).strip(),
        ),
    ] = None
    awater: Annotated[
        int64 | None,
        Field(
            alias="AWATER",
            description=textwrap.dedent("""
                Current water area (square meters)
            """).strip(),
        ),
    ] = None
    intptlat: Annotated[
        str | None,
        Field(
            alias="INTPTLAT",
            description=textwrap.dedent("""
                Current latitude of the internal point
            """).strip(),
        ),
    ] = None
    intptlon: Annotated[
        str | None,
        Field(
            alias="INTPTLON",
            description=textwrap.dedent("""
                Current longitude of the internal point
            """).strip(),
        ),
    ] = None
