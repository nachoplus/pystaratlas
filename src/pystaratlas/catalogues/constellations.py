from __future__ import annotations

import math
import unicodedata
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..errors import ConfigError, DataError
from ..resources import data_path

Point = tuple[float, float]

_FULL_NAMES = {
    "AND": "Andromeda",
    "ANT": "Antlia",
    "APS": "Apus",
    "AQL": "Aquila",
    "AQR": "Aquarius",
    "ARA": "Ara",
    "ARI": "Aries",
    "AUR": "Auriga",
    "BOO": "Boötes",
    "CAE": "Caelum",
    "CAM": "Camelopardalis",
    "CAP": "Capricornus",
    "CAR": "Carina",
    "CAS": "Cassiopeia",
    "CEN": "Centaurus",
    "CEP": "Cepheus",
    "CET": "Cetus",
    "CHA": "Chamaeleon",
    "CIR": "Circinus",
    "CMA": "Canis Major",
    "CMI": "Canis Minor",
    "CNC": "Cancer",
    "COL": "Columba",
    "COM": "Coma Berenices",
    "CRA": "Corona Australis",
    "CRB": "Corona Borealis",
    "CRT": "Crater",
    "CRU": "Crux",
    "CRV": "Corvus",
    "CVN": "Canes Venatici",
    "CYG": "Cygnus",
    "DEL": "Delphinus",
    "DOR": "Dorado",
    "DRA": "Draco",
    "EQU": "Equuleus",
    "ERI": "Eridanus",
    "FOR": "Fornax",
    "GEM": "Gemini",
    "GRU": "Grus",
    "HER": "Hercules",
    "HOR": "Horologium",
    "HYA": "Hydra",
    "HYI": "Hydrus",
    "IND": "Indus",
    "LAC": "Lacerta",
    "LEO": "Leo",
    "LEP": "Lepus",
    "LIB": "Libra",
    "LMI": "Leo Minor",
    "LUP": "Lupus",
    "LYN": "Lynx",
    "LYR": "Lyra",
    "MEN": "Mensa",
    "MIC": "Microscopium",
    "MON": "Monoceros",
    "MUS": "Musca",
    "NOR": "Norma",
    "OCT": "Octans",
    "OPH": "Ophiuchus",
    "ORI": "Orion",
    "PAV": "Pavo",
    "PEG": "Pegasus",
    "PER": "Perseus",
    "PHE": "Phoenix",
    "PIC": "Pictor",
    "PSA": "Piscis Austrinus",
    "PSC": "Pisces",
    "PUP": "Puppis",
    "PYX": "Pyxis",
    "RET": "Reticulum",
    "SCL": "Sculptor",
    "SCO": "Scorpius",
    "SCT": "Scutum",
    "SER1": "Serpens Caput",
    "SER2": "Serpens Cauda",
    "SEX": "Sextans",
    "SGE": "Sagitta",
    "SGR": "Sagittarius",
    "TAU": "Taurus",
    "TEL": "Telescopium",
    "TRA": "Triangulum Australe",
    "TRI": "Triangulum",
    "TUC": "Tucana",
    "UMA": "Ursa Major",
    "UMI": "Ursa Minor",
    "VEL": "Vela",
    "VIR": "Virgo",
    "VOL": "Volans",
    "VUL": "Vulpecula",
}

_CANONICAL = {key: ("SER" if key in {"SER1", "SER2"} else key) for key in _FULL_NAMES}

_ALIASES = {
    "orion": "ORI",
    "ser": "SER",
    "serpens": "SER",
    "serpens caput": "SER",
    "serpens cauda": "SER",
    "serpiente": "SER",
    "casiopea": "CAS",
    "osa mayor": "UMA",
    "osa menor": "UMI",
    "cisne": "CYG",
    "tauro": "TAU",
    "geminis": "GEM",
    "leon": "LEO",
    "leon menor": "LMI",
    "escorpio": "SCO",
    "escorpion": "SCO",
    "sagitario": "SGR",
    "acuario": "AQR",
    "capricornio": "CAP",
    "aries": "ARI",
    "virgen": "VIR",
    "libra": "LIB",
    "perro mayor": "CMA",
    "perro menor": "CMI",
    "liebre": "LEP",
    "unicornio": "MON",
    "eridano": "ERI",
    "paloma": "COL",
    "cruz del sur": "CRU",
    "corona boreal": "CRB",
    "corona austral": "CRA",
    "cabellera de berenice": "COM",
    "triangulo": "TRI",
    "triangulo austral": "TRA",
    "dragones": "DRA",
    "dragon": "DRA",
    "fenix": "PHE",
    "grulla": "GRU",
    "pavo": "PAV",
    "tucan": "TUC",
}


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().replace("-", " ").split())


def canonical_key(name: str) -> str:
    """Normalise a boundary/figure key to its IAU abbreviation."""
    key = _normalize(name).replace(" ", "").upper()
    return "SER" if key in {"SER1", "SER2"} else key


