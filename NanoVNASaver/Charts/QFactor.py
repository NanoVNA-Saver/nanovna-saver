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
import math
import logging
from typing import List

from PyQt5 import QtWidgets, QtGui

from NanoVNASaver.RFTools import Datapoint
from .Frequency import FrequencyChart

logger = logging.getLogger(__name__)


class QualityFactorChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 35
        self.chartWidth = 250
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.minQ = 0
        self.maxQ = 0
        self.span = 0
        self.minDisplayValue = 0
        self.maxDisplayValue = 100

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawChart(self, qp: QtGui.QPainter):
        super().drawChart(qp)

        # Make up some sensible scaling here
        if self.fixedValues:
            maxQ = self.maxDisplayValue
            minQ = self.minDisplayValue
        else:
            minQ = 0
            maxQ = 0
            for d in self.data:
                Q = d.qFactor()
                if Q > maxQ:
                    maxQ = Q
            scale = 0
            if maxQ > 0:
                scale = max(scale, math.floor(math.log10(maxQ)))
                maxQ = math.ceil(maxQ / 10 ** scale) * 10 ** scale
        self.minQ = minQ
        self.maxQ = maxQ
        self.span = self.maxQ - self.minQ
        if self.span == 0:
            return  # No data to draw the graph from

        tickcount = math.floor(self.chartHeight / 60)

        for i in range(tickcount):
            q = self.minQ + i * self.span / tickcount
            y = self.topMargin + round((self.maxQ - q) / self.span * self.chartHeight)
            if q < 10:
                q = round(q, 2)
            elif q < 20:
                q = round(q, 1)
            else:
                q = round(q)
            qp.setPen(QtGui.QPen(self.textColor))
            qp.drawText(3, y+3, str(q))
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin + self.chartWidth, y)
        qp.drawLine(self.leftMargin - 5,
                    self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        if maxQ < 10:
            qstr = str(round(maxQ, 2))
        elif maxQ < 20:
            qstr = str(round(maxQ, 1))
        else:
            qstr = str(round(maxQ))
        qp.drawText(3, 35, qstr)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        if self.span == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if self.fixedSpan:
            fstart = self.minFrequency
            fstop = self.maxFrequency
        else:
            if len(self.data) > 0:
                fstart = self.data[0].freq
                fstop = self.data[len(self.data)-1].freq
            else:
                fstart = self.reference[0].freq
                fstop = self.reference[len(self.reference) - 1].freq
        self.fstart = fstart
        self.fstop = fstop

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        self.drawFrequencyTicks(qp)
        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        Q = d.qFactor()
        return self.topMargin + round((self.maxQ - Q) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxQ)
        return [val]
