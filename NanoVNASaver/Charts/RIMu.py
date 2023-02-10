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
import math
import numpy as np
import logging
from scipy.constants import mu_0

from PyQt5 import QtWidgets, QtGui

from NanoVNASaver.Formatting import format_frequency_chart
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Charts.Chart import Chart

from .RI import RealImaginaryChart

logger = logging.getLogger(__name__)

MU = "\N{GREEK SMALL LETTER MU}"

class RealImaginaryMuChart(RealImaginaryChart):
    
    def __init__(self, name=""):
        super().__init__(name)
        self.y_menu.addSeparator()

        self.action_set_fixed_maximum_real = QtWidgets.QAction(
            f"Maximum {MU}' ({self.maxDisplayReal})")
        self.action_set_fixed_maximum_real.triggered.connect(
            self.setMaximumRealValue)

        self.action_set_fixed_minimum_real = QtWidgets.QAction(
            f"Minimum {MU}' ({self.minDisplayReal})")
        self.action_set_fixed_minimum_real.triggered.connect(
            self.setMinimumRealValue)

        self.action_set_fixed_maximum_imag = QtWidgets.QAction(
            f"Maximum {MU}'' ({self.maxDisplayImag})")
        self.action_set_fixed_maximum_imag.triggered.connect(
            self.setMaximumImagValue)

        self.action_set_fixed_minimum_imag = QtWidgets.QAction(
            f"Minimum {MU}'' ({self.minDisplayImag})")
        self.action_set_fixed_minimum_imag.triggered.connect(
            self.setMinimumImagValue)
        
        self.y_menu.addAction(self.action_set_fixed_maximum_real)
        self.y_menu.addAction(self.action_set_fixed_minimum_real)
        self.y_menu.addSeparator()
        self.y_menu.addAction(self.action_set_fixed_maximum_imag)
        self.y_menu.addAction(self.action_set_fixed_minimum_imag)

        # Manage core parameters 
        # TODO pick some sane default values?
        self.coreLength = 1.
        self.coreArea = 1.
        self.coreWindings = 1

        self.y_menu.addSeparator()
        self.action_set_core_length = QtWidgets.QAction(
            "Core effective length")
        self.action_set_core_length.triggered.connect(
            self.setCoreLength)

        self.y_menu.addSeparator()
        self.action_set_core_area = QtWidgets.QAction(
            "Core area")
        self.action_set_core_area.triggered.connect(
            self.setCoreArea)

        self.y_menu.addSeparator()
        self.action_set_core_windings = QtWidgets.QAction(
            "Core number of windings")
        self.action_set_core_windings.triggered.connect(
            self.setCoreWindings)

        self.y_menu.addAction(self.action_set_core_length)
        self.y_menu.addAction(self.action_set_core_area)
        self.y_menu.addAction(self.action_set_core_windings)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(Chart.color.text))
        qp.drawText(self.leftMargin + 5, 15,
                    f"{self.name}")
        qp.drawText(5, 15, f"{MU}'")
        qp.drawText(self.leftMargin + self.dim.width + 10, 15, f"{MU}''")
        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(self.leftMargin,
                    self.topMargin - 5,
                    self.leftMargin,
                    self.topMargin + self.dim.height + 5)
        qp.drawLine(self.leftMargin-5,
                    self.topMargin + self.dim.height,
                    self.leftMargin + self.dim.width + 5,
                    self.topMargin + self.dim.height)
        self.drawTitle(qp)

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText(
            f"Start ({format_frequency_chart(self.minFrequency)})")
        self.action_set_fixed_stop.setText(
            f"Stop ({format_frequency_chart(self.maxFrequency)})")
        self.action_set_fixed_minimum_real.setText(
            f"Minimum {MU}' ({self.minDisplayReal})")
        self.action_set_fixed_maximum_real.setText(
            f"Maximum {MU}' ({self.maxDisplayReal})")
        self.action_set_fixed_minimum_imag.setText(
            f"Minimum {MU}'' ({self.minDisplayImag})")
        self.action_set_fixed_maximum_imag.setText(
            f"Maximum {MU}'' ({self.maxDisplayImag})")
        self.menu.exec_(event.globalPos())

    def setCoreLength(self):
        val, selected = QtWidgets.QInputDialog.getDouble(
            self, "Core effective length",
            "Set core effective length in mm", value=self.coreLength,
            decimals=2)
        if not selected:
            return
        if not (self.fixedValues and val >= 0):
            self.coreLength = val
        if self.fixedValues:
            self.update()

    def setCoreArea(self):
        val, selected = QtWidgets.QInputDialog.getDouble(
            self, "Core effective area",
            "Set core cross section area length in mm\N{SUPERSCRIPT TWO}", value=self.coreArea,
            decimals=2)
        if not selected:
            return
        if not (self.fixedValues and val >= 0):
            self.coreArea = val
        if self.fixedValues:
            self.update()

    def setCoreWindings(self):
        val, selected = QtWidgets.QInputDialog.getInt(
            self, "Core number of windings",
            "Set core number of windings", value=self.coreWindings)
        if not selected:
            return
        if not (self.fixedValues and val >= 0):
            self.coreWindings = val
        if self.fixedValues:
            self.update()

    def value(self, p: Datapoint) -> complex:
        return self.mu_r(p)

    def mu_r(self, p: Datapoint) -> complex:
        inductance = np.conj(-1j * p.impedance()/(2*math.pi*p.freq))

        # Core length and core area are in mm and mm2 respectively
        return inductance * (self.coreLength/1e3) / (mu_0 * self.coreWindings**2 * (self.coreArea/1e6))
