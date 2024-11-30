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
from NanoVNASaver.Charts.Frequency import FrequencyChart
from NanoVNASaver.RFTools import Datapoint

logger = logging.getLogger(__name__)


class QualityFactorChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 35
        self.dim.width = 250
        self.dim.height = 250
        self.fstart = 0
        self.fstop = 0
        self.minQ = 0
        self.maxQ = 0
        self.span = 0
        self.minDisplayValue = 0
        self.maxDisplayValue = 100

    def drawChart(self, qp: QtGui.QPainter):
        ROUND_ONE_DIGIT = 20
        ROUND_TWO_DIGITS = 10
        super().drawChart(qp)

        # Make up some sensible scaling here
        if self.fixedValues:
            maxQ = self.maxDisplayValue
        else:
            maxQ = 0
            for d in self.data:
                Q = d.qFactor()
                maxQ = max(maxQ, Q)
            scale = 0
            if maxQ > 0:
                scale = max(scale, math.floor(math.log10(maxQ)))
                maxQ = math.ceil(maxQ / 10**scale) * 10**scale

        self.minQ = self.minDisplayValue
        self.maxQ = maxQ
        self.span = self.maxQ - self.minQ
        if self.span == 0:
            return  # No data to draw the graph from

        tickcount = math.floor(self.dim.height / 60)

        for i in range(tickcount):
            q = self.minQ + i * self.span / tickcount
            y = self.topMargin + int(
                (self.maxQ - q) / self.span * self.dim.height
            )
            if q < ROUND_TWO_DIGITS:
                q = round(q, 2)
            if q < ROUND_ONE_DIGIT:
                q = round(q, 1)
            else:
                q = round(q)
            qp.setPen(QtGui.QPen(Chart.color.text))
            qp.drawText(3, y + 3, str(q))
            qp.setPen(QtGui.QPen(Chart.color.foreground))
            qp.drawLine(
                self.leftMargin - 5, y, self.leftMargin + self.dim.width, y
            )
        qp.drawLine(
            self.leftMargin - 5,
            self.topMargin,
            self.leftMargin + self.dim.width,
            self.topMargin,
        )
        qp.setPen(Chart.color.text)

        if maxQ < ROUND_TWO_DIGITS:
            max_q = round(maxQ, 2)
        elif maxQ < ROUND_ONE_DIGIT:
            max_q = round(maxQ, 1)
        else:
            max_q = round(maxQ)
        qp.drawText(3, 35, f"{max_q}")

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        if self.span == 0:
            return
        pen = QtGui.QPen(Chart.color.sweep)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(Chart.color.sweep)
        line_pen.setWidth(self.dim.line)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)

        self._set_start_stop()

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, self.fstart, self.fstop)

        self.drawFrequencyTicks(qp)
        self.drawData(qp, self.data, Chart.color.sweep)
        self.drawData(qp, self.reference, Chart.color.reference)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        Q = d.qFactor()
        return self.topMargin + int(
            (self.maxQ - Q) / self.span * self.dim.height
        )

    def valueAtPosition(self, y) -> list[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.dim.height * self.span) - self.maxQ)
        return [val]
