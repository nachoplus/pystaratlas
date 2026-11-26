from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from astropy.io import fits

from ..errors import DataError
from ..models import SkyObject
from ..resources import data_path


def _text(value: Any) -> str:
    return str(value).strip()


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number == 0 else number


def _coordinates(row: Any) -> tuple[float, float]:
    ra = (float(row["RAh"]) + float(row["RAm"]) / 60) * 15.0
    sign = -1 if _text(row["DE-"]) == "-" else 1
    dec = sign * (float(row["DEd"]) + float(row["DEm"]) / 60)
    return ra, dec


def _label(row: Any) -> str:
    name = _text(row["Name"]).split("/")[0].split(",")[0].strip()
    if re.fullmatch(r"M\s*\d+", name):
        name = ""
    messier, caldwell = _text(row["MESSIER"]), _text(row["CALDWELL"])
    designation = f"M{messier}" if messier else (f"C{caldwell}" if caldwell else "")
    if name and designation:
        return f"{name} ({designation})"
    return designation or name or _text(row["NGC_IC"])


def load(path: str | Path | None = None) -> list[SkyObject]:
    """Read the curated Messier/Caldwell/deep-sky catalogue."""
    source = Path(path) if path else data_path("deepspace.fits")
    records: list[tuple[Any, str]] = []
    try:
        with fits.open(source) as hdulist:
            for row in hdulist[1].data:
                records.append((row, _label(row)))
    except (OSError, KeyError, ValueError) as exc:
        raise DataError(f"Cannot read deep-space catalogue {source}: {exc}") from exc

    duplicates = Counter(label for _, label in records)
    objects: list[SkyObject] = []
    for row, label in records:
        identifier = _text(row["NGC_IC"])
        if duplicates[label] > 1:
            label = f"{label} ({identifier})"
        ra, dec = _coordinates(row)
        objects.append(
            SkyObject(
                name=label,
                ra=ra,
                dec=dec,
                magnitude=_number(row["mag"]),
                kind="deepspace",
                attributes={
                    "identifier": identifier,
                    "messier": _text(row["MESSIER"]),
                    "caldwell": _text(row["CALDWELL"]),
                    "type": _text(row["Type"]),
                    "size": _number(row["size"]),
                    "common": _text(row["Name"]),
                },
            )
        )
    return objects
