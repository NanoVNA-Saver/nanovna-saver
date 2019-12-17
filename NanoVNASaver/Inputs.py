#  NanoVNASaver
#  A python program to view and export Touchstone data from a NanoVNA
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

from PyQt5 import QtGui, QtWidgets, QtCore
from NanoVNASaver.Formatting import format_frequency_inputs


class FrequencyInputWidget(QtWidgets.QLineEdit):
    def __init__(self, text=""):
        super().__init__(text)
        self.nextFrequency = -1
        self.previousFrequency = -1

    def setText(self, text: str) -> None:
        # TODO: Fix wrong type here
        super().setText(format_frequency_inputs(text))


class MarkerFrequencyInputWidget(FrequencyInputWidget):
    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.type() == QtCore.QEvent.KeyPress:
            if a0.key() == QtCore.Qt.Key_Up and self.nextFrequency != -1:
                a0.accept()
                self.setText(str(self.nextFrequency))
                self.textEdited.emit(self.text())
                return
            if a0.key() == QtCore.Qt.Key_Down and self.previousFrequency != -1:
                a0.accept()
                self.setText(str(self.previousFrequency))
                self.textEdited.emit(self.text())
                return
        super().keyPressEvent(a0)
