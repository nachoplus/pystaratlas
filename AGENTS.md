# Agent notes

This branch (`explerimental`) is the Python 3 rewrite. The Python 2 scripts in the repo root are legacy-only, excluded from lint/typecheck, and must not be extended.

## Commands

- `poetry install`
- `poetry run pytest`
- `poetry run ruff check .`
- `poetry run mypy`
- `poetry build`
- `poetry run pystaratlas validate examples/orion.toml`
- `poetry run pystaratlas render examples/orion.toml --format pdf,svg,html --out build/orion`
- `poetry run pystaratlas render examples/all-sky-mollweide.toml --out build/all-sky-mollweide`

There is no Makefile or task runner; the commands above are the verification pipeline.

## Architecture

- `src/pystaratlas/config.py` validates TOML v1 with Pydantic and resolves local `include` paths.
- `pipeline.build_scene()` converts config + catalogues into backend-independent primitives (`Circle`, `Polyline`, `Text`).
- `render/` contains `pdf`, `svg` and `html` backends; HTML embeds the SVG and writes a sibling CSS file.
- Page coordinates are y-up; SVG flips y at render time.
- `resources.py` loads bundled data/fonts from package resources. Keep catalogue readers by column name, not HDU position.
- Hipparcos is not in git: maintainers run `python scripts/fetch_hip2.py`. The reader expects `hip2.dat.gz` fixed-width CDS `I/311` rows.

## Current scope

- Supported regions: `equatorial` and `constellation` (by full name, Spanish alias or abbreviation; centred on the target with direct neighbours). Other `region.kind` values validate but raise `NotImplementedError`.
- Supported layers: `catalog`, `objects`, `grid`, `constellations`. `ephemeris` and DSS2/imagebook layers are not ported yet.
- Object names are resolved from the bundled cross-index; explicit `[[objects]]` entries need `ra`/`dec` in degrees.
- The legacy root files still document old behaviour but use Python 2 syntax, CWD-relative `./data/...`, global state and network calls in constructors. Do not import them.

## Conventions

- TOML is the only user-facing input format; CLI flags only override config.
- RA/Dec in TOML are degrees; dates are ISO 8601 with timezone.
- Keep data filename spellings: `costellations_bound_20.dat`, `Hiparcos`, `drawEcuatorialGrid` in legacy code.
- Code licence is MIT; data provenance is documented in `README.md`.
