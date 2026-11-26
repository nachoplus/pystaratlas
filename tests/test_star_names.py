from pathlib import Path

import pytest

from pystaratlas import pipeline
from pystaratlas.catalogues import bsc, cross_index
from pystaratlas.config import load_map
from pystaratlas.models import SkyObject
from pystaratlas.scene import Text

CONFIG = Path(__file__).parents[1] / "examples" / "all-sky-mollweide.toml"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 21Alp And", "21 α And"),
        ("   Alp Eri", "α Eri"),
        ("57Gam1And", "57 γ¹ And"),
        (" 12Alp2CVn", "12 α² CVn"),
        ("   Pi  Tuc", "π Tuc"),
        (" 33    Psc", "33 Psc"),
    ],
)
def test_bsc_designation(raw: str, expected: str) -> None:
    assert bsc.designation(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 21Alp And", "α And"),
        ("57Gam1And", "γ¹ And"),
        (" 12Alp2CVn", "α² CVn"),
        ("    alf01 Cru", "α¹ Cru"),
        (" 33    Psc", ""),
    ],
)
def test_bayer_designation(raw: str, expected: str) -> None:
    assert bsc.bayer_designation(raw) == expected


def test_bsc_named_stars() -> None:
    stars = bsc.load()
    assert len(stars) > 3000
    vega = next(star for star in stars if star.name == "3 α Lyr")
    assert vega.magnitude is not None and vega.magnitude == pytest.approx(0.03)
    assert bsc.designations_by_hd()[172167] == "3 α Lyr"
    assert bsc.bayer_designations_by_hd()[172167] == "α Lyr"


def test_cross_index_star_names() -> None:
    names = cross_index.star_names()
    assert names[677] == "Alpheratz (α And)"
    assert names[746] == "Caph (β Cas)"
    assert names[3179] == "Schedar (α Cas)"
    assert names[91262] == "Vega (α Lyr)"
    assert all(name.strip() for name in names.values())


def test_star_labels_use_bsc_and_cross_index(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pystaratlas.pipeline.hipparcos.load",
        lambda: [
            SkyObject("HIP000677", 0.5, 29.0, magnitude=2.06, attributes={"hip": 677}),
            SkyObject("HIP091262", 279.2, 38.8, magnitude=0.03, attributes={"hip": 91262}),
            SkyObject("HIP000001", 0.0, 1.0, magnitude=9.0, attributes={"hip": 1}),
        ],
    )
    scene = pipeline.build_scene(load_map(CONFIG))
    labels = [
        item for item in scene.primitives if isinstance(item, Text) and item.style_key == "star-labels"
    ]
    assert [item.value for item in labels] == ["Vega (α Lyr)", "Alpheratz (α And)"]
    assert all(item.fill == "#202060" for item in labels)
