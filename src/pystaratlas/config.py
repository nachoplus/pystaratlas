from __future__ import annotations

import copy
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import ConfigError


class RegionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["equatorial", "galactic", "ecliptic", "altaz", "constellation", "object"] = "equatorial"
    frame: str = "icrs"
    ra: tuple[float, float] | None = None
    dec: tuple[float, float] | None = None
    name: str | None = None
    names: list[str] = Field(default_factory=list)
    center: tuple[float, float] | None = None
    radius: float | None = None
    city: str | None = None
    date: str | None = None

    @model_validator(mode="after")
    def validate_region(self) -> RegionSpec:
        if self.kind == "equatorial" and (self.ra is None or self.dec is None):
            raise ValueError("equatorial regions require ra and dec")
        if self.kind in {"galactic", "ecliptic"} and (self.ra is None or self.dec is None):
            raise ValueError(f"{self.kind} regions require ra and dec")
        if self.kind == "constellation" and not (self.name or self.names):
            raise ValueError("constellation regions require name or names")
        if self.kind == "object" and (self.center is None or self.radius is None):
            raise ValueError("object regions require center and radius")
        if self.kind == "altaz" and self.city is None:
            raise ValueError("altaz regions require city")
        return self


class ProjectionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proj: str = "moll"
    proj4: str | None = None
    params: dict[str, str | float] = Field(default_factory=dict)

    def to_proj4(self) -> str:
        if self.proj4:
            return self.proj4
        parts = [f"+proj={self.proj}"]
        for key, value in self.params.items():
            parts.append(f"+{key}={value}")
        return " ".join(parts)


class CanvasSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    size: tuple[float, float] = (1200, 800)
    background: str = "#ffffff"

    @property
    def width(self) -> float:
        return self.size[0]

    @property
    def height(self) -> float:
        return self.size[1]


class OutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formats: list[str] = Field(default_factory=lambda: ["pdf"])
    dir: str = "build/map"
    embed_images: bool = False
    png_scale: int = Field(default=3, ge=1, le=8)


class ObserverSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str = "Madrid"
    date: str | None = None


class LayerSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["catalog", "objects", "grid", "constellations", "ephemeris"]
    source: str | None = None
    filter: dict[str, Any] = Field(default_factory=dict)
    names: list[str] = Field(default_factory=list)
    objects: list[dict[str, Any]] = Field(default_factory=list)
    frame: str | None = None
    step: float | None = None
    bodies: list[str] = Field(default_factory=list)
    bounds: bool = False
    figures: bool = False
    labels: bool = False

    @model_validator(mode="after")
    def validate_layer(self) -> LayerSpec:
        if self.kind == "catalog" and not self.source:
            raise ValueError("catalog layers require source")
        return self


class ThemeSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    include: str | None = None
    colors: dict[str, str] = Field(default_factory=dict)
    styles: dict[str, Any] = Field(default_factory=dict)


class MapSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    name: str = "sky-map"
    region: RegionSpec = Field(default_factory=RegionSpec)
    projection: ProjectionSpec = Field(default_factory=ProjectionSpec)
    canvas: CanvasSpec = Field(default_factory=CanvasSpec)
    output: OutputSpec = Field(default_factory=OutputSpec)
    observer: ObserverSpec = Field(default_factory=ObserverSpec)
    theme: ThemeSpec = Field(default_factory=ThemeSpec)
    layers: list[LayerSpec] = Field(default_factory=list)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Cannot read {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _expand_include(node: dict[str, Any], base_dir: Path, stack: tuple[Path, ...]) -> dict[str, Any]:
    if "include" not in node:
        return node
    includes = node.get("include")
    paths = [str(includes)] if isinstance(includes, str) else [str(item) for item in (includes or [])]
    merged: dict[str, Any] = {}
    for raw_path in paths:
        include_path = (base_dir / str(raw_path)).resolve()
        if include_path in stack:
            raise ConfigError(f"TOML include cycle: {include_path}")
        included = _read_toml(include_path)
        included = _expand_include(included, include_path.parent, stack + (include_path,))
        merged = _merge(merged, included)
    local = {key: value for key, value in node.items() if key != "include"}
    return _merge(merged, local)


def load_map(path: str | Path) -> MapSpec:
    """Load and validate a map configuration, resolving local includes."""
    config_path = Path(path).resolve()
    data = _read_toml(config_path)
    data = _expand_include(data, config_path.parent, (config_path,))

    for layer in data.get("layers", []):
        if "include" in layer:
            layer.update(_expand_include(layer, config_path.parent, (config_path,)))

    if "include" in data.get("theme", {}):
        data["theme"] = _expand_include(data["theme"], config_path.parent, (config_path,))

    try:
        return MapSpec.model_validate(data)
    except ValueError as exc:
        raise ConfigError(f"Invalid configuration in {config_path}: {exc}") from exc
