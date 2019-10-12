# Author Carl Tremblay - Cinosh07 AKA VA2SAJ
#  Copyright (C) 2019.  Rune B. Broberg
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import logging
import sys
import qtpy
from qtpy.QtGui import QPalette, QColor
from os.path import join, dirname, abspath, curdir
# from PyQt5.QtWidgets import QCommonStyle
from PyQt5 import QtGui, QtCore

ROOT_DIRECTORY = dirname(dirname(__file__))

logger = logging.getLogger(__name__)

_QT_VERSION = tuple(int(v) for v in qtpy.QT_VERSION.split('.'))

def _DEFAULT_UI():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/default.css'
    else:
        url = join(ROOT_DIRECTORY, "skins\\default.css")
        return url


def _DARK_SKIN_MONOCHROME():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/dark-monochrome.css'
    else:
        url = join(ROOT_DIRECTORY, 'skins\\dark-monochrome.css')
        return url


def _DARK_SKIN_COLORED():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/dark-colored.css'
    else:
        url = join(ROOT_DIRECTORY, 'skins\\dark-colored.css')
        return url


def _LIGHT_SKIN_MONOCHROME():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/light-monochrome.css'
    else:
        url = join(ROOT_DIRECTORY, 'skins\\light-monochrome.css')
        return url


def _LIGHT_SKIN_COLORED():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS + '/skins/light-colored.css'
    else:
        url = join(ROOT_DIRECTORY, 'skins\\light-colored.css')
        return url


_DARK_SKIN_STRING_COLORED = "Dark Colored"
_DARK_SKIN_STRING_MONOCHROME = "Dark"
_LIGHT_SKIN_STRING_COLORED = "Light Colored"
_LIGHT_SKIN_STRING_MONOCHROME = "Light"


def _defaultUI(self):
    with open(_DEFAULT_UI()) as stylesheet:
        self.app.setStyleSheet(stylesheet.read())


def _changeSkin(self, skin):
    if skin == _DARK_SKIN_STRING_COLORED:
        current_skin = _DARK_SKIN_COLORED()
        logger.debug("Skin set to DARK_SKIN_COLORED")
        _dark(self, current_skin)
    if skin == _DARK_SKIN_STRING_MONOCHROME:
        current_skin = _DARK_SKIN_MONOCHROME()
        _dark(self, current_skin)
        logger.debug("Skin set to DARK_SKIN_MONOCHROME")
    if skin == _LIGHT_SKIN_STRING_MONOCHROME:
        current_skin = _LIGHT_SKIN_MONOCHROME()
        _light(self, current_skin)
        logger.debug("Skin set to LIGHT_SKIN_STRING_MONOCHROME")
    if skin == _LIGHT_SKIN_STRING_COLORED:
        current_skin = _LIGHT_SKIN_COLORED()
        _light(self, current_skin)
        logger.debug("Skin set to LIGHT_SKIN_STRING_COLORED")


def _dark(self, cssUrl):

    style = cssUrl
    darkPalette = QPalette()
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

    self.app.setPalette(darkPalette)
    self.app.loadStyle()
    # self.app.setStyle('Fusion')
    # self.app.setStyle('plastique')
    # if _QT_VERSION < (5,):
        # self.app.setStyle('plastique')
    # else:
        # self.app.setStyle('Fusion')

    try:
        with open(style) as stylesheet:
            self.app.setStyleSheet(stylesheet.read())
            for c in self.app.charts:
                c.setBackgroundColor(QtGui.QColor(QtCore.Qt.black))
                c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
                c.setTextColor(QtGui.QColor(QtCore.Qt.white))
            logger.debug("Skin sucessfully set to dark palette")
    except NameError:
      logger.debug("Error loadind css file")




def _light(self, cssUrl):
    style = cssUrl
    lightPalette = QPalette()
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

    self.app.setPalette(lightPalette)
    self.app.loadStyle()
    # self.app.setStyle('Fusion')
    # self.app.setStyle('plastique')
    # if _QT_VERSION < (5,):
    #     self.app.setStyle('plastique')
    # else:
    #     self.app.setStyle('Fusion')

    with open(style) as stylesheet:
        self.app.setStyleSheet(stylesheet.read())
        for c in self.app.charts:
            c.setBackgroundColor(QtGui.QColor(QtCore.Qt.white))
            c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
            c.setTextColor(QtGui.QColor(QtCore.Qt.black))
        logger.debug("Skin sucessfully set to light palette")


def _default(self):
    # TODO Known issue: The app need to be restarted when return to default UI when you change from a skinned UI

    self.app.setStyleSheet("")
    lightPalette = QPalette()
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

    self.app.setPalette(lightPalette)
    self.app.displaySetupWindow.btn_background_picker.setDisabled(True)
    self.app.displaySetupWindow.btn_foreground_picker.setDisabled(True)
    self.app.displaySetupWindow.btn_text_picker.setDisabled(True)

    p = self.app.displaySetupWindow.btn_background_picker.palette()
    p.setColor(QPalette.ButtonText, self.app.displaySetupWindow.backgroundColor)
    self.app.displaySetupWindow.btn_background_picker.setPalette(p)

    p = self.app.displaySetupWindow.btn_foreground_picker.palette()
    p.setColor(QPalette.ButtonText, self.app.displaySetupWindow.foregroundColor)
    self.app.displaySetupWindow.btn_foreground_picker.setPalette(p)

    p = self.app.displaySetupWindow.btn_text_picker.palette()
    p.setColor(QPalette.ButtonText, self.app.displaySetupWindow.textColor)
    self.app.displaySetupWindow.btn_text_picker.setPalette(p)

    p = self.app.displaySetupWindow.btn_bands_picker.palette()
    p.setColor(QPalette.ButtonText, self.app.displaySetupWindow.bandsColor)
    self.app.displaySetupWindow.btn_bands_picker.setPalette(p)

    for c in self.app.charts:
        c.setBackgroundColor(QtGui.QColor(QtCore.Qt.white))
        c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
        c.setTextColor(QtGui.QColor(QtCore.Qt.black))
    # (For future release)
    # default_style = QCommonStyle()
    # app.setStyle(default_style)
    logger.debug("Skin sucessfully set to default palette")


class NanoVNA_UI_Manager():
    def __init__(self, app):
        super().__init__()

        from .NanoVNASaver import NanoVNASaver
        self.app: NanoVNASaver = app

    def getSkins(self):
        return [_DARK_SKIN_STRING_COLORED, _DARK_SKIN_STRING_MONOCHROME, _LIGHT_SKIN_STRING_COLORED, _LIGHT_SKIN_STRING_MONOCHROME]

    def defaultUI(self):
        with open(_DEFAULT_UI()) as stylesheet:
            self.app.setStyleSheet(stylesheet.read())

    def setSkinMode(self):
        _changeSkin(self,  _DARK_SKIN_STRING_COLORED)

    def setDefaultMode(self):
        _default(self)
        _defaultUI(self)
        logger.debug("Skin set to Default")

    def changeSkin(self, skin):
        _changeSkin(self, skin)

    def validateSkin(self, saved_skin):
        if saved_skin is _DARK_SKIN_STRING_COLORED or saved_skin is _DARK_SKIN_STRING_MONOCHROME or  saved_skin is _LIGHT_SKIN_STRING_COLORED or saved_skin is _LIGHT_SKIN_STRING_MONOCHROME:
            return True
        else:
            return False
