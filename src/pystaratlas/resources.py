from importlib.resources import files
from pathlib import Path

from .errors import DataError

_ROOT = files("pystaratlas")


def data_path(name: str) -> Path:
    path = Path(str(_ROOT.joinpath("resources", "data", name)))
    if not path.is_file():
        raise DataError(f"Missing bundled data file: {name}")
    return path


def font_path(name: str) -> Path:
    path = Path(str(_ROOT.joinpath("resources", "fonts", name)))
    if not path.is_file():
        raise DataError(f"Missing bundled font: {name}")
    return path
