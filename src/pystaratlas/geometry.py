from __future__ import annotations

import math
import re
from dataclasses import dataclass

from pyproj import CRS, Transformer

from .config import RegionSpec
from .errors import ConfigError


def _source_crs(proj4: str) -> CRS:
    """Match the target body so PROJ does not reject a unit-sphere projection."""
    radius = re.search(r"\+R=([^\s]+)", proj4)
    if radius:
        return CRS.from_proj4(f"+proj=lonlat +R={radius.group(1)}")
    semi_major = re.search(r"\+a=([^\s]+)", proj4)
    if semi_major:
        semi_minor = re.search(r"\+b=([^\s]+)", proj4)
        b = semi_minor.group(1) if semi_minor else semi_major.group(1)
        return CRS.from_proj4(f"+proj=lonlat +a={semi_major.group(1)} +b={b}")
    return CRS.from_proj4("+proj=lonlat +ellps=sphere")


def normalize_ra(ra: float) -> float:
    return ra % 360.0


def expanded_ra_range(ra0: float, ra1: float) -> tuple[float, float]:
    return (ra0, ra1 + 360.0) if ra1 < ra0 else (ra0, ra1)


def in_ra_range(ra: float, ra0: float, ra1: float) -> bool:
    start, end = expanded_ra_range(ra0, ra1)
    value = normalize_ra(ra)
    if value < start:
        value += 360.0
    return start <= value <= end


@dataclass(frozen=True, slots=True)
class SkyRegion:
    kind: str
    ra: tuple[float, float] | None = None
    dec: tuple[float, float] | None = None
    frame: str = "icrs"
    names: tuple[str, ...] = ()
    center: tuple[float, float] | None = None
    radius: float | None = None

    @classmethod
    def from_spec(cls, spec: RegionSpec) -> SkyRegion:
        return cls(
            kind=spec.kind,
            ra=spec.ra,
            dec=spec.dec,
            frame=spec.frame,
            names=tuple(spec.names),
            center=spec.center,
            radius=spec.radius,
        )

    def contains(self, ra: float, dec: float) -> bool:
        if self.ra is None or self.dec is None:
            return True
        return in_ra_range(ra, *self.ra) and self.dec[0] <= dec <= self.dec[1]


class Viewport:
    """Projects sky coordinates into page coordinates with y increasing upwards."""

    def __init__(self, region: SkyRegion, proj4: str, size: tuple[float, float]):
        if region.ra is None or region.dec is None:
            raise ConfigError("Only equatorial and constellation regions are implemented")
        self.region = region
        self.width, self.height = size
        self._full_sky = region.ra[1] - region.ra[0] >= 360.0
        self.transformer = Transformer.from_crs(
            _source_crs(proj4), CRS.from_proj4(proj4), always_xy=True
        )
        self._fit(region.ra, region.dec, region.center)

    def _longitude(self, ra: float) -> float:
        """Keep RA=360 at the eastern edge; PROJ otherwise folds it back to 0."""
        if not self._full_sky:
            return normalize_ra(ra)
        value = ra % 360.0
        return 360.0 - 1e-9 if value == 0.0 and ra >= 360.0 else value

    def _fit(
        self,
        ra_range: tuple[float, float],
        dec_range: tuple[float, float],
        center: tuple[float, float] | None = None,
    ) -> None:
        ra0, ra1 = expanded_ra_range(*ra_range)
        dec0, dec1 = dec_range
        xs: list[float] = []
        ys: list[float] = []
        for i in range(17):
            ra = self._longitude(ra0 + (ra1 - ra0) * i / 16)
            for j in range(9):
                dec = dec0 + (dec1 - dec0) * j / 8
                x, y = self.transformer.transform(ra, dec)
                if math.isfinite(x) and math.isfinite(y):
                    xs.append(x)
                    ys.append(y)
        if not xs:
            raise ConfigError("Projection produced no finite points for the requested region")
        if center is None:
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            span_x = max(x1 - x0, 1e-9)
            span_y = max(y1 - y0, 1e-9)
            self.center_x = (x0 + x1) / 2
            self.center_y = (y0 + y1) / 2
        else:
            center_x, center_y = self.transformer.transform(
                self._longitude(center[0]), center[1]
            )
            if not math.isfinite(center_x) or not math.isfinite(center_y):
                raise ConfigError("Projection centre is not finite for this region")
            span_x = max(2.0 * max(abs(x - center_x) for x in xs), 1e-9)
            span_y = max(2.0 * max(abs(y - center_y) for y in ys), 1e-9)
            self.center_x = center_x
            self.center_y = center_y
        self.scale = 0.9 * min(self.width / span_x, self.height / span_y)

    def project(self, ra: float, dec: float) -> tuple[float, float] | None:
        x, y = self.transformer.transform(self._longitude(ra), dec)
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        page_x = self.width / 2 - (x - self.center_x) * self.scale
        page_y = self.height / 2 + (y - self.center_y) * self.scale
        return page_x, page_y
