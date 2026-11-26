from pathlib import Path

from pystaratlas.catalogues import hipparcos


def _row(hip: int, ra: float, dec: float, mag: float, bv: float) -> str:
    chars = [" "] * 171
    for start, end, value in [
        (0, 6, f"{hip:6d}"),
        (15, 28, f"{ra:13.10f}"),
        (29, 42, f"{dec:13.10f}"),
        (129, 136, f"{mag:7.4f}"),
        (152, 158, f"{bv:6.3f}"),
    ]:
        chars[start:end] = value.ljust(end - start)[: end - start]
    return "".join(chars) + "\n"


def test_load_fixed_width_rows(tmp_path: Path) -> None:
    source = tmp_path / "hip2.dat"
    source.write_text(
        "HIP Sn So Nc RArad DErad\n"
        + _row(1, 0.1, 0.2, 5.5, 0.6)
        + _row(2, 0.3, -0.4, 9.0, 1.1),
        encoding="ascii",
    )

    stars = hipparcos.load(source)

    assert len(stars) == 2
    assert stars[0].name == "HIP000001"
    assert round(stars[0].ra, 3) == round(0.1 * 180 / 3.141592653589793, 3)
    assert stars[0].magnitude == 5.5
    assert stars[1].color_index == 1.1
