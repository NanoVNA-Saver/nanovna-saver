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
import logging

from typing import List
import numpy as np

from PyQt5 import QtWidgets, QtGui

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Frequency import FrequencyChart

logger = logging.getLogger(__name__)


class PhaseChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)

        self.minAngle = 0
        self.maxAngle = 0
        self.span = 0
        self.unwrap = False

        self.unwrappedData = []
        self.unwrappedReference = []

        self.minDisplayValue = -180
        self.maxDisplayValue = 180

        self.y_menu.addSeparator()
        self.action_unwrap = QtWidgets.QAction("Unwrap")
        self.action_unwrap.setCheckable(True)
        self.action_unwrap.triggered.connect(
            lambda: self.setUnwrap(self.action_unwrap.isChecked()))
        self.y_menu.addAction(self.action_unwrap)

    def copy(self):
        new_chart = super().copy()
        new_chart.setUnwrap(self.unwrap)
        new_chart.action_unwrap.setChecked(self.unwrap)
        return new_chart

    def setUnwrap(self, unwrap: bool):
        self.unwrap = unwrap
        self.update()

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return

        if self.unwrap:
            rawData = [d.phase for d in self.data]
            rawReference = [d.phase for d in self.reference]
            self.unwrappedData = np.degrees(np.unwrap(rawData))
            self.unwrappedReference = np.degrees(np.unwrap(rawReference))

        if self.fixedValues:
            minAngle = self.minDisplayValue
            maxAngle = self.maxDisplayValue
        elif self.unwrap and self.data:
            minAngle = math.floor(np.min(self.unwrappedData))
            maxAngle = math.ceil(np.max(self.unwrappedData))
        elif self.unwrap and self.reference:
            minAngle = math.floor(np.min(self.unwrappedReference))
            maxAngle = math.ceil(np.max(self.unwrappedReference))
        else:
            minAngle = -180
            maxAngle = 180

        span = maxAngle - minAngle
        if span == 0:
            span = 0.01
        self.minAngle = minAngle
        self.maxAngle = maxAngle
        self.span = span

        tickcount = math.floor(self.dim.height / 60)

        for i in range(tickcount):
            angle = minAngle + span * i / tickcount
            y = self.topMargin + int(
                (self.maxAngle - angle) / self.span * self.dim.height)
            if angle not in [minAngle, maxAngle]:
                qp.setPen(QtGui.QPen(Chart.color.text))
                if angle != 0:
                    digits = max(
                        0, min(2, math.floor(3 - math.log10(abs(angle)))))
                    anglestr = str(round(angle)) if digits == 0 else str(
                        round(angle, digits))
                else:
                    anglestr = "0"
                qp.drawText(3, y + 3, f"{anglestr}°")
                qp.setPen(QtGui.QPen(Chart.color.foreground))
                qp.drawLine(self.leftMargin - 5, y,
                            self.leftMargin + self.dim.width, y)
        qp.drawLine(self.leftMargin - 5,
                    self.topMargin,
                    self.leftMargin + self.dim.width,
                    self.topMargin)
        qp.setPen(Chart.color.text)
        qp.drawText(3, self.topMargin + 5, f"{maxAngle}°")
        qp.drawText(3, self.dim.height + self.topMargin, f"{minAngle}°")

        self._set_start_stop()

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, self.fstart, self.fstop)

        self.drawFrequencyTicks(qp)
        self.drawData(qp, self.data, Chart.color.sweep)
        self.drawData(qp, self.reference, Chart.color.reference)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        if self.unwrap and d in self.data:
            angle = self.unwrappedData[self.data.index(d)]
        elif self.unwrap and d in self.reference:
            angle = self.unwrappedReference[self.reference.index(d)]
        else:
            angle = math.degrees(d.phase)
        return self.topMargin + int(
            (self.maxAngle - angle) / self.span * self.dim.height)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.dim.height * self.span) - self.maxAngle)
        return [val]
