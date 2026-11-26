"""Fetch the Hipparcos new-reduction catalogue from CDS.

Run from the repository root. The SHA-256 is printed so it can be pinned later.
"""

from __future__ import annotations

import argparse
import hashlib
import urllib.request
from pathlib import Path

URL = "https://cdsarc.cds.unistra.fr/ftp/I/311/hip2.dat.gz"
DESTINATION = Path("src/pystaratlas/resources/data/hip2.dat.gz")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha256", help="Fail if the downloaded file does not match this digest")
    args = parser.parse_args()

    with urllib.request.urlopen(URL, timeout=120) as response:
        payload = response.read()
    if len(payload) < 1000 or payload[:2] != b"\x1f\x8b":
        raise SystemExit("Downloaded file does not look like a gzip archive")
    digest = hashlib.sha256(payload).hexdigest()
    if args.sha256 and digest != args.sha256:
        raise SystemExit(f"SHA-256 mismatch: expected {args.sha256}, got {digest}")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_bytes(payload)
    print(f"Wrote {DESTINATION} ({len(payload)} bytes)")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
