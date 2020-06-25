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
from .LogMag import LogMagChart

logger = logging.getLogger(__name__)


class SParameterChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = -1
        self.maxDisplayValue = 1
        self.fixedValues = True

        self.y_action_automatic.setChecked(False)
        self.y_action_fixed_span.setChecked(True)

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.isInverted = False

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
        qp.drawText(int(round(self.chartWidth / 2)) - 20, 15, self.name + "")
        qp.drawText(10, 15, "Real")
        qp.drawText(self.leftMargin + self.chartWidth - 15, 15, "Imag")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)

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
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = -1
            maxValue = 1
            self.maxValue = maxValue
            self.minValue = minValue
            # for d in self.data:
            #     val = d.re
            #     if val > maxValue:
            #         maxValue = val
            #     if val < minValue:
            #         minValue = val
            # for d in self.reference:  # Also check min/max for the reference sweep
            #     if d.freq < self.fstart or d.freq > self.fstop:
            #         continue
            #     logmag = self.logMag(d)
            #     if logmag > maxValue:
            #         maxValue = logmag
            #     if logmag < minValue:
            #         minValue = logmag

            # minValue = 10*math.floor(minValue/10)
            # self.minValue = minValue
            # maxValue = 10*math.ceil(maxValue/10)
            # self.maxValue = maxValue

        span = maxValue-minValue
        if span == 0:
            span = 0.01
        self.span = span

        tick_count = math.floor(self.chartHeight / 60)
        tick_step = self.span / tick_count

        for i in range(tick_count):
            val = minValue + i * tick_step
            y = self.topMargin + round((maxValue - val)/span*self.chartHeight)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            if val > minValue and val != maxValue:
                qp.setPen(QtGui.QPen(self.textColor))
                qp.drawText(3, y + 4, str(round(val, 2)))

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.chartHeight+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, self.sweepColor, self.getReYPosition)
        self.drawData(qp, self.reference, self.referenceColor, self.getReYPosition)
        self.drawData(qp, self.data, self.secondarySweepColor, self.getImYPosition)
        self.drawData(qp, self.reference, self.secondaryReferenceColor, self.getImYPosition)
        self.drawMarkers(qp, y_function=self.getReYPosition)
        self.drawMarkers(qp, y_function=self.getImYPosition)

    def getYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.maxValue - d.re) / self.span * self.chartHeight)

    def getReYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.maxValue - d.re) / self.span * self.chartHeight)

    def getImYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.maxValue - d.im) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val]

    def logMag(self, p: Datapoint) -> float:
        if self.isInverted:
            return -p.gain
        return p.gain

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        return new_chart
