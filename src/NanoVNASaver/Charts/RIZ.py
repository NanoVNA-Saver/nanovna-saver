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

from PyQt6 import QtGui

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Formatting import format_frequency_chart
from NanoVNASaver.RFTools import Datapoint

from .RI import RealImaginaryChart

logger = logging.getLogger(__name__)


class RealImaginaryZChart(RealImaginaryChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.y_menu.addSeparator()

        self.action_set_fixed_maximum_real = QtGui.QAction(
            f"Maximum R ({self.maxDisplayReal})"
        )
        self.action_set_fixed_maximum_real.triggered.connect(
            self.setMaximumRealValue
        )

        self.action_set_fixed_minimum_real = QtGui.QAction(
            f"Minimum R ({self.minDisplayReal})"
        )
        self.action_set_fixed_minimum_real.triggered.connect(
            self.setMinimumRealValue
        )

        self.action_set_fixed_maximum_imag = QtGui.QAction(
            f"Maximum jX ({self.maxDisplayImag})"
        )
        self.action_set_fixed_maximum_imag.triggered.connect(
            self.setMaximumImagValue
        )

        self.action_set_fixed_minimum_imag = QtGui.QAction(
            f"Minimum jX ({self.minDisplayImag})"
        )
        self.action_set_fixed_minimum_imag.triggered.connect(
            self.setMinimumImagValue
        )

        self.y_menu.addAction(self.action_set_fixed_maximum_real)
        self.y_menu.addAction(self.action_set_fixed_minimum_real)
        self.y_menu.addSeparator()
        self.y_menu.addAction(self.action_set_fixed_maximum_imag)
        self.y_menu.addAction(self.action_set_fixed_minimum_imag)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(Chart.color.text))
        qp.drawText(self.leftMargin + 5, 15, f"{self.name} (\N{OHM SIGN})")
        qp.drawText(10, 15, "R")
        qp.drawText(self.leftMargin + self.dim.width + 10, 15, "X")
        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(
            self.leftMargin,
            self.topMargin - 5,
            self.leftMargin,
            self.topMargin + self.dim.height + 5,
        )
        qp.drawLine(
            self.leftMargin - 5,
            self.topMargin + self.dim.height,
            self.leftMargin + self.dim.width + 5,
            self.topMargin + self.dim.height,
        )
        self.drawTitle(qp)

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText(
            f"Start ({format_frequency_chart(self.minFrequency)})"
        )
        self.action_set_fixed_stop.setText(
            f"Stop ({format_frequency_chart(self.maxFrequency)})"
        )
        self.action_set_fixed_minimum_real.setText(
            f"Minimum R ({self.minDisplayReal})"
        )
        self.action_set_fixed_maximum_real.setText(
            f"Maximum R ({self.maxDisplayReal})"
        )
        self.action_set_fixed_minimum_imag.setText(
            f"Minimum jX ({self.minDisplayImag})"
        )
        self.action_set_fixed_maximum_imag.setText(
            f"Maximum jX ({self.maxDisplayImag})"
        )
        self.menu.exec(event.globalPos())

    def value(self, p: Datapoint) -> complex:
        return self.impedance(p)

    def impedance(self, p: Datapoint) -> complex:
        return p.impedance()
