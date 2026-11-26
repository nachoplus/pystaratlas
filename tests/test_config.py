from pathlib import Path

import pytest

from pystaratlas.config import load_map
from pystaratlas.errors import ConfigError


def test_load_map_resolves_includes(tmp_path: Path) -> None:
    (tmp_path / "objects.toml").write_text(
        'version = 1\nnames = ["M31"]\n[[objects]]\nname = "X"\nra = 1.0\ndec = 2.0\n',
        encoding="utf-8",
    )
    (tmp_path / "theme.toml").write_text(
        'version = 1\n[colors]\nbackground = "#010203"\n', encoding="utf-8"
    )
    config = tmp_path / "map.toml"
    config.write_text(
        """version = 1
[region]
kind = "equatorial"
ra = [0, 10]
dec = [-5, 5]
[projection]
proj = "moll"
[projection.params]
ellps = "sphere"
[[layers]]
kind = "objects"
include = "objects.toml"
[theme]
include = "theme.toml"
""",
        encoding="utf-8",
    )

    spec = load_map(config)

    assert spec.region.ra == (0.0, 10.0)
    assert spec.projection.to_proj4() == "+proj=moll +ellps=sphere"
    assert spec.layers[0].names == ["M31"]
    assert spec.layers[0].objects[0]["name"] == "X"
    assert spec.theme.colors["background"] == "#010203"


def test_rejects_invalid_region(tmp_path: Path) -> None:
    config = tmp_path / "bad.toml"
    config.write_text('version = 1\n[region]\nkind = "equatorial"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="ra and dec"):
        load_map(config)
