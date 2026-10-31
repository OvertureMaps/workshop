"""The pipeline: read the data, read what ships beside it, emit a model."""

from __future__ import annotations

from pathlib import Path

from .column import Column
from .introspect import describe, observe_values
from .render import render
from .sidecar import SidecarResult, apply_sidecar, resolve_meanings


def inspect_source(path: str | Path) -> tuple[list[Column], SidecarResult]:
    """Everything known about a file's columns, and what the sidecar did and did not supply."""
    columns = describe(path)
    observe_values(path, columns)
    sidecar = apply_sidecar(columns, path)
    resolve_meanings(columns)
    return columns, sidecar


def bootstrap(
    path: str | Path,
    *,
    class_name: str,
) -> str:
    columns, sidecar = inspect_source(path)
    source = Path(path).name
    if sidecar.path is not None:
        source = f"{source} (+ {sidecar.path.name})"
        if sidecar.unmatched:
            source += (
                f"; {len(sidecar.unmatched)} metadata attribute(s) matched no column "
                f"and were NOT applied: {', '.join(sorted(sidecar.unmatched))}"
            )
    return render(columns, class_name=class_name, source=source)
