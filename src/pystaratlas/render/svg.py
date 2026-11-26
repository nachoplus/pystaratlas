from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import svgwrite

from ..errors import RenderError
from ..scene import Circle, Polyline, Scene, Symbol, Text

_FONT = "DejaVu Sans, Helvetica, Arial, sans-serif"


class SvgRenderer:
    def __init__(self, scene: Scene):
        self.scene = scene

    def _drawing(self) -> Any:
        drawing = svgwrite.Drawing(
            size=(self.scene.width, self.scene.height),
            viewBox=f"0 0 {self.scene.width} {self.scene.height}",
        )
        drawing.add(
            drawing.rect(
                (0, 0),
                (self.scene.width, self.scene.height),
                fill=self.scene.background,
            )
        )
        for primitive in self.scene.primitives:
            if isinstance(primitive, Circle):
                self._circle(drawing, primitive)
            elif isinstance(primitive, Polyline):
                self._polyline(drawing, primitive)
            elif isinstance(primitive, Text):
                self._text(drawing, primitive)
            elif isinstance(primitive, Symbol):
                self._symbol(drawing, primitive)
        return drawing

    def render_string(self) -> str:
        return str(self._drawing().tostring())

    def render(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.render_string(), encoding="utf-8")
        return target

    def _circle(self, drawing: Any, item: Circle) -> None:
        drawing.add(
            drawing.circle(
                (item.x, self.scene.height - item.y),
                item.radius,
                fill=item.fill,
                stroke=item.stroke,
                opacity=item.opacity,
                class_=f"s-{self.scene.theme.slug(item.style_key)}",
            )
        )

    def _polyline(self, drawing: Any, item: Polyline) -> None:
        if len(item.points) < 2:
            return
        points = [(x, self.scene.height - y) for x, y in item.points]
        drawing.add(
            drawing.polyline(
                points,
                fill="none",
                stroke=item.stroke,
                stroke_width=item.width,
                opacity=item.opacity,
                class_=f"s-{self.scene.theme.slug(item.style_key)}",
            )
        )

    def _symbol(self, drawing: Any, item: Symbol) -> None:
        x, cy, size = item.x, self.scene.height - item.y, item.size
        attrs = {
            "fill": item.fill,
            "stroke": item.stroke,
            "opacity": item.opacity,
            "class_": f"s-{self.scene.theme.slug(item.style_key)}",
        }
        ring = {
            "fill": "none",
            "stroke": item.stroke,
            "stroke_width": 0.9,
            "opacity": item.opacity,
            "class_": attrs["class_"],
        }
        if item.kind == "galaxy":
            drawing.add(drawing.ellipse((x, cy), (size * 0.9, size * 0.45), **ring))
        elif item.kind == "globular":
            drawing.add(drawing.circle((x, cy), size * 1.4, **ring))
            drawing.add(
                drawing.line((x - size * 1.7, cy), (x + size * 1.7, cy), **ring)
            )
            drawing.add(
                drawing.line((x, cy - size * 1.7), (x, cy + size * 1.7), **ring)
            )
        elif item.kind == "open":
            for index in range(12):
                angle = 2 * math.pi * index / 12
                drawing.add(
                    drawing.circle(
                        (
                            x + size * 1.4 * math.cos(angle),
                            cy - size * 1.4 * math.sin(angle),
                        ),
                        size * 0.28,
                        **attrs,
                    )
                )
        elif item.kind == "nebula":
            half = size * 1.2
            drawing.add(
                drawing.rect((x - half, cy - half), (half * 2, half * 2), **ring)
            )
        elif item.kind == "planetary":
            radius = size * 1.4
            points = [
                (x, cy - radius),
                (x + radius, cy),
                (x, cy + radius),
                (x - radius, cy),
            ]
            drawing.add(drawing.polygon(points, **ring))
        elif item.kind == "star":
            drawing.add(
                drawing.line((x - size * 1.6, cy), (x + size * 1.6, cy), **attrs)
            )
            drawing.add(
                drawing.line((x, cy - size * 1.6), (x, cy + size * 1.6), **attrs)
            )
        else:
            drawing.add(drawing.circle((x, cy), size, **attrs))

    def _text(self, drawing: Any, item: Text) -> None:
        label = drawing.text(
            item.value,
            insert=(item.x, self.scene.height - item.y),
            fill=item.fill,
            font_family=_FONT,
            font_size=item.size,
            class_=f"s-{self.scene.theme.slug(item.style_key)}",
        )
        drawing.add(label)


def render(scene: Scene, path: str | Path) -> Path:
    try:
        return SvgRenderer(scene).render(path)
    except OSError as exc:
        raise RenderError(f"Cannot write SVG {path}: {exc}") from exc
