from importlib.metadata import (
    PackageNotFoundError,
    version,
)

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = "nanovna-saver"
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError
