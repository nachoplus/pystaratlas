from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from .catalogues import constellations, cross_index, deepspace, hipparcos, ngc
from .config import MapSpec
from .geometry import SkyRegion, Viewport, expanded_ra_range
from .models import SkyObject
from .scene import Circle, Polyline, Scene, Symbol, Text, Theme


def _style(
    theme: Theme, key: str, defaults: dict[str, Any], fallbacks: Iterable[str] = ()
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for fallback in fallbacks:
        values.update(theme.style(fallback))
    values.update(theme.style(key))
    return {**defaults, **{name: values[name] for name in defaults if name in values}}


def _magnitude_filter(objects: Iterable[SkyObject], filters: dict[str, Any]) -> list[SkyObject]:
    limit = filters.get("mag_lt")
    result = list(objects)
    if limit is not None:
        result = [obj for obj in result if obj.magnitude is not None and obj.magnitude <= float(limit)]
    return result


def _segments(
    coordinates: Iterable[tuple[float, float]], region: SkyRegion, viewport: Viewport
) -> list[tuple[tuple[float, float], ...]]:
    segments: list[tuple[tuple[float, float], ...]] = []
    current: list[tuple[float, float]] = []
    for ra, dec in coordinates:
        point = viewport.project(ra, dec)
        if point is not None and region.contains(ra, dec):
            if current and abs(point[0] - current[-1][0]) > viewport.width * 0.5:
                if len(current) > 1:
                    segments.append(tuple(current))
                current = []
            current.append(point)
        elif len(current) > 1:
            segments.append(tuple(current))
            current = []
        else:
            current = []
    if len(current) > 1:
        segments.append(tuple(current))
    return segments


def _interpolate(
    start: tuple[float, float], end: tuple[float, float], samples: int = 17
) -> list[tuple[float, float]]:
    """Sample a great-circle segment, as Stellarium does for stick figures."""
    if samples < 2:
        return [start]
    ra0, dec0 = math.radians(start[0]), math.radians(start[1])
    ra1, dec1 = math.radians(end[0]), math.radians(end[1])
    x0, y0, z0 = math.cos(dec0) * math.cos(ra0), math.cos(dec0) * math.sin(ra0), math.sin(dec0)
    x1, y1, z1 = math.cos(dec1) * math.cos(ra1), math.cos(dec1) * math.sin(ra1), math.sin(dec1)
    dot = max(-1.0, min(1.0, x0 * x1 + y0 * y1 + z0 * z1))
    omega = math.acos(dot)

    points: list[tuple[float, float]] = []
    for index in range(samples):
        if omega < 1e-9 or math.pi - omega < 1e-9:
            fraction = index / (samples - 1)
            ra = math.degrees(ra0 + (ra1 - ra0) * fraction) % 360.0
            dec = math.degrees(dec0 + (dec1 - dec0) * fraction)
            points.append((ra, dec))
            continue
        fraction = index / (samples - 1)
        first = math.sin((1.0 - fraction) * omega) / math.sin(omega)
        second = math.sin(fraction * omega) / math.sin(omega)
        x, y, z = first * x0 + second * x1, first * y0 + second * y1, first * z0 + second * z1
        ra = math.degrees(math.atan2(y, x)) % 360.0
        dec = math.degrees(math.atan2(z, math.hypot(x, y)))
        points.append((ra, dec))
    points[0] = start
    points[-1] = end
    return points


def _hip_number(star: SkyObject) -> int | None:
    value = star.attributes.get("hip")
    if value is not None:
        return int(value)
    if star.name.startswith("HIP"):
        try:
            return int(star.name[3:])
        except ValueError:
            return None
    return None


Box = tuple[float, float, float, float]


def _overlap(first: Box, second: Box) -> bool:
    x, y, width, height = first
    other_x, other_y, other_width, other_height = second
    return (
        x < other_x + other_width
        and other_x < x + width
        and y < other_y + other_height
        and other_y < y + height
    )


_VISIBLE_NGC_KINDS = {"globular", "planetary"}


def _visible_ngc_symbol_size(viewport: Viewport) -> float:
    """Size for compact catalogue types, scaled to the projected page."""
    return float(min(12.0, max(2.5, 0.22 * math.sqrt(viewport.scale))))


def _catalogue_symbol_size(angular_size: Any, viewport: Viewport) -> float:
    """Convert a catalogue's largest dimension (arcmin) into page units."""
    try:
        arcmin = float(angular_size)
    except (TypeError, ValueError):
        return 3.0
    if arcmin <= 0:
        return 3.0
    radius = math.radians(arcmin / 120.0) * viewport.scale
    return float(min(20.0, max(1.5, radius)))


def _star_radius(magnitude: float) -> float:
    """Brighter stars are slightly larger; all remain small filled circles."""
    return float(min(2.0, max(0.30, 0.06 * math.pow(12.0 - magnitude, 1.5))))


_STAR_COLORS = (
    (-0.40, "#8fa8ff"),
    (0.00, "#b3c8ff"),
    (0.20, "#dbe5f5"),
    (0.40, "#e6ebf5"),
    (0.60, "#fff1cf"),
    (0.80, "#ffd6a0"),
    (1.20, "#ffae66"),
    (2.00, "#ff7a55"),
)


def _star_color(bv: float | None) -> str:
    """Approximate the star hue from its B-V colour index."""
    if bv is None:
        return "#e6ebf5"
    for limit, color in _STAR_COLORS:
        if bv <= limit:
            return color
    return "#ff7b5a"


_NGC_SYMBOLS = {
    "Gx": "galaxy",
    "OC": "open",
    "Gb": "globular",
    "Nb": "nebula",
    "C+N": "nebula",
    "Pl": "planetary",
    "*": "star",
    "D*": "star",
    "***": "star",
    "Ast": "star",
    "Kt": "star",
}

_NGC_COLORS = {
    "galaxy": "#2b6cb0",
    "globular": "#b83227",
    "open": "#2f855a",
    "nebula": "#4f46e5",
    "planetary": "#6b46c1",
    "star": "#b7791f",
    "generic": "#4a5568",
}


def _center(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not points:
        return None
    xs = [math.cos(math.radians(ra)) for ra, _ in points]
    ys = [math.sin(math.radians(ra)) for ra, _ in points]
    ra = math.degrees(math.atan2(sum(ys), sum(xs))) % 360.0
    dec = sum(value for _, value in points) / len(points)
    return ra, dec


def _grid_lines(region: SkyRegion, step: float) -> list[list[tuple[float, float]]]:
    if region.ra is None or region.dec is None:
        return []
    ra0, ra1 = region.ra
    dec0, dec1 = region.dec
    ra_start, ra_end = expanded_ra_range(ra0, ra1)
    lines: list[list[tuple[float, float]]] = []
    for ra in range(int(ra_start), int(ra_end) + 1, int(step)):
        lines.append([(float(ra), dec0 + (dec1 - dec0) * i / 40) for i in range(41)])
    for dec in range(int(dec0), int(dec1) + 1, int(step)):
        lines.append([(ra_start + (ra_end - ra_start) * i / 80, float(dec)) for i in range(81)])
    return lines


def build_scene(spec: MapSpec) -> Scene:
    """Build the backend-independent drawing scene from a validated configuration."""
    theme = Theme.from_spec(spec.theme)
    projection = spec.projection
    if spec.region.kind == "constellation":
        region_name = spec.region.name or (spec.region.names[0] if spec.region.names else "")
        field = constellations.field_for(region_name)
        region = SkyRegion(
            kind="constellation",
            ra=field.ra,
            dec=field.dec,
            frame=spec.region.frame,
            names=(field.target, *field.neighbours),
            center=field.center,
        )
        params = dict(projection.params)
        params.setdefault("lon_0", field.center[0])
        params.setdefault("lat_0", field.center[1])
        projection = projection.model_copy(update={"params": params})
    else:
        region = SkyRegion.from_spec(spec.region)
    viewport = Viewport(region, projection.to_proj4(), spec.canvas.size)
    primitives: list[Any] = []

    for layer in spec.layers:
        if layer.kind == "catalog" and layer.source == "hipparcos":
            style = _style(theme, "stars", {"opacity": 1.0})
            label_style = _style(theme, "star-labels", {"fill": "#202060", "size": 9.0})
            label_limit = layer.filter.get("label_mag_lt")
            label_limit = float(label_limit) if label_limit is not None else 2.5
            names = cross_index.star_names() if layer.labels else {}
            candidates: list[tuple[float, tuple[float, float], str]] = []
            for star in _magnitude_filter(hipparcos.load(), layer.filter):
                point = viewport.project(star.ra, star.dec)
                if point is None or not region.contains(star.ra, star.dec):
                    continue
                magnitude = star.magnitude if star.magnitude is not None else 9.0
                primitives.append(
                    Circle(
                        point[0],
                        point[1],
                        _star_radius(magnitude),
                        "stars",
                        fill=_star_color(star.color_index),
                        stroke="none",
                        opacity=float(style.get("opacity", 1.0)),
                    )
                )
                hip = _hip_number(star)
                name = names.get(hip) if hip is not None else None
                if name and magnitude <= label_limit:
                    candidates.append((magnitude, point, name))

            placed: list[Box] = []
            size = float(label_style["size"])
            fill = str(label_style["fill"])
            for _, point, name in sorted(candidates):
                box = (point[0] + 4, point[1] + 5, len(name) * size * 0.52, size)
                if any(_overlap(box, other) for other in placed):
                    continue
                placed.append(box)
                primitives.append(
                    Text(point[0] + 4, point[1] + 5, name, size, "star-labels", fill=fill)
                )

        elif layer.kind == "catalog" and layer.source == "ngc":
            styles = {
                kind: _style(
                    theme,
                    f"ngc.{kind}",
                    {"fill": color, "stroke": color, "opacity": 0.9},
                )
                for kind, color in _NGC_COLORS.items()
            }
            types = set(layer.filter.get("types", []))
            for obj in _magnitude_filter(ngc.load(), layer.filter):
                obj_type = str(obj.attributes.get("type", ""))
                if types and obj_type not in types:
                    continue
                kind = _NGC_SYMBOLS.get(obj_type, "generic")
                point = viewport.project(obj.ra, obj.dec)
                if point is None or not region.contains(obj.ra, obj.dec):
                    continue
                if kind in _VISIBLE_NGC_KINDS:
                    symbol_size = _visible_ngc_symbol_size(viewport)
                else:
                    symbol_size = _catalogue_symbol_size(obj.attributes.get("size"), viewport)
                primitives.append(
                    Symbol(point[0], point[1], kind, symbol_size, f"ngc.{kind}", **styles[kind])
                )

        elif layer.kind == "catalog" and layer.source == "deepspace":
            marker_style = _style(
                theme, "deepspace-markers", {"fill": "#202060", "opacity": 0.9}
            )
            label_style = _style(theme, "deepspace-labels", {"fill": "#202060", "size": 8.0})
            placed_deepspace: list[Box] = []
            label_size = float(label_style["size"])
            label_fill = str(label_style["fill"])
            for obj in _magnitude_filter(deepspace.load(), layer.filter):
                point = viewport.project(obj.ra, obj.dec)
                if point is None or not region.contains(obj.ra, obj.dec):
                    continue
                primitives.append(
                    Circle(
                        point[0],
                        point[1],
                        1.2,
                        "deepspace-markers",
                        fill=str(marker_style["fill"]),
                        stroke="none",
                        opacity=float(marker_style["opacity"]),
                    )
                )
                if not layer.labels:
                    continue
                box = (
                    point[0] + 3,
                    point[1] + 3,
                    len(obj.name) * label_size * 0.52,
                    label_size,
                )
                if any(_overlap(box, other) for other in placed_deepspace):
                    continue
                placed_deepspace.append(box)
                primitives.append(
                    Text(
                        point[0] + 3,
                        point[1] + 3,
                        obj.name,
                        label_size,
                        "deepspace-labels",
                        fill=label_fill,
                    )
                )

        elif layer.kind == "objects":
            style = _style(theme, "objects", {"fill": "#cc0000", "stroke": "#cc0000", "opacity": 0.8})
            explicit = [
                SkyObject(
                    name=str(item["name"]),
                    ra=float(item["ra"]),
                    dec=float(item["dec"]),
                    kind="object",
                )
                for item in layer.objects
            ]
            for obj in explicit + cross_index.resolve(layer.names):
                point = viewport.project(obj.ra, obj.dec)
                if point is None or not region.contains(obj.ra, obj.dec):
                    continue
                primitives.append(Circle(point[0], point[1], 3.0, "objects", **style))
                if layer.labels:
                    primitives.append(Text(point[0] + 4, point[1] + 4, obj.name, 9.0, "object-labels"))

        elif layer.kind == "grid":
            step = layer.step or 10.0
            style = _style(
                theme,
                f"grid.{layer.frame or 'equatorial'}",
                {"stroke": "#666666", "width": 0.3, "opacity": 0.2},
            )
            for line in _grid_lines(region, step):
                for segment in _segments(line, region, viewport):
                    primitives.append(Polyline(segment, f"grid.{layer.frame or 'equatorial'}", **style))

        elif layer.kind == "constellations":
            bounds_style = _style(
                theme,
                "constellation-bounds",
                {"stroke": "#8a8aa8", "width": 0.5, "opacity": 0.35},
                fallbacks=("constellations",),
            )
            figure_style = _style(
                theme,
                "constellation-figures",
                {"stroke": "#404090", "width": 1.1, "opacity": 0.95},
                fallbacks=("constellations",),
            )
            allowed: set[str] = (
                {constellations.canonical_key(name) for name in region.names}
                if region.kind == "constellation"
                else set()
            )
            groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
            if layer.bounds or layer.labels:
                for ra, dec, name in constellations.load_bounds():
                    if allowed and constellations.canonical_key(name) not in allowed:
                        continue
                    groups[name].append((ra, dec))
                if layer.bounds:
                    for points in groups.values():
                        for segment in _segments(points, region, viewport):
                            primitives.append(
                                Polyline(segment, "constellation-bounds", **bounds_style)
                            )

            if layer.figures or layer.labels:
                positions = cross_index.load_hip_positions()
                for star in hipparcos.load():
                    hip = _hip_number(star)
                    if hip is not None:
                        positions.setdefault(hip, (star.ra, star.dec))
                figures = constellations.load_figures(positions)
                for name, links in figures.items():
                    if allowed and constellations.canonical_key(name) not in allowed:
                        continue
                    for start, end in links:
                        groups[name].extend((start, end))
                        if layer.figures:
                            for segment in _segments(_interpolate(start, end), region, viewport):
                                primitives.append(
                                    Polyline(segment, "constellation-figures", **figure_style)
                                )

            if layer.labels:
                label_style = _style(theme, "constellation-labels", {"fill": "#202060"})
                centers: dict[str, tuple[float, float]] = {}
                for name, points in groups.items():
                    center = _center(points)
                    if center is not None:
                        centers.setdefault(name.rstrip("0123456789") or name, center)
                for label, center in centers.items():
                    point = viewport.project(*center)
                    if point is None or not region.contains(*center):
                        continue
                    primitives.append(
                        Text(
                            point[0] + 4,
                            point[1] + 4,
                            label,
                            11.0,
                            "constellation-labels",
                            fill=str(label_style.get("fill", "#202060")),
                        )
                    )

        elif layer.kind in {"ephemeris"}:
            raise NotImplementedError("ephemeris layers are not implemented in this milestone")

    return Scene(
        width=spec.canvas.width,
        height=spec.canvas.height,
        background=theme.color("background", spec.canvas.background),
        theme=theme,
        primitives=tuple(primitives),
    )
