from pathlib import Path

from pystaratlas.render import html, svg
from pystaratlas.scene import Circle, Scene, Theme


def _scene() -> Scene:
    return Scene(
        width=200,
        height=100,
        background="#ffffff",
        theme=Theme(
            styles={
                "stars": {"fill": "#000000"},
                "grid": {"equatorial": {"stroke": "#666666", "width": 0.3}},
            }
        ),
        primitives=(Circle(100, 50, 5, "stars"),),
    )


def test_svg_output(tmp_path: Path) -> None:
    target = svg.render(_scene(), tmp_path / "map.svg")
    content = target.read_text(encoding="utf-8")

    assert "<svg" in content
    assert "s-stars" in content


def test_html_output(tmp_path: Path) -> None:
    target = html.render(_scene(), tmp_path / "map.html")

    assert "<svg" in target.read_text(encoding="utf-8")
    css = target.with_suffix(".css").read_text(encoding="utf-8")
    assert ".s-grid-equatorial" in css
    assert "equatorial: {" not in css
