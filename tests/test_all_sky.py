import re
from pathlib import Path

import pytest
from PIL import Image

from pystaratlas import pipeline
from pystaratlas.config import load_map
from pystaratlas.geometry import SkyRegion, Viewport
from pystaratlas.models import SkyObject
from pystaratlas.render import pdf, png, svg
from pystaratlas.scene import Circle, Scene, Symbol, Text, Theme

CONFIG = Path(__file__).parents[1] / "examples" / "all-sky-mollweide.toml"
ORION_CONFIG = Path(__file__).parents[1] / "examples" / "orion.toml"


def test_orion_uses_stereographic_projection() -> None:
    spec = load_map(ORION_CONFIG)
    assert "+proj=stere" in spec.projection.to_proj4()
    assert "+lon_0=90.0" in spec.projection.to_proj4()

    viewport = Viewport(
        SkyRegion.from_spec(spec.region), spec.projection.to_proj4(), spec.canvas.size
    )
    east = viewport.project(105.0, 2.5)
    west = viewport.project(75.0, 2.5)
    assert east is not None and west is not None
    assert east[0] < west[0]


def test_mollweide_covers_full_sky(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = load_map(CONFIG)

    assert "+proj=moll" in spec.projection.to_proj4()
    assert "+lon_0=180" in spec.projection.to_proj4()
    assert spec.region.ra == (0.0, 360.0)
    assert spec.region.dec == (-90.0, 90.0)

    viewport = Viewport(
        SkyRegion.from_spec(spec.region), spec.projection.to_proj4(), spec.canvas.size
    )
    points = [viewport.project(ra, 0.0) for ra in (0.0, 90.0, 180.0, 270.0, 359.9, 360.0)]

    assert all(point is not None for point in points)
    xs = [point[0] for point in points if point]
    assert xs == sorted(xs, reverse=True)
    assert points[0] is not None and points[-1] is not None
    assert 0 < points[-1][0] < points[0][0] < spec.canvas.width

    north = viewport.project(180.0, 80.0)
    south = viewport.project(180.0, -80.0)
    assert north is not None and south is not None
    assert north[1] > south[1]

    monkeypatch.setattr(
        "pystaratlas.pipeline.hipparcos.load",
        lambda: [
            SkyObject("HIP0", 0.0, 0.0, magnitude=2.0, color_index=-0.3),
            SkyObject("HIP180", 180.0, 0.0, magnitude=4.0, color_index=0.7),
            SkyObject("HIP360", 360.0, 0.0, magnitude=5.5, color_index=1.5),
        ],
    )
    scene = pipeline.build_scene(spec)

    stars = [
        item
        for item in scene.primitives
        if isinstance(item, Circle) and item.style_key == "stars"
    ]
    radii = [item.radius for item in stars]
    assert len(radii) == 3
    assert radii[0] > radii[1] > radii[2]
    assert max(radii) <= 2.0
    assert len({item.fill for item in stars}) == 3

    assert any(
        getattr(item, "style_key", None) == "grid.equatorial" for item in scene.primitives
    )
    symbols = {
        item.kind: item.fill
        for item in scene.primitives
        if isinstance(item, Symbol) and item.style_key.startswith("ngc.")
    }
    assert {"galaxy", "open", "globular", "nebula", "planetary"} <= set(symbols)
    assert len(set(symbols.values())) == len(symbols)

    labels = [item.value for item in scene.primitives if isinstance(item, Text)]
    assert labels
    assert len(labels) == len(set(labels))

    target = svg.render(scene, tmp_path / "all-sky.svg")
    content = target.read_text(encoding="utf-8")

    assert "<svg" in content
    assert content.count("<polyline") > 20
    assert "<ellipse" in content
    assert "<polygon" in content
    assert 'class="s-ngc-galaxy"' in content
    assert 'class="s-ngc-open"' in content
    assert re.search(r'<ellipse[^>]*class="s-ngc-galaxy"[^>]*fill="none"', content)
    assert re.search(r'<polygon[^>]*class="s-ngc-planetary"[^>]*fill="none"', content)
    assert re.search(r'<rect[^>]*class="s-ngc-nebula"[^>]*fill="none"[^>]*stroke="#4f46e5"', content)
    assert "s-constellation-labels" in content
    assert "s-constellation-figures" in content
    assert "s-constellation-bounds" in content
    assert 'stroke-width="1.1"' in content

    assert pdf.render(scene, tmp_path / "all-sky.pdf").is_file()

    target_png = png.render(scene, tmp_path / "all-sky.png", scale=1)
    with Image.open(target_png) as image:
        assert image.format == "PNG"
        assert image.size == (int(spec.canvas.width), int(spec.canvas.height))


def test_png_defaults_to_high_resolution(tmp_path: Path) -> None:
    scene = Scene(width=100, height=60, background="#ffffff", theme=Theme())
    target = png.render(scene, tmp_path / "high-res.png")
    with Image.open(target) as image:
        assert image.size == (100 * png.DEFAULT_SCALE, 60 * png.DEFAULT_SCALE)