def resolve_name(name: str) -> str:
    """Resolve a full name, Spanish alias or abbreviation to an IAU key."""
    normalized = _normalize(name)
    if normalized in _ALIASES:
        return _ALIASES[normalized]
    for key, canonical in _CANONICAL.items():
        if normalized in {key.lower(), _normalize(_FULL_NAMES[key])}:
            return canonical
    raise ConfigError(f"Unknown constellation: {name!r}")


def _path(path: str | Path | None, default: str) -> str:
    return str(Path(path) if path else data_path(default))


@lru_cache(maxsize=8)
def _boundary_points(source: str) -> dict[str, tuple[Point, ...]]:
    points: dict[str, list[Point]] = defaultdict(list)
    try:
        for line in Path(source).read_text(encoding="latin-1").splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            points[parts[2].upper()].append((float(parts[0]) * 15.0, float(parts[1])))
    except OSError as exc:
        raise DataError(f"Cannot read constellation bounds {source}: {exc}") from exc
    return {key: tuple(value) for key, value in points.items()}


def load_bounds(path: str | Path | None = None) -> list[tuple[float, float, str]]:
    source = _path(path, "costellations_bound_20.dat")
    return [
        (ra, dec, name)
        for name, points in _boundary_points(source).items()
        for ra, dec in points
    ]


@dataclass(frozen=True, slots=True)
class ConstellationField:
    """Equatorial window containing a constellation and its direct neighbours."""

    target: str
    neighbours: tuple[str, ...]
    center: tuple[float, float]
    ra: tuple[float, float]
    dec: tuple[float, float]


def _boundary_keys(abbreviation: str) -> tuple[str, ...]:
    return ("SER1", "SER2") if abbreviation == "SER" else (abbreviation,)


def _rounded(point: Point) -> tuple[float, float]:
    return round(point[0], 5), round(point[1], 5)


def neighbours(name: str, path: str | Path | None = None) -> tuple[str, ...]:
    """Return the constellations sharing boundary vertices with ``name``."""
    abbreviation = resolve_name(name)
    points = _boundary_points(_path(path, "costellations_bound_20.dat"))
    target_keys = _boundary_keys(abbreviation)
    shared: set[tuple[float, float]] = set()
    for key in target_keys:
        shared.update(_rounded(point) for point in points.get(key, ()))

    result = {
        canonical_key(key)
        for key, values in points.items()
        if key not in target_keys and any(_rounded(point) in shared for point in values)
    }
    return tuple(sorted(result))


def _center(points: list[Point]) -> tuple[float, float]:
    if not points:
        raise ConfigError("Cannot centre a constellation without boundary points")
    xs = [math.cos(math.radians(ra)) for ra, _ in points]
    ys = [math.sin(math.radians(ra)) for ra, _ in points]
    ra = math.degrees(math.atan2(sum(ys), sum(xs))) % 360.0
    dec = sum(value for _, value in points) / len(points)
    return ra, dec


def _separation(first: Point, second: Point) -> float:
    ra0, dec0 = math.radians(first[0]), math.radians(first[1])
    ra1, dec1 = math.radians(second[0]), math.radians(second[1])
    cosine = math.sin(dec0) * math.sin(dec1) + math.cos(dec0) * math.cos(dec1) * math.cos(
        ra0 - ra1
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def field_for(
    name: str, path: str | Path | None = None, padding: float = 0.25
) -> ConstellationField:
    """Build a centred equatorial field around a constellation and its neighbours."""
    abbreviation = resolve_name(name)
    boundary_path = _path(path, "costellations_bound_20.dat")
    points = _boundary_points(boundary_path)
    target_keys = _boundary_keys(abbreviation)
    target_points = [point for key in target_keys for point in points.get(key, ())]
    center = _center(target_points)
    target_rounded = {_rounded(point) for point in target_points}
    shared = [
        point
        for key, values in points.items()
        if key not in target_keys
        for point in values
        if _rounded(point) in target_rounded
    ]

    radius = max(_separation(center, point) for point in target_points + shared)
    radius *= 1.0 + padding
    ra_margin = radius / max(math.cos(math.radians(center[1])), 0.2)
    return ConstellationField(
        target=abbreviation,
        neighbours=neighbours(abbreviation, boundary_path),
        center=center,
        ra=(center[0] - ra_margin, center[0] + ra_margin),
        dec=(
            max(-90.0, center[1] - radius),
            min(90.0, center[1] + radius),
        ),
    )


def load_figures(
    hip_positions: Mapping[int, tuple[float, float]], path: str | Path | None = None
) -> dict[str, list[tuple[tuple[float, float], tuple[float, float]]]]:
    """Read constellation stick figures as pairs of ICRS degrees."""
    source = Path(path) if path else data_path("constellationship.fab")
    figures: dict[str, list[tuple[tuple[float, float], tuple[float, float]]]] = defaultdict(list)
    try:
        for line in source.read_text(encoding="latin-1").splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[0].upper()
            identifiers = [int(part) for part in parts[2:]]
            for index in range(0, len(identifiers) - 1, 2):
                start = hip_positions.get(identifiers[index])
                end = hip_positions.get(identifiers[index + 1])
                if start is not None and end is not None:
                    figures[name].append((start, end))
    except (OSError, ValueError) as exc:
        raise DataError(f"Cannot read constellation figures {source}: {exc}") from exc
    return dict(figures)
