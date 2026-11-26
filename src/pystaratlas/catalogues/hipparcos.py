from __future__ import annotations

import gzip
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from ..errors import DataError
from ..models import SkyObject
from ..resources import data_path

_SLICES = {
    "hip": slice(0, 6),
    "ra_rad": slice(15, 28),
    "dec_rad": slice(29, 42),
    "hpmag": slice(129, 136),
    "bv": slice(152, 158),
}


def _number(line: str, key: str) -> float | None:
    value = line[_SLICES[key]].strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise DataError(f"Invalid {key} value in Hipparcos row: {value!r}") from exc


def _lines(source: Path) -> Iterator[str]:
    if source.suffix == ".gz":
        with gzip.open(source, "rt", encoding="ascii") as handle:
            yield from handle
    else:
        with source.open("r", encoding="ascii") as handle:
            yield from handle


@lru_cache(maxsize=1)
def load(path: str | Path | None = None) -> list[SkyObject]:
    source = Path(path) if path else data_path("hip2.dat.gz")
    stars: list[SkyObject] = []
    try:
        for line in _lines(source):
            if line.startswith("HIP") or len(line) < 158:
                continue
            ra = _number(line, "ra_rad")
            dec = _number(line, "dec_rad")
            hip = _number(line, "hip")
            if ra is None or dec is None or hip is None:
                continue
            identifier = int(hip)
            stars.append(
                SkyObject(
                    name=f"HIP{identifier:06d}",
                    ra=ra * 180.0 / 3.141592653589793,
                    dec=dec * 180.0 / 3.141592653589793,
                    magnitude=_number(line, "hpmag"),
                    color_index=_number(line, "bv"),
                    attributes={"hip": identifier},
                )
            )
    except OSError as exc:
        raise DataError(f"Cannot read Hipparcos catalogue {source}: {exc}") from exc
    return stars
