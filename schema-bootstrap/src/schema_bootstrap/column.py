"""The shared vocabulary: what every stage of the pipeline knows about a column.

`introspect` fills in what the data says, `sidecar` fills in what the metadata says,
and `render` writes it out. They agree on nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Column:
    """One column, as progressively understood.

    `name`/`source_type` come from the data. `description`/`domain` come from metadata
    beside it. `observed_values` comes from counting. Everything else is derived.
    """

    name: str
    source_type: str

    py_type: str = "str"
    is_geometry: bool = False
    srid: int | None = None

    #: Distinct values present in THIS extract, when few enough to be a vocabulary.
    observed_values: list[str] | None = None

    #: Values the data's own metadata declares legal. Wider than `observed_values`.
    domain: dict[str, str] | None = None

    #: Meanings resolved for `observed_values`, from the domain or a fallback authority.
    meanings: dict[str, str] = field(default_factory=dict)

    description: str | None = None
    authority_url: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def undeclared_values(self) -> list[str]:
        """Values in the data that the declared domain does not cover.

        Not an error. A code can be real, in use, and absent from every authority --
        TIGER's `LSAD` 35 ("metro township") is missing from both the Census code list
        and the shipped feature catalogue, and appears five times in Utah.
        """
        if not self.observed_values or not self.domain:
            return []
        return [v for v in self.observed_values if v not in self.domain]

    @property
    def unobserved_values(self) -> list[str]:
        """Declared values this extract happens not to contain."""
        if not self.domain:
            return []
        observed = set(self.observed_values or ())
        return [v for v in self.domain if v not in observed]

    @property
    def is_enum(self) -> bool:
        return bool(self.observed_values)
