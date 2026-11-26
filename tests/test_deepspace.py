from pathlib import Path

import pytest

from pystaratlas import pipeline
from pystaratlas.catalogues import deepspace, ngc
from pystaratlas.config import load_map
from pystaratlas.models import SkyObject
from pystaratlas.scene import Circle, Symbol, Text

EXAMPLES = Path(__file__).parents[1] / "examples"
ORION_CONFIG = EXAMPLES / "orion.toml"
ALL_SKY_CONFIG = EXAMPLES / "all-sky-mollweide.toml"


def test_ngc_catalogue_exposes_angular_size() -> None:
    objects = ngc.load()
    assert len(objects) > 10000
    assert any(obj.attributes.get("size") for obj in objects)


def test_ngc_symbols_scale_with_catalogue_size(monkeypatch: pytest.MonkeyPatch) -> None:
    objects = [
        SkyObject(
            f"NGC{index}",
            ra,
            0.0,
            kind="ngc",
            attributes={"type": "Gx", "size": size},
        )
        for index, (ra, size) in enumerate(((82.0, 2.0), (90.0, 20.0), (98.0, 200.0)), start=1)
    ]
    monkeypatch.setattr("pystaratlas.pipeline.hipparcos.load", list)
    monkeypatch.setattr("pystaratlas.pipeline.ngc.load", lambda: objects)

    scene = pipeline.build_scene(load_map(ORION_CONFIG))
    sizes = [
        item.size
        for item in scene.primitives
        if isinstance(item, Symbol) and item.style_key == "ngc.galaxy"
    ]

    assert len(sizes) == 3
    assert sizes == sorted(sizes)
    assert sizes[0] == pytest.approx(1.5)
    assert sizes[0] < sizes[1] < sizes[2]
    assert sizes[2] == pytest.approx(20.0)


def test_ngc_globulars_and_planetary_nebulae_scale_with_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    objects = [
        SkyObject(
            "NGC1",
            82.0,
            0.0,
            magnitude=5.0,
            kind="ngc",
            attributes={"type": "Gb", "size": 0.5},
        ),
        SkyObject(
            "NGC2",
            90.0,
            0.0,
            magnitude=5.0,
            kind="ngc",
            attributes={"type": "Pl", "size": 0.5},
        ),
    ]
    monkeypatch.setattr("pystaratlas.pipeline.hipparcos.load", list)
    monkeypatch.setattr("pystaratlas.pipeline.ngc.load", lambda: objects)

    def sizes_for(config: Path) -> dict[str, float]:
        scene = pipeline.build_scene(load_map(config))
        return {
            item.kind: item.size
            for item in scene.primitives
            if isinstance(item, Symbol) and item.style_key in {"ngc.globular", "ngc.planetary"}
        }

    orion = sizes_for(ORION_CONFIG)
    all_sky = sizes_for(ALL_SKY_CONFIG)

    assert 7.0 < orion["globular"] < 10.0
    assert 3.0 < all_sky["globular"] < 5.0
    assert orion["globular"] > all_sky["globular"]
    assert orion["planetary"] == pytest.approx(orion["globular"])
    assert all_sky["planetary"] == pytest.approx(all_sky["globular"])


def test_deepspace_catalogue_labels_messier_and_caldwell() -> None:
    objects = {obj.attributes["identifier"]: obj for obj in deepspace.load()}

    orion_nebula = objects["NGC1976"]
    assert orion_nebula.name == "Great Nebula In Orion (M42)"
    assert orion_nebula.attributes["messier"] == "42"
    assert orion_nebula.attributes["size"] == pytest.approx(66.0)

    variable_nebula = objects["NGC2261"]
    assert variable_nebula.name == "Hubble's Variable Nebula (C46)"
    assert variable_nebula.attributes["caldwell"] == "46"


def test_deepspace_layer_draws_and_labels_orion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pystaratlas.pipeline.hipparcos.load", list)
    scene = pipeline.build_scene(load_map(ORION_CONFIG))

    markers = [
        item
        for item in scene.primitives
        if isinstance(item, Circle) and item.style_key == "deepspace-markers"
    ]
    labels = [
        item.value
        for item in scene.primitives
        if isinstance(item, Text) and item.style_key == "deepspace-labels"
    ]

    assert len(markers) == 12
    assert "Great Nebula In Orion (M42)" in labels
    assert "Hubble's Variable Nebula (C46)" in labels
