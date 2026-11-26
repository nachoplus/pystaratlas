import math

from pystaratlas.config import RegionSpec
from pystaratlas.geometry import SkyRegion, Viewport, in_ra_range, normalize_ra


def test_helpers() -> None:
    assert normalize_ra(370) == 10
    assert in_ra_range(5, 350, 20)
    assert not in_ra_range(100, 350, 20)


def test_viewport_projects_center() -> None:
    spec = RegionSpec(kind="equatorial", ra=(0, 20), dec=(-10, 10))
    viewport = Viewport(SkyRegion.from_spec(spec), "+proj=moll +ellps=sphere +R=1", (800, 600))
    point = viewport.project(10, 0)

    assert point is not None
    assert math.isclose(point[0], 400, abs_tol=1e-6)
    assert math.isclose(point[1], 300, abs_tol=1e-6)
