from __future__ import annotations

from pathlib import Path

import click

from . import __version__
from .config import load_map
from .errors import PystarAtlasError
from .pipeline import build_scene
from .render import html, pdf, png, svg

_RENDERERS = {"pdf": pdf.render, "svg": svg.render, "html": html.render, "png": png.render}


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """Generate sky maps from TOML configurations."""


@cli.command()
@click.argument("config", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def validate(config: Path) -> None:
    """Validate a TOML configuration and its includes."""
    spec = load_map(config)
    click.echo(f"OK: {config} ({len(spec.layers)} layers)")


@cli.command()
@click.argument("config", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--format", "format_arg", help="Comma-separated output formats: pdf,svg,html,png"
)
@click.option("--out", type=click.Path(path_type=Path), help="Override output directory")
def render(config: Path, format_arg: str | None, out: Path | None) -> None:
    """Render a configuration to one or more output formats."""
    try:
        spec = load_map(config)
        formats = (
            [item.strip() for item in format_arg.split(",") if item.strip()]
            if format_arg
            else list(spec.output.formats)
        )
        unknown = [item for item in formats if item not in _RENDERERS]
        if unknown:
            raise click.BadParameter(f"unknown format(s): {', '.join(unknown)}")
        output_dir = out or Path(spec.output.dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        scene = build_scene(spec)
        for fmt in formats:
            path = output_dir / f"{spec.name}.{fmt}"
            if fmt == "png":
                target = png.render(scene, path, scale=spec.output.png_scale)
            else:
                target = _RENDERERS[fmt](scene, path)
            click.echo(str(target))
    except PystarAtlasError as exc:
        raise click.ClickException(str(exc)) from exc
    except NotImplementedError as exc:
        raise click.ClickException(str(exc)) from exc
