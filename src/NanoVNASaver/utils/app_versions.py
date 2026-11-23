import platform
from functools import cache
from importlib.metadata import PackageNotFoundError, distributions, version

UNKNOWN_VERSION = "unknown"


@cache
def get_app_version() -> str:
    try:
        # Change here if project is renamed and does not equal the package name
        return version("NanoVNASaver")
    except PackageNotFoundError:  # pragma: no cover
        return UNKNOWN_VERSION


@cache
def get_lib_versions() -> list[str]:
    return [f"{dist.name}: {dist.version}" for dist in distributions()]


@cache
def get_host_platform() -> list[str]:
    return [f"Platform: {platform.platform()}", f"CPU: {platform.processor()}"]


def get_runtime_information() -> list[str]:
    return get_host_platform() + get_lib_versions()
