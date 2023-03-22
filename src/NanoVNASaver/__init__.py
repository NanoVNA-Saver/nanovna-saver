import importlib.metadata

try:
    # Change here if project is renamed and does not equal the package name
    __version__ = importlib.metadata.version(distribution_name="nanovna-saver")
except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
