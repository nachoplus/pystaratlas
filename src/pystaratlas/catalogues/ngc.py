from __future__ import annotations

from pathlib import Path

from astropy.io import fits

from ..errors import DataError
from ..models import SkyObject
from ..resources import data_path


def _degrees(hours: float, minutes: float) -> float:
    return (hours + minutes / 60.0) * 15.0


def load(path: str | Path | None = None) -> list[SkyObject]:
    source = Path(path) if path else data_path("ngc2000.fits")
    objects: list[SkyObject] = []
    try:
        with fits.open(source) as hdulist:
            names = {
                row["Name"].strip(): row["Object"].strip()
                for row in hdulist[2].data
                if row["Name"] and row["Object"]
            }
            for row in hdulist[1].data:
                ident = row["Name"].strip()
                sign = -1 if row["DE-"].strip() == "-" else 1
                dec = sign * (float(row["DEd"]) + float(row["DEm"]) / 60.0)
                mag = row["mag"]
                size = row["size"]
                objects.append(
                    SkyObject(
                        name=ident,
                        ra=_degrees(float(row["RAh"]), float(row["RAm"])),
                        dec=dec,
                        magnitude=None if mag == 0 else float(mag),
                        kind="ngc",
                        attributes={
                            "type": row["Type"].strip(),
                            "constellation": row["Const"].strip(),
                            "size": None if size == 0 else float(size),
                            "common": names.get(ident, ""),
                        },
                    )
                )
    except (OSError, KeyError, ValueError) as exc:
        raise DataError(f"Cannot read NGC catalogue {source}: {exc}") from exc
    return objects
