from pathlib import Path

import pytest

from pystaratlas import pipeline
from pystaratlas.config import load_map
from pystaratlas.models import SkyObject


def test_build_scene_with_mocked_catalogues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "map.toml"
    config.write_text(
        """version = 1
[region]
kind = "equatorial"
ra = [0, 20]
dec = [-10, 10]
[projection]
proj = "moll"
[[layers]]
kind = "catalog"
source = "hipparcos"
filter = { mag_lt = 8 }
[[layers]]
kind = "grid"
frame = "equatorial"
step = 10
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "pystaratlas.pipeline.hipparcos.load",
        lambda: [SkyObject("HIP1", 10.0, 0.0, magnitude=5.0)],
    )

    scene = pipeline.build_scene(load_map(config))

    assert scene.primitives
    assert any(getattr(item, "style_key", None) == "stars" for item in scene.primitives)
    assert any(getattr(item, "style_key", None) == "grid.equatorial" for item in scene.primitives)
