#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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
from PyQt5 import QtWidgets, QtCore, QtGui

logger = logging.getLogger(__name__)


class ScreenshotWindow(QtWidgets.QLabel):
    pix = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screenshot")
        # TODO : self.setWindowIcon(self.app.icon)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.action_original_size = QtWidgets.QAction("Original size")
        self.action_original_size.triggered.connect(lambda: self.setScale(1))
        self.action_2x_size = QtWidgets.QAction("2x size")
        self.action_2x_size.triggered.connect(lambda: self.setScale(2))
        self.action_3x_size = QtWidgets.QAction("3x size")
        self.action_3x_size.triggered.connect(lambda: self.setScale(3))
        self.action_4x_size = QtWidgets.QAction("4x size")
        self.action_4x_size.triggered.connect(lambda: self.setScale(4))
        self.action_5x_size = QtWidgets.QAction("5x size")
        self.action_5x_size.triggered.connect(lambda: self.setScale(5))

        self.addAction(self.action_original_size)
        self.addAction(self.action_2x_size)
        self.addAction(self.action_3x_size)
        self.addAction(self.action_4x_size)
        self.addAction(self.action_5x_size)
        self.action_save_screenshot = QtWidgets.QAction("Save image")
        self.action_save_screenshot.triggered.connect(self.saveScreenshot)
        self.addAction(self.action_save_screenshot)

    def setScreenshot(self, pixmap: QtGui.QPixmap):
        if self.pix is None:
            self.resize(pixmap.size())
        self.pix = pixmap
        self.setPixmap(
            self.pix.scaled(
                self.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.FastTransformation))
        w, h = pixmap.width(), pixmap.height()
        self.action_original_size.setText(
            "Original size (" + str(w) + "x" + str(h) + ")")
        self.action_2x_size.setText(
            "2x size (" + str(w * 2) + "x" + str(h * 2) + ")")
        self.action_3x_size.setText(
            "3x size (" + str(w * 3) + "x" + str(h * 3) + ")")
        self.action_4x_size.setText(
            "4x size (" + str(w * 4) + "x" + str(h * 4) + ")")
        self.action_5x_size.setText(
            "5x size (" + str(w * 5) + "x" + str(h * 5) + ")")

    def saveScreenshot(self):
        if self.pix is not None:
            logger.info("Saving screenshot to file...")
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent=self, caption="Save image",
                filter="PNG (*.png);;All files (*.*)")

            logger.debug("Filename: %s", filename)
            if filename != "":
                self.pixmap().save(filename)
        else:
            logger.warning("The user got shown an empty screenshot window?")

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        if self.pixmap() is not None:
            self.setPixmap(
                self.pix.scaled(
                    self.size(),
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.FastTransformation))

    def setScale(self, scale):
        width, height = (self.pix.size().width() * scale,
                         self.pix.size().height() * scale)
        self.resize(width, height)
