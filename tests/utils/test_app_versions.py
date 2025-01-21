

from NanoVNASaver.utils import get_app_version, get_lib_versions


def test_get_app_version() -> None:
    result = get_app_version()

    assert result
    assert result != "unknown"

def test_get_lib_versions() -> None:
    result1 = get_lib_versions()

    # at least 2xQt, numpy, scipy and NanoVNASaver itself
    assert len(result1) > 6  # noqa: PLR2004
