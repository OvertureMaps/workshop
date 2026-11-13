"""The tag provider: how a `Feature` subclass gets found once it has no theme or type.

What is under test is the emitted provider's matching rule, which is the one place the
output departs from the workshop template: a generated model is registered as
`package.module:Class`, not re-exported from the package root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from overture.schema.system.discovery import ModelKey

from schema_bootstrap.cli import main
from schema_bootstrap.tag_provider import (
    check_package,
    provider_name,
    render_entry_points,
    render_tag_provider,
)

FIXTURE = Path(__file__).parent / "fixtures" / "utah_places.shp"


@pytest.fixture
def provider() -> Any:
    namespace: dict[str, Any] = {}
    exec(render_tag_provider("utah_schema"), namespace)
    return namespace[provider_name("utah_schema")]


@pytest.mark.parametrize(
    ("entry_point", "tagged"),
    [
        ("utah_schema.utah_places:UtahPlace", True),
        ("utah_schema:UtahPlace", True),
        ("utah_schema_extra.models:Other", False),
        ("overture.schema.places:Place", False),
    ],
)
def test_provider_tags_only_its_own_package(provider: Any, entry_point: str, tagged: bool) -> None:
    tags = provider([], ModelKey("m", entry_point, frozenset()), set())
    assert ("utah_schema" in tags) is tagged


def test_entry_points_name_what_was_written() -> None:
    toml = render_entry_points("utah_schema", "utah_places", "UtahPlace")
    assert 'utah_place = "utah_schema.utah_places:UtahPlace"' in toml
    assert f'utah_schema = "utah_schema.tags:{provider_name("utah_schema")}"' in toml
    assert '[project.entry-points."overture.tag_providers"]' in toml


@pytest.mark.parametrize("package", ["feature", "overture", "Utah", "utah-schema", "9lives"])
def test_unusable_package_names_are_refused(package: str) -> None:
    assert check_package(package) is not None


def test_cli_writes_provider_beside_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "utah_places.py"
    argv = [str(FIXTURE), "--class-name", "UtahPlace", "-o", str(output)]
    assert main([*argv, "--tag-provider", "utah_schema"]) == 0
    assert "def utah_schema_provider(" in (tmp_path / "tags.py").read_text()
    assert 'utah_place = "utah_schema.utah_places:UtahPlace"' in capsys.readouterr().out


def test_cli_does_not_overwrite_an_existing_provider(tmp_path: Path) -> None:
    (tmp_path / "tags.py").write_text("# edited by hand\n")
    argv = [str(FIXTURE), "--class-name", "UtahPlace", "-o", str(tmp_path / "m.py")]
    with pytest.raises(SystemExit):
        main([*argv, "--tag-provider", "utah_schema"])
    assert (tmp_path / "tags.py").read_text() == "# edited by hand\n"
    assert not (tmp_path / "m.py").exists()
