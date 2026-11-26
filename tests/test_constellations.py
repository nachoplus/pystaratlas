from pathlib import Path

import pytest

from pystaratlas import pipeline
from pystaratlas.catalogues import constellations, cross_index
from pystaratlas.config import load_map
from pystaratlas.errors import ConfigError
from pystaratlas.geometry import SkyRegion, Viewport
from pystaratlas.scene import Polyline, Text

EXAMPLES = Path(__file__).parents[1] / "examples"
ORION_CONFIG = EXAMPLES / "orion.toml"
CONSTELLATION_CONFIG = EXAMPLES / "orion-constellation.toml"
SAGITTARIUS_CONFIG = EXAMPLES / "sagittarius-constellation.toml"
SCORPIUS_CONFIG = EXAMPLES / "scorpius-constellation.toml"
LEO_CONFIG = EXAMPLES / "leo-constellation.toml"


def test_load_figures_reads_stellarium_fab_pairs() -> None:
    figures = constellations.load_figures({26727: (1.0, 2.0), 26311: (3.0, 4.0)})
    assert ((1.0, 2.0), (3.0, 4.0)) in figures["ORI"]
    assert len(constellations.load_figures(cross_index.load_hip_positions())) >= 80


def test_orion_figures_are_drawn_separately_from_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pystaratlas.pipeline.hipparcos.load", list)
    scene = pipeline.build_scene(load_map(ORION_CONFIG))

    figures = [
        item
        for item in scene.primitives
        if isinstance(item, Polyline) and item.style_key == "constellation-figures"
    ]
    bounds = [
        item
        for item in scene.primitives
        if isinstance(item, Polyline) and item.style_key == "constellation-bounds"
    ]

    assert len(figures) > 10
    assert bounds
    assert all(item.width == pytest.approx(1.1) for item in figures)


def test_resolves_names_and_finds_neighbours() -> None:
    assert constellations.resolve_name("Orión") == "ORI"
    assert constellations.resolve_name("ori") == "ORI"
    assert constellations.resolve_name("Osa Mayor") == "UMA"
    assert constellations.resolve_name("Serpens") == "SER"
    assert constellations.resolve_name("Sagitario") == "SGR"
    assert constellations.resolve_name("Escorpio") == "SCO"
    assert constellations.resolve_name("León") == "LEO"

    field = constellations.field_for("Orion")
    assert field.target == "ORI"
    assert set(field.neighbours) == {"ERI", "GEM", "LEP", "MON", "TAU"}
    assert field.center[0] == pytest.approx(84.5, abs=1.0)
    assert field.center[1] == pytest.approx(6.7, abs=1.0)
    assert field.ra[0] < field.center[0] < field.ra[1]
    assert field.dec[0] < field.center[1] < field.dec[1]


def test_unknown_constellation_name_is_rejected() -> None:
    with pytest.raises(ConfigError, match="Unknown constellation"):
        constellations.resolve_name("NoSuchConstellation")


def test_constellation_region_centres_target_with_neighbours() -> None:
    spec = load_map(CONSTELLATION_CONFIG)
    scene = pipeline.build_scene(spec)

    labels = {
        item.value: item
        for item in scene.primitives
        if isinstance(item, Text) and item.style_key == "constellation-labels"
    }
    assert "ORI" in labels
    orion = labels["ORI"]
    assert abs(orion.x - spec.canvas.width / 2.0) < 40.0
    assert abs(orion.y - spec.canvas.height / 2.0) < 40.0
    assert {"GEM", "TAU", "MON"} <= set(labels)

    figures = [
        item
        for item in scene.primitives
        if isinstance(item, Polyline) and item.style_key == "constellation-figures"
    ]
    assert len(figures) > 20


@pytest.mark.parametrize(
    ("config", "target"),
    [
        (CONSTELLATION_CONFIG, "ORI"),
        (SAGITTARIUS_CONFIG, "SGR"),
        (SCORPIUS_CONFIG, "SCO"),
        (LEO_CONFIG, "LEO"),
    ],
)
def test_constellation_examples_draw_target_complete(config: Path, target: str) -> None:
    spec = load_map(config)
    field = constellations.field_for(spec.region.name or spec.region.names[0])
    params = dict(spec.projection.params)
    params.setdefault("lon_0", field.center[0])
    params.setdefault("lat_0", field.center[1])
    projection = spec.projection.model_copy(update={"params": params})
    region = SkyRegion(
        kind="constellation", ra=field.ra, dec=field.dec, center=field.center
    )
    viewport = Viewport(region, projection.to_proj4(), spec.canvas.size)

    points = [
        viewport.project(ra, dec)
        for ra, dec, name in constellations.load_bounds()
        if constellations.canonical_key(name) == target
    ]
    assert points
    assert all(point is not None for point in points)
    assert all(
        0.0 <= point[0] <= spec.canvas.width and 0.0 <= point[1] <= spec.canvas.height
        for point in points
        if point is not None
    )

    labels = {
        item.value: item
        for item in pipeline.build_scene(spec).primitives
        if isinstance(item, Text) and item.style_key == "constellation-labels"
    }
    assert target in labels
    label = labels[target]
    assert abs(label.x - spec.canvas.width / 2.0) < 40.0
    assert abs(label.y - spec.canvas.height / 2.0) < 40.0
