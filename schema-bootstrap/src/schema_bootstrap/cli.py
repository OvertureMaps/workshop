"""Command-line interface for schema-bootstrap."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bootstrap import bootstrap, inspect_source
from .tag_provider import check_package, render_entry_points, render_tag_provider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="schema-bootstrap",
        description=(
            "Bootstrap an Overture-convention Pydantic model from a data file. "
            "Proposes; never decides -- everything it could not source is a TODO."
        ),
    )
    parser.add_argument("source", type=Path, help="Shapefile, Parquet, GeoPackage, or GeoJSON")
    parser.add_argument("--class-name", help="Model class to emit, e.g. TigerPlace")
    parser.add_argument("-o", "--output", type=Path, help="Write here instead of stdout")
    parser.add_argument(
        "--tag-provider",
        metavar="PACKAGE",
        help=(
            "Also write tags.py beside --output, tagging models from PACKAGE so the tools "
            "select them with --tag PACKAGE, and print the pyproject.toml entry points"
        ),
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Describe what was found and where it came from, instead of emitting a model",
    )
    args = parser.parse_args(argv)

    if not args.source.exists():
        parser.error(f"no such file: {args.source}")

    if args.report:
        columns, sidecar = inspect_source(args.source)
        print(f"source:  {args.source}")
        print(f"sidecar: {sidecar.path or 'none found'}")
        if sidecar.path is not None:
            print(
                f"         {sidecar.matched} attribute(s) matched, "
                f"{len(sidecar.unmatched)} unmatched"
            )
            if sidecar.unmatched:
                print(
                    f"         UNMATCHED (described in metadata, applied to nothing): "
                    f"{', '.join(sorted(sidecar.unmatched))}"
                )
        print(f"columns: {len(columns)}")
        for column in columns:
            bits = [column.py_type]
            if column.is_geometry and column.srid:
                bits.append(f"EPSG:{column.srid}")
            if column.domain:
                bits.append(f"domain={len(column.domain)}")
            if column.observed_values:
                bits.append(f"observed={len(column.observed_values)}")
            if column.undeclared_values:
                bits.append(f"UNDECLARED={','.join(column.undeclared_values)}")
            if not column.description:
                bits.append("no-description")
            print(f"  {column.name:<12} {' '.join(bits)}")
        return 0

    if not args.class_name:
        parser.error("required unless --report: --class-name")

    tags_path = None
    if args.tag_provider:
        if not args.output:
            parser.error("--tag-provider writes tags.py beside the model; it needs --output")
        if problem := check_package(args.tag_provider):
            parser.error(f"--tag-provider: {problem}")
        if not args.output.stem.isidentifier():
            parser.error(f"--output: {args.output.stem!r} is not an importable module name")
        tags_path = args.output.parent / "tags.py"
        if tags_path.exists():
            parser.error(f"{tags_path} exists; not overwriting a provider that may be edited")

    source = bootstrap(args.source, class_name=args.class_name)
    if args.output:
        args.output.write_text(source)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(source)

    if tags_path is not None:
        tags_path.write_text(render_tag_provider(args.tag_provider))
        print(f"wrote {tags_path}; add to pyproject.toml:", file=sys.stderr)
        sys.stdout.write(render_entry_points(args.tag_provider, args.output.stem, args.class_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
