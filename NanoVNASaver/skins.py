import logging
import qtpy
# from os.path import join, dirname, abspath
from qtpy.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QCommonStyle
from .skins_utils import DARK_SKIN_COLORED, DARK_SKIN_MONOCHROME, LIGHT_SKIN_COLORED,\
 LIGHT_SKIN_MONOCHROME

logger = logging.getLogger(__name__)


class Skins:
    def dark(app):
        QT_VERSION = tuple(int(v) for v in qtpy.QT_VERSION.split('.'))
        _STYLESHEET = LIGHT_SKIN_MONOCHROME
        darkPalette = QPalette()
        default_style = QCommonStyle()
        # base
        darkPalette.setColor(QPalette.WindowText, QColor(180, 180, 180))
        darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
        darkPalette.setColor(QPalette.Light, QColor(180, 180, 180))
        darkPalette.setColor(QPalette.Midlight, QColor(90, 90, 90))
        darkPalette.setColor(QPalette.Dark, QColor(35, 35, 35))
        darkPalette.setColor(QPalette.Text, QColor(180, 180, 180))
        darkPalette.setColor(QPalette.BrightText, QColor(180, 180, 180))
        darkPalette.setColor(QPalette.ButtonText, QColor(180, 180, 180))
        darkPalette.setColor(QPalette.Base, QColor(42, 42, 42))
        darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
        darkPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
        darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        darkPalette.setColor(QPalette.HighlightedText, QColor(180, 180, 180))
        darkPalette.setColor(QPalette.Link, QColor(56, 252, 196))
        darkPalette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
        darkPalette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
        darkPalette.setColor(QPalette.ToolTipText, QColor(180, 180, 180))

        # disabled
        darkPalette.setColor(QPalette.Disabled, QPalette.WindowText,
                             QColor(127, 127, 127))
        darkPalette.setColor(QPalette.Disabled, QPalette.Text,
                             QColor(127, 127, 127))
        darkPalette.setColor(QPalette.Disabled, QPalette.ButtonText,
                             QColor(127, 127, 127))
        darkPalette.setColor(QPalette.Disabled, QPalette.Highlight,
                             QColor(80, 80, 80))
        darkPalette.setColor(QPalette.Disabled, QPalette.HighlightedText,
                             QColor(127, 127, 127))

        app.setPalette(darkPalette)

        if QT_VERSION < (5,):
            app.setStyle('plastique')
        else:
            app.setStyle('Fusion')

        with open(_STYLESHEET) as stylesheet:
            app.setStyleSheet(stylesheet.read())

    def light(app):
        QT_VERSION = tuple(int(v) for v in qtpy.QT_VERSION.split('.'))
        _STYLESHEET = LIGHT_SKIN_MONOCHROME
        lightPalette = QPalette()
        default_style = QCommonStyle()
        # base
        lightPalette.setColor(QPalette.WindowText, QColor(0, 0, 0))
        lightPalette.setColor(QPalette.Button, QColor(240, 240, 240))
        lightPalette.setColor(QPalette.Light, QColor(180, 180, 180))
        lightPalette.setColor(QPalette.Midlight, QColor(200, 200, 200))
        lightPalette.setColor(QPalette.Dark, QColor(225, 225, 225))
        lightPalette.setColor(QPalette.Text, QColor(0, 0, 0))
        lightPalette.setColor(QPalette.BrightText, QColor(0, 0, 0))
        lightPalette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        lightPalette.setColor(QPalette.Base, QColor(237, 237, 237))
        lightPalette.setColor(QPalette.Window, QColor(240, 240, 240))
        lightPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
        lightPalette.setColor(QPalette.Highlight, QColor(76, 163, 224))
        lightPalette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        lightPalette.setColor(QPalette.Link, QColor(0, 162, 232))
        lightPalette.setColor(QPalette.AlternateBase, QColor(225, 225, 225))
        lightPalette.setColor(QPalette.ToolTipBase, QColor(240, 240, 240))
        lightPalette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))

        # disabled
        lightPalette.setColor(QPalette.Disabled, QPalette.WindowText,
                              QColor(115, 115, 115))
        lightPalette.setColor(QPalette.Disabled, QPalette.Text,
                              QColor(115, 115, 115))
        lightPalette.setColor(QPalette.Disabled, QPalette.ButtonText,
                              QColor(115, 115, 115))
        lightPalette.setColor(QPalette.Disabled, QPalette.Highlight,
                              QColor(190, 190, 190))
        lightPalette.setColor(QPalette.Disabled, QPalette.HighlightedText,
                              QColor(115, 115, 115))

        app.setPalette(lightPalette)

        if QT_VERSION < (5,):
            app.setStyle(default_style)
        else:
            app.setStyle(default_style)

        with open(_STYLESHEET) as stylesheet:
            app.setStyleSheet(stylesheet.read())
