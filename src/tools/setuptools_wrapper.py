import subprocess

from setuptools import build_meta as _orig
from setuptools.build_meta import *  # Do not remove this line, it's nedded!  # noqa: F403


def compile_ui() -> None:
    protoc_call = ["python", "-m", "src.tools.ui_compile"]
    subprocess.call(protoc_call)


def get_requires_for_build_wheel(config_settings=None):
    compile_ui()
    return _orig.get_requires_for_build_wheel(config_settings)


def get_requires_for_build_sdist(config_settings=None):
    compile_ui()
    return _orig.get_requires_for_build_sdist(config_settings)
