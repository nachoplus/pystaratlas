class PystarAtlasError(Exception):
    """Base class for pystaratlas errors."""


class ConfigError(PystarAtlasError):
    """Invalid or unresolved configuration."""


class DataError(PystarAtlasError):
    """Missing or malformed astronomical data."""


class RenderError(PystarAtlasError):
    """A renderer could not produce the requested output."""
