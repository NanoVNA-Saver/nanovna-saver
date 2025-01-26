

from NanoVNASaver.utils import (
    get_app_version,
    get_host_platform,
    get_lib_versions,
    get_runtime_information,
)


def test_get_app_version() -> None:
    result = get_app_version()

    assert result
    assert result != "unknown"

def test_get_lib_versions() -> None:
    result = get_lib_versions()

    # at least 2xQt, numpy, scipy and NanoVNASaver itself
    assert len(result) > 6  # noqa: PLR2004


def test_get_host_platform() -> None:
    result = get_host_platform()

    assert len(result) == 2  # noqa: PLR2004


def test_get_runtime_information() -> None:
    result = get_runtime_information()

    assert len(result) > 8  # noqa: PLR2004
    assert result[0].startswith("Platform: ")
    assert result[1].startswith("CPU: ")
