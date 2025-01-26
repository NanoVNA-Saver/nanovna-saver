from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

from .about import Ui_DialogAbout
from .main_rc import qInitResources

WINDOW_ICON_RES = ":/window/icon_48x48.png"


def get_window_icon() -> QIcon:
    icon = QIcon()
    icon.addFile(WINDOW_ICON_RES, QSize(), QIcon.Mode.Normal, QIcon.State.Off)
    return icon


__all__ = [
    "qInitResources",
    "Ui_DialogAbout",
    "WINDOW_ICON_RES",
    "get_window_icon",
]
