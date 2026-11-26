from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..errors import DataError, RenderError
from ..resources import font_path
from ..scene import Circle, Polyline, Scene, Symbol, Text

DEFAULT_SCALE = 3
_FONTS: dict[int, ImageFont.FreeTypeFont] = {}


def _color(value: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
    text = value.lstrip("#")
    if len(text) == 3:
        text = "".join(character * 2 for character in text)
    number = int(text, 16)
    alpha = max(0, min(1, opacity))
    return (number >> 16 & 255, number >> 8 & 255, number & 255, int(alpha * 255))


def _font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _FONTS:
        try:
            _FONTS[size] = ImageFont.truetype(str(font_path("DejaVuSans.ttf")), size)
        except OSError as exc:
            raise DataError(f"Cannot load font for PNG output: {exc}") from exc
    return _FONTS[size]


class PngRenderer:
    def __init__(self, scene: Scene, scale: int = DEFAULT_SCALE):
        if scale < 1:
            raise RenderError("PNG scale must be at least 1")
        self.scene = scene
        self.scale = scale

    def render(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.render_image().save(target, format="PNG")
        except OSError as exc:
            raise RenderError(f"Cannot write PNG {path}: {exc}") from exc
        return target

    def render_image(self) -> Image.Image:
        scale = self.scale
        width = max(1, round(self.scene.width * scale))
        height = max(1, round(self.scene.height * scale))
        image = Image.new("RGBA", (width, height), _color(self.scene.background))
        draw = ImageDraw.Draw(image, "RGBA")
        for item in self.scene.primitives:
            if isinstance(item, Circle):
                self._circle(draw, item)
            elif isinstance(item, Polyline):
                self._polyline(draw, item)
            elif isinstance(item, Symbol):
                self._symbol(draw, item)
            elif isinstance(item, Text):
                self._text(draw, item)
        return image.convert("RGB")

    def _point(self, x: float, y: float) -> tuple[float, float]:
        return x * self.scale, (self.scene.height - y) * self.scale

    def _circle(self, draw: ImageDraw.ImageDraw, item: Circle) -> None:
        x, y = self._point(item.x, item.y)
        radius = item.radius * self.scale
        box = (x - radius, y - radius, x + radius, y + radius)
        if item.fill != "none":
            draw.ellipse(box, fill=_color(item.fill, item.opacity))
        if item.stroke != "none":
            draw.ellipse(
                box,
                outline=_color(item.stroke, item.opacity),
                width=max(1, round(0.9 * self.scale)),
            )

    def _polyline(self, draw: ImageDraw.ImageDraw, item: Polyline) -> None:
        points = [self._point(x, y) for x, y in item.points]
        if len(points) < 2:
            return
        draw.line(
            points,
            fill=_color(item.stroke, item.opacity),
            width=max(1, round(item.width * self.scale)),
            joint="curve",
        )

    def _symbol(self, draw: ImageDraw.ImageDraw, item: Symbol) -> None:
        x, y = self._point(item.x, item.y)
        size = item.size * self.scale
        stroke = _color(item.stroke, item.opacity)
        fill = _color(item.fill, item.opacity)
        outline = max(1, round(0.9 * self.scale))

        if item.kind == "galaxy":
            box = (x - size * 0.9, y - size * 0.45, x + size * 0.9, y + size * 0.45)
            draw.ellipse(box, outline=stroke, width=outline)
        elif item.kind == "globular":
            radius = size * 1.4
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius),
                outline=stroke,
                width=outline,
            )
            self._cross(draw, x, y, size * 1.7, stroke, outline)
        elif item.kind == "open":
            for index in range(12):
                angle = 2 * math.pi * index / 12
                cx = x + size * 1.4 * math.cos(angle)
                cy = y - size * 1.4 * math.sin(angle)
                radius = size * 0.28
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=fill)
        elif item.kind == "nebula":
            half = size * 1.2
            draw.rectangle(
                (x - half, y - half, x + half, y + half), outline=stroke, width=outline
            )
        elif item.kind == "planetary":
            radius = size * 1.4
            points = [(x, y - radius), (x + radius, y), (x, y + radius), (x - radius, y)]
            draw.line(points + [points[0]], fill=stroke, width=outline, joint="curve")
        elif item.kind == "star":
            self._cross(draw, x, y, size * 1.6, stroke, max(1, round(0.8 * self.scale)))
        else:
            draw.ellipse((x - size, y - size, x + size, y + size), fill=fill)

    @staticmethod
    def _cross(
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        radius: float,
        color: tuple[int, int, int, int],
        width: int,
    ) -> None:
        draw.line((x - radius, y, x + radius, y), fill=color, width=width)
        draw.line((x, y - radius, x, y + radius), fill=color, width=width)

    def _text(self, draw: ImageDraw.ImageDraw, item: Text) -> None:
        x, y = self._point(item.x, item.y)
        draw.text(
            (x, y),
            item.value,
            font=_font(max(1, round(item.size * self.scale))),
            fill=_color(item.fill),
            anchor="ls",
        )


def render(scene: Scene, path: str | Path, scale: int = DEFAULT_SCALE) -> Path:
    return PngRenderer(scene, scale).render(path)
