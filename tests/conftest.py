"""
Dummy conftest.py for NanoVNASaver.

If you don't know what this is for, just leave it empty.
Read more about conftest.py under:
- https://docs.pytest.org/en/stable/fixture.html
- https://docs.pytest.org/en/stable/writing_plugins.html
"""

# import pytest

import os
import tempfile

# GUI tests run headless and must never touch the user's real settings.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="nanovna-test-appdata-")
os.environ["XDG_DATA_HOME"] = os.environ["APPDATA"]

from PySide6.QtCore import QSettings  # noqa: E402

QSettings.setPath(
    QSettings.Format.IniFormat,
    QSettings.Scope.UserScope,
    tempfile.mkdtemp(prefix="nanovna-test-settings-"),
)
