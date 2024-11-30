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
import math

from PyQt6 import QtGui

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.LogMag import LogMagChart
from NanoVNASaver.RFTools import Datapoint

logger = logging.getLogger(__name__)


class CombinedLogMagChart(LogMagChart):
    def __init__(self, name=""):
        super().__init__(name)

        self.data11: list[Datapoint] = []
        self.data21: list[Datapoint] = []

        self.reference11: list[Datapoint] = []
        self.reference21: list[Datapoint] = []

    def setCombinedData(self, data11, data21):
        self.data11 = data11
        self.data21 = data21
        self.update()

    def setCombinedReference(self, data11, data21):
        self.reference11 = data11
        self.reference21 = data21
        self.update()

    def resetReference(self):
        self.reference11 = []
        self.reference21 = []
        self.update()

    def resetDisplayLimits(self):
        self.reference11 = []
        self.reference21 = []
        self.update()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(Chart.color.text))
        qp.drawText(
            int(self.dim.width // 2) - 20, 15, f"{self.name} {self.name_unit}"
        )
        qp.drawText(10, 15, "S11")
        qp.drawText(self.leftMargin + self.dim.width - 8, 15, "S21")
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
            self.leftMargin + self.dim.width,
            self.topMargin + self.dim.height,
        )

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data11) == 0 and len(self.reference11) == 0:
            return
        pen = QtGui.QPen(Chart.color.sweep)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(Chart.color.sweep)
        line_pen.setWidth(self.dim.line)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if not self.fixedSpan:
            if len(self.data11) > 0:
                fstart = self.data11[0].freq
                fstop = self.data11[len(self.data11) - 1].freq
            else:
                fstart = self.reference11[0].freq
                fstop = self.reference11[len(self.reference11) - 1].freq
            self.fstart = fstart
            self.fstop = fstop
        else:
            fstart = self.fstart = self.minFrequency
            fstop = self.fstop = self.maxFrequency

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        self.calc_scaling()
        self.draw_grid(qp)

        if self.data11:
            c = QtGui.QColor(Chart.color.sweep)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(33, 9, 38, 9)
            c = QtGui.QColor(Chart.color.sweep_secondary)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(
                self.leftMargin + self.dim.width - 20,
                9,
                self.leftMargin + self.dim.width - 15,
                9,
            )

        if self.reference11:
            c = QtGui.QColor(Chart.color.reference)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(33, 14, 38, 14)
            c = QtGui.QColor(Chart.color.reference_secondary)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(
                self.leftMargin + self.dim.width - 20,
                14,
                self.leftMargin + self.dim.width - 15,
                14,
            )

        self.drawData(qp, self.data11, Chart.color.sweep)
        self.drawData(qp, self.data21, Chart.color.sweep_secondary)
        self.drawData(qp, self.reference11, Chart.color.reference)
        self.drawData(qp, self.reference21, Chart.color.reference_secondary)
        self.drawMarkers(qp, data=self.data11)
        self.drawMarkers(qp, data=self.data21)

    def calc_scaling(self) -> None:
        if self.fixedValues:
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
        else:
            # Find scaling
            minValue = 100
            maxValue = -100
            for d in self.data11 + self.data21:
                logmag = self.logMag(d)
                if math.isinf(logmag):
                    continue
                maxValue = max(maxValue, logmag)
                minValue = min(minValue, logmag)

            for d in self.reference11 + self.reference21:
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                logmag = self.logMag(d)
                if math.isinf(logmag):
                    continue
                maxValue = max(maxValue, logmag)
                minValue = min(minValue, logmag)

            minValue = 10 * math.floor(minValue / 10)
            maxValue = 10 * math.ceil(maxValue / 10)

        self.minValue = minValue
        self.maxValue = maxValue

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        new_chart.data11 = self.data11
        new_chart.data21 = self.data21
        new_chart.reference11 = self.reference11
        new_chart.reference21 = self.reference21
        return new_chart
