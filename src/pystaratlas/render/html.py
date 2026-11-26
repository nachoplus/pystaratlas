from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from jinja2 import Template

from ..errors import RenderError
from ..scene import Scene
from .svg import SvgRenderer

_TEMPLATE = Template(
    """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="{{ css }}">
</head>
<body>
  {{ svg }}
</body>
</html>
"""
)


def _flatten_styles(styles: dict[str, Any], prefix: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    for key, value in styles.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and all(isinstance(item, dict) for item in value.values()):
            yield from _flatten_styles(value, path)
        elif isinstance(value, dict):
            yield path, value


def _css(scene: Scene) -> str:
    lines = [
        "body { margin: 0; background: " + scene.background + "; }",
        "svg { display: block; max-width: 100%; height: auto; }",
    ]
    for key, style in sorted(_flatten_styles(scene.theme.styles)):
        declarations = []
        for prop, value in style.items():
            if prop == "size":
                continue
            name = "stroke-width" if prop == "width" else prop.replace("_", "-")
            declarations.append(f"{name}: {value}")
        if declarations:
            lines.append(f".s-{scene.theme.slug(key)} {{ {'; '.join(declarations)} }}")
    return "\n".join(lines) + "\n"


class HtmlRenderer:
    def __init__(self, scene: Scene, title: str = "pystaratlas"):
        self.scene = scene
        self.title = title

    def render(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        css_path = target.with_suffix(".css")
        try:
            css_path.write_text(_css(self.scene), encoding="utf-8")
            target.write_text(
                _TEMPLATE.render(
                    title=self.title,
                    css=css_path.name,
                    svg=SvgRenderer(self.scene).render_string(),
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            raise RenderError(f"Cannot write HTML {path}: {exc}") from exc
        return target


def render(scene: Scene, path: str | Path, title: str = "pystaratlas") -> Path:
    return HtmlRenderer(scene, title).render(path)
