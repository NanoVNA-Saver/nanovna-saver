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
from NanoVNASaver.SITools import Format, Value
from .Frequency import FrequencyChart

logger = logging.getLogger(__name__)


class InductanceChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = 0
        self.maxDisplayValue = 100

        self.minValue = -1
        self.maxValue = 1
        self.span = 1

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name + " (H)")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if not self.fixedSpan:
            if len(self.data) > 0:
                fstart = self.data[0].freq
                fstop = self.data[len(self.data)-1].freq
            else:
                fstart = self.reference[0].freq
                fstop = self.reference[len(self.reference) - 1].freq
            self.fstart = fstart
            self.fstop = fstop
        else:
            fstart = self.fstart = self.minFrequency
            fstop = self.fstop = self.maxFrequency

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue / 10e11
            minValue = self.minDisplayValue / 10e11
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = 1
            maxValue = -1
            for d in self.data:
                val = d.inductiveEquivalent()
                if val > maxValue:
                    maxValue = val
                if val < minValue:
                    minValue = val
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                val = d.inductiveEquivalent()
                if val > maxValue:
                    maxValue = val
                if val < minValue:
                    minValue = val
            self.maxValue = maxValue
            self.minValue = minValue

        span = maxValue - minValue
        if span == 0:
            logger.info("Span is zero for CapacitanceChart, setting to a small value.")
            span = 1e-15
        self.span = span

        target_ticks = math.floor(self.chartHeight / 60)
        fmt = Format(max_nr_digits=1)
        for i in range(target_ticks):
            val = minValue + (i / target_ticks) * span
            y = self.topMargin + round((self.maxValue - val) / self.span * self.chartHeight)
            qp.setPen(self.textColor)
            if val != minValue:
                valstr = str(Value(val, fmt=fmt))
                qp.drawText(3, y + 3, valstr)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth, y)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(Value(maxValue, fmt=fmt)))
        qp.drawText(3, self.chartHeight+self.topMargin, str(Value(minValue, fmt=fmt)))
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        return (self.topMargin +
                round((self.maxValue - d.inductiveEquivalent()) /
                      self.span * self.chartHeight))

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val * 10e11]

    def copy(self):
        new_chart: InductanceChart = super().copy()
        new_chart.span = self.span
        return new_chart
