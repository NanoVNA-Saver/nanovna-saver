# This code is in part copied and inspired from qtmodern library - https://github.com/gmarull/qtmodern
# so original Mit licence is include
# Author Carl Tremblay - Cinosh07 AKA VA2SAJ
# MIT License
#
# Copyright (c) 2017 Gerard Marull-Paretas <gerardmarull@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import logging
import qtpy
from qtpy.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QCommonStyle
from PyQt5 import QtGui, QtCore

logger = logging.getLogger(__name__)


class Skins:
    def dark(app, self, _STYLESHEET):
        QT_VERSION = tuple(int(v) for v in qtpy.QT_VERSION.split('.'))
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

        app.setPalette(darkPalette)

        if QT_VERSION < (5,):
            app.setStyle('plastique')
        else:
            app.setStyle('Fusion')

        with open(_STYLESHEET) as stylesheet:
            app.setStyleSheet(stylesheet.read())
            for c in self.app.charts:
                c.setBackgroundColor(QtGui.QColor(QtCore.Qt.black))
                c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
                c.setTextColor(QtGui.QColor(QtCore.Qt.white))
            logger.debug("Skin sucessfully set to dark palette")

    def light(app, self, _STYLESHEET):
        QT_VERSION = tuple(int(v) for v in qtpy.QT_VERSION.split('.'))
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

        app.setPalette(lightPalette)

        if QT_VERSION < (5,):
            app.setStyle('plastique')
        else:
            app.setStyle('Fusion')

        with open(_STYLESHEET) as stylesheet:
            app.setStyleSheet(stylesheet.read())
            for c in self.app.charts:
                c.setBackgroundColor(QtGui.QColor(QtCore.Qt.white))
                c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
                c.setTextColor(QtGui.QColor(QtCore.Qt.black))
            logger.debug("Skin sucessfully set to light palette")

    def default(app, self):
        # TODO Known issue: The app need to be restarted when return to default UI when you change from a skinned UI
        app.setStyleSheet("")
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

        default_style = QCommonStyle()
        app.setStyle(default_style)
        app.setPalette(lightPalette)

        self.btn_background_picker.setDisabled(True)
        self.btn_foreground_picker.setDisabled(True)
        self.btn_text_picker.setDisabled(True)

        p = self.btn_background_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.backgroundColor)
        self.btn_background_picker.setPalette(p)

        p = self.btn_foreground_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.foregroundColor)
        self.btn_foreground_picker.setPalette(p)

        p = self.btn_text_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.textColor)
        self.btn_text_picker.setPalette(p)

        p = self.btn_bands_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.bandsColor)
        self.btn_bands_picker.setPalette(p)

        for c in self.app.charts:
            c.setBackgroundColor(QtGui.QColor(QtCore.Qt.white))
            c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
            c.setTextColor(QtGui.QColor(QtCore.Qt.black))
        logger.debug("Skin sucessfully set to default palette")
