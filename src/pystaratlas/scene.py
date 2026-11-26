from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .config import ThemeSpec


def _slug(key: str) -> str:
    return key.replace(".", "-").replace("_", "-")


@dataclass(frozen=True, slots=True)
class Circle:
    x: float
    y: float
    radius: float
    style_key: str = "default"
    fill: str = "#000000"
    stroke: str = "none"
    opacity: float = 1.0


@dataclass(frozen=True, slots=True)
class Polyline:
    points: tuple[tuple[float, float], ...]
    style_key: str = "default"
    stroke: str = "#000000"
    width: float = 1.0
    opacity: float = 1.0


@dataclass(frozen=True, slots=True)
class Text:
    x: float
    y: float
    value: str
    size: float = 10.0
    style_key: str = "default"
    fill: str = "#000000"


@dataclass(frozen=True, slots=True)
class Symbol:
    x: float
    y: float
    kind: str
    size: float
    style_key: str = "default"
    fill: str = "#000000"
    stroke: str = "#000000"
    opacity: float = 1.0


Primitive = Circle | Polyline | Text | Symbol


@dataclass(frozen=True, slots=True)
class Theme:
    colors: dict[str, str] = field(default_factory=dict)
    styles: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_spec(cls, spec: ThemeSpec) -> Theme:
        return cls(colors=dict(spec.colors), styles=dict(spec.styles))

    def color(self, key: str, default: str) -> str:
        return self.colors.get(key, default)

    def style(self, key: str) -> dict[str, Any]:
        node: Any = self.styles
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node or not isinstance(node[part], dict):
                return {}
            node = node[part]
        return dict(node)

    @staticmethod
    def slug(key: str) -> str:
        return _slug(key)


@dataclass(frozen=True, slots=True)
class Scene:
    width: float
    height: float
    background: str
    theme: Theme
    primitives: tuple[Primitive, ...] = ()

    def add(self, primitive: Primitive) -> Scene:
        return Scene(self.width, self.height, self.background, self.theme, self.primitives + (primitive,))

    @classmethod
    def of(cls, scene: Scene, primitives: Iterable[Primitive]) -> Scene:
        return Scene(scene.width, scene.height, scene.background, scene.theme, tuple(primitives))
