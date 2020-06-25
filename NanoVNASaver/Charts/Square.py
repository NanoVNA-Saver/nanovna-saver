#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020 NanoVNA-Saver Authors
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

from PyQt5 import QtWidgets, QtGui

from NanoVNASaver.Charts.Chart import Chart

logger = logging.getLogger(__name__)


class SquareChart(Chart):
    def __init__(self, name):
        super().__init__(name)
        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.MinimumExpanding)
        self.setSizePolicy(sizepolicy)
        self.chartWidth = self.width()-40
        self.chartHeight = self.height()-40

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if not self.isPopout:
            self.setFixedWidth(a0.size().height())
            self.chartWidth = a0.size().height()-40
            self.chartHeight = a0.size().height()-40
        else:
            min_dimension = min(a0.size().height(), a0.size().width())
            self.chartWidth = self.chartHeight = min_dimension - 40
        self.update()
