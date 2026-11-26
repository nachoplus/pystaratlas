from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SkyObject:
    name: str
    ra: float
    dec: float
    magnitude: float | None = None
    color_index: float | None = None
    kind: str = "star"
    attributes: Mapping[str, Any] = field(default_factory=dict)
