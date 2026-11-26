from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from ..errors import RenderError
from ..resources import font_path
from ..scene import Circle, Polyline, Scene, Symbol, Text

_FONT = "DejaVuSans"


def _register_font() -> None:
    if _FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_FONT, str(font_path("DejaVuSans.ttf"))))


def _color(value: str, opacity: float = 1.0) -> Color:
    color = HexColor(value)
    return Color(color.red, color.green, color.blue, alpha=opacity)


class PdfRenderer:
    def __init__(self, scene: Scene):
        self.scene = scene
        _register_font()

    def render(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        output = canvas.Canvas(str(target), pagesize=(self.scene.width, self.scene.height))
        output.setFillColor(_color(self.scene.background))
        output.rect(0, 0, self.scene.width, self.scene.height, fill=1, stroke=0)
        for primitive in self.scene.primitives:
            if isinstance(primitive, Circle):
                self._circle(output, primitive)
            elif isinstance(primitive, Polyline):
                self._polyline(output, primitive)
            elif isinstance(primitive, Text):
                self._text(output, primitive)
            elif isinstance(primitive, Symbol):
                self._symbol(output, primitive)
        output.showPage()
        output.save()
        return target

    @staticmethod
    def _circle(output: canvas.Canvas, item: Circle) -> None:
        if item.fill != "none":
            output.setFillColor(_color(item.fill, item.opacity))
        if item.stroke != "none":
            output.setStrokeColor(_color(item.stroke, item.opacity))
        output.circle(
            item.x,
            item.y,
            item.radius,
            stroke=1 if item.stroke != "none" else 0,
            fill=1 if item.fill != "none" else 0,
        )

    @staticmethod
    def _polyline(output: canvas.Canvas, item: Polyline) -> None:
        if len(item.points) < 2:
            return
        output.setStrokeColor(_color(item.stroke, item.opacity))
        output.setLineWidth(item.width)
        path = output.beginPath()
        path.moveTo(*item.points[0])
        for point in item.points[1:]:
            path.lineTo(*point)
        output.drawPath(path, stroke=1, fill=0)

    @staticmethod
    def _symbol(output: canvas.Canvas, item: Symbol) -> None:
        x, y, size = item.x, item.y, item.size
        fill = _color(item.fill, item.opacity)
        stroke = _color(item.stroke, item.opacity)
        output.setFillColor(fill)
        output.setStrokeColor(stroke)

        if item.kind == "galaxy":
            output.setLineWidth(0.9)
            output.ellipse(
                x - size * 0.9, y - size * 0.45, x + size * 0.9, y + size * 0.45,
                stroke=1, fill=0,
            )
        elif item.kind == "globular":
            output.setLineWidth(0.9)
            output.circle(x, y, size * 1.4, stroke=1, fill=0)
            output.line(x - size * 1.7, y, x + size * 1.7, y)
            output.line(x, y - size * 1.7, x, y + size * 1.7)
        elif item.kind == "open":
            for index in range(12):
                angle = 2 * math.pi * index / 12
                output.circle(
                    x + size * 1.4 * math.cos(angle),
                    y + size * 1.4 * math.sin(angle),
                    size * 0.28,
                    stroke=0,
                    fill=1,
                )
        elif item.kind == "nebula":
            half = size * 1.2
            output.setLineWidth(0.9)
            output.rect(x - half, y - half, half * 2, half * 2, stroke=1, fill=0)
        elif item.kind == "planetary":
            radius = size * 1.4
            path = output.beginPath()
            path.moveTo(x, y + radius)
            path.lineTo(x + radius, y)
            path.lineTo(x, y - radius)
            path.lineTo(x - radius, y)
            path.close()
            output.setLineWidth(0.9)
            output.drawPath(path, stroke=1, fill=0)
        elif item.kind == "star":
            output.setLineWidth(0.8)
            for dx, dy in ((size * 1.6, 0), (0, size * 1.6)):
                path = output.beginPath()
                path.moveTo(x - dx, y - dy)
                path.lineTo(x + dx, y + dy)
                output.drawPath(path, stroke=1, fill=0)
        else:
            output.circle(x, y, size, stroke=0, fill=1)

    @staticmethod
    def _text(output: canvas.Canvas, item: Text) -> None:
        output.setFillColor(_color(item.fill))
        output.setFont(_FONT, item.size)
        output.drawString(item.x, item.y, item.value)


def render(scene: Scene, path: str | Path) -> Path:
    try:
        return PdfRenderer(scene).render(path)
    except OSError as exc:
        raise RenderError(f"Cannot write PDF {path}: {exc}") from exc
