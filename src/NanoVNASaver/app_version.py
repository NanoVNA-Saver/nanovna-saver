import importlib.metadata

APP_VERSION = "unknown"
try:
    # Change here if project is renamed and does not equal the package name
    APP_VERSION = importlib.metadata.version("NanoVNASaver")
except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    # Looks like we neded this case for apps out of pyinstaller packages
    from ._version import version

    APP_VERSION = version
