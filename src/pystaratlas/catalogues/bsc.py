from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from astropy.io import fits

from ..errors import DataError
from ..models import SkyObject
from ..resources import data_path

# BSC/CDS designations concatenate a Flamsteed number, a Bayer letter with an
# optional superscript and a constellation abbreviation, with variable padding.
_DESIGNATION = re.compile(
    r"^(?:(\d{1,3}))?\s*([A-Za-z]{2,3}\d{0,2})?\s*([A-Za-z]{2,3})$"
)

_GREEK = {
    "alf": "α",
    "alp": "α",
    "bet": "β",
    "gam": "γ",
    "del": "δ",
    "eps": "ε",
    "zet": "ζ",
    "eta": "η",
    "the": "θ",
    "iot": "ι",
    "kap": "κ",
    "lam": "λ",
    "mu": "μ",
    "mu.": "μ",
    "nu": "ν",
    "nu.": "ν",
    "ksi": "ξ",
    "omi": "ο",
    "pi": "π",
    "pi.": "π",
    "rho": "ρ",
    "sig": "σ",
    "tau": "τ",
    "ups": "υ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "ome": "ω",
}
_SUPERSCRIPTS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _parse(raw: str | bytes) -> tuple[str | None, str | None, str | None] | None:
    match = _DESIGNATION.fullmatch(str(raw).strip())
    if match is None:
        return None
    number, bayer, constellation = match.groups()
    return number, bayer, constellation


def designation(raw: str | bytes) -> str:
    """Decode a BSC/CDS Bayer-Flamsteed field into a readable designation."""
    parsed = _parse(raw)
    if parsed is None:
        return str(raw).strip()
    number, bayer, constellation = parsed
    letter = _GREEK.get(bayer[:3].lower(), "") if bayer else ""
    suffix = bayer[3:].lstrip("0").translate(_SUPERSCRIPTS) if bayer else ""
    return " ".join(part for part in (number, letter + suffix, constellation) if part)


def bayer_designation(raw: str | bytes) -> str:
    """Return just the Greek-letter Bayer designation, if the star has one."""
    parsed = _parse(raw)
    if parsed is None:
        return ""
    _, bayer, constellation = parsed
    if not bayer:
        return ""
    letter = _GREEK.get(bayer[:3].lower(), "")
    if not letter:
        return ""
    suffix = bayer[3:].lstrip("0").translate(_SUPERSCRIPTS)
    return f"{letter}{suffix} {constellation}"


def load(path: str | Path | None = None) -> list[SkyObject]:
    """Read the named stars of the Bright Star Catalogue."""
    source = Path(path) if path else data_path("BSC.fits")
    stars: list[SkyObject] = []
    try:
        with fits.open(source) as hdulist:
            for row in hdulist["catalog"].data:
                raw = str(row["Name"])
                if not raw.strip():
                    continue
                ra = (
                    float(row["RAh"]) + float(row["RAm"]) / 60 + float(row["RAs"]) / 3600
                ) * 15.0
                sign = -1 if str(row["DE-"]).strip() == "-" else 1
                dec = sign * (
                    float(row["DEd"]) + float(row["DEm"]) / 60 + float(row["DEs"]) / 3600
                )
                stars.append(
                    SkyObject(
                        name=designation(raw),
                        ra=ra,
                        dec=dec,
                        magnitude=_optional_float(row["Vmag"]),
                        color_index=_optional_float(row["B-V"]),
                        attributes={
                            "hd": _optional_int(row["HD"]),
                            "hr": _optional_int(row["HR"]),
                            "raw_name": raw.strip(),
                        },
                    )
                )
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise DataError(f"Cannot read Bright Star Catalogue {source}: {exc}") from exc
    return stars


def designations_by_hd(path: str | Path | None = None) -> dict[int, str]:
    """Map HD numbers to their decoded Bright Star Catalogue designations."""
    result: dict[int, str] = {}
    for star in load(path):
        hd = star.attributes.get("hd")
        if hd is not None:
            result[int(hd)] = star.name
    return result


def bayer_designations_by_hd(path: str | Path | None = None) -> dict[int, str]:
    """Map HD numbers to Greek-letter Bayer designations (without Flamsteed numbers)."""
    result: dict[int, str] = {}
    for star in load(path):
        hd = star.attributes.get("hd")
        raw = star.attributes.get("raw_name")
        if hd is not None and isinstance(raw, str):
            name = bayer_designation(raw)
            if name:
                result[int(hd)] = name
    return result


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    number = _optional_float(value)
    return None if number is None else int(number)
