from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from astropy.io import fits

from ..errors import DataError
from ..models import SkyObject
from ..resources import data_path
from . import bsc


def _clean(name: str) -> str:
    return name.split("(")[0].split(";")[0].strip().upper()


def _proper_name(raw: str) -> str:
    """Keep one plausible common name from the cross-index alias list."""
    name = str(raw).split("(")[0].split(";")[0].strip()
    if len(name) > 22 or "HD" in name or "the " in name.lower():
        return ""
    if not re.fullmatch(r"[A-Za-z][A-Za-z '\-.]*", name):
        return ""
    return name


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coordinates(row: Any) -> tuple[float, float]:
    ra = (float(row["RAh"]) + float(row["RAm"]) / 60 + float(row["RAs"]) / 3600) * 15.0
    sign = -1 if str(row["DE-"]).strip() == "-" else 1
    dec = sign * (
        float(row["DEd"]) + float(row["DEm"]) / 60 + float(row["DEs"]) / 3600
    )
    return ra, dec


def load_hip_positions(path: str | Path | None = None) -> dict[int, tuple[float, float]]:
    """Map HIP numbers to ICRS degrees using the bundled cross-index."""
    source = Path(path) if path else data_path("cross_index.fits")
    positions: dict[int, tuple[float, float]] = {}
    try:
        with fits.open(source) as hdulist:
            for row in hdulist[1].data:
                hip = _integer(row["HIP"])
                if hip:
                    positions[hip] = _coordinates(row)
    except (OSError, KeyError, ValueError) as exc:
        raise DataError(f"Cannot read HIP positions from {source}: {exc}") from exc
    return positions


def load_hd_to_hip(path: str | Path | None = None) -> dict[int, int]:
    """Map HD numbers to HIP numbers using the bundled cross-index."""
    source = Path(path) if path else data_path("cross_index.fits")
    mapping: dict[int, int] = {}
    try:
        with fits.open(source) as hdulist:
            for row in hdulist[1].data:
                hd, hip = _integer(row["HD"]), _integer(row["HIP"])
                if hd and hip:
                    mapping.setdefault(hd, hip)
    except (OSError, KeyError, ValueError) as exc:
        raise DataError(f"Cannot read HD/HIP cross-index from {source}: {exc}") from exc
    return mapping


def load_proper_names(path: str | Path | None = None) -> dict[int, str]:
    """Map HD numbers to common star names from the cross-index."""
    source = Path(path) if path else data_path("cross_index.fits")
    names: dict[int, str] = {}
    try:
        with fits.open(source) as hdulist:
            for row in hdulist[4].data:
                hd, name = _integer(row["HD"]), _proper_name(str(row["Name"]))
                if hd and name:
                    names.setdefault(hd, name)
    except (OSError, KeyError, ValueError) as exc:
        raise DataError(f"Cannot read star names from {source}: {exc}") from exc
    return names


def star_names(
    path: str | Path | None = None, bsc_path: str | Path | None = None
) -> dict[int, str]:
    """Map HIP numbers to common names with their Greek-letter Bayer designation."""
    source = Path(path) if path else data_path("cross_index.fits")
    bayer = bsc.bayer_designations_by_hd(bsc_path)
    proper = load_proper_names(source)
    names: dict[int, str] = {}
    try:
        with fits.open(source) as hdulist:
            for row in hdulist[1].data:
                hip = _integer(row["HIP"])
                if not hip:
                    continue
                hd = _integer(row["HD"])
                letter = bayer.get(hd, "") if hd is not None else ""
                if not letter:
                    letter = bsc.bayer_designation(str(row["BFD"]))
                common = proper.get(hd, "") if hd is not None else ""
                if common and letter:
                    name = f"{common} ({letter})"
                else:
                    name = common or letter
                if name:
                    names.setdefault(hip, name)
    except (OSError, KeyError, ValueError) as exc:
        raise DataError(f"Cannot read star names from {source}: {exc}") from exc
    return names


def resolve(names: list[str], path: str | Path | None = None) -> list[SkyObject]:
    """Resolve a subset of common names using the bundled CDS cross-index."""
    source = Path(path) if path else data_path("cross_index.fits")
    wanted = {_clean(name) for name in names}
    resolved: list[SkyObject] = []
    try:
        with fits.open(source) as hdulist:
            rows = hdulist[1].data
            by_hd: dict[int, Any] = {int(row["HD"]): row for row in rows if row["HD"]}
            for entry in hdulist[4].data:
                common = _clean(str(entry["Name"]))
                if common not in wanted:
                    continue
                row = by_hd.get(int(entry["HD"]))
                if row is None:
                    continue
                ra, dec = _coordinates(row)
                resolved.append(
                    SkyObject(
                        name=common,
                        ra=ra,
                        dec=dec,
                        kind="object",
                        attributes={"resolved": True},
                    )
                )
    except (OSError, KeyError, ValueError) as exc:
        raise DataError(f"Cannot resolve names with {source}: {exc}") from exc
    return resolved
