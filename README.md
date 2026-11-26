# pystaratlas

Vector sky maps driven by TOML configuration. A single configuration can be rendered to PDF, SVG, PNG and HTML/CSS.

> Experimental rewrite. The legacy Python 2 scripts are kept temporarily; the new API is in `src/pystaratlas`.

## Install

```bash
pip install pystaratlas
```

## Data

The Hipparcos catalogue is not stored in git. Maintainers can fetch it with:

```bash
python scripts/fetch_hip2.py
```

This writes `src/pystaratlas/resources/data/hip2.dat.gz`.

## Star names

Bright-star labels keep the proper name when the star has one and append its Greek-letter Bayer designation in parentheses, for example `Vega (α Lyr)` and `Rigel (β Ori)`. Stars without a proper name are labelled just by the Bayer designation (`α CMa`). Names come from the bundled Bright Star Catalogue and CDS cross-index. Enable them on a Hipparcos layer:

```toml
[[layers]]
kind = "catalog"
source = "hipparcos"
labels = true
filter = { mag_lt = 7.5, label_mag_lt = 2.5 }
```

`label_mag_lt` selects the brightest named stars to label; the `star-labels` theme style controls their colour and size.

## Deep-sky objects

Most NGC symbols are scaled from the catalogue's largest angular dimension (`size`, in arcminutes), clipped to a readable range in page units. Globular clusters and planetary nebulae instead use a size derived from the projected page scale: larger in detailed fields such as Orion and smaller in all-sky Mollweide maps. Messier, Caldwell and other curated deep-sky objects are read from the bundled `deepspace.fits` catalogue and can be layered with their own labels:

```toml
[[layers]]
kind = "catalog"
source = "deepspace"
labels = true
```

Labels include the Messier or Caldwell designation, for example `Great Nebula In Orion (M42)` and `Hubble's Variable Nebula (C46)`. The `deepspace-markers` and `deepspace-labels` theme styles control their appearance.

## Constellation figures

Constellation stick figures are drawn from the bundled Stellarium `constellationship.fab`, connecting the listed HIP stars along great-circle segments. Missing cross-index positions are filled from Hipparcos. Figures can be styled independently from the constellation boundaries:

```toml
[[layers]]
kind = "constellations"
bounds = true
figures = true
labels = true
```

Use `styles.constellation-figures` for the stick lines and `styles.constellation-bounds` for the lookup boundaries.

A single constellation can be requested by name. The map is centred on it and framed to include the constellations sharing its boundary; the projection centre is filled in automatically:

```toml
[region]
kind = "constellation"
name = "Orión"
```

Full IAU names, common Spanish names and abbreviations (for example `Orion`, `Orión`, `ori`) are accepted. The target constellation is drawn in full; neighbouring constellations may be clipped to fit the canvas. Ready-to-use examples are provided for Orion, Sagittarius, Scorpius and Leo in `examples/*-constellation.toml`.

## Usage

```bash
pystaratlas validate examples/orion.toml
pystaratlas render examples/orion.toml --format pdf,svg,html,png
```

`--format` accepts `pdf`, `svg`, `html` and `png`, and defaults to the formats declared in the configuration. `--out` overrides the output directory. HTML embeds the SVG and writes a sibling CSS file. PNG is rendered at `output.png_scale` times the canvas size (3 by default, range 1–8) to keep labels and symbols sharp.

## Data sources

- Hipparcos new reduction: CDS `I/311` (van Leeuwen, 2007).
- Bright Star Catalogue, NGC/IC, cross-index and deep-space tables: CDS.
- Constellation boundaries and figures: Stellarium project.

See `data/README.txt` for the legacy provenance notes.
